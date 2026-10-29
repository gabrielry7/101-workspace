"""Sandbox protocol and real commerce ledger boundaries; no external requests."""

import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_payment_durability_m3 import factory as payment_factory
from test_payment_durability_m3 import request
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.errors import InvalidTransitionError, PaymentError
from world_model.restaurant_commerce.models import (
    Order,
    Payment,
    RestaurantCommerceProfile,
    WompiSandboxLookup,
    utcnow,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID
from world_model.restaurant_commerce.service import RestaurantCommerceService
from world_model.restaurant_commerce.wompi_sandbox import NAME, SandboxKeys, WompiSandboxProvider
from world_model.restaurant_commerce.wompi_workflow import enqueue, process, recover

factory = payment_factory

KEYS = SandboxKeys(
    "pub_test_synthetic", "prv_test_synthetic", "test_events_synthetic", "test_integrity_synthetic"
)


def provider(handler):
    return WompiSandboxProvider(
        KEYS,
        business_id=DEMO_BUSINESS_ID,
        return_url="http://127.0.0.1:8765/",
        transport=httpx.MockTransport(handler),
    )


def signature_event(tx, **changes):
    event = {
        "event": "transaction.updated",
        "environment": "test",
        "timestamp": 1700000000,
        "data": {"transaction": dict(tx)},
        "signature": {
            "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
        },
    }
    text = f"{tx['id']}{tx['status']}{tx['amount_in_cents']}{event['timestamp']}{KEYS.events}"
    event["signature"]["checksum"] = hashlib.sha256(text.encode()).hexdigest()
    event.update(changes)
    return event


def setup_order(factory, *, status="APPROVED"):
    response, calls = {}, []

    def handler(req):
        calls.append(req)
        assert str(req.url).startswith("https://sandbox.wompi.co/v1/transactions/")
        assert req.headers["authorization"] == "Bearer " + KEYS.private
        return httpx.Response(200, json={"data": response})

    adapter = provider(handler)
    with factory() as session:
        session.get(RestaurantCommerceProfile, DEMO_BUSINESS_ID).payment_provider = NAME
        session.commit()
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        req = request(svc).model_copy(update={"payment_provider": NAME})
        order = svc.create_order(DEMO_BUSINESS_ID, req)
    response.update(
        merchant={"public_key": KEYS.public},
        id="123-456-test",
        reference=adapter.reference(order.id),
        status=status,
        amount_in_cents=order.total_minor * 100,
        currency="COP",
    )
    return adapter, response, calls, order, req


def test_checkout_pesos_to_cents_and_replay_no_io():
    adapter = provider(lambda _: pytest.fail("checkout must not call provider"))
    kw = dict(
        order_id="order-1",
        public_code="O1",
        amount_minor=32900,
        currency="COP",
        customer_email="private@example.invalid",
        idempotency_key="intent-1",
    )
    checkout = adapter.create_checkout(**kw)
    assert checkout == adapter.create_checkout(**kw)
    q = parse_qs(urlsplit(checkout.checkout_url).query)
    assert q["amount-in-cents"] == ["3290000"]
    assert q["signature:integrity"] == [
        hashlib.sha256(("101sb_order-13290000COP" + KEYS.integrity).encode()).hexdigest()
    ]
    assert "private@example.invalid" not in checkout.checkout_url
    assert KEYS.private not in checkout.checkout_url and KEYS.integrity not in checkout.checkout_url


@pytest.mark.parametrize("field", ["public", "private", "events", "integrity"])
def test_production_keys_rejected(field):
    values = dict(
        public=KEYS.public, private=KEYS.private, events=KEYS.events, integrity=KEYS.integrity
    )
    values[field] = values[field].replace("test", "prod")
    with pytest.raises(ValueError):
        SandboxKeys(**values)
    assert KEYS.private not in repr(KEYS)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/?x=1",
        "https://user:pass@host/",
        "http://external.test/",
        "https://host/#frag",
        "//evil.test/",
    ],
)
def test_return_url_validation(url):
    with pytest.raises(ValueError):
        WompiSandboxProvider(KEYS, business_id="biz", return_url=url)


def test_redirect_not_followed_and_404_unknown():
    calls = []

    def redirect(req):
        calls.append(req)
        return httpx.Response(302, headers={"location": "https://production.wompi.co/v1/x"})

    with pytest.raises(PaymentError):
        provider(redirect).transaction("abc")
    assert len(calls) == 1
    with pytest.raises(PaymentError):
        provider(lambda _: httpx.Response(404)).transaction("abc")


def test_valid_native_signature_unsigned_reference_does_not_authorize():
    adapter = provider(lambda _: pytest.fail("signature verification is local"))
    tx = {"id": "tx-1", "status": "APPROVED", "amount_in_cents": 10000, "reference": "untrusted"}
    event = signature_event(tx)
    assert adapter.verify_event(event) == "tx-1"
    event["data"]["transaction"]["reference"] = "attacker-reference"
    assert adapter.verify_event(event) == "tx-1"
    event["data"]["transaction"]["amount_in_cents"] += 1
    with pytest.raises(ValueError):
        adapter.verify_event(event)
    with pytest.raises(ValueError):
        adapter.verify_event(signature_event(tx, environment="prod"))
    event = signature_event(tx)
    event["signature"]["properties"] = []
    with pytest.raises(ValueError):
        adapter.verify_event(event)


@pytest.mark.parametrize(
    "status,expected", [("APPROVED", "paid"), ("DECLINED", "failed"), ("PENDING", "pending")]
)
def test_persisted_hint_drives_verified_ledger_after_restart(factory, status, expected):
    adapter, tx, calls, order, _ = setup_order(factory, status=status)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
    assert not calls
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        assert recover(svc) == 1
        assert svc.order_out(order.id).payment_status == expected
        assert session.get(WompiSandboxLookup, key).state == (
            "pending" if expected == "pending" else "processed"
        )
        enqueue(svc, tx["id"], order.id)
        process(svc, key)
        assert len(calls) == 1
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        assert session.scalar(select(func.count()).select_from(Payment)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"amount_in_cents": 1},
        {"amount_in_cents": 999900},
        {"currency": "USD"},
        {"reference": "101sb_another-order"},
        {"id": "wrong-id"},
        {"status": "VOIDED"},
    ],
)
def test_forged_or_mismatched_observation_cannot_settle(factory, change):
    adapter, tx, _, order, _ = setup_order(factory)
    transaction_id = tx["id"]
    tx.update(change)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, transaction_id, order.id)
        process(svc, key)
        assert svc.order_out(order.id).payment_status == "pending"
        assert session.get(WompiSandboxLookup, key).state == "review_required"


def test_timeout_preserves_job_and_later_recovers(factory):
    adapter, tx, _, order, _ = setup_order(factory)

    def timeout(_):
        raise httpx.ReadTimeout("synthetic")

    adapter._transport = httpx.MockTransport(timeout)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        process(svc, key)
        row = session.get(WompiSandboxLookup, key)
        assert row.state == "pending" and svc.order_out(order.id).payment_status == "pending"
        row.next_attempt_at = utcnow() - timedelta(seconds=1)
        session.commit()
        adapter._transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"data": tx}))
        recover(svc)
        assert svc.order_out(order.id).payment_status == "paid"


def test_native_webhook_durable_ack_and_authenticated_return(factory):
    adapter, tx, calls, order, req = setup_order(factory)
    app = create_app(
        engine=factory.kw["bind"],
        auto_init_schema=False,
        wompi_sandbox=adapter,
        demo_mode=False,
        payment_recovery_enabled=False,
    )
    with TestClient(app) as client:
        route = f"/api/restaurants/{DEMO_BUSINESS_ID}/orders/recover"
        body = {
            "idempotency_key": req.idempotency_key,
            "recovery_secret": "b" * 64,
            "wompi_transaction_id": tx["id"],
        }
        assert client.post(route, json=body).status_code == 404
        assert not calls
        event = signature_event(tx)
        event["data"]["transaction"]["reference"] = "forged-unsigned-reference"
        response = client.post("/api/webhooks/payments/wompi_sandbox", json=event)
        assert response.status_code == 200 and response.json() == {"status": "accepted"}
        assert not calls
        body["recovery_secret"] = req.recovery_secret
        response = client.post(route, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["payment_status"] == "paid"
        assert len(calls) == 1
        assert client.get("/api/browser-policy").json()["checkout_origins"] == [
            "https://checkout.wompi.co"
        ]
        assert client.post("/api/webhooks/payments/wompi_sandbox", json={}).status_code == 401
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        recover(svc)
        assert svc.order_out(order.id).payment_status == "paid"


def test_production_rejects_sandbox(factory):
    adapter = provider(lambda _: pytest.fail("no HTTP"))
    with pytest.raises(RuntimeError, match="production"):
        create_app(engine=factory.kw["bind"], environment="production", wompi_sandbox=adapter)
    with pytest.raises(RuntimeError, match="production"):
        create_app(
            engine=factory.kw["bind"], environment="production", payment_providers={NAME: adapter}
        )


def test_other_merchant_evidence_is_rejected(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    tx["merchant"]["public_key"] = "pub_test_otherMerchant"
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        process(svc, key)
        assert svc.order_out(order.id).payment_status == "pending"
        assert session.get(WompiSandboxLookup, key).state == "review_required"


def test_multiple_remote_approvals_flag_reconciliation(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        process(svc, enqueue(svc, tx["id"], order.id))
        tx["id"] = "second-approved-transaction"
        process(svc, enqueue(svc, tx["id"], order.id))
        result = svc.order_out(order.id)
        assert result.payment_status == "paid" and result.reconciliation_required
        assert (
            svc.list_payment_reconciliation(DEMO_BUSINESS_ID)[0]["reason"]
            == "multiple_wompi_transactions"
        )


def test_expired_lease_recovers_after_interruption(factory):
    adapter, tx, calls, order, _ = setup_order(factory)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        row = session.get(WompiSandboxLookup, key)
        row.lease_token = "terminated-process"
        row.lease_until = utcnow() + timedelta(seconds=60)
        session.commit()
        assert recover(svc) == 0 and not calls
        row.lease_until = utcnow() - timedelta(seconds=1)
        session.commit()
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        assert recover(svc) == 1
        assert svc.order_out(order.id).payment_status == "paid"


def test_existing_database_requires_explicit_sandbox_upgrade(factory):
    from sqlalchemy import inspect
    from world_model.restaurant_commerce.db import init_schema
    from world_model.restaurant_commerce.migrations import upgrade_wompi_sandbox

    engine = factory.kw["bind"]
    WompiSandboxLookup.__table__.drop(engine)
    init_schema(engine)
    assert WompiSandboxLookup.__tablename__ not in inspect(engine).get_table_names()
    with pytest.raises(RuntimeError, match="offline"):
        create_app(engine=engine, wompi_sandbox=provider(lambda _: pytest.fail("no HTTP")))
    upgrade_wompi_sandbox(engine)
    upgrade_wompi_sandbox(engine)
    assert WompiSandboxLookup.__tablename__ in inspect(engine).get_table_names()


def test_pending_attempt_budget_opens_visible_review(factory):
    adapter, tx, calls, order, _ = setup_order(factory, status="PENDING")
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        key = enqueue(svc, tx["id"], order.id)
        for _attempt in range(12):
            row = session.get(WompiSandboxLookup, key)
            row.next_attempt_at = utcnow() - timedelta(seconds=1)
            session.commit()
            process(svc, key)
        assert len(calls) == 12
        assert session.get(WompiSandboxLookup, key).state == "review_required"
        assert recover(svc) == 0 and len(calls) == 12
        assert svc.order_out(order.id).reconciliation_required


def test_verified_void_after_approval_holds_fulfillment_without_fake_refund(factory):
    adapter, tx, _, order, _ = setup_order(factory)
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        process(svc, enqueue(svc, tx["id"], order.id))
        tx["status"] = "VOIDED"
        key = enqueue(svc, tx["id"], event_key="new-signed-state")
        process(svc, key)
        state = svc.order_out(order.id)
        assert state.payment_status == "paid" and state.reconciliation_required
        assert session.get(WompiSandboxLookup, key).state == "review_required"
        with pytest.raises(InvalidTransitionError, match="reconciliation"):
            svc.transition_order(order.id, "accepted")


def test_cross_business_provider_binding_rejects_order(factory):
    from world_model.restaurant_commerce.errors import ValidationError

    adapter, _, _, _, _ = setup_order(factory)
    adapter.business_id = "another-business"
    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
        req = request(svc).model_copy(update={"payment_provider": NAME})
        with pytest.raises(ValidationError, match="merchant"):
            svc.create_order(DEMO_BUSINESS_ID, req)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Order)) == 1


def test_demo_requires_public_return_url_and_preserves_it(tmp_path):
    import json

    from world_model.restaurant_commerce.wompi_sandbox_demo import application

    path = tmp_path / "keys.json"
    path.write_text(
        json.dumps(
            {
                "WOMPI_PUBLIC_KEY": KEYS.public,
                "WOMPI_PRIVATE_KEY": KEYS.private,
                "WOMPI_EVENTS_SECRET": KEYS.events,
                "WOMPI_INTEGRITY_SECRET": KEYS.integrity,
            }
        )
    )
    path.chmod(0o600)
    target = tmp_path / "demo"
    with pytest.raises(ValueError, match="public HTTPS"):
        application(target, path, 8876)
    for invalid in ("http://example.test/", "https://localhost/", "https://127.0.0.1/"):
        with pytest.raises(ValueError, match="public HTTPS"):
            application(target, path, 8876, return_url=invalid)
    assert not target.exists()
    app = application(target, path, 8876, return_url="https://sandbox.example.test/")
    assert app.state.payment_providers[NAME].return_url == "https://sandbox.example.test/"
    app.state.engine.dispose()
    resumed = application(target, path, 8876, resume=True)
    assert resumed.state.payment_providers[NAME].return_url == "https://sandbox.example.test/"
    resumed.state.engine.dispose()
