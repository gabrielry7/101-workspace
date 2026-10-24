from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import init_schema
from world_model.restaurant_commerce.enums import OrderStatus
from world_model.restaurant_commerce.errors import InvalidTransitionError, ValidationError
from world_model.restaurant_commerce.events import MemoryEventSink
from world_model.restaurant_commerce.models import Customer, MenuItem, Order, Reservation, RestaurantCommerceProfile
from world_model.restaurant_commerce.notifications import format_order_message, whatsapp_click_to_chat_url
from world_model.restaurant_commerce.schemas import CartItemIn, CreateOrderRequest, CreateReservationRequest, CustomerIn, ModifierSelectionIn
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


def smash_selection(service: RestaurantCommerceService):
    store = service.storefront(DEMO_BUSINESS_ID)
    smash = next(i for m in store.menus for c in m.categories for i in c.items if i.name == "Smash 101")
    term = next(g for g in smash.modifier_groups if g.name == "Término")
    extras = next(g for g in smash.modifier_groups if g.name == "Extras")
    return smash, term, extras


def valid_cart(service: RestaurantCommerceService):
    smash, term, extras = smash_selection(service)
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


def test_storefront_exposes_menu_and_capabilities(service):
    store = service.storefront(DEMO_BUSINESS_ID)
    assert store.display_name == "Casa 101"
    assert store.ordering_enabled is True
    assert store.pickup_enabled is True
    assert store.accepts_reservations is True
    assert sum(len(c.items) for m in store.menus for c in m.categories) == 4


def test_quote_uses_integer_minor_units_and_modifiers(service):
    quote = service.quote(DEMO_BUSINESS_ID, valid_cart(service))
    assert quote.currency == "COP"
    # (32,900 + 5,500) * 2
    assert quote.total_minor == 76_800
    assert isinstance(quote.total_minor, int)


def test_required_modifier_is_enforced(service):
    smash, term, extras = smash_selection(service)
    with pytest.raises(ValidationError, match="choose at least"):
        service.quote(
            DEMO_BUSINESS_ID,
            [CartItemIn(menu_item_id=smash.id, quantity=1, modifiers=[])],
        )


def test_unknown_modifier_group_rejected(service):
    smash, *_ = smash_selection(service)
    with pytest.raises(ValidationError, match="Unknown modifier group"):
        service.quote(
            DEMO_BUSINESS_ID,
            [
                CartItemIn(
                    menu_item_id=smash.id,
                    quantity=1,
                    modifiers=[ModifierSelectionIn(group_id="fake", option_ids=["nope"])],
                )
            ],
        )


def test_sold_out_item_rejected(service, session):
    smash, *_ = smash_selection(service)
    item = session.get(MenuItem, smash.id)
    item.sold_out = True
    session.commit()
    with pytest.raises(ValidationError, match="unavailable"):
        service.quote(DEMO_BUSINESS_ID, valid_cart(service))


def test_create_order_snapshots_menu_and_creates_customer(service, session):
    req = CreateOrderRequest(
        customer=CustomerIn(name="Thomas", phone="+57 300 123 4567"),
        items=valid_cart(service),
        idempotency_key="abc-1",
    )
    order = service.create_order(DEMO_BUSINESS_ID, req)
    assert order.status == "awaiting_payment"
    assert order.payment_status == "pending"
    assert order.total_minor == 76_800
    assert order.items[0].name == "Smash 101"
    assert order.items[0].modifiers[0].group_name == "Término"
    customer = session.scalar(select(Customer).where(Customer.business_id == DEMO_BUSINESS_ID))
    assert customer is not None
    assert customer.phone == "+573001234567"


def test_idempotency_returns_same_order(service):
    req = CreateOrderRequest(
        customer=CustomerIn(name="Thomas", phone="3001234567"),
        items=valid_cart(service),
        idempotency_key="same-request",
    )
    first = service.create_order(DEMO_BUSINESS_ID, req)
    second = service.create_order(DEMO_BUSINESS_ID, req)
    assert first.id == second.id


def test_payment_completion_places_order(service):
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="A", phone="3001234567"), items=valid_cart(service)),
    )
    payment = order.payments[0]
    updated = service.apply_payment_status(payment.provider_reference, "paid")
    assert updated.payment_status == "paid"
    assert updated.status == "placed"


def test_order_state_machine_rejects_skips(service):
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="A", phone="3001234567"), items=valid_cart(service)),
    )
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    with pytest.raises(InvalidTransitionError):
        service.transition_order(order.id, "ready")


def test_order_happy_path(service):
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="A", phone="3001234567"), items=valid_cart(service)),
    )
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    for status in ["accepted", "preparing", "ready", "completed"]:
        order = service.transition_order(order.id, status)
    assert order.status == "completed"


def test_event_sink_receives_transaction_events(session):
    sink = MemoryEventSink()
    service = RestaurantCommerceService(session, event_sink=sink)
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="A", phone="3001234567"), items=valid_cart(service)),
    )
    service.apply_payment_status(order.payments[0].provider_reference, "paid")
    assert [e.kind for e in sink.events] == ["order.created", "payment.updated"]


def test_reservation_validates_slots_and_party_size(service):
    starts = datetime.now(timezone.utc) + timedelta(days=1)
    starts = starts.replace(minute=0, second=0, microsecond=0)
    reservation = service.create_reservation(
        DEMO_BUSINESS_ID,
        CreateReservationRequest(
            customer=CustomerIn(name="Laura", phone="3100000000"),
            starts_at=starts,
            party_size=4,
        ),
    )
    assert reservation.party_size == 4
    assert reservation.status == "requested"

    with pytest.raises(ValidationError, match="maximum"):
        service.create_reservation(
            DEMO_BUSINESS_ID,
            CreateReservationRequest(
                customer=CustomerIn(name="Laura", phone="3100000000"),
                starts_at=starts,
                party_size=20,
            ),
        )


def test_reservation_must_be_future(service):
    with pytest.raises(ValidationError, match="future"):
        service.create_reservation(
            DEMO_BUSINESS_ID,
            CreateReservationRequest(
                customer=CustomerIn(name="Laura", phone="3100000000"),
                starts_at=datetime.now(timezone.utc) - timedelta(hours=1),
                party_size=2,
            ),
        )


def test_business_isolation(service, session):
    session.add(
        RestaurantCommerceProfile(
            business_id="other-business",
            slug="other",
            display_name="Other",
            currency="COP",
        )
    )
    session.commit()
    smash, *_ = smash_selection(service)
    with pytest.raises(ValidationError, match="does not belong"):
        service.quote("other-business", valid_cart(service))


def test_whatsapp_message_is_operational_not_sent(service):
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="A", phone="3001234567"), items=valid_cart(service)),
    )
    message = format_order_message(order)
    assert order.public_code in message
    assert "Smash 101" in message
    url = whatsapp_click_to_chat_url("+57 300 000 0000", message)
    assert url.startswith("https://wa.me/573000000000?text=")


def test_customer_summary_tracks_paid_completed_orders(service):
    order = service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(customer=CustomerIn(name="Repeat", phone="3009999999"), items=valid_cart(service)),
    )
    customer_id = service.session.get(Order, order.id).customer_id
    before = service.customer_summary(DEMO_BUSINESS_ID, customer_id)
    assert before.order_count == 0
    assert before.lifetime_value_minor == 0
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    for status in ["accepted", "preparing", "ready", "completed"]:
        order = service.transition_order(order.id, status)
    summary = service.customer_summary(DEMO_BUSINESS_ID, customer_id)
    assert summary.order_count == 1
    assert summary.lifetime_value_minor == 76_800


def test_api_public_and_operator_paths(engine):
    app = create_app(engine=engine, operator_token="secret")
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    store = client.get(f"/api/restaurants/{DEMO_BUSINESS_ID}/storefront")
    assert store.status_code == 200
    denied = client.get(f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/orders")
    assert denied.status_code == 401
    allowed = client.get(
        f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/orders",
        headers={"X-101-Operator-Token": "secret"},
    )
    assert allowed.status_code == 200


def test_api_can_place_and_complete_simulated_order(engine):
    app = create_app(engine=engine, operator_token="secret")
    client = TestClient(app)
    store = client.get(f"/api/restaurants/{DEMO_BUSINESS_ID}/storefront").json()
    smash = next(i for m in store["menus"] for c in m["categories"] for i in c["items"] if i["name"] == "Smash 101")
    term = next(g for g in smash["modifier_groups"] if g["name"] == "Término")
    payload = {
        "customer": {"name": "Web", "phone": "3001111111"},
        "items": [{
            "menu_item_id": smash["id"],
            "quantity": 1,
            "modifiers": [{"group_id": term["id"], "option_ids": [term["options"][0]["id"]]}],
        }],
        "payment_provider": "simulated",
        "idempotency_key": "web-1",
    }
    created = client.post(f"/api/restaurants/{DEMO_BUSINESS_ID}/orders", json=payload)
    assert created.status_code == 200, created.text
    order = created.json()
    ref = order["payments"][0]["provider_reference"]
    paid = client.post(f"/api/payments/simulated/{ref}/complete")
    assert paid.status_code == 200
    assert paid.json()["status"] == "placed"
