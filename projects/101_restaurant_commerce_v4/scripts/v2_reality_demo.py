from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from sqlalchemy import select

from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.models import Customer, Order, RewardDefinition
from world_model.restaurant_commerce.schemas import CartItemIn, CreateOrderRequest, CustomerIn, ModifierSelectionIn
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


def cart(service: RestaurantCommerceService):
    store = service.storefront(DEMO_BUSINESS_ID)
    item = next(i for m in store.menus for c in m.categories for i in c.items if i.name == "Smash 101")
    term = next(g for g in item.modifier_groups if g.name == "Término")
    extras = next(g for g in item.modifier_groups if g.name == "Extras")
    return [CartItemIn(
        menu_item_id=item.id,
        quantity=2,
        modifiers=[
            ModifierSelectionIn(group_id=term.id, option_ids=[term.options[0].id]),
            ModifierSelectionIn(group_id=extras.id, option_ids=[extras.options[0].id]),
        ],
    )]


def complete(service: RestaurantCommerceService, order):
    order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
    for status in ["accepted", "preparing", "ready", "completed"]:
        order = service.transition_order(order.id, status)
    return order


def main() -> None:
    db = Path("/tmp/101-restaurant-commerce-v2-reality.db")
    if db.exists():
        db.unlink()
    engine = make_engine(f"sqlite:///{db}")
    init_schema(engine)
    Session = session_factory(engine)
    with Session() as session:
        seed_demo(session)
        commerce = RestaurantCommerceService(session)
        growth = RestaurantGrowthService(session)

        first = complete(commerce, commerce.create_order(
            DEMO_BUSINESS_ID,
            CreateOrderRequest(
                customer=CustomerIn(
                    name="Ana",
                    phone="+573001111111",
                    whatsapp_opt_in=True,
                    marketing_opt_in=True,
                    consent_source="web_checkout",
                ),
                items=cart(commerce),
                promo_code="DIRECTO10",
                idempotency_key="v2-demo-1",
            ),
        ))
        first_model = session.get(Order, first.id)
        customer_id = first_model.customer_id
        after_first = growth.loyalty_account(DEMO_BUSINESS_ID, customer_id)

        reward = session.scalar(select(RewardDefinition).where(RewardDefinition.business_id == DEMO_BUSINESS_ID))
        second = complete(commerce, commerce.create_order(
            DEMO_BUSINESS_ID,
            CreateOrderRequest(
                customer=CustomerIn(
                    name="Ana",
                    phone="+573001111111",
                    whatsapp_opt_in=True,
                    marketing_opt_in=True,
                    consent_source="web_checkout",
                ),
                items=cart(commerce),
                reward_id=reward.id,
                idempotency_key="v2-demo-2",
            ),
        ))
        after_second = growth.loyalty_account(DEMO_BUSINESS_ID, customer_id)

        quiet = complete(commerce, commerce.create_order(
            DEMO_BUSINESS_ID,
            CreateOrderRequest(
                customer=CustomerIn(name="Luis", phone="+573002222222"),
                items=cart(commerce),
                idempotency_key="v2-demo-3",
            ),
        ))

        ana = session.get(Customer, customer_id)
        ana.last_order_at = datetime.now(timezone.utc) - timedelta(days=45)
        session.commit()
        growth.plan_winback(DEMO_BUSINESS_ID, as_of=datetime.now(timezone.utc), dormant_days=30)
        session.commit()

        analytics = growth.analytics(DEMO_BUSINESS_ID)
        outbox = growth.list_outbox(DEMO_BUSINESS_ID)

        result = {
            "first_order": {
                "code": first.public_code,
                "subtotal_minor": first.subtotal_minor,
                "discount_minor": first.discount_minor,
                "total_minor": first.total_minor,
                "points_after": after_first.available_points,
            },
            "reward_order": {
                "code": second.public_code,
                "reward_discount_minor": second.reward_discount_minor,
                "total_minor": second.total_minor,
                "points_after": after_second.available_points,
            },
            "non_opted_order": {"code": quiet.public_code},
            "analytics": analytics.model_dump(mode="json"),
            "outbox": [m.model_dump(mode="json") for m in outbox],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("RESTAURANT_COMMERCE_V2_REALITY_PASS")


if __name__ == "__main__":
    main()
