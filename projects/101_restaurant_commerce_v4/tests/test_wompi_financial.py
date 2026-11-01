"""Real commerce ledger with controlled Wompi HTTP evidence; no remote calls."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select
from test_financial_resolution_m3b import principal
from test_wompi_sandbox import factory as factory
from test_wompi_sandbox import setup_order
from world_model.restaurant_commerce.errors import (
    IdempotencyConflictError,
    InvalidTransitionError,
    PaymentError,
    ValidationError,
)
from world_model.restaurant_commerce.models import (
    FinancialAudit,
    FinancialOperation,
    Order,
    PaymentReconciliation,
    utcnow,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService
from world_model.restaurant_commerce.wompi_financial import WompiSandboxFinancialProvider
from world_model.restaurant_commerce.wompi_sandbox import NAME
from world_model.restaurant_commerce.wompi_workflow import enqueue, process


def prepared(factory):
    payment, tx, _, order, _ = setup_order(factory)
    calls = []
    refund = {
        "id": 123,
        "transaction_id": tx["id"],
        "amount_in_cents": tx["amount_in_cents"],
        "status": "APPROVED",
        "is_sandbox": False,
    }

    def handler(req):
        calls.append(req)
        assert req.method == "GET"
        if "/refunds/" in req.url.path:
            return httpx.Response(200, json={"data": refund})
        return httpx.Response(
            200,
            json={
                "data": [{"id": tx["id"], "reference": tx["reference"]}]
                if req.url.path.endswith("/transactions")
                else tx
            },
        )

    payment._transport = httpx.MockTransport(handler)
    adapter = WompiSandboxFinancialProvider(payment)
    with factory() as s:
        svc = RestaurantCommerceService(s, payment_providers={NAME: payment})
        process(svc, enqueue(svc, tx["id"], order.id))
    calls.clear()
    return adapter, tx, refund, order, calls


def service(session, adapter):
    return RestaurantCommerceService(session, financial_providers={NAME: adapter})


def action(svc, order, kind="lookup", key="lookup-one", refund_reference=None):
    return svc.request_financial_operation(
        BID, order.id, kind, key, "Audited test", principal(), refund_reference=refund_reference
    )


def test_write_gate_rejects_without_records_and_lookup_still_works(factory):
    a, _, _, o, calls = prepared(factory)
    with factory() as s:
        svc = service(s, a)

        def counts():
            return [
                s.scalar(select(func.count()).select_from(t))
                for t in (FinancialOperation, FinancialAudit, PaymentReconciliation)
            ]

        before = counts()
        for _ in range(3):
            with pytest.raises(PaymentError):
                action(svc, o, kind="refund")
        assert counts() == before and calls == []
        caps = svc.financial_history(BID, o.id, principal())["capabilities"]
        assert caps["refund"] is False and caps["lookup"] and caps["inspect_refund"]
        result = action(svc, o)
        assert result["state"] == "succeeded" and result["result"]["status"] == "paid"
        assert len(calls) == 2
        assert action(svc, o)["id"] == result["id"] and len(calls) == 2


@pytest.mark.parametrize(
    "flag,amount,status",
    [
        (False, 100, "APPROVED"),
        (None, 100, "APPROVED"),
        (True, None, "APPROVED"),
        (True, 100, "APPROVED"),
        (True, None, "PENDING"),
        (True, None, "DECLINED"),
    ],
)
def test_refund_inspection_is_audited_review_never_money_authority(factory, flag, amount, status):
    a, tx, refund, o, calls = prepared(factory)
    refund.update(is_sandbox=flag, amount_in_cents=amount or tx["amount_in_cents"], status=status)
    with factory() as s:
        svc = service(s, a)
        op = action(svc, o, refund_reference="123")
        assert op["state"] == "review_required"
        assert op["result"]["refund_status"] == status
        assert op["result"]["refund_reference"] == "123"
        assert svc.order_out(o.id).payment_status == "paid"
        history = svc.financial_history(BID, o.id, principal())
        assert len(history["audit"]) == 2 and history["reviews"][0]["status"] == "open"
        with pytest.raises(ValidationError):
            svc.resolve_financial_review(
                BID, o.id, history["reviews"][0]["id"], op["id"], "Resolve", principal()
            )
        with pytest.raises(IdempotencyConflictError):
            action(svc, o, refund_reference="124")
    with factory() as s:
        replay = action(
            service(s, WompiSandboxFinancialProvider(a.payments)), o, refund_reference="123"
        )
        assert replay["id"] == op["id"] and len(calls) == 2


@pytest.mark.parametrize(
    "mutation",
    [
        {"id": 124},
        {"transaction_id": "other-order-tx"},
        {"amount_in_cents": True},
        {"amount_in_cents": 101},
        {"is_sandbox": "true"},
        {"status": "BOGUS"},
    ],
)
def test_malformed_or_foreign_refund_evidence_never_settles(factory, mutation):
    a, _, refund, o, _ = prepared(factory)
    refund.update(mutation)
    with factory() as s:
        svc = service(s, a)
        op = action(svc, o, refund_reference="123")
        assert (
            op["state"] == "review_required"
            and op["result"]["error"] == "invalid_financial_evidence"
        )
        assert svc.order_out(o.id).payment_status == "paid"


def test_other_business_denied_before_provider_calls(factory):
    a, _, _, o, calls = prepared(factory)
    a.business_id = "other-business"
    with factory() as s:
        svc = service(s, a)
        assert svc.financial_history(BID, o.id, principal())["capabilities"]["lookup"] is False
        with pytest.raises(PaymentError):
            action(svc, o)
        assert not calls and not s.scalar(select(FinancialOperation))


def test_bounded_network_retries_and_direct_click_backoff(factory):
    a, _, _, o, calls = prepared(factory)

    def fail(req):
        calls.append(req)
        raise httpx.ReadTimeout("synthetic outage")

    a.payments._transport = httpx.MockTransport(fail)
    with factory() as s:
        svc = service(s, a)
        op = action(svc, o)
        assert op["state"] == "unknown" and len(calls) == 1
        for _ in range(5):
            action(svc, o)
        assert len(calls) == 1
        for attempt in range(2, 7):
            row = s.get(FinancialOperation, op["id"])
            row.next_attempt_at = utcnow() - timedelta(seconds=1)
            s.commit()
            op = svc.process_financial_operation(op["id"])
            assert op["attempts"] == attempt
        assert op["state"] == "review_required" and len(calls) == 6
        assert op["result"]["error"] == "financial_attempt_budget_exhausted"
        svc.recover_financial_operations()
        assert len(calls) == 6


def test_disabled_gate_blocks_a_retained_refund_before_any_remote_io(factory):
    a, _, _, o, calls = prepared(factory)
    with factory() as s:
        svc = service(s, a)
        op = action(svc, o)
        row = s.get(FinancialOperation, op["id"])
        row.kind = "refund"
        row.state = "unknown"
        row.next_attempt_at = utcnow() - timedelta(seconds=1)
        s.commit()
        calls.clear()
        result = svc.process_financial_operation(row.id)
        assert result["state"] == "review_required"
        assert result["result"]["error"] == "refund_submission_disabled" and not calls


def test_refund_evidence_in_payment_lookup_cannot_be_cleared_as_paid(factory):
    a, tx, _, o, _ = prepared(factory)
    tx["refunds"] = [{"status": "APPROVED", "amount_in_cents": 100}]
    with factory() as s:
        svc = service(s, a)
        result = action(svc, o)
        assert result["state"] == "review_required"
        assert result["result"]["review_reason"] == "refund_evidence_requires_review"
        assert svc.order_out(o.id).payment_status == "paid"


def test_uncertain_non_idempotent_refund_is_not_resubmitted_after_restart(factory):
    from test_financial_resolution_m3b import Controlled, refund, setup

    adapter = Controlled()
    adapter.supports_idempotent_refund = False
    adapter.lose_refund = True
    session, svc, _, order = setup(factory, adapter)
    try:
        result = refund(svc, order)
        assert result["state"] == "unknown" and adapter.effects == 1
    finally:
        session.close()
    # Model a provider with no demonstrated lookup-by-idempotency-key contract.
    adapter.lookup_refund = lambda **kwargs: None
    with factory() as session:
        restarted = RestaurantCommerceService(session, financial_providers={"simulated": adapter})
        result = restarted.process_financial_operation(result["id"])
        assert result["state"] == "review_required"
        assert result["result"]["error"] == "refund_replay_unsupported"
        assert adapter.effects == adapter.calls == 1
        assert restarted.order_out(order.id).payment_status == "paid"


def test_paid_lookup_cannot_clear_unresolved_refund_evidence(factory):
    a, _, _, order, _ = prepared(factory)
    with factory() as s:
        svc = service(s, a)
        inspected = action(svc, order, refund_reference="123")
        assert inspected["state"] == "review_required"
        paid = action(svc, order, key="ordinary-paid-lookup")
        assert paid["state"] == "succeeded"
        for review in svc.financial_history(BID, order.id, principal())["reviews"]:
            try:
                svc.resolve_financial_review(
                    BID, order.id, review["id"], paid["id"], "Attempt close", principal()
                )
            except PaymentError:
                s.rollback()
        assert svc.order_out(order.id).reconciliation_required
        with pytest.raises(InvalidTransitionError):
            svc.transition_order(order.id, "accepted")


def test_uniqueness_race_rechecks_refund_reference(factory, monkeypatch):
    a, _, _, order, calls = prepared(factory)
    with factory() as s:
        action(service(s, a), order, refund_reference="123")
    with factory() as s:
        scalar = s.scalar
        missed = False

        def stale_read(statement, *args, **kwargs):
            nonlocal missed
            if not missed and "restaurant_financial_operations.dedupe_key =" in str(statement):
                missed = True
                return None  # Deterministic read-before-concurrent-commit interleaving.
            return scalar(statement, *args, **kwargs)

        monkeypatch.setattr(s, "scalar", stale_read)
        with pytest.raises(IdempotencyConflictError):
            action(service(s, a), order, refund_reference="124")
        assert missed and len(calls) == 2


def test_concurrent_stale_read_cannot_bypass_atomic_retry_due_time(factory):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Event, current_thread

    from sqlalchemy import event

    a, _, _, order, calls = prepared(factory)

    def unavailable(req):
        calls.append(req)
        raise httpx.ReadTimeout("controlled outage")

    a.payments._transport = httpx.MockTransport(unavailable)
    with factory() as s:
        op = action(service(s, a), order)
        s.get(FinancialOperation, op["id"]).next_attempt_at = utcnow() - timedelta(seconds=1)
        s.commit()
        engine = s.get_bind()
    calls.clear()
    ready, finished = Barrier(2), Event()

    def intercept(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.startswith("UPDATE restaurant_financial_operations SET")
            and "attempts=" in statement
        ):
            ready.wait(timeout=10)
            if current_thread().name.endswith("_1"):
                assert finished.wait(timeout=10)

    def attempt():
        try:
            with factory() as s:
                return service(s, a).process_financial_operation(op["id"])
        finally:
            if current_thread().name.endswith("_0"):
                finished.set()

    event.listen(engine, "before_cursor_execute", intercept)
    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="retry") as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]
        assert len(calls) == 1
        assert all(r["attempts"] == 2 for r in results)
    finally:
        event.remove(engine, "before_cursor_execute", intercept)


@pytest.mark.parametrize("refresh_generic", [False, True])
def test_legacy_refund_hold_cannot_be_resolved_by_fresh_paid_lookup(factory, refresh_generic):
    a, _, _, order, _ = prepared(factory)
    with factory() as s:
        svc = service(s, a)
        svc._reconciliation(
            s.get(Order, order.id),
            "wompi_provider_review",
            {"reason": "provider_refund_observed"},
        )
        s.commit()
        paid = action(svc, order)
        review = svc.financial_history(BID, order.id, principal())["reviews"][0]
        assert not review["resolvable"]
        with pytest.raises(PaymentError, match="Unresolved refund evidence"):
            svc.resolve_financial_review(
                BID, order.id, review["id"], paid["id"], "Attempt close", principal()
            )
        assert svc.order_out(order.id).reconciliation_required
        if refresh_generic:
            svc._reconciliation(
                s.get(Order, order.id),
                "wompi_provider_review",
                {"reason": "unsupported_provider_status"},
            )
            s.commit()
            fresh_paid = action(svc, order, key="post-refresh-paid")
            for hold in svc.financial_history(BID, order.id, principal())["reviews"]:
                try:
                    svc.resolve_financial_review(
                        BID, order.id, hold["id"], fresh_paid["id"], "Attempt close", principal()
                    )
                except PaymentError:
                    s.rollback()
            assert svc.order_out(order.id).reconciliation_required


def test_wompi_background_financial_batch_is_bounded(factory):
    a, _, _, order, calls = prepared(factory)

    def unavailable(req):
        calls.append(req)
        raise httpx.ReadTimeout("controlled outage")

    a.payments._transport = httpx.MockTransport(unavailable)
    with factory() as s:
        svc = service(s, a)
        for n in range(3):
            op = action(svc, order, key=f"backlog-{n}")
            s.get(FinancialOperation, op["id"]).next_attempt_at = utcnow() - timedelta(seconds=1)
            s.commit()
        calls.clear()
        assert svc.recover_financial_operations(limit=25) == 1
        assert len(calls) == 1
