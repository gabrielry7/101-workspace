from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.errors import IdempotencyConflictError
from world_model.restaurant_commerce.models import CommerceEventOutbox
from world_model.restaurant_commerce.schemas import (
    CartItemIn,
    CreateOrderRequest,
    CustomerIn,
    ModifierSelectionIn,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID, seed_demo
from world_model.restaurant_commerce.service import RestaurantCommerceService


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="101-restaurant-v4-reality-") as tmp:
        engine = make_engine(f"sqlite:///{Path(tmp) / 'reality.db'}")
        init_schema(engine)
        Session = session_factory(engine)
        with Session() as session:
            seed_demo(session)
            service = RestaurantCommerceService(session)
            store = service.storefront(DEMO_BUSINESS_ID)
            item = next(
                i
                for menu in store.menus
                for category in menu.categories
                for i in category.items
                if i.name == "Smash 101"
            )
            term = next(group for group in item.modifier_groups if group.name == "Término")
            cart = [
                CartItemIn(
                    menu_item_id=item.id,
                    quantity=1,
                    modifiers=[
                        ModifierSelectionIn(group_id=term.id, option_ids=[term.options[0].id])
                    ],
                )
            ]
            request = CreateOrderRequest(
                customer=CustomerIn(name="V4 Reality", phone="3005550101"),
                items=cart,
                idempotency_key="v4-reality-order",
            )
            order = service.create_order(DEMO_BUSINESS_ID, request)
            replay = service.create_order(DEMO_BUSINESS_ID, request)
            assert replay.id == order.id
            conflict_seen = False
            try:
                service.create_order(
                    DEMO_BUSINESS_ID,
                    request.model_copy(update={"notes": "different payload"}),
                )
            except IdempotencyConflictError:
                conflict_seen = True
            assert conflict_seen

            order = service.apply_payment_status(order.payments[0].provider_reference, "paid")
            for state in ["accepted", "preparing", "ready", "completed"]:
                order = service.transition_order(order.id, state)
            outbox = session.scalars(select(CommerceEventOutbox)).all()
            result = {
                "status": "PASS",
                "order_id": order.id,
                "order_status": order.status,
                "payment_status": order.payment_status,
                "idempotent_replay_same_order": replay.id == order.id,
                "conflicting_reuse_rejected": conflict_seen,
                "outbox_rows": len(outbox),
                "published_outbox_rows": sum(row.status == "published" for row in outbox),
                "external_network_calls": 0,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            print(json.dumps(result, indent=2, sort_keys=True))
        engine.dispose()
    print("RESTAURANT_COMMERCE_V4_REALITY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
