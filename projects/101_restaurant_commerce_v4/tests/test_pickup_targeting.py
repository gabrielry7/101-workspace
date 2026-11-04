"""Single-slot admission must match the published calendar without enumerating it."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import event
from test_financial_resolution_m3b import principal
from test_operations_m5 import settings
from test_payment_durability_m3 import factory as factory
from test_payment_durability_m3 import request as order_request
from world_model.restaurant_commerce.models import RestaurantCommerceProfile
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService as Service


@pytest.mark.parametrize(
    "zone,date",
    [
        ("America/Bogota", "2026-11-03T12:00:00+00:00"),
        ("America/New_York", "2026-03-07T05:00:00+00:00"),
        ("America/New_York", "2026-10-31T04:00:00+00:00"),
        ("Australia/Lord_Howe", "2026-10-03T00:00:00+00:00"),
    ],
)
def test_target_matches_calendar_at_boundaries_and_dst(factory, monkeypatch, zone, date):
    now = datetime.fromisoformat(date)
    monkeypatch.setattr("world_model.restaurant_commerce.operations.utcnow", lambda: now)
    with factory() as s:
        svc = Service(s)
        s.get(RestaurantCommerceProfile, BID).timezone = zone
        s.commit()
        policy = settings().model_copy(update={"opens": 17, "closes": 1439, "slot_minutes": 30})
        svc.save_operations_settings(BID, policy, principal())
        full = svc.pickup_slots(BID, now=now)
        available = {datetime.fromisoformat(x["at"]): x for x in full["slots"]}
        # Every valid slot, wrong minute/second, horizon, expired and naive input.
        candidates = list(available)
        candidates += [now - timedelta(days=1), now + timedelta(days=8), now.replace(tzinfo=None)]
        candidates += [t + timedelta(seconds=1) for t in list(available)[::31]]
        candidates += [t + timedelta(minutes=1) for t in list(available)[::31]]
        for t in candidates:
            actual = svc.pickup_slots(BID, now=now, requested_at=t)
            assert actual["slots"] == ([available[t]] if t in available else [])


def test_checkout_requests_only_one_slot(factory):
    class Targeted(Service):
        def pickup_slots(self, business_id, *, now=None, requested_at=None):
            assert requested_at is not None, "Admission enumerated the entire calendar"
            return super().pickup_slots(business_id, now=now, requested_at=requested_at)

    with factory() as s:
        svc = Service(s)
        body = order_request(svc)
        svc.save_operations_settings(BID, settings(), principal())
        at = datetime.fromisoformat(svc.pickup_slots(BID)["slots"][0]["at"])
        body = body.model_copy(update={"requested_pickup_at": at})
        assert Targeted(s).create_order(BID, body).id


def test_target_query_does_not_group_unrelated_slots(factory, monkeypatch):
    with factory() as s:
        svc = Service(s)
        svc.save_operations_settings(BID, settings(), principal())
        at = datetime.fromisoformat(svc.pickup_slots(BID)["slots"][0]["at"])
        statements = []
        candidates = []

        class CountedDateTime(datetime):
            @classmethod
            def combine(cls, *args, **kwargs):
                candidates.append(1)
                return super().combine(*args, **kwargs)

        monkeypatch.setattr("world_model.restaurant_commerce.operations.datetime", CountedDateTime)

        def capture(conn, cursor, statement, parameters, context, executemany):
            if "restaurant_orders" in statement:
                statements.append(statement)

        event.listen(s.bind, "before_cursor_execute", capture)
        try:
            assert svc.pickup_slots(BID, requested_at=at)["slots"]
        finally:
            event.remove(s.bind, "before_cursor_execute", capture)
        assert len(candidates) == 1
        assert len(statements) == 1
        assert "restaurant_orders.requested_pickup_at =" in statements[0]


def test_closed_dates_weekdays_and_pause_match_target(factory):
    with factory() as s:
        svc = Service(s)
        svc.save_operations_settings(BID, settings(), principal())
        at = datetime.fromisoformat(svc.pickup_slots(BID)["slots"][0]["at"])
        from zoneinfo import ZoneInfo

        day = at.astimezone(ZoneInfo(s.get(RestaurantCommerceProfile, BID).timezone)).date()
        for change in [{"closed_dates": [day]}, {"weekdays": []}, {"ordering_enabled": False}]:
            version = svc.operations_settings(BID)["version"]
            svc.save_operations_settings(
                BID,
                settings().model_copy(update={"expected_version": version, **change}),
                principal(),
            )
            assert svc.pickup_slots(BID, requested_at=at)["slots"] == []
