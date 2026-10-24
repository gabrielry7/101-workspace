from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.errors import ValidationError
from world_model.restaurant_commerce.models import (
    Customer,
    LoyaltyAccount,
    Order,
    OutboundMessage,
    PromotionRedemption,
    RewardDefinition,
    RewardRedemption,
)
from world_model.restaurant_commerce.schemas import (
    CartItemIn,
    CreateOrderRequest,
    CustomerIn,
    ModifierSelectionIn,
    PromotionCreateIn,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture()
def session(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'growth-v2.db'}")
    init_schema(engine)
    Session = session_factory(engine)
    try:
        with Session() as s:
            seed_demo(s)
            yield s
    finally:
        engine.dispose()


def cart(service: RestaurantCommerceService):
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


def place(service: RestaurantCommerceService, *, phone="3001111111", promo=None, reward=None, opt_in=True):
    return service.create_order(
        DEMO_BUSINESS_ID,
        CreateOrderRequest(
            customer=CustomerIn(
                name="Cliente",
                phone=phone,
                whatsapp_opt_in=opt_in,
                marketing_opt_in=opt_in,
                consent_source="checkout",
            ),
            items=cart(service),
            promo_code=promo,
            reward_id=reward,
        ),
    )


def pay_and_complete(service: RestaurantCommerceService, order):
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    for status in ["accepted", "preparing", "ready", "completed"]:
        order = service.transition_order(order.id, status)
    return order


def test_promotion_changes_server_side_quote_and_order(session):
    service = RestaurantCommerceService(session)
    q = service.quote(DEMO_BUSINESS_ID, cart(service), promo_code="directo10")
    assert q.subtotal_minor == 76800
    assert q.discounts.promotion_discount_minor == 7680
    assert q.total_minor == 69120

    order = place(service, promo="DIRECTO10")
    assert order.discount_minor == 7680
    assert order.total_minor == 69120
    redemption = session.scalar(select(PromotionRedemption).where(PromotionRedemption.order_id == order.id))
    assert redemption.status == "reserved"
    service.apply_payment_status(order.payments[0].provider_reference, "paid")
    assert redemption.status == "applied"


def test_failed_payment_releases_promotion_slot(session):
    service = RestaurantCommerceService(session)
    order = place(service, promo="DIRECTO10")
    service.apply_payment_status(order.payments[0].provider_reference, "failed")
    redemption = session.scalar(select(PromotionRedemption).where(PromotionRedemption.order_id == order.id))
    assert redemption.status == "released"


def test_completed_order_awards_points_exactly_once(session):
    service = RestaurantCommerceService(session)
    order = pay_and_complete(service, place(service))
    customer_id = session.get(Order, order.id).customer_id
    account = RestaurantGrowthService(session).loyalty_account(DEMO_BUSINESS_ID, customer_id)
    assert account.available_points == 76
    assert account.lifetime_earned_points == 76

    # Completed is terminal; querying/analytics cannot award again.
    RestaurantGrowthService(session).analytics(DEMO_BUSINESS_ID)
    account2 = RestaurantGrowthService(session).loyalty_account(DEMO_BUSINESS_ID, customer_id)
    assert account2.available_points == 76


def test_reward_reserves_points_then_applies(session):
    service = RestaurantCommerceService(session)
    first = pay_and_complete(service, place(service, phone="3002222222"))
    customer_id = session.get(Order, first.id).customer_id
    reward = session.scalar(select(RewardDefinition).where(RewardDefinition.business_id == DEMO_BUSINESS_ID))
    assert reward is not None

    second = place(service, phone="3002222222", reward=reward.id)
    assert second.reward_discount_minor == 10000
    assert second.total_minor == 66800
    account = session.scalar(select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id))
    assert account.available_points == 26
    redemption = session.scalar(select(RewardRedemption).where(RewardRedemption.order_id == second.id))
    assert redemption.status == "reserved"

    service.apply_payment_status(second.payments[0].provider_reference, "paid")
    assert redemption.status == "applied"


def test_cancelled_reward_order_returns_reserved_points(session):
    service = RestaurantCommerceService(session)
    first = pay_and_complete(service, place(service, phone="3003333333"))
    customer_id = session.get(Order, first.id).customer_id
    reward = session.scalar(select(RewardDefinition).where(RewardDefinition.business_id == DEMO_BUSINESS_ID))
    second = place(service, phone="3003333333", reward=reward.id)
    account = session.scalar(select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id))
    assert account.available_points == 26
    service.transition_order(second.id, "cancelled")
    assert account.available_points == 76
    redemption = session.scalar(select(RewardRedemption).where(RewardRedemption.order_id == second.id))
    assert redemption.status == "released"


def test_review_request_is_queued_only_with_whatsapp_consent(session):
    service = RestaurantCommerceService(session)
    opted = pay_and_complete(service, place(service, phone="3004444444", opt_in=True))
    msg = session.scalar(select(OutboundMessage).where(OutboundMessage.order_id == opted.id))
    assert msg.message_kind == "review_request"
    assert msg.status == "queued"
    assert msg.purpose == "service_followup"

    not_opted = pay_and_complete(service, place(service, phone="3005555555", opt_in=False))
    suppressed = session.scalar(select(OutboundMessage).where(OutboundMessage.order_id == not_opted.id))
    assert suppressed.status == "suppressed"
    assert suppressed.suppression_reason == "WHATSAPP_OPT_IN_REQUIRED"


def test_winback_requires_marketing_consent_and_dedupes(session):
    service = RestaurantCommerceService(session)
    old = pay_and_complete(service, place(service, phone="3006666666", opt_in=True))
    customer = session.get(Customer, session.get(Order, old.id).customer_id)
    customer.last_order_at = datetime.now(timezone.utc) - timedelta(days=60)
    session.commit()

    growth = RestaurantGrowthService(session)
    rows = growth.plan_winback(DEMO_BUSINESS_ID, as_of=datetime.now(timezone.utc), dormant_days=30)
    session.commit()
    rows2 = growth.plan_winback(DEMO_BUSINESS_ID, as_of=datetime.now(timezone.utc), dormant_days=30)
    session.commit()
    assert len(rows) == 1
    assert rows[0].status == "queued"
    assert len(rows2) == 1
    assert rows2[0].id == rows[0].id

    # Same business, opted into WhatsApp but not marketing => suppression.
    quiet = pay_and_complete(service, place(service, phone="3007777777", opt_in=False))
    quiet_customer = session.get(Customer, session.get(Order, quiet.id).customer_id)
    quiet_customer.whatsapp_opt_in = True
    quiet_customer.marketing_opt_in = False
    quiet_customer.last_order_at = datetime.now(timezone.utc) - timedelta(days=60)
    session.commit()
    planned = growth.plan_winback(DEMO_BUSINESS_ID, as_of=datetime.now(timezone.utc), dormant_days=30)
    session.commit()
    quiet_msg = next(r for r in planned if r.customer_id == quiet_customer.id)
    assert quiet_msg.status == "suppressed"
    assert quiet_msg.suppression_reason == "MARKETING_OPT_IN_REQUIRED"


def test_growth_analytics_reports_completed_commerce(session):
    service = RestaurantCommerceService(session)
    pay_and_complete(service, place(service, phone="3008888888", promo="DIRECTO10"))
    pay_and_complete(service, place(service, phone="3008888888"))
    pay_and_complete(service, place(service, phone="3009999999"))

    analytics = RestaurantGrowthService(session).analytics(DEMO_BUSINESS_ID)
    assert analytics.completed_orders == 3
    assert analytics.unique_customers == 2
    assert analytics.repeat_customers == 1
    assert analytics.repeat_customer_rate == pytest.approx(0.5)
    assert analytics.gross_revenue_minor == 230400
    assert analytics.discount_minor == 7680
    assert analytics.net_revenue_minor == 222720
    assert analytics.channel_order_counts == {"web": 3}


def test_operator_growth_api_is_protected_and_operational(session):
    engine = session.get_bind()
    app = create_app(engine=engine, operator_token="secret")
    client = TestClient(app)

    denied = client.get(f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/analytics")
    assert denied.status_code == 401
    headers = {"X-101-Operator-Token": "secret"}
    ok = client.get(f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/analytics", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["completed_orders"] == 0

    created = client.post(
        f"/api/operator/restaurants/{DEMO_BUSINESS_ID}/promotions",
        headers=headers,
        json={
            "code": "VUELVE5",
            "name": "Vuelve",
            "discount_type": "fixed",
            "value": 5000,
            "minimum_order_minor": 20000,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["code"] == "VUELVE5"


def test_reward_cannot_be_spent_without_points(session):
    service = RestaurantCommerceService(session)
    reward = session.scalar(select(RewardDefinition).where(RewardDefinition.business_id == DEMO_BUSINESS_ID))
    with pytest.raises(ValidationError, match="Not enough loyalty points"):
        place(service, phone="3010000000", reward=reward.id)


def test_promotion_per_customer_limit_is_enforced(session):
    service = RestaurantCommerceService(session)
    phone = "3011111111"
    first = place(service, phone=phone, promo="DIRECTO10")
    service.apply_payment_status(first.payments[0].provider_reference, "paid")
    second = place(service, phone=phone, promo="DIRECTO10")
    service.apply_payment_status(second.payments[0].provider_reference, "paid")
    with pytest.raises(ValidationError, match="Customer promotion limit reached"):
        place(service, phone=phone, promo="DIRECTO10")
