"""Adversarial sandbox boundaries. Transport is controlled; ledger and DB are real."""

from datetime import timedelta

import httpx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from test_wompi_sandbox import factory as payment_factory
from test_wompi_sandbox import provider, setup_order, signature_event
from world_model.restaurant_commerce.errors import PaymentError
from world_model.restaurant_commerce.models import (
    Payment,
    WompiSandboxDiscovery,
    WompiSandboxLookup,
    utcnow,
)
from world_model.restaurant_commerce.service import RestaurantCommerceService
from world_model.restaurant_commerce.wompi_sandbox import NAME
from world_model.restaurant_commerce.wompi_workflow import enqueue, process
from world_model.restaurant_commerce.wompi_workflow import recover as discover

factory = payment_factory


def test_exhausted_lookup_outage_is_visible_to_staff(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    adapter._transport = httpx.MockTransport(lambda _: httpx.Response(503))
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        for _ in range(12):
            session.get(WompiSandboxLookup, key).next_attempt_at = utcnow() - timedelta(seconds=1)
            session.commit()
            process(svc, key)
        assert session.get(WompiSandboxLookup, key).state == "review_required"
        assert svc.order_out(order.id).reconciliation_required
        assert (
            svc.list_payment_reconciliation(adapter.business_id)[0]["reason"]
            == "wompi_lookup_exhausted"
        )


def test_no_browser_return_or_webhook_still_discovers_payment(factory):
    from world_model.restaurant_commerce.wompi_workflow import recover

    adapter, tx, calls, order, _ = setup_order(factory)

    def handler(req):
        calls.append(req)
        if req.url.path.endswith("/transactions"):
            assert req.url.params["reference"] == tx["reference"]
            # Listing is only a hint; it has no merchant identity.
            return httpx.Response(
                200, json={"data": [{"id": tx["id"], "reference": tx["reference"]}], "meta": {}}
            )
        return httpx.Response(200, json={"data": tx})

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        assert not session.scalars(select(WompiSandboxLookup)).all()
        session.scalar(select(Payment).where(Payment.order_id == order.id)).created_at = (
            utcnow() - timedelta(minutes=2)
        )
        session.commit()
        recover(svc)
        assert svc.order_out(order.id).payment_status == "paid"
        assert len(calls) == 2


def test_crashes_cannot_bypass_lookup_attempt_budget(factory):
    adapter, tx, calls, order, _ = setup_order(factory)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        # Last process died after its durable claim and before recording any result.
        row = session.get(WompiSandboxLookup, key)
        row.attempts = 12
        row.lease_token = "terminated"
        row.lease_until = utcnow() - timedelta(seconds=1)
        session.commit()
        process(svc, key)
        assert not calls
        assert session.get(WompiSandboxLookup, key).state == "review_required"
        assert svc.order_out(order.id).reconciliation_required


def age_payment(session, order):
    session.scalar(select(Payment).where(Payment.order_id == order.id)).created_at = (
        utcnow() - timedelta(minutes=2)
    )
    session.commit()


@pytest.mark.parametrize(
    "envelope",
    [
        {"data": []},
        {"data": {}},
        {"data": [{"id": "tx", "reference": "101sb_wrong"}]},
        {"data": [{"id": "../escape", "reference": "101sb_order"}]},
        {"data": [], "meta": {"next": "https://other.example"}},
    ],
)
def test_reference_list_never_authorizes_a_payment(envelope):
    adapter = provider(lambda _: httpx.Response(200, json=envelope))
    if envelope == {"data": []}:
        assert adapter.transactions_for_order("order") == []
    else:
        with pytest.raises((ValueError, PaymentError)):
            adapter.transactions_for_order("order")


def test_list_hint_requires_independent_merchant_validation(factory):
    adapter, tx, calls, order, _ = setup_order(factory)

    def handler(req):
        calls.append(req)
        if req.url.path.endswith("/transactions"):
            return httpx.Response(
                200, json={"data": [{"id": tx["id"], "reference": tx["reference"]}]}
            )
        return httpx.Response(
            200, json={"data": {**tx, "merchant": {"public_key": "pub_test_other"}}}
        )

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        age_payment(session, order)
        discover(svc)
        assert len(calls) == 2
        assert svc.order_out(order.id).payment_status == "pending"
        assert session.scalar(select(WompiSandboxLookup)).state == "review_required"


def test_empty_list_budget_does_not_invent_failed_payment(factory):
    adapter, _, _, order, _ = setup_order(factory)
    adapter._transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"data": []}))
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        age_payment(session, order)
        discover(svc)
        row = session.get(WompiSandboxDiscovery, order.id)
        assert row.state == "pending"
        row.attempts = 60
        row.next_attempt_at = utcnow() - timedelta(seconds=1)
        session.commit()
        discover(svc)
        assert row.state == "review_required"
        assert svc.order_out(order.id).payment_status == "pending"
        assert svc.order_out(order.id).reconciliation_required


def test_duplicate_and_conflicting_reference_results_hold_only_one_order(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    ids = ["approved-A", "approved-A", "approved-B"]

    def handler(req):
        if req.url.path.endswith("/transactions"):
            return httpx.Response(
                200, json={"data": [{"id": i, "reference": tx["reference"]} for i in ids]}
            )
        return httpx.Response(200, json={"data": {**tx, "id": req.url.path.rsplit("/", 1)[-1]}})

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        age_payment(session, order)
        discover(svc)
        assert svc.order_out(order.id).payment_status == "paid"
        assert svc.order_out(order.id).reconciliation_required
        assert len(session.scalars(select(Payment)).all()) == 1
        assert len(session.scalars(select(WompiSandboxLookup)).all()) == 2


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=100),
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(st.text(max_size=30), children, max_size=5)
    ),
    max_leaves=20,
)


@settings(max_examples=400, deadline=None, derandomize=True)
@given(json_values)
def test_generated_malformed_events_fail_closed(value):
    adapter = provider(lambda _: pytest.fail("verification must be local"))
    with pytest.raises(ValueError):
        adapter.verify_event(value)


@settings(max_examples=200, deadline=None, derandomize=True)
@given(st.sampled_from(["id", "status", "amount_in_cents"]), json_values)
def test_generated_signed_field_mutations_cannot_forge_a_signature(field, value):
    adapter = provider(lambda _: pytest.fail("verification must be local"))
    tx = {"id": "tx-1", "status": "APPROVED", "amount_in_cents": 10000}
    event = signature_event(tx)
    event["data"]["transaction"][field] = value
    if value == tx[field] and type(value) is type(tx[field]):
        assert adapter.verify_event(event) == tx["id"]
    else:
        with pytest.raises(ValueError):
            adapter.verify_event(event)


def test_discovery_refreshes_exhausted_pending_and_declined_evidence(factory):
    adapter, tx, _, order, _ = setup_order(factory, status="PENDING")
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        row = session.get(WompiSandboxLookup, key)
        row.attempts = 11
        session.commit()
        process(svc, key)
        assert row.state == "review_required"
        age_payment(session, order)
        tx["status"] = "APPROVED"

        def handler(req):
            if req.url.path.endswith("/transactions"):
                return httpx.Response(
                    200, json={"data": [{"id": tx["id"], "reference": tx["reference"]}]}
                )
            return httpx.Response(200, json={"data": tx})

        adapter._transport = httpx.MockTransport(handler)
        discover(svc)
        assert svc.order_out(order.id).payment_status == "paid"
        # Earlier unresolved evidence remains auditable; no automatic hold deletion.
        assert svc.order_out(order.id).reconciliation_required
        assert session.get(WompiSandboxLookup, key).state == "review_required"


def test_discovery_observes_later_attempt_after_decline(factory):
    adapter, tx, _, order, _ = setup_order(factory, status="DECLINED")
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        process(svc, enqueue(svc, tx["id"], order.id))
        assert svc.order_out(order.id).payment_status == "failed"
        age_payment(session, order)
        tx.update(id="second-attempt", status="APPROVED")

        def handler(req):
            if req.url.path.endswith("/transactions"):
                return httpx.Response(
                    200, json={"data": [{"id": tx["id"], "reference": tx["reference"]}]}
                )
            return httpx.Response(200, json={"data": tx})

        adapter._transport = httpx.MockTransport(handler)
        discover(svc)
        # Decline already cancelled/released the order: fresh approval must create
        # an audited financial hold, not silently resurrect fulfilment.
        assert svc.order_out(order.id).payment_status == "failed"
        assert svc.order_out(order.id).reconciliation_required
        assert (
            svc.list_payment_reconciliation(adapter.business_id)[0]["reason"]
            == "contradictory_payment_notification"
        )
        observations = session.scalars(select(WompiSandboxLookup)).all()
        assert any(r.transaction_id == "second-attempt" and r.result_json for r in observations)


def test_verified_amount_conflict_opens_visible_hold(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    tx["amount_in_cents"] += 100
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        process(svc, enqueue(svc, tx["id"], order.id))
        assert svc.order_out(order.id).reconciliation_required
        assert (
            svc.list_payment_reconciliation(adapter.business_id)[0]["reason"]
            == "wompi_payment_mismatch"
        )


def test_discovery_never_queries_transactions_inside_reference_loop(factory):
    from world_model.restaurant_commerce.wompi_discovery import recover as reference_only

    adapter, tx, calls, order, _ = setup_order(factory)

    def handler(req):
        calls.append(req)
        assert req.url.path.endswith("/transactions")
        return httpx.Response(
            200, json={"data": [{"id": str(i), "reference": tx["reference"]} for i in range(19)]}
        )

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        age_payment(session, order)
        reference_only(svc)
        assert len(calls) == 1
        assert len(session.scalars(select(WompiSandboxLookup)).all()) == 19
        assert svc.order_out(order.id).payment_status == "pending"


def test_receiver_ack_loss_replays_durable_receipt_without_duplicate_effect(factory):
    from world_model.restaurant_commerce.wompi_receiver import SandboxReceiver

    adapter, tx, _, order, _ = setup_order(factory)
    event = signature_event(tx)
    checksum = event["signature"]["checksum"]
    calls = []

    def receiver(req):
        calls.append(req)
        assert req.headers["authorization"] == "Bearer " + "a" * 64
        if req.method == "GET":
            return httpx.Response(200, json={"events": [{"id": checksum, "event": event}]})
        # A separate DB session must see receipt before any remote ack attempt.
        with factory() as independent:
            assert len(independent.scalars(select(WompiSandboxLookup)).all()) == 1
        if len(calls) == 2:
            raise httpx.ReadTimeout("ack lost")
        return httpx.Response(200, json={"status": "acknowledged"})

    inbox = SandboxReceiver(
        "https://receiver.test", "a" * 64, transport=httpx.MockTransport(receiver)
    )
    adapter.receiver = inbox
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        discover(svc)  # ack fails; independent existing lookup still settles.
        assert svc.order_out(order.id).payment_status == "paid"
        discover(svc)
        assert len(session.scalars(select(WompiSandboxLookup)).all()) == 1
        assert len(session.scalars(select(Payment)).all()) == 1
        assert len(calls) == 4


def test_receiver_unavailable_does_not_block_reference_discovery(factory):
    from world_model.restaurant_commerce.wompi_receiver import SandboxReceiver

    adapter, tx, _, order, _ = setup_order(factory)
    adapter.receiver = SandboxReceiver(
        "https://receiver.test",
        "a" * 64,
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )

    def handler(req):
        if req.url.path.endswith("/transactions"):
            return httpx.Response(
                200, json={"data": [{"id": tx["id"], "reference": tx["reference"]}]}
            )
        return httpx.Response(200, json={"data": tx})

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        age_payment(session, order)
        discover(svc)
        assert svc.order_out(order.id).payment_status == "paid"


def test_concurrent_duplicate_receipts_settle_once(factory):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    adapter, tx, calls, order, _ = setup_order(factory)

    def handler(req):
        calls.append(req)
        time.sleep(0.05)
        return httpx.Response(200, json={"data": tx})

    adapter._transport = httpx.MockTransport(handler)
    barrier = Barrier(8)

    def submit(_):
        with factory() as session:
            svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
            barrier.wait(timeout=5)
            process(svc, enqueue(svc, tx["id"], order.id))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(submit, range(8)))
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        assert svc.order_out(order.id).payment_status == "paid"
        assert len(calls) == 1
        assert len(session.scalars(select(WompiSandboxLookup)).all()) == 1
        assert len(session.scalars(select(Payment)).all()) == 1


def test_stale_worker_result_is_fenced_after_takeover(factory):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock

    adapter, tx, calls, order, _ = setup_order(factory)
    entered, release, lock = Event(), Event(), Lock()

    def handler(req):
        with lock:
            calls.append(req)
            number = len(calls)
        if number == 1:
            entered.set()
            assert release.wait(timeout=10)
        return httpx.Response(
            200, json={"data": {**tx, "status": "DECLINED" if number == 1 else "APPROVED"}}
        )

    adapter._transport = httpx.MockTransport(handler)
    with factory() as session:
        key = enqueue(
            RestaurantCommerceService(session, payment_providers={NAME: adapter}),
            tx["id"],
            order.id,
        )

    def work():
        with factory() as session:
            process(RestaurantCommerceService(session, payment_providers={NAME: adapter}), key)

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(work)
        try:
            assert entered.wait(timeout=5)
            with factory() as session:
                session.get(WompiSandboxLookup, key).lease_until = utcnow() - timedelta(seconds=1)
                session.commit()
            work()
        finally:
            release.set()
        first.result(timeout=5)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        assert svc.order_out(order.id).payment_status == "paid"
        assert not svc.order_out(order.id).reconciliation_required
        assert len(calls) == 2


def test_external_refund_evidence_holds_without_inventing_local_refund(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        process(svc, enqueue(svc, tx["id"], order.id))
        assert svc.order_out(order.id).payment_status == "paid"
        tx["refunds"] = [{"id": 123, "status": "APPROVED", "amount_in_cents": 10000}]
        process(svc, enqueue(svc, tx["id"], order.id, event_key="refund-observation"))
        state = svc.order_out(order.id)
        assert state.payment_status == "paid"  # No fabricated refund accounting.
        assert state.reconciliation_required
        assert (
            svc.list_payment_reconciliation(adapter.business_id)[0]["reason"]
            == "wompi_provider_review"
        )
        assert (
            svc.list_payment_reconciliation(adapter.business_id)[0]["evidence"]["reason"]
            == "provider_refund_observed"
        )


def test_upgrade_from_previous_sandbox_schema_is_explicit_and_preserves_jobs(factory):
    from sqlalchemy import inspect, text
    from world_model.restaurant_commerce.api import create_app
    from world_model.restaurant_commerce.db import init_schema
    from world_model.restaurant_commerce.migrations import upgrade_wompi_sandbox

    adapter, tx, _, order, _ = setup_order(factory)
    with factory() as session:
        key = enqueue(
            RestaurantCommerceService(session, payment_providers={NAME: adapter}),
            tx["id"],
            order.id,
        )
    engine = factory.kw["bind"]
    WompiSandboxDiscovery.__table__.drop(engine)
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE restaurant_wompi_sandbox_lookups DROP COLUMN single_attempt")
        )
    init_schema(engine)
    assert WompiSandboxDiscovery.__tablename__ not in inspect(engine).get_table_names()
    with pytest.raises(RuntimeError, match="offline"):
        create_app(engine=engine, wompi_sandbox=adapter)
    upgrade_wompi_sandbox(engine)
    upgrade_wompi_sandbox(engine)
    with factory() as session:
        row = session.get(WompiSandboxLookup, key)
        assert row.transaction_id == tx["id"] and row.attempts == 0
        assert row.single_attempt is False
        assert session.scalar(select(Payment)).status == "pending"
