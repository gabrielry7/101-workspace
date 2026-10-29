"""Durability, fencing and reconciliation invariants, on SQLite and optional private PG."""

import hashlib
import json
import os
import time
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.errors import (
    IdempotencyConflictError,
    NotFoundError,
    PaymentError,
)
from world_model.restaurant_commerce.models import (
    CommerceEventOutbox,
    Order,
    Payment,
    PaymentIntent,
    PaymentNotificationInbox,
    PaymentReconciliation,
    utcnow,
)
from world_model.restaurant_commerce.payment_workflow import CheckoutRecoveryExpired
from world_model.restaurant_commerce.payments import SimulatedPaymentProvider
from world_model.restaurant_commerce.schemas import (
    CreateOrderRequest,
    PaymentNotificationAccepted,
    PaymentWebhookIn,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture
def factory(tmp_path):
    url = os.environ.get("COMMERCE_PAYMENT_TEST_DATABASE_URL")
    admin = schema = None
    if url:
        from sqlalchemy.engine import make_url

        assert make_url(url).host in {"127.0.0.1", "localhost", "::1"}, (
            "Disposable loopback PostgreSQL only"
        )
        admin = make_engine(url)
        schema = "m3_payment_" + uuid4().hex
        with admin.begin() as conn:
            conn.execute(text("CREATE SCHEMA " + schema))
        engine = make_engine(url)

        @event.listens_for(engine, "connect")
        def search_path(connection, _record):
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO " + schema)
            connection.commit()
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'payment.db'}")
    init_schema(engine)
    sessions = session_factory(engine)
    with sessions() as session:
        seed_demo(session)
    try:
        yield sessions
    finally:
        engine.dispose()
        if admin:
            with admin.begin() as conn:
                conn.execute(text("DROP SCHEMA " + schema + " CASCADE"))
            admin.dispose()


def request(service, *, key=None):
    store = service.storefront(DEMO_BUSINESS_ID)
    item = next(
        i
        for m in store.menus
        for c in m.categories
        for i in c.items
        if not i.modifier_groups
    )
    return CreateOrderRequest.model_validate(
        {
            "customer": {"name": "Synthetic durability", "phone": "3005550600"},
            "items": [{"menu_item_id": item.id, "quantity": 1}],
            "idempotency_key": key or uuid4().hex,
            "recovery_secret": "a" * 64,
        }
    )


class LostReply(SimulatedPaymentProvider):
    def __init__(self):
        self.calls = []
        self.reply = None

    def create_checkout(self, **kw):
        self.calls.append(dict(kw))
        if self.reply is None:
            self.reply = super().create_checkout(**kw)
            raise TimeoutError("synthetic response lost")
        return self.reply


def test_intent_and_items_are_committed_before_provider(factory):
    class Inspect(SimulatedPaymentProvider):
        def create_checkout(self, **kw):
            with factory() as other:
                order = other.get(Order, kw["order_id"])
                intent = other.scalar(
                    select(PaymentIntent).where(PaymentIntent.order_id == order.id)
                )
                assert order.items and intent and intent.state == "processing"
                assert json.loads(intent.request_json) == kw
            return super().create_checkout(**kw)

    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": Inspect()}
        )
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        assert order.checkout_state == "ready" and len(order.payments) == 1


def test_lost_reply_reuses_committed_order_and_immutable_provider_input(factory):
    provider = LostReply()
    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": provider}
        )
        req = request(svc)
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, req)
        original = session.scalar(select(Order))
        assert original is not None and session.scalar(select(Payment)) is None
        assert session.scalar(select(PaymentIntent)).state == "unknown"
        recovered = svc.create_order(DEMO_BUSINESS_ID, req)
        assert recovered.id == original.id and len(recovered.payments) == 1
        assert provider.calls[0] == provider.calls[1]
        assert len(list(session.scalars(select(Order)))) == 1


def test_unknown_nonidempotent_provider_is_not_called_twice(factory):
    provider = LostReply()
    provider.supports_idempotent_checkout = False
    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": provider}
        )
        req = request(svc)
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, req)
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, req)
        assert len(provider.calls) == 1
        assert session.scalar(select(PaymentIntent)).state == "review_required"
        assert (
            session.scalar(select(PaymentReconciliation)).reason
            == "provider_replay_not_supported"
        )


def test_cancelled_unknown_does_not_initiate_another_checkout(factory):
    provider = LostReply()
    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": provider}
        )
        req = request(svc)
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, req)
        order = session.scalar(select(Order))
        svc.transition_order(order.id, "cancelled")
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, req)
        assert (
            len(provider.calls) == 1
            and session.scalar(select(PaymentIntent)).state == "review_required"
        )


def test_late_paid_notification_has_one_durable_obligation_and_event(factory):
    with factory() as session:
        svc = RestaurantCommerceService(session)
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        svc.transition_order(order.id, "cancelled")
        for event_id in ["late", "late", "late-again"]:
            got = svc.apply_payment_status(
                order.payments[0].provider_reference,
                "paid",
                provider="simulated",
                event_id=event_id,
                amount_minor=order.total_minor,
                currency=order.currency,
            )
            assert (
                got.status == "cancelled"
                and got.payment_status == "paid"
                and got.reconciliation_required
            )
        rows = list(session.scalars(select(PaymentReconciliation)))
        assert len(rows) == 1 and rows[0].reason == "paid_after_cancellation"
        events = list(
            session.scalars(
                select(CommerceEventOutbox).where(
                    CommerceEventOutbox.kind == "payment.reconciliation_required"
                )
            )
        )
        assert len(events) == 1
        assert (
            svc.list_payment_reconciliation(DEMO_BUSINESS_ID)[0]["order_id"] == order.id
        )
        assert svc.list_payment_reconciliation("other-business") == []


def test_notification_can_arrive_before_reference_binding(factory):
    class Early(SimulatedPaymentProvider):
        def create_checkout(self, **kw):
            checkout = super().create_checkout(**kw)
            with factory() as other:
                result = RestaurantCommerceService(other).receive_payment_notification(
                    "simulated",
                    PaymentWebhookIn(
                        event_id="early",
                        provider_reference=checkout.provider_reference,
                        status="paid",
                        amount_minor=kw["amount_minor"],
                        currency=kw["currency"],
                    ),
                )
                assert isinstance(result, PaymentNotificationAccepted)
            return checkout

    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": Early()}
        )
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        assert order.payment_status == "paid"
        assert session.scalar(select(PaymentNotificationInbox)).state == "processed"


def test_unmatched_inbox_entries_cannot_starve_a_matchable_notification(factory):
    with factory() as session:
        svc = RestaurantCommerceService(session)
        for i in range(30):
            svc.receive_payment_notification(
                "simulated",
                PaymentWebhookIn(
                    event_id=f"unknown-{i}",
                    provider_reference=f"unknown-{i}",
                    status="paid",
                    amount_minor=1,
                    currency="COP",
                ),
            )
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        body = PaymentWebhookIn(
            event_id="known",
            provider_reference=order.payments[0].provider_reference,
            status="paid",
            amount_minor=order.total_minor,
            currency=order.currency,
        ).model_dump(mode="json")
        from world_model.restaurant_commerce.reliability import request_fingerprint

        session.add(
            PaymentNotificationInbox(
                provider="simulated",
                event_id="known",
                provider_reference=body["provider_reference"],
                payload_sha256=request_fingerprint(body),
                payload_json=json.dumps(body),
            )
        )
        session.commit()
        assert svc.drain_payment_notifications(limit=25) == 1
        assert svc.order_out(order.id).payment_status == "paid"


def test_expired_owner_cannot_overwrite_takeover_completion(factory):
    class Takeover(SimulatedPaymentProvider):
        calls = 0

        def create_checkout(self, **kw):
            self.calls += 1
            if self.calls == 1:
                with factory() as other:
                    intent = other.scalar(
                        select(PaymentIntent).where(
                            PaymentIntent.order_id == kw["order_id"]
                        )
                    )
                    intent.lease_until = utcnow() - timedelta(seconds=1)
                    other.commit()
                    svc = RestaurantCommerceService(
                        other, payment_providers={"simulated": self}
                    )
                    recovered = svc.process_payment_intent(kw["order_id"])
                    assert recovered.payments[0].provider_reference == "winner"
                return replace(
                    super().create_checkout(**kw), provider_reference="stale-loser"
                )
            return replace(super().create_checkout(**kw), provider_reference="winner")

    with factory() as session:
        provider = Takeover()
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": provider}
        )
        with pytest.raises(IdempotencyConflictError):
            svc.create_order(DEMO_BUSINESS_ID, request(svc))
        session.expire_all()
        assert session.scalar(select(Payment)).provider_reference == "winner"
        assert session.scalar(select(PaymentIntent)).state == "ready"


@pytest.mark.parametrize(
    "field,value",
    [
        ("checkout_url", {}),
        ("checkout_url", "bad\x00url"),
        ("provider_reference", "\ud800"),
        ("amount_minor", True),
    ],
)
def test_malformed_provider_fields_are_quarantined(factory, field, value):
    class Bad(SimulatedPaymentProvider):
        def create_checkout(self, **kw):
            return replace(super().create_checkout(**kw), **{field: value})

    with factory() as session:
        svc = RestaurantCommerceService(session, payment_providers={"simulated": Bad()})
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, request(svc))
        assert session.scalar(select(Payment)) is None
        assert session.scalar(select(PaymentIntent)).state == "review_required"


def test_recovery_secret_is_hashed_scoped_expiring_and_revocable(factory):
    with factory() as session:
        svc = RestaurantCommerceService(session)
        req = request(svc)
        order = svc.create_order(DEMO_BUSINESS_ID, req)
        intent = session.scalar(select(PaymentIntent))
        assert (
            intent.recovery_secret_hash
            == hashlib.sha256(req.recovery_secret.encode()).hexdigest()
        )
        assert req.recovery_secret not in intent.request_json
        assert (
            svc.recover_order(
                DEMO_BUSINESS_ID, req.idempotency_key, req.recovery_secret
            ).id
            == order.id
        )
        for bid, secret in [("other", "a" * 64), (DEMO_BUSINESS_ID, "b" * 64)]:
            with pytest.raises(NotFoundError):
                svc.recover_order(bid, req.idempotency_key, secret)
        svc.revoke_order_access(order.id)
        with pytest.raises(CheckoutRecoveryExpired):
            svc.recover_order(
                DEMO_BUSINESS_ID, req.idempotency_key, req.recovery_secret
            )
        session.get(Order, order.id).access_token_version = 0
        intent.created_at = utcnow() - timedelta(hours=25)
        session.commit()
        with pytest.raises(CheckoutRecoveryExpired):
            svc.recover_order(
                DEMO_BUSINESS_ID, req.idempotency_key, req.recovery_secret
            )


def test_api_restart_recovers_without_customer_retry(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    provider = LostReply()
    app = create_app(
        database_url=url,
        seed=True,
        payment_providers={"simulated": provider},
        payment_recovery_enabled=False,
    )
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            body = request(RestaurantCommerceService(session)).model_dump(mode="json")
        assert (
            client.post(
                "/api/restaurants/" + DEMO_BUSINESS_ID + "/orders", json=body
            ).status_code
            == 503
        )
    restarted = create_app(
        database_url=url,
        payment_providers={"simulated": provider},
        payment_recovery_interval_seconds=0.02,
    )
    with TestClient(restarted):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with restarted.state.session_factory() as session:
                intent = session.scalar(select(PaymentIntent))
                if intent.state == "ready":
                    break
            time.sleep(0.02)
        else:
            pytest.fail("recovery did not run without a customer retry")
        assert len(provider.calls) == 2 and provider.calls[0] == provider.calls[1]


def test_old_paid_event_after_refund_and_cancel_is_effect_free(factory):
    with factory() as session:
        svc = RestaurantCommerceService(session)
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        ref = order.payments[0].provider_reference
        svc.apply_payment_status(
            ref, "paid", provider="simulated", event_id="paid-original"
        )
        svc.apply_payment_status(
            ref, "refunded", provider="simulated", event_id="refund"
        )
        svc.transition_order(order.id, "cancelled")
        result = svc.apply_payment_status(
            ref, "paid", provider="simulated", event_id="paid-original"
        )
        assert result.payment_status == "refunded" and result.status == "cancelled"
        assert not result.reconciliation_required
        assert session.scalar(select(PaymentReconciliation)) is None


def test_locked_payment_refreshes_cached_state(factory):
    from world_model.restaurant_commerce.errors import InvalidTransitionError

    with factory() as session:
        svc = RestaurantCommerceService(session)
        order = svc.create_order(DEMO_BUSINESS_ID, request(svc))
        cached = session.scalar(select(Payment))
        session.commit()
        assert cached.status == "pending"
        with factory() as other:
            RestaurantCommerceService(other).apply_payment_status(
                cached.provider_reference, "paid"
            )
        with pytest.raises(InvalidTransitionError):
            svc.apply_payment_status(cached.provider_reference, "failed")
        session.rollback()
        assert svc.order_out(order.id).payment_status == "paid"


def test_recovery_orders_by_due_time_not_old_failed_creation(factory):
    provider = LostReply()
    with factory() as session:
        svc = RestaurantCommerceService(
            session, payment_providers={"simulated": provider}
        )
        with pytest.raises(PaymentError):
            svc.create_order(DEMO_BUSINESS_ID, request(svc))
        old = session.scalar(select(PaymentIntent))
        old.next_attempt_at = utcnow() - timedelta(seconds=1)
        session.commit()
        newer = RestaurantCommerceService(session).create_order(
            DEMO_BUSINESS_ID, request(svc)
        )
        new_intent = session.scalar(
            select(PaymentIntent).where(PaymentIntent.order_id == newer.id)
        )
        # A first-send pending intent must not be starved by an old repeatedly failing row.
        new_intent.state = "pending"
        new_intent.created_at = utcnow() - timedelta(seconds=5)
        new_intent.next_attempt_at = None
        session.commit()
        visited = []
        svc.process_payment_intent = lambda oid, **kw: visited.append(oid)
        svc.recover_payments(limit=1)
        assert visited == [newer.id]


@pytest.mark.parametrize("field", ["name", "menu_item_id", "idempotency_key"])
def test_invalid_unicode_does_not_leave_durable_intent(tmp_path, field):
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'unicode.db'}",
        seed=True,
        payment_recovery_enabled=False,
    )
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            body = request(RestaurantCommerceService(session)).model_dump(mode="json")
        if field == "name":
            body["customer"]["name"] = "bad\ud800"
        elif field == "menu_item_id":
            body["items"][0]["menu_item_id"] = "bad\ud800"
        else:
            body[field] = "bad\ud800"
        response = client.post(
            "/api/restaurants/" + DEMO_BUSINESS_ID + "/orders",
            content=json.dumps(body),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        with app.state.session_factory() as session:
            assert (
                session.scalar(select(Order)) is None
                and session.scalar(select(PaymentIntent)) is None
            )
