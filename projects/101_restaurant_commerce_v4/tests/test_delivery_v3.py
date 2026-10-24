from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import init_schema
from world_model.restaurant_commerce.deliveries import (
    DeliveryAddress,
    MensajerosUrbanosDeliveryProvider,
    SimulatedDeliveryProvider,
    UberDirectDeliveryProvider,
    haversine_meters,
)
from world_model.restaurant_commerce.errors import DeliveryError, InvalidTransitionError, ValidationError
from world_model.restaurant_commerce.models import Delivery, DeliveryEvent, DeliveryQuote, Order
from world_model.restaurant_commerce.schemas import (
    CartItemIn,
    CreateOrderRequest,
    CustomerIn,
    DeliveryAddressIn,
    ModifierSelectionIn,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    init_schema(engine)
    with Session(engine) as session:
        seed_demo(session)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def service(session):
    return RestaurantCommerceService(session)


def valid_cart(service: RestaurantCommerceService):
    store = service.storefront(DEMO_BUSINESS_ID)
    smash = next(i for m in store.menus for c in m.categories for i in c.items if i.name == "Smash 101")
    term = next(g for g in smash.modifier_groups if g.name == "Término")
    extras = next(g for g in smash.modifier_groups if g.name == "Extras")
    return [
        CartItemIn(
            menu_item_id=smash.id,
            quantity=2,
            modifiers=[
                ModifierSelectionIn(group_id=term.id, option_ids=[term.options[0].id]),
                ModifierSelectionIn(group_id=extras.id, option_ids=[extras.options[0].id]),
            ],
        )
    ]


def destination() -> DeliveryAddressIn:
    return DeliveryAddressIn(
        address_line="Calle 85 # 12-34",
        city="Bogotá",
        latitude=4.6697,
        longitude=-74.0549,
        instructions="Portería principal",
    )


def delivery_order(service: RestaurantCommerceService, *, idem: str = "delivery-1"):
    quote = service.create_delivery_quote(DEMO_BUSINESS_ID, destination())
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(
            customer=CustomerIn(name="Thomas", phone="+57 300 123 4567"),
            items=valid_cart(service),
            fulfillment_type="delivery",
            delivery_quote_id=quote.id,
            idempotency_key=idem,
        ),
    )
    return quote, order


def pay_accept(service: RestaurantCommerceService, order):
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    order = service.transition_order(order.id, "accepted")
    return order


def test_storefront_exposes_delivery_capability(service):
    store = service.storefront(DEMO_BUSINESS_ID)
    assert store.delivery_enabled is True
    assert store.delivery_provider == "simulated_delivery"
    cap = service.capability(DEMO_BUSINESS_ID)
    assert cap.delivery_enabled is True
    assert cap.delivery_quote_endpoint.endswith("/delivery/quote")


def test_haversine_and_simulated_quote_are_deterministic_enough():
    origin = DeliveryAddress("Origin", "Bogotá", 4.6486, -74.0630)
    target = DeliveryAddress("Target", "Bogotá", 4.6697, -74.0549)
    meters = haversine_meters(origin, target)
    assert 2_000 < meters < 3_500
    provider = SimulatedDeliveryProvider(base_fee_minor=6_000, per_km_minor=1_800)
    q = provider.quote(
        business_id="x", origin=origin, destination=target, currency="COP", prep_minutes=25
    )
    assert q.fee_minor >= 9_600
    assert q.distance_meters == meters
    assert q.expires_at > datetime.now(timezone.utc)


def test_delivery_quote_persists_snapshot(service, session):
    quote = service.create_delivery_quote(DEMO_BUSINESS_ID, destination())
    row = session.get(DeliveryQuote, quote.id)
    assert row is not None
    assert row.destination_address == "Calle 85 # 12-34"
    assert row.destination_instructions == "Portería principal"
    assert row.fee_minor == quote.fee_minor
    assert row.consumed_at is None


def test_delivery_order_includes_fee_and_consumes_quote(service, session):
    quote, order = delivery_order(service)
    assert order.fulfillment_type == "delivery"
    assert order.delivery_fee_minor == quote.fee_minor
    assert order.total_minor == 76_800 + quote.fee_minor
    assert order.delivery is not None
    assert order.delivery.status == "quoted"
    row = session.get(DeliveryQuote, quote.id)
    assert row.consumed_at is not None
    delivery = session.scalar(select(Delivery).where(Delivery.order_id == order.id))
    assert delivery.destination_city == "Bogotá"


def test_delivery_quote_cannot_be_reused(service):
    quote = service.create_delivery_quote(DEMO_BUSINESS_ID, destination())
    req = CreateOrderRequest(
        customer=CustomerIn(name="A", phone="3001234567"),
        items=valid_cart(service),
        fulfillment_type="delivery",
        delivery_quote_id=quote.id,
    )
    service.create_order(DEMO_BUSINESS_ID, req)
    with pytest.raises(ValidationError, match="already been used"):
        service.create_order(
            DEMO_BUSINESS_ID,
            req.model_copy(update={"customer": CustomerIn(name="B", phone="3007654321")}),
        )


def test_expired_delivery_quote_is_rejected(service, session):
    quote = service.create_delivery_quote(DEMO_BUSINESS_ID, destination())
    row = session.get(DeliveryQuote, quote.id)
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()
    with pytest.raises(ValidationError, match="expired"):
        service.create_order(
            DEMO_BUSINESS_ID,
            CreateOrderRequest(
                customer=CustomerIn(name="A", phone="3001234567"),
                items=valid_cart(service),
                fulfillment_type="delivery",
                delivery_quote_id=quote.id,
            ),
        )


def test_dispatch_requires_paid_accepted_order(service):
    _, order = delivery_order(service)
    with pytest.raises(ValidationError, match="payment"):
        service.dispatch_delivery(order.id)
    paid = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    with pytest.raises(ValidationError, match="accept"):
        service.dispatch_delivery(paid.id)


def test_delivery_lifecycle_completes_order_only_after_delivery(service, session):
    _, order = delivery_order(service)
    order = pay_accept(service, order)
    delivery = service.dispatch_delivery(order.id)
    assert delivery.status == "courier_assigned"
    assert delivery.provider_delivery_reference.startswith("simdel_")

    service.transition_order(order.id, "preparing")
    service.transition_order(order.id, "ready")

    with pytest.raises(InvalidTransitionError, match="only after"):
        service.transition_order(order.id, "completed")

    delivery = service.apply_delivery_status(delivery.provider_delivery_reference, "picked_up")
    assert delivery.status == "picked_up"
    delivery = service.apply_delivery_status(delivery.provider_delivery_reference, "delivered")
    assert delivery.status == "delivered"
    final = service.order_out(order.id)
    assert final.status == "completed"
    assert final.delivery.delivered_at is not None

    events = session.scalars(select(DeliveryEvent).where(DeliveryEvent.delivery_id == delivery.id)).all()
    assert {e.normalized_status for e in events} >= {"courier_assigned", "picked_up", "delivered"}


def test_pickup_cannot_happen_before_order_ready(service):
    _, order = delivery_order(service)
    order = pay_accept(service, order)
    delivery = service.dispatch_delivery(order.id)
    with pytest.raises(InvalidTransitionError, match="ready"):
        service.apply_delivery_status(delivery.provider_delivery_reference, "picked_up")


def test_paid_undispatched_delivery_requires_refund_before_order_cancellation(service):
    _, order = delivery_order(service)
    paid = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    with pytest.raises(InvalidTransitionError, match="refund workflow"):
        service.transition_order(paid.id, "cancelled")
    refunded = service.apply_payment_status(order.payments[0].provider_reference, "refunded")
    cancelled = service.transition_order(refunded.id, "cancelled")
    assert cancelled.status == "cancelled"
    delivery = service.delivery_tracking(order.id)
    assert delivery.status == "cancelled"


def test_dispatched_delivery_must_be_refunded_and_cancelled_before_order(service):
    _, order = delivery_order(service)
    order = pay_accept(service, order)
    service.dispatch_delivery(order.id)
    with pytest.raises(InvalidTransitionError, match="refund workflow"):
        service.transition_order(order.id, "cancelled")
    service.apply_payment_status(order.payments[0].provider_reference, "refunded")
    with pytest.raises(InvalidTransitionError, match="Cancel the dispatched delivery"):
        service.transition_order(order.id, "cancelled")
    delivery = service.cancel_delivery(order.id)
    assert delivery.status == "cancelled"
    cancelled = service.transition_order(order.id, "cancelled")
    assert cancelled.status == "cancelled"


def test_delivery_tracking_does_not_expose_customer_address(service):
    _, order = delivery_order(service)
    tracking = service.delivery_tracking(order.id)
    payload = tracking.model_dump()
    assert "destination_address" not in payload
    assert payload["status"] == "quoted"


def test_live_provider_boundaries_fail_closed():
    origin = DeliveryAddress("A", "Bogotá", 4.65, -74.06)
    target = DeliveryAddress("B", "Bogotá", 4.66, -74.05)
    for provider in [UberDirectDeliveryProvider(), MensajerosUrbanosDeliveryProvider()]:
        with pytest.raises(DeliveryError):
            provider.quote(
                business_id="x",
                origin=origin,
                destination=target,
                currency="COP",
                prep_minutes=20,
            )


def test_delivery_api_flow(engine):
    app = create_app(engine=engine, seed=False, operator_token="token")
    client = TestClient(app)
    headers = {"X-101-Operator-Token": "token"}

    quote_r = client.post(
        f"/api/restaurants/{DEMO_BUSINESS_ID}/delivery/quote",
        json={"destination": destination().model_dump()},
    )
    assert quote_r.status_code == 200
    quote = quote_r.json()

    with Session(engine) as s:
        svc = RestaurantCommerceService(s)
        cart = [x.model_dump() for x in valid_cart(svc)]

    order_r = client.post(
        f"/api/restaurants/{DEMO_BUSINESS_ID}/orders",
        json={
            "customer": {"name": "API", "phone": "3005550000"},
            "items": cart,
            "fulfillment_type": "delivery",
            "delivery_quote_id": quote["id"],
            "payment_provider": "simulated",
        },
    )
    assert order_r.status_code == 200
    order = order_r.json()
    pay_ref = order["payments"][0]["provider_reference"]
    assert client.post(f"/api/payments/simulated/{pay_ref}/complete").status_code == 200
    assert client.patch(
        f"/api/operator/orders/{order['id']}", headers=headers, json={"status": "accepted"}
    ).status_code == 200
    dispatch = client.post(
        f"/api/operator/orders/{order['id']}/delivery/dispatch", headers=headers
    )
    assert dispatch.status_code == 200
    assert dispatch.json()["status"] == "courier_assigned"
    tracking = client.get(
        f"/api/orders/{order['id']}/delivery/tracking",
        headers={"X-101-Order-Token": order["access_token"]},
    )
    assert tracking.status_code == 200
    assert tracking.json()["status"] == "courier_assigned"


def test_growth_analytics_separates_delivery_fees(service):
    _, order = delivery_order(service)
    order = pay_accept(service, order)
    delivery = service.dispatch_delivery(order.id)
    service.transition_order(order.id, "preparing")
    service.transition_order(order.id, "ready")
    service.apply_delivery_status(delivery.provider_delivery_reference, "picked_up")
    service.apply_delivery_status(delivery.provider_delivery_reference, "delivered")

    from world_model.restaurant_commerce.growth import RestaurantGrowthService

    analytics = RestaurantGrowthService(service.session).analytics(DEMO_BUSINESS_ID)
    assert analytics.completed_orders == 1
    assert analytics.delivery_fees_minor == order.delivery_fee_minor
    assert analytics.food_net_revenue_minor == order.total_minor - order.delivery_fee_minor
    assert analytics.net_revenue_minor == order.total_minor


def test_delivery_radius_is_enforced(service):
    far = DeliveryAddressIn(
        address_line="Medellín",
        city="Medellín",
        latitude=6.2442,
        longitude=-75.5812,
    )
    with pytest.raises(ValidationError, match="outside the configured delivery radius"):
        service.create_delivery_quote(DEMO_BUSINESS_ID, far)
