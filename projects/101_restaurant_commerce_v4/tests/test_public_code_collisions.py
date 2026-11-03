"""Retained regression: growing PostgreSQL load exposed public-code collisions."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_payment_durability_m3 import factory as factory
from test_payment_durability_m3 import request
from world_model.restaurant_commerce import service as module
from world_model.restaurant_commerce.models import ItemStock, Order, PaymentIntent, Reservation
from world_model.restaurant_commerce.schemas import CreateReservationRequest
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.mark.parametrize("kind", ["order", "reservation"])
def test_collision_retries_insert_without_duplicating_intent(factory, monkeypatch, kind):
    codes = iter(["COLLISION", "COLLISION", "FRESH"])
    monkeypatch.setattr(module, "_public_code", lambda prefix: prefix + next(codes))
    with factory() as session:
        service = RestaurantCommerceService(session)
        if kind == "order":
            first_request = request(service, key="first")
            session.merge(ItemStock(item_id=first_request.items[0].menu_item_id, remaining=2))
            session.commit()
            first = service.create_order(DEMO_BUSINESS_ID, first_request)
            second_request = request(service, key="second")
            second = service.create_order(DEMO_BUSINESS_ID, second_request)
            assert service.create_order(DEMO_BUSINESS_ID, second_request).id == second.id
            assert session.scalar(select(func.count()).select_from(PaymentIntent)) == 2
            assert session.get(ItemStock, first_request.items[0].menu_item_id).remaining == 0
            model = Order
        else:

            def reservation(key):
                return CreateReservationRequest.model_validate(
                    {
                        "customer": {"name": "Synthetic", "phone": "3005550600"},
                        "starts_at": (datetime.now(UTC) + timedelta(days=2)).replace(
                            minute=0, second=0, microsecond=0
                        ),
                        "party_size": 2,
                        "idempotency_key": key,
                    }
                )

            first = service.create_reservation(DEMO_BUSINESS_ID, reservation("first"))
            second = service.create_reservation(DEMO_BUSINESS_ID, reservation("second"))
            model = Reservation
        assert first.public_code != second.public_code
        assert session.scalar(select(func.count()).select_from(model)) == 2


def test_collision_exhaustion_rolls_back_and_retry_key_is_reusable(factory, monkeypatch):
    from world_model.restaurant_commerce.errors import ConcurrencyConflictError

    monkeypatch.setattr(module, "_public_code", lambda prefix: prefix + "SAME")
    with factory() as session:
        service = RestaurantCommerceService(session)
        service.create_order(DEMO_BUSINESS_ID, request(service, key="first"))
        pending = request(service, key="recover")
        with pytest.raises(ConcurrencyConflictError):
            service.create_order(DEMO_BUSINESS_ID, pending)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        monkeypatch.setattr(module, "_public_code", lambda prefix: prefix + "FRESH")
        result = service.create_order(DEMO_BUSINESS_ID, pending)
        assert result.id
        assert session.scalar(select(func.count()).select_from(PaymentIntent)) == 2


def test_other_integrity_errors_are_not_retried(factory, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    def unexpected(prefix):
        raise AssertionError("An unrelated integrity error must not allocate another code")

    monkeypatch.setattr(module, "_public_code", unexpected)
    with factory() as session:
        service = RestaurantCommerceService(session)
        with pytest.raises(IntegrityError):
            service._insert_with_public_code(Reservation(public_code="INVALID"), "R")
        session.rollback()
