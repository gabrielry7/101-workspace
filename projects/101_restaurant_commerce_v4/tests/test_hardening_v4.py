from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from threading import Lock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.cache import TTLCache
from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.deliveries import SimulatedDeliveryProvider
from world_model.restaurant_commerce.enums import DeliveryStatus
from world_model.restaurant_commerce.errors import (
    IdempotencyConflictError,
    InvalidTransitionError,
    PaymentError,
    ProviderCircuitOpenError,
    RetryableProviderError,
)
from world_model.restaurant_commerce.events import CommerceEvent
from world_model.restaurant_commerce.models import (
    CommerceEventOutbox,
    IdempotencyRecord,
    MenuItem,
    Order,
    Payment,
    WebhookReceipt,
)
from world_model.restaurant_commerce.payments import PaymentCheckout, SimulatedPaymentProvider
from world_model.restaurant_commerce.reliability import ProviderExecutor
from world_model.restaurant_commerce.schemas import (
    CartItemIn,
    DeliveryAddressIn,
    CreateOrderRequest,
    CreateReservationRequest,
    CustomerIn,
    ModifierSelectionIn,
)
from world_model.restaurant_commerce.security import sign_webhook
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture()
def engine(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'v4.db'}")
    init_schema(eng)
    Session = session_factory(eng)
    with Session() as s:
        seed_demo(s)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def SessionLocal(engine):
    return session_factory(engine)


@pytest.fixture()
def session(SessionLocal):
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def service(session):
    return RestaurantCommerceService(session)


def cart(service: RestaurantCommerceService, *, quantity: int = 1):
    store = service.storefront(DEMO_BUSINESS_ID)
    smash = next(i for m in store.menus for c in m.categories for i in c.items if i.name == "Smash 101")
    term = next(g for g in smash.modifier_groups if g.name == "Término")
    return [
        CartItemIn(
            menu_item_id=smash.id,
            quantity=quantity,
            modifiers=[ModifierSelectionIn(group_id=term.id, option_ids=[term.options[0].id])],
        )
    ]


def request(service: RestaurantCommerceService, *, idem="v4-idem", phone="3001234567", quantity=1):
    return CreateOrderRequest(
        customer=CustomerIn(name="V4", phone=phone),
        items=cart(service, quantity=quantity),
        idempotency_key=idem,
    )


def destination():
    return DeliveryAddressIn(
        address_line="Calle 85 # 12-34",
        city="Bogotá",
        latitude=4.6697,
        longitude=-74.0549,
    )


def delivery_order(service: RestaurantCommerceService, *, idem="delivery-v4"):
    q = service.create_delivery_quote(DEMO_BUSINESS_ID, destination())
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(
            customer=CustomerIn(name="V4", phone="3001234567"),
            items=cart(service),
            fulfillment_type="delivery",
            delivery_quote_id=q.id,
            idempotency_key=idem,
        ),
    )
    return q, order


# ---------------------------------------------------------------------------
# Boot/security envelope
# ---------------------------------------------------------------------------


def test_production_requires_strong_secrets(engine):
    with pytest.raises(RuntimeError, match="OPERATOR_TOKEN"):
        create_app(engine=engine, environment="production")
    with pytest.raises(RuntimeError, match="at least 32"):
        create_app(engine=engine, environment="production", operator_token="short")
    with pytest.raises(RuntimeError, match="PUBLIC_ACCESS_SECRET"):
        create_app(engine=engine, environment="production", operator_token="x" * 32)
    app = create_app(
        engine=engine,
        environment="production",
        operator_token="o" * 32,
        public_access_secret="p" * 32,
    )
    assert app.state.demo_mode is False


def test_demo_payment_endpoint_absent_in_production(engine):
    app = create_app(
        engine=engine,
        environment="production",
        operator_token="o" * 32,
        public_access_secret="p" * 32,
    )
    r = TestClient(app).post("/api/payments/simulated/whatever/complete")
    assert r.status_code == 404


def test_public_order_and_tracking_require_capability_token(engine):
    app = create_app(engine=engine, seed=False, operator_token="secret")
    client = TestClient(app)
    with session_factory(engine)() as s:
        svc = RestaurantCommerceService(s)
        q = svc.create_delivery_quote(DEMO_BUSINESS_ID, destination())
        payload = CreateOrderRequest(
            customer=CustomerIn(name="API", phone="3009999999"),
            items=cart(svc),
            fulfillment_type="delivery",
            delivery_quote_id=q.id,
            idempotency_key="access-test",
        ).model_dump(mode="json")
    created = client.post(f"/api/restaurants/{DEMO_BUSINESS_ID}/orders", json=payload)
    assert created.status_code == 200, created.text
    body = created.json()
    token = body["access_token"]
    assert token and len(token) == 64
    order_id = body["id"]
    assert client.get(f"/api/orders/{order_id}").status_code == 401
    assert client.get(f"/api/orders/{order_id}", headers={"X-101-Order-Token": "wrong"}).status_code == 401
    assert client.get(f"/api/orders/{order_id}", headers={"X-101-Order-Token": token}).status_code == 200
    assert client.get(f"/api/orders/{order_id}/delivery/tracking").status_code == 401
    tracked = client.get(
        f"/api/orders/{order_id}/delivery/tracking", headers={"X-101-Order-Token": token}
    )
    assert tracked.status_code == 200
    assert "destination_address" not in tracked.json()


def test_security_headers_request_id_and_readiness(engine):
    client = TestClient(create_app(engine=engine, operator_token="secret"))
    r = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "abc-123"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "x-process-time-ms" in r.headers
    assert client.get("/ready").json()["status"] == "ready"


def test_body_size_limit_rejects_before_route(engine):
    app = create_app(engine=engine, operator_token="secret", max_body_bytes=128)
    client = TestClient(app)
    r = client.post(
        f"/api/restaurants/{DEMO_BUSINESS_ID}/orders/quote",
        content=b"x" * 129,
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 413


def test_rate_limit_fails_closed(engine):
    app = create_app(engine=engine, operator_token="secret", rate_limit_per_minute=2)
    client = TestClient(app)
    bad = {"items": []}
    assert client.post(f"/api/restaurants/{DEMO_BUSINESS_ID}/orders/quote", json=bad).status_code == 422
    assert client.post(f"/api/restaurants/{DEMO_BUSINESS_ID}/orders/quote", json=bad).status_code == 422
    third = client.post(f"/api/restaurants/{DEMO_BUSINESS_ID}/orders/quote", json=bad)
    assert third.status_code == 429
    assert int(third.headers["retry-after"]) >= 1


def test_strict_request_models_reject_unknown_fields(service):
    payload = request(service).model_dump()
    payload["admin"] = True
    with pytest.raises(PydanticValidationError):
        CreateOrderRequest.model_validate(payload)


# ---------------------------------------------------------------------------
# Idempotency / external side effects
# ---------------------------------------------------------------------------


def test_same_order_idempotency_replays_without_second_payment_call(session):
    class CountingProvider(SimulatedPaymentProvider):
        def __init__(self):
            self.calls = 0
        def create_checkout(self, **kwargs):
            self.calls += 1
            return super().create_checkout(**kwargs)

    provider = CountingProvider()
    svc = RestaurantCommerceService(session, payment_providers={"simulated": provider})
    req = request(svc, idem="same-body")
    first = svc.create_order(DEMO_BUSINESS_ID, req)
    second = svc.create_order(DEMO_BUSINESS_ID, req)
    assert first.id == second.id
    assert provider.calls == 1


def test_same_order_idempotency_key_different_payload_is_conflict(service):
    first = request(service, idem="conflict-key", quantity=1)
    service.create_order(DEMO_BUSINESS_ID, first)
    changed = request(service, idem="conflict-key", quantity=2)
    with pytest.raises(IdempotencyConflictError):
        service.create_order(DEMO_BUSINESS_ID, changed)


def test_reservation_idempotency_fingerprints_payload(service):
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    req = CreateReservationRequest(
        customer=CustomerIn(name="R", phone="3003333333"),
        starts_at=starts,
        party_size=2,
        idempotency_key="res-key",
    )
    a = service.create_reservation(DEMO_BUSINESS_ID, req)
    b = service.create_reservation(DEMO_BUSINESS_ID, req)
    assert a.id == b.id
    with pytest.raises(IdempotencyConflictError):
        service.create_reservation(DEMO_BUSINESS_ID, req.model_copy(update={"party_size": 3}))


@pytest.mark.parametrize("bad", ["provider", "amount", "currency", "reference", "status"])
def test_untrusted_payment_provider_output_is_validated(session, bad):
    class BadProvider:
        name = "bad"
        def create_checkout(self, **kwargs):
            return PaymentCheckout(
                provider="wrong" if bad == "provider" else self.name,
                provider_reference="" if bad == "reference" else "ref-1",
                amount_minor=kwargs["amount_minor"] + (1 if bad == "amount" else 0),
                currency="USD" if bad == "currency" else kwargs["currency"],
                status="banana" if bad == "status" else "pending",
            )

    from world_model.restaurant_commerce.models import RestaurantCommerceProfile
    profile = session.get(RestaurantCommerceProfile, DEMO_BUSINESS_ID)
    profile.payment_provider = "bad"
    session.commit()
    svc = RestaurantCommerceService(session, payment_providers={"bad": BadProvider()})
    req = request(svc, idem=f"bad-{bad}").model_copy(update={"payment_provider": "bad"})
    with pytest.raises(PaymentError):
        svc.create_order(DEMO_BUSINESS_ID, req)
    assert session.scalar(select(Order).where(Order.idempotency_key == f"bad-{bad}")) is None


def test_provider_executor_retries_only_explicit_retryable_errors():
    exe = ProviderExecutor(failure_threshold=5, max_attempts=3, base_backoff_seconds=0)
    calls = 0
    def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RetryableProviderError("temporary")
        return "ok"
    assert exe.call("p", "op", flaky) == "ok"
    assert calls == 3

    calls2 = 0
    def unknown():
        nonlocal calls2
        calls2 += 1
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        exe.call("q", "op", unknown)
    assert calls2 == 1


def test_provider_executor_circuit_breaker_opens():
    exe = ProviderExecutor(failure_threshold=2, max_attempts=1, recovery_seconds=30, base_backoff_seconds=0)
    def fail():
        raise RetryableProviderError("down")
    with pytest.raises(RetryableProviderError):
        exe.call("p", "quote", fail)
    with pytest.raises(RetryableProviderError):
        exe.call("p", "quote", fail)
    with pytest.raises(ProviderCircuitOpenError):
        exe.call("p", "quote", lambda: "should-not-run")
    assert exe.snapshot()["p:quote"]["open"] is True


# ---------------------------------------------------------------------------
# Durable events / state machines / webhooks
# ---------------------------------------------------------------------------


def test_event_sink_failure_does_not_rollback_order_and_is_retryable(session):
    class FailingSink:
        def __init__(self):
            self.fail = True
            self.events: list[CommerceEvent] = []
        def publish(self, event):
            if self.fail:
                raise RuntimeError("sink down")
            self.events.append(event)

    sink = FailingSink()
    svc = RestaurantCommerceService(session, event_sink=sink)
    order = svc.create_order(DEMO_BUSINESS_ID, request(svc, idem="outbox-test"))
    assert session.get(Order, order.id) is not None
    row = session.scalar(select(CommerceEventOutbox).where(CommerceEventOutbox.entity_id == order.id))
    assert row is not None and row.status == "pending" and row.publish_attempts == 1
    sink.fail = False
    stats = svc.drain_event_outbox()
    assert stats == {"attempted": 1, "published": 1, "failed": 0}
    session.refresh(row)
    assert row.status == "published"
    assert len(sink.events) == 1


def test_payment_state_machine_does_not_allow_paid_to_failed(service):
    order = service.create_order(DEMO_BUSINESS_ID, request(service, idem="pay-state"))
    ref = order.payments[0].provider_reference
    paid = service.apply_payment_status(ref, "paid")
    replay = service.apply_payment_status(ref, "paid")
    assert replay.status == paid.status
    with pytest.raises(InvalidTransitionError):
        service.apply_payment_status(ref, "failed")


def test_paid_order_requires_refund_before_cancel(service):
    order = service.create_order(DEMO_BUSINESS_ID, request(service, idem="refund-first"))
    ref = order.payments[0].provider_reference
    service.apply_payment_status(ref, "paid")
    with pytest.raises(InvalidTransitionError, match="refund"):
        service.transition_order(order.id, "cancelled")
    service.apply_payment_status(ref, "refunded")
    assert service.transition_order(order.id, "cancelled").status == "cancelled"


def test_cash_at_pickup_can_progress_and_becomes_paid_on_completion(service):
    req = request(service, idem="cash-flow").model_copy(update={"payment_provider": "cash_at_pickup"})
    order = service.create_order(DEMO_BUSINESS_ID, req)
    assert order.status == "placed" and order.payment_status == "pending"
    for state in ["accepted", "preparing", "ready", "completed"]:
        order = service.transition_order(order.id, state)
    assert order.status == "completed" and order.payment_status == "paid"
    assert order.payments[0].status == "paid"


def test_reservation_terminal_state_cannot_escape(service):
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    r = service.create_reservation(
        DEMO_BUSINESS_ID,
        CreateReservationRequest(customer=CustomerIn(name="R", phone="3004444444"), starts_at=starts, party_size=2),
    )
    service.transition_reservation(r.id, "cancelled")
    with pytest.raises(InvalidTransitionError):
        service.transition_reservation(r.id, "confirmed")


def test_signed_payment_webhook_is_authenticated_and_idempotent(engine):
    secret = "webhook-secret"
    app = create_app(engine=engine, operator_token="secret", webhook_secrets={"simulated": secret})
    client = TestClient(app)
    with session_factory(engine)() as s:
        svc = RestaurantCommerceService(s)
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc, idem="webhook-pay"))
        ref = order.payments[0].provider_reference
    payload = {
        "event_id": "evt-pay-1",
        "provider_reference": ref,
        "status": "paid",
        "amount_minor": order.total_minor,
        "currency": "COP",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    assert client.post("/api/webhooks/payments/simulated", content=raw, headers={"content-type": "application/json"}).status_code == 401
    sig = sign_webhook(secret, raw)
    ok = client.post("/api/webhooks/payments/simulated", content=raw, headers={"content-type": "application/json", "X-101-Webhook-Signature": sig})
    assert ok.status_code == 200
    replay = client.post("/api/webhooks/payments/simulated", content=raw, headers={"content-type": "application/json", "X-101-Webhook-Signature": sig})
    assert replay.status_code == 200
    tampered = {**payload, "status": "failed"}
    raw2 = json.dumps(tampered, separators=(",", ":")).encode()
    conflict = client.post("/api/webhooks/payments/simulated", content=raw2, headers={"content-type": "application/json", "X-101-Webhook-Signature": sign_webhook(secret, raw2)})
    assert conflict.status_code == 409
    with session_factory(engine)() as s:
        assert s.scalar(select(WebhookReceipt).where(WebhookReceipt.event_id == "evt-pay-1")) is not None


def test_delivery_webhook_out_of_order_event_cannot_rewind(session):
    svc = RestaurantCommerceService(session)
    _, order = delivery_order(svc, idem="delivery-stale")
    order = svc.apply_payment_status(order.payments[0].provider_reference, "paid")
    svc.transition_order(order.id, "accepted")
    delivery = svc.dispatch_delivery(order.id)
    svc.transition_order(order.id, "preparing")
    svc.transition_order(order.id, "ready")
    now = datetime.now(timezone.utc)
    picked = svc.apply_delivery_status(
        delivery.provider_delivery_reference,
        "picked_up",
        event_id="fresh",
        occurred_at=now,
    )
    assert picked.status == "picked_up"
    stale = svc.apply_delivery_status(
        delivery.provider_delivery_reference,
        "courier_assigned",
        event_id="old",
        occurred_at=now - timedelta(minutes=5),
    )
    assert stale.status == "picked_up"


def test_delivery_completion_atomically_completes_order_and_awards_once(session):
    svc = RestaurantCommerceService(session)
    _, order = delivery_order(svc, idem="delivery-atomic")
    svc.apply_payment_status(order.payments[0].provider_reference, "paid")
    svc.transition_order(order.id, "accepted")
    d = svc.dispatch_delivery(order.id)
    svc.transition_order(order.id, "preparing")
    svc.transition_order(order.id, "ready")
    svc.apply_delivery_status(d.provider_delivery_reference, "picked_up", event_id="pickup-atomic")
    svc.apply_delivery_status(d.provider_delivery_reference, "delivered", event_id="delivered-atomic")
    final = svc.order_out(order.id)
    assert final.status == "completed"
    # replay cannot double-complete / double-award
    svc.apply_delivery_status(d.provider_delivery_reference, "delivered", event_id="delivered-replay")
    assert svc.order_out(order.id).status == "completed"


# ---------------------------------------------------------------------------
# DB integrity / performance shape
# ---------------------------------------------------------------------------


def test_sqlite_foreign_keys_and_wal_are_enabled(engine):
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert str(conn.execute(text("PRAGMA journal_mode")).scalar_one()).lower() == "wal"
        assert int(conn.execute(text("PRAGMA busy_timeout")).scalar_one()) >= 30000


def test_database_constraint_rejects_negative_menu_price(session):
    item = session.scalar(select(MenuItem).limit(1))
    item.base_price_minor = -1
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def count_selects(engine, fn):
    count = 0
    lock = Lock()
    def before(*_):
        nonlocal count
        with lock:
            count += 1
    event.listen(engine, "before_cursor_execute", before)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return count, result


def test_storefront_shared_cache_removes_second_db_read(engine, SessionLocal):
    cache = TTLCache(ttl_seconds=60)
    with SessionLocal() as s:
        svc = RestaurantCommerceService(s, storefront_cache=cache)
        first_count, first = count_selects(engine, lambda: svc.storefront(DEMO_BUSINESS_ID))
        second_count, second = count_selects(engine, lambda: svc.storefront(DEMO_BUSINESS_ID))
    assert first.display_name == second.display_name
    assert first_count > 0
    assert second_count == 0


def test_quote_query_count_is_bounded_for_larger_cart(engine, SessionLocal):
    with SessionLocal() as s:
        svc = RestaurantCommerceService(s)
        one = cart(svc)[0]
        # Same menu item repeated 40 times; query shape must remain bounded.
        large = [one.model_copy(update={"quantity": 1}) for _ in range(40)]
        queries, result = count_selects(engine, lambda: svc.quote(DEMO_BUSINESS_ID, large))
    assert len(result.items) == 40
    assert queries <= 12


def test_metrics_endpoint_is_operator_only(engine):
    app = create_app(engine=engine, operator_token="metrics-secret")
    client = TestClient(app)
    client.get("/health")
    assert client.get("/api/operator/metrics").status_code == 401
    r = client.get("/api/operator/metrics", headers={"X-101-Operator-Token": "metrics-secret"})
    assert r.status_code == 200
    body = r.json()
    assert "http" in body and "provider_circuits" in body and "storefront_cache_entries" in body


def test_concurrent_identical_order_calls_provider_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    import time

    class SlowCountingProvider(SimulatedPaymentProvider):
        def __init__(self):
            self.calls = 0
            self.lock = Lock()

        def create_checkout(self, **kwargs):
            with self.lock:
                self.calls += 1
            time.sleep(0.03)
            return super().create_checkout(**kwargs)

    eng = make_engine(f"sqlite:///{tmp_path / 'concurrency.db'}")
    init_schema(eng)
    Sessions = session_factory(eng)
    with Sessions() as s:
        seed_demo(s)
        base = RestaurantCommerceService(s)
        req = request(base, idem="CONCURRENT-SAME")

    provider = SlowCountingProvider()

    def submit(_):
        with Sessions() as s:
            svc = RestaurantCommerceService(s, payment_providers={"simulated": provider})
            try:
                return ("ok", svc.create_order(DEMO_BUSINESS_ID, req).id)
            except IdempotencyConflictError:
                return ("conflict", None)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, range(8)))

    assert sum(kind == "ok" for kind, _ in results) == 1
    assert sum(kind == "conflict" for kind, _ in results) == 7
    assert provider.calls == 1
    with Sessions() as s:
        assert s.scalar(select(Order).where(Order.idempotency_key == "CONCURRENT-SAME")) is not None
    eng.dispose()


def test_production_defaults_exclude_simulated_providers(engine):
    app = create_app(
        engine=engine,
        environment="production",
        operator_token="o" * 32,
        public_access_secret="p" * 32,
    )
    assert "simulated" not in app.state.payment_providers
    assert "simulated_delivery" not in app.state.delivery_providers
    assert "wompi" in app.state.payment_providers
    assert "uber_direct" in app.state.delivery_providers
