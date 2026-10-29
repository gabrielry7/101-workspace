import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from test_hardening_v4 import cart

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import database_ready, init_schema
from world_model.restaurant_commerce.errors import ValidationError
from world_model.restaurant_commerce.migrations import upgrade_customer_safety
from world_model.restaurant_commerce.models import (
    Customer,
    IdempotencyRecord,
    LoyaltyAccount,
    Order,
    OutboundMessage,
    Reservation,
    RewardDefinition,
)
from world_model.restaurant_commerce.schemas import CreateOrderRequest
from world_model.restaurant_commerce.security import sign_resource
from world_model.restaurant_commerce.service import RestaurantCommerceService

BUSINESS = "demo-restaurant-bogota"
ROOT = f"/api/restaurants/{BUSINESS}"
HEADERS = {"X-101-Operator-Token": "test-operator"}


@pytest.fixture
def env(tmp_path):
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'safety.db'}",
        seed=True,
        operator_token="test-operator",
        public_access_secret="test-access-secret",
    )
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            victim = Customer(
                business_id=BUSINESS,
                phone="3001234567",
                name="Private original",
                email="private@example.test",
                whatsapp_opt_in=True,
                marketing_opt_in=True,
                marketing_opt_in_source="verified-fixture",
                whatsapp_verified_at=datetime.now(UTC),
                marketing_verified_at=datetime.now(UTC),
            )
            session.add(victim)
            session.flush()
            session.add(
                LoyaltyAccount(
                    business_id=BUSINESS,
                    customer_id=victim.id,
                    available_points=100,
                    lifetime_earned_points=100,
                )
            )
            session.commit()
            items = [
                i.model_dump(mode="json")
                for i in cart(RestaurantCommerceService(session))
            ]
            reward = session.scalar(select(RewardDefinition)).id
            victim_id = victim.id
        yield app, client, items, reward, victim_id


def payload(items, **extra):
    return {
        "customer": {
            "name": "Guest supplied",
            "phone": "3001234567",
            "email": "guest@example.test",
            "whatsapp_opt_in": False,
            "marketing_opt_in": False,
            "consent_source": "forged",
        },
        "items": items,
        "idempotency_key": "guest-key",
        **extra,
    }


def test_public_reward_denied_before_any_side_effect(env):
    app, c, items, reward, victim = env
    for url, body in [
        (ROOT + "/orders", payload(items, reward_id=reward)),
        (
            ROOT + "/orders/quote",
            {"items": items, "customer_phone": "3001234567", "reward_id": reward},
        ),
    ]:
        r = c.post(url, json=body)
        assert r.status_code == 422 and "Verified customer required" in r.text
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 0
        assert s.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
        assert s.scalar(select(LoyaltyAccount)).available_points == 100
        assert s.get(Customer, victim).name == "Private original"
    bad = payload(items)
    bad["verified_customer_id"] = victim
    assert c.post(ROOT + "/orders", json=bad).status_code == 422


@pytest.mark.parametrize("consent", [True, False])
def test_guest_contact_snapshot_never_mutates_or_discloses_existing_profile(
    env, consent
):
    app, c, items, _, victim = env
    body = payload(items)
    body["customer"].update(whatsapp_opt_in=consent, marketing_opt_in=consent)
    r = c.post(ROOT + "/orders", json=body)
    assert r.status_code == 200, r.text
    o = r.json()
    assert (
        o["customer_name"] == "Guest supplied"
        and "Private original" not in r.text
        and "private@example" not in r.text
    )
    assert r.headers["cache-control"] == "no-store"
    repeat = c.post(ROOT + "/orders", json=body).json()
    assert repeat["id"] == o["id"]
    with app.state.session_factory() as s:
        row = s.get(Customer, victim)
        assert (
            row.name,
            row.email,
            row.whatsapp_opt_in,
            row.marketing_opt_in,
            row.marketing_opt_in_source,
        ) == (
            "Private original",
            "private@example.test",
            True,
            True,
            "verified-fixture",
        )
        snap = json.loads(s.get(Order, o["id"]).customer_snapshot_json)
        assert snap["source"] == "web_checkout:commerce-consent-v1"
        assert (
            snap["identity_verified"] is False
            and snap["marketing_requested"] == consent
        )
        assert snap["policy_version"] == "commerce-consent-v1" and snap["recorded_at"]
        row.name = "Later verified name"
        s.commit()
    got = c.get(
        "/api/orders/" + o["id"], headers={"X-101-Order-Token": o["access_token"]}
    )
    assert got.status_code == 200 and got.json()["customer_name"] == "Guest supplied"
    assert (
        c.post(
            "/api/payments/simulated/"
            + o["payments"][0]["provider_reference"]
            + "/complete"
        ).status_code
        == 200
    )
    for status in ["accepted", "preparing", "ready", "completed"]:
        assert (
            c.patch(
                "/api/operator/orders/" + o["id"],
                json={"status": status},
                headers=HEADERS,
            ).status_code
            == 200
        )
    with app.state.session_factory() as s:
        assert s.scalar(select(LoyaltyAccount)).available_points == 100
        assert s.scalar(select(func.count()).select_from(OutboundMessage)) == 0
        assert s.get(Customer, victim).last_order_at is None


def test_guest_reservation_and_new_contact_preserve_unverified_consent(env):
    app, c, items, _, victim = env
    body = payload(items)["customer"]
    when = (datetime.now(UTC) + timedelta(days=2)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    data = {
        "customer": body,
        "starts_at": when.isoformat(),
        "party_size": 2,
        "idempotency_key": "reservation-key",
        "source_channel": "forged",
    }
    r = c.post(ROOT + "/reservations", json=data)
    assert r.status_code == 200, r.text
    assert (
        r.json()["customer_name"] == "Guest supplied"
        and r.json()["source_channel"] == "web"
    )
    assert c.post(ROOT + "/reservations", json=data).json()["id"] == r.json()["id"]
    body = payload(items)
    body["customer"].update(
        phone="3000009999", marketing_opt_in=True, whatsapp_opt_in=True
    )
    assert c.post(ROOT + "/orders", json=body).status_code == 200
    with app.state.session_factory() as s:
        row = s.scalar(select(Customer).where(Customer.phone == "3000009999"))
        assert not row.whatsapp_opt_in and not row.marketing_opt_in
        assert s.get(Customer, victim).name == "Private original"
        snap = json.loads(s.get(Reservation, r.json()["id"]).customer_snapshot_json)
        assert (
            snap["source"] == "web_reservation:commerce-consent-v1"
            and not snap["identity_verified"]
        )


def test_verified_server_identity_can_redeem_once_and_cannot_cross_scope(env):
    app, c, items, reward, victim = env
    req = CreateOrderRequest(**payload(items, reward_id=reward))
    with app.state.session_factory() as s:
        svc = RestaurantCommerceService(s, verified_customer_id=victim)
        o = svc.create_order(BUSINESS, req)
        assert o.reward_discount_minor == 10000
        assert svc.create_order(BUSINESS, req).id == o.id
        assert s.scalar(select(LoyaltyAccount)).available_points == 50
        with pytest.raises(ValidationError):
            svc.quote(
                "other-business",
                req.items,
                customer_phone=req.customer.phone,
                reward_id=reward,
            )
        with pytest.raises(ValidationError):
            svc.quote(
                BUSINESS, req.items, customer_phone="3009999999", reward_id=reward
            )
    # Same payload/key without verified context cannot replay or spend.
    assert c.post(ROOT + "/orders", json=req.model_dump(mode="json")).status_code == 422


def test_legacy_order_and_reservation_replay_fail_closed(env):
    app, c, items, _, _ = env
    body = payload(items)
    o = c.post(ROOT + "/orders", json=body).json()
    with app.state.session_factory() as s:
        s.execute(delete(IdempotencyRecord))
        s.get(Order, o["id"]).customer_snapshot_json = None
        s.commit()
    body["customer"]["name"] = "Different"
    r = c.post(ROOT + "/orders", json=body)
    assert (
        r.status_code == 409
        and "access_token" not in r.text
        and "Private original" not in r.text
    )
    assert (
        c.get(
            "/api/orders/" + o["id"], headers={"X-101-Order-Token": o["access_token"]}
        ).status_code
        == 401
    )


def test_capability_expiry_wrong_scope_revocation_and_no_replay_renewal(env):
    app, c, items, _, _ = env
    body = payload(items)
    o = c.post(ROOT + "/orders", json=body).json()
    url = "/api/orders/" + o["id"]
    assert (
        c.get(url, headers={"X-101-Order-Token": o["access_token"]}).status_code == 200
    )
    for token in [
        "a" * 64,
        o["access_token"] + "x",
        sign_resource("test-access-secret", kind="reservation", resource_id=o["id"]),
        sign_resource(
            "test-access-secret",
            kind="order",
            resource_id=o["id"],
            expires_at=int(time.time()) - 1,
        ),
    ]:
        assert c.get(url, headers={"X-101-Order-Token": token}).status_code == 401
    revoke = "/api/operator/orders/" + o["id"] + "/access/revoke"
    assert c.post(revoke).status_code == 401
    assert c.post(revoke, headers=HEADERS).status_code == 200
    assert (
        c.get(url, headers={"X-101-Order-Token": o["access_token"]}).status_code == 401
    )
    assert c.post(ROOT + "/orders", json=body).status_code == 409
    with app.state.session_factory() as s:
        row = s.get(Order, o["id"])
        row.access_token_version = 0
        row.created_at = datetime.now(UTC) - timedelta(days=8)
        s.commit()
    assert c.post(ROOT + "/orders", json=body).status_code == 409


def test_outbox_handoff_rechecks_consent_and_never_claims_sent(env):
    app, c, _, _, victim = env
    with app.state.session_factory() as s:
        msg = OutboundMessage(
            business_id=BUSINESS,
            customer_id=victim,
            channel="whatsapp",
            purpose="marketing",
            message_kind="winback",
            destination="3001234567",
            body="Hello",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
            dedupe_key="msg",
        )
        s.add(msg)
        s.commit()
        mid = msg.id
    url = "/api/operator/outbox/" + mid
    assert c.post(url + "/handoff").status_code == 401
    first = c.post(url + "/handoff", headers=HEADERS)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "handed_off" and first.json()["sent_at"] is None
    assert c.post(url + "/handoff", headers=HEADERS).json()["status"] == "handed_off"
    assert c.patch(url + "/sent", headers=HEADERS, json={}).status_code == 409
    with app.state.session_factory() as s:
        s.get(Customer, victim).marketing_opt_in = False
        s.commit()
    assert c.post(url + "/handoff", headers=HEADERS).status_code == 422
    with app.state.session_factory() as s:
        msg = s.get(OutboundMessage, mid)
        assert msg.status == "suppressed" and msg.sent_at is None


def test_populated_sqlite_upgrade_preserves_rows_without_inventing_authority(env):
    app, c, items, _, _ = env
    o = c.post(ROOT + "/orders", json=payload(items)).json()
    engine = app.state.engine
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE restaurant_customers DROP COLUMN whatsapp_verified_at")
        )
        conn.execute(
            text("ALTER TABLE restaurant_customers DROP COLUMN marketing_verified_at")
        )
        conn.execute(
            text("ALTER TABLE restaurant_orders DROP COLUMN customer_snapshot_json")
        )
        conn.execute(
            text("ALTER TABLE restaurant_orders DROP COLUMN access_token_version")
        )
        conn.execute(
            text(
                "ALTER TABLE restaurant_reservations DROP COLUMN customer_snapshot_json"
            )
        )
    assert not database_ready(engine)
    with pytest.raises(RuntimeError, match="explicit offline upgrade"):
        init_schema(engine)
    upgrade_customer_safety(engine)
    upgrade_customer_safety(engine)
    assert database_ready(engine)
    with app.state.session_factory() as s:
        old = s.get(Order, o["id"])
        assert (
            old and old.customer_snapshot_json is None and old.access_token_version == 0
        )
    assert c.post(ROOT + "/orders", json=payload(items)).status_code == 409


def test_guest_cannot_exhaust_personal_promotion_allowance(env):
    app, c, items, _, _ = env
    r = c.post(ROOT + "/orders", json=payload(items, promo_code="DIRECTO10"))
    assert r.status_code == 422 and "Verified customer required" in r.text
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0


def test_historical_consent_flags_do_not_authorize_handoff(env):
    app, c, _, _, victim = env
    with app.state.session_factory() as s:
        customer = s.get(Customer, victim)
        customer.whatsapp_verified_at = None
        customer.marketing_verified_at = None
        msg = OutboundMessage(
            business_id=BUSINESS,
            customer_id=victim,
            channel="whatsapp",
            purpose="marketing",
            message_kind="winback",
            destination=customer.phone,
            body="Legacy",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
            dedupe_key="legacy-consent",
        )
        s.add(msg)
        s.commit()
        mid = msg.id
    assert (
        c.post("/api/operator/outbox/" + mid + "/handoff", headers=HEADERS).status_code
        == 422
    )
    with app.state.session_factory() as s:
        assert s.get(
            Customer, victim
        ).marketing_opt_in  # history preserved, not promoted
        assert s.get(OutboundMessage, mid).status == "suppressed"


@pytest.mark.parametrize(
    "change", ["recipient", "channel", "future", "suppressed", "sent", "business"]
)
def test_handoff_rejects_stale_or_unsupported_message_context(env, change):
    app, c, _, _, victim = env
    with app.state.session_factory() as session:
        msg = OutboundMessage(
            business_id=BUSINESS,
            customer_id=victim,
            channel="whatsapp",
            purpose="marketing",
            message_kind="winback",
            destination="3001234567",
            body="Synthetic",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
            dedupe_key="context",
        )
        if change == "recipient":
            msg.destination = "3009999999"
        elif change == "channel":
            msg.channel = "email"
        elif change == "future":
            msg.scheduled_at = datetime.now(UTC) + timedelta(days=1)
        elif change in {"suppressed", "sent"}:
            msg.status = change
        elif change == "business":
            msg.business_id = "other-business"
        session.add(msg)
        session.commit()
        mid = msg.id
    response = c.post("/api/operator/outbox/" + mid + "/handoff", headers=HEADERS)
    assert response.status_code == 422
    with app.state.session_factory() as session:
        assert session.get(OutboundMessage, mid).sent_at is None
