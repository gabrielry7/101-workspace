"""Pickup capacity, inventory and staff contracts on SQLite and disposable PostgreSQL."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from staff_helpers import staff_headers
from test_financial_resolution_m3b import principal
from test_payment_durability_m3 import factory as factory
from test_payment_durability_m3 import request as order_request
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import database_ready, init_schema
from world_model.restaurant_commerce.errors import IdempotencyConflictError, ValidationError
from world_model.restaurant_commerce.migrations import upgrade_operations
from world_model.restaurant_commerce.models import (
    CommerceEventOutbox,
    ItemStock,
    Order,
    PickupPolicy,
    utcnow,
)
from world_model.restaurant_commerce.operations import PickupSettings, StockSettings
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService as Service


def settings(**kwargs):
    return PickupSettings(
        expected_version=0,
        ordering_enabled=True,
        scheduled=True,
        opens=0,
        closes=1440,
        lead_minutes=5,
        capacity=1,
        reason="Synthetic hours",
        **kwargs,
    )


def prepare(factory, *, stock=False, capacity=1):
    with factory() as s:
        svc = Service(s)
        request = order_request(svc)
        svc.save_operations_settings(
            BID, settings().model_copy(update={"capacity": capacity}), principal()
        )
        slot = svc.pickup_slots(BID)["slots"][0]["at"]
        request = request.model_copy(
            update={"requested_pickup_at": __import__("datetime").datetime.fromisoformat(slot)}
        )
        if stock:
            svc.save_item_stock(
                BID,
                request.items[0].menu_item_id,
                StockSettings(
                    expected_version=0,
                    remaining=request.items[0].quantity,
                    sold_out=False,
                    reason="Last portion",
                ),
                principal(),
            )
        return request


@pytest.mark.parametrize("resource", ["both", "slot", "stock"])
def test_capacity_stock_race_and_replay(factory, resource):
    request = prepare(factory, stock=resource != "slot", capacity=10 if resource == "stock" else 1)
    barrier = Barrier(2)

    def buy(n):
        with factory() as s:
            svc = Service(s)
            body = request.model_copy(update={"idempotency_key": f"m5-race-{n}"})
            barrier.wait(timeout=5)
            try:
                return svc.create_order(BID, body).id
            except ValidationError:
                s.rollback()
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(buy, range(2)))
    assert sum(x is not None for x in results) == 1
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1
        if resource != "slot":
            assert s.scalar(select(ItemStock.remaining)) == 0
        svc = Service(s)
        winner = results.index(next(x for x in results if x))
        again = svc.create_order(
            BID, request.model_copy(update={"idempotency_key": f"m5-race-{winner}"})
        )
        assert again.id in results
        if resource != "slot":
            assert s.scalar(select(ItemStock.remaining)) == 0
        assert (resource == "stock") == any(
            x["at"] == request.requested_pickup_at.isoformat()
            for x in svc.pickup_slots(BID)["slots"]
        )


@pytest.mark.parametrize("kind", ["past", "naive", "wrong-minute", "holiday", "closed"])
def test_invalid_pickup_rejected_without_order_or_stock_effect(factory, kind):
    request = prepare(factory, stock=True)
    with factory() as s:
        svc = Service(s)
        if kind == "past":
            request = request.model_copy(
                update={"requested_pickup_at": utcnow() - timedelta(days=1)}
            )
        if kind == "naive":
            request = request.model_copy(
                update={"requested_pickup_at": request.requested_pickup_at.replace(tzinfo=None)}
            )
        if kind == "wrong-minute":
            request = request.model_copy(
                update={"requested_pickup_at": request.requested_pickup_at + timedelta(minutes=1)}
            )
        if kind in {"holiday", "closed"}:
            row = s.get(PickupPolicy, BID)
            policy = json.loads(row.policy_json)
            if kind == "closed":
                policy["weekdays"] = []
            else:
                from zoneinfo import ZoneInfo

                policy["closed_dates"] = [
                    request.requested_pickup_at.astimezone(ZoneInfo("America/Bogota"))
                    .date()
                    .isoformat()
                ]
            row.policy_json = json.dumps(policy)
            s.commit()
        with pytest.raises(ValidationError):
            svc.create_order(BID, request)
        s.rollback()
        assert s.scalar(select(func.count()).select_from(Order)) == 0
        assert s.scalar(select(ItemStock.remaining)) == request.items[0].quantity


def test_price_and_expected_version_and_daily_summary(factory):
    with factory() as s:
        svc = Service(s)
        request = order_request(svc)
        with pytest.raises(ValidationError, match="precio"):
            svc.create_order(BID, request.model_copy(update={"expected_total_minor": 1}))
        s.rollback()
        order = svc.create_order(BID, request)
        svc.apply_payment_status(order.payments[0].provider_reference, "paid", provider="simulated")
        current = svc.order_out(order.id)
        next_order = svc.transition_order(
            order.id, "accepted", expected_version=current.version, reason="Kitchen accepted"
        )
        assert next_order.version > current.version
        with pytest.raises(IdempotencyConflictError):
            svc.transition_order(order.id, "preparing", expected_version=current.version)
        summary = svc.daily_finance(
            BID, utcnow().astimezone(__import__("zoneinfo").ZoneInfo("America/Bogota")).date()
        )
        assert summary["gross_minor"] == order.total_minor
        assert summary["provider_fees_minor"] is summary["settled_net_minor"] is None


def test_manager_settings_scoped_and_audited(factory):
    with factory() as s:
        engine = s.get_bind()
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as c:
        url = f"/api/operator/restaurants/{BID}/settings"
        assert c.get(url).status_code == 401
        headers = staff_headers(c, role="operator", name="operator")
        assert (
            c.put(url, json=settings().model_dump(mode="json"), headers=headers).status_code == 403
        )
        headers = staff_headers(c)
        assert (
            c.put(url, json=settings().model_dump(mode="json"), headers=headers).status_code == 200
        )
        assert (
            c.put(url, json=settings().model_dump(mode="json"), headers=headers).status_code == 409
        )
        assert c.get("/api/operator/restaurants/other/settings").status_code == 403
        assert c.get(f"/api/restaurants/{BID}/pickup-slots").json()["slots"]
    with factory() as s:
        events = list(
            s.scalars(
                select(CommerceEventOutbox).where(
                    CommerceEventOutbox.kind == "operations.settings_changed"
                )
            )
        )
        assert events and json.loads(events[0].payload_json)["reason"] == "Synthetic hours"


def test_explicit_upgrade_preserves_data_and_does_not_seed_promises(factory):
    with factory() as s:
        engine = s.get_bind()
        svc = Service(s)
        existing = svc.create_order(BID, order_request(svc))
        before = s.scalar(select(func.count()).select_from(Order))
        assert before == 1
        reference = existing.payments[0].provider_reference
    ItemStock.__table__.drop(engine)
    PickupPolicy.__table__.drop(engine)
    assert not database_ready(engine)
    with pytest.raises(RuntimeError, match="offline"):
        init_schema(engine)
    upgrade_operations(engine)
    upgrade_operations(engine)
    assert database_ready(engine)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == before
        restored = Service(s).order_out(existing.id)
        assert restored.total_minor == existing.total_minor
        assert restored.payments[0].provider_reference == reference
        assert s.scalar(select(func.count()).select_from(PickupPolicy)) == 0


def test_signed_quote_expiry_payload_binding_and_replay(factory, monkeypatch):
    import time

    from world_model.restaurant_commerce.models import IdempotencyRecord

    with factory() as s:
        engine = s.get_bind()
        body = order_request(Service(s)).model_dump(mode="json")
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as c:
        root = f"/api/restaurants/{BID}/orders"
        quoted = c.post(root + "/quote", json={"items": body["items"]}).json()
        assert quoted["quote_token"] and quoted["expires_at"]
        request = {
            **body,
            "quote_token": quoted["quote_token"],
            "expected_total_minor": quoted["total_minor"],
        }
        wrong = {
            **request,
            "idempotency_key": "altered-cart",
            "items": [{**body["items"][0], "quantity": 2}],
        }
        assert c.post(root, json=wrong).status_code == 422
        accepted = c.post(root, json=request)
        assert accepted.status_code == 200, accepted.text
        actual = time.time()
        monkeypatch.setattr(time, "time", lambda: actual + 121)
        assert c.post(root, json=request).json()["id"] == accepted.json()["id"]
        expired = c.post(root, json={**request, "idempotency_key": "expired-quote"})
        assert expired.status_code == 422 and "cotización" in expired.json()["detail"]
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1
        assert (
            s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == "expired-quote"))
            is None
        )


def test_stock_stale_manager_edit_and_pause_reject_new_order(factory):
    with factory() as s:
        svc = Service(s)
        request = order_request(svc)
        item = request.items[0].menu_item_id
        first = svc.save_item_stock(
            BID,
            item,
            StockSettings(expected_version=0, remaining=2, sold_out=False, reason="Counted"),
            principal(),
        )
        stock = next(i for i in first["items"] if i["id"] == item)
        svc.create_order(BID, request)
        with pytest.raises(IdempotencyConflictError):
            svc.save_item_stock(
                BID,
                item,
                StockSettings(
                    expected_version=stock["version"],
                    remaining=99,
                    sold_out=False,
                    reason="Stale count",
                ),
                principal(),
            )
        s.rollback()
        assert s.scalar(select(ItemStock.remaining)) == 1
        svc.save_operations_settings(
            BID, settings().model_copy(update={"ordering_enabled": False}), principal()
        )
        with pytest.raises(ValidationError):
            svc.create_order(BID, request.model_copy(update={"idempotency_key": "paused-order"}))
        s.rollback()
        assert s.scalar(select(func.count()).select_from(Order)) == 1


def test_bound_storefront_link_resolves_existing_business_only(factory):
    with factory() as s:
        engine = s.get_bind()
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as c:
        capability = c.get(f"/api/restaurants/{BID}/capability").json()
        response = c.get(capability["storefront_url"], follow_redirects=False)
        assert (
            response.status_code == 307 and response.headers["location"] == "/?business_id=" + BID
        )
        assert c.get("/r/not-a-business").status_code == 404


def test_equivalent_offset_cannot_bypass_slot_capacity(factory):
    from datetime import timezone

    request = prepare(factory)
    offset = request.requested_pickup_at.astimezone(timezone(timedelta(hours=-5)))
    with factory() as s:
        svc = Service(s)
        first = svc.create_order(
            BID,
            request.model_copy(
                update={"requested_pickup_at": offset, "idempotency_key": "offset-first"}
            ),
        )
        from world_model.restaurant_commerce.operations import aware

        assert aware(first.requested_pickup_at) == request.requested_pickup_at
        assert not any(
            slot["at"] == request.requested_pickup_at.isoformat()
            for slot in svc.pickup_slots(BID)["slots"]
        )
        with pytest.raises(ValidationError, match="completo"):
            svc.create_order(BID, request.model_copy(update={"idempotency_key": "offset-second"}))
        s.rollback()
        assert s.scalar(select(func.count()).select_from(Order)) == 1


@pytest.mark.parametrize("changed", ["disabled", "party", "slot", "past"])
def test_reservation_exact_recovery_survives_current_policy(factory, monkeypatch, changed):
    from datetime import datetime

    from world_model.restaurant_commerce import service as module
    from world_model.restaurant_commerce.models import RestaurantCommerceProfile
    from world_model.restaurant_commerce.schemas import CreateReservationRequest

    when = (utcnow() + timedelta(days=2)).replace(hour=12, minute=30, second=0, microsecond=0)
    body = CreateReservationRequest(
        customer={"name": "Synthetic", "phone": "3005550111"},
        starts_at=when,
        party_size=4,
        idempotency_key="reservation-recovery-m5",
    )
    with factory() as session:
        service = Service(session)
        original = service.create_reservation(BID, body)
        profile = session.get(RestaurantCommerceProfile, BID)
        if changed == "disabled":
            profile.accepts_reservations = False
        if changed == "party":
            profile.max_party_size = 2
        if changed == "slot":
            profile.reservation_slot_minutes = 60
        session.commit()
        if changed == "past":

            class Future(datetime):
                @classmethod
                def now(cls, tz=None):
                    return when + timedelta(days=1)

            monkeypatch.setattr(module, "datetime", Future)
        assert service.create_reservation(BID, body).id == original.id
        with pytest.raises(IdempotencyConflictError):
            service.create_reservation(BID, body.model_copy(update={"party_size": 3}))


@pytest.mark.parametrize("changed", ["ordering_enabled", "pickup_enabled"])
def test_order_exact_recovery_survives_pause(factory, changed):
    from world_model.restaurant_commerce.models import RestaurantCommerceProfile

    with factory() as session:
        service = Service(session)
        body = order_request(service, key="paused-recovery-m5")
        original = service.create_order(BID, body)
        setattr(session.get(RestaurantCommerceProfile, BID), changed, False)
        session.commit()
        assert service.create_order(BID, body).id == original.id
        with pytest.raises(ValidationError):
            service.create_order(
                BID, body.model_copy(update={"idempotency_key": "different-intent"})
            )
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Order)) == 1
