from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session

from world_model.restaurant_commerce.db import init_schema, make_engine
from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.schemas import (
    CartItemIn,
    CreateOrderRequest,
    CustomerIn,
    DeliveryAddressIn,
    ModifierSelectionIn,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


def cart_for(service: RestaurantCommerceService) -> list[CartItemIn]:
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


def main() -> None:
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "v3-reality.db"
        engine = make_engine(f"sqlite:///{db_path}")
        init_schema(engine)
        with Session(engine) as session:
            seed_demo(session)
            service = RestaurantCommerceService(session)
            growth = RestaurantGrowthService(session)

            delivery_quote = service.create_delivery_quote(
                DEMO_BUSINESS_ID,
                DeliveryAddressIn(
                    address_line="Calle 85 # 12-34",
                    city="Bogotá",
                    latitude=4.6697,
                    longitude=-74.0549,
                    instructions="Portería principal",
                ),
            )
            order = service.create_order(
                DEMO_BUSINESS_ID,
                CreateOrderRequest(
                    customer=CustomerIn(
                        name="Cliente V3",
                        phone="+57 300 555 0101",
                        whatsapp_opt_in=True,
                        marketing_opt_in=True,
                        consent_source="v3_reality_demo",
                    ),
                    items=cart_for(service),
                    fulfillment_type="delivery",
                    delivery_quote_id=delivery_quote.id,
                    promo_code="DIRECTO10",
                    payment_provider="simulated",
                    idempotency_key="v3-reality-order",
                ),
            )
            food_subtotal = order.subtotal_minor
            food_after_discount = order.subtotal_minor - order.discount_minor
            expected_total = food_after_discount + delivery_quote.fee_minor
            assert order.total_minor == expected_total
            assert order.delivery_fee_minor == delivery_quote.fee_minor

            order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
            order = service.transition_order(order.id, "accepted")
            delivery = service.dispatch_delivery(order.id)
            assert delivery.status == "courier_assigned"
            service.transition_order(order.id, "preparing")
            service.transition_order(order.id, "ready")
            delivery = service.apply_delivery_status(delivery.provider_delivery_reference, "picked_up")
            assert delivery.status == "picked_up"
            delivery = service.apply_delivery_status(delivery.provider_delivery_reference, "delivered")
            assert delivery.status == "delivered"

            final = service.order_out(order.id)
            assert final.status == "completed"
            tracking = service.delivery_tracking(order.id)
            assert tracking.status == "delivered"
            analytics = growth.analytics(DEMO_BUSINESS_ID)
            assert analytics.completed_orders == 1
            assert analytics.delivery_fees_minor == delivery_quote.fee_minor
            assert analytics.food_net_revenue_minor == food_after_discount
            assert analytics.net_revenue_minor == expected_total

            # Customer lookup for loyalty proof.
            from world_model.restaurant_commerce.models import Customer
            from sqlalchemy import select
            customer = session.scalar(select(Customer).where(Customer.business_id == DEMO_BUSINESS_ID))
            loyalty = growth.loyalty_account(DEMO_BUSINESS_ID, customer.id)
            expected_points = food_after_discount // 1000
            assert loyalty.available_points == expected_points

            result = {
                "order": {
                    "public_code": final.public_code,
                    "fulfillment_type": final.fulfillment_type,
                    "subtotal_minor": food_subtotal,
                    "discount_minor": final.discount_minor,
                    "food_net_minor": food_after_discount,
                    "delivery_fee_minor": final.delivery_fee_minor,
                    "total_minor": final.total_minor,
                    "status": final.status,
                },
                "delivery": {
                    "provider": delivery.provider,
                    "status": delivery.status,
                    "distance_meters": delivery_quote.distance_meters,
                    "tracking_url": delivery.tracking_url,
                    "courier_name": delivery.courier_name,
                },
                "loyalty": {
                    "available_points": loyalty.available_points,
                    "delivery_fee_earned_points": 0,
                },
                "analytics": analytics.model_dump(mode="json"),
                "external_network_calls": 0,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("RESTAURANT_COMMERCE_V3_REALITY_PASS")


if __name__ == "__main__":
    main()
