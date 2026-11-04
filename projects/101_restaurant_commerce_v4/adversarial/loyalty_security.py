"""Real optional-schema fixtures. Trusted selection is not public enrollment proof."""

from datetime import UTC, datetime
from uuid import uuid4

from security_fixtures import Fixtures
from sqlalchemy import select
from sqlalchemy.orm import Session
from world_model.restaurant_commerce.loyalty_execution import ExecutionSelection
from world_model.restaurant_commerce.models import Customer, LoyaltyAccount, Order, Payment
from world_model.restaurant_commerce.refunds import PaymentRefund, record_refund
from world_model.restaurant_commerce.schemas import CreateOrderRequest
from world_model.restaurant_commerce.service import RestaurantCommerceService

PREVIEW = (
    "/api/operator/restaurants/{business_id}/loyalty-config/programs/"
    "{resource_id}/versions/{version_id}/preview"
)
ALLOCATION = "/api/finance/restaurants/{business_id}/loyalty-refunds/{refund_id}/allocation"
DOCUMENT = {
    "name": "Synthetic security points",
    "currency": "COP",
    "earning": {"type": "points", "spend_minor_per_point": 1000},
    "maximum_reward_minor": 10000,
    "per_customer_budget_minor": 50000,
    "campaign_budget_minor": 1000000,
    "estimated_cost_per_point_minor": 10,
}


class LoyaltyFixtures(Fixtures):
    def __init__(self, config):
        super().__init__(config)
        assert "restaurant_loyalty_refund_allocations" in self.installed_tables
        self.programs = {}
        for business in config["business_ids"]:
            root = f"/api/operator/restaurants/{business}/loyalty-config/programs"
            draft = self.call(
                "POST",
                root,
                {"request_key": uuid4().hex, "document": DOCUMENT},
                headers=config["dual_staff_headers"],
            )
            version = self.call(
                "POST",
                root + "/" + draft["id"] + "/publish",
                {"expected_revision": draft["revision"], "digest": draft["digest"]},
                headers=config["dual_staff_headers"],
            )
            store = self.call("GET", f"/api/restaurants/{business}/storefront")
            item = next(
                i
                for m in store["menus"]
                for cat in m["categories"]
                for i in cat["items"]
                if i["available"] and not i["modifier_groups"]
            )
            self.programs[business] = {
                "resource_id": draft["id"],
                "version_id": version["version_id"],
                "item_id": item["id"],
            }

    def preview(self, business=None):
        business = business or self.business
        program = self.programs[business]
        ids = {"business_id": business, **program}
        body = {
            "currency": "COP",
            "at": datetime.now(UTC).isoformat(),
            "lines": [
                {
                    "line_id": "synthetic-line",
                    "product_id": program["item_id"],
                    "subtotal_minor": 10000,
                }
            ],
            "customer_id": self.config["customer_ids"][self.config["business_ids"].index(business)],
        }
        return ids, body

    def allocation(self, business=None):
        business = business or self.business
        program = self.programs[business]
        # Real domain selection uses the controlled Stage3 seam. Public enrollment remains off.
        with Session(self.engine) as session:
            phone = "300" + str(uuid4().int)[:10]
            customer = Customer(business_id=business, name="Synthetic S03", phone=phone)
            session.add(customer)
            session.commit()
            cid = customer.id
            svc = RestaurantCommerceService(
                session,
                verified_customer_id=cid,
                loyalty_execution=ExecutionSelection(
                    program["version_id"], False, True, "synthetic_tax_exclusive"
                ),
            )
            order = svc.create_order(
                business,
                CreateOrderRequest.model_validate(
                    {
                        "customer": {"name": "Synthetic S03", "phone": phone},
                        "items": [{"menu_item_id": program["item_id"], "quantity": 1}],
                        "idempotency_key": uuid4().hex,
                    }
                ),
            )
            # Explicit simulator seam, no remote-provider success claim.
            svc.apply_payment_status(order.payments[0].provider_reference, "paid")
            for state in ["accepted", "preparing", "ready", "completed"]:
                svc.transition_order(order.id, state)
            payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
            reference = "s03-" + uuid4().hex
            record_refund(
                svc,
                "simulated",
                {
                    "provider_reference": payment.provider_reference,
                    "amount_minor": payment.amount_minor,
                    "currency": payment.currency,
                    "refund_reference": reference,
                    "refund_amount_minor": 1001,
                    "event_id": reference,
                },
                '{"source":"synthetic authenticated-adapter seam"}',
            )
            refund = session.scalar(
                select(PaymentRefund).where(PaymentRefund.reference == reference)
            )
            line = session.get(Order, order.id).items[0].id
            account = session.scalar(
                select(LoyaltyAccount).where(LoyaltyAccount.customer_id == cid)
            )
            ids = {"business_id": business, "refund_id": refund.id}
            info = {
                "order_id": order.id,
                "customer_id": cid,
                "account_id": account.id,
                "before_points": account.available_points,
                "total_minor": order.total_minor,
            }
        return ids, {"lines": {line: 1001}, "delivery_fee_minor": 0}, info

    def snapshot(self):
        # The legacy snapshot omitted confirmed refund history and event outbox.
        # Include every durable financial effect needed for optional allocation proof.
        import json

        from world_model.restaurant_commerce.models import Base

        result = json.loads(super().snapshot())
        with self.engine.connect() as conn:
            for name in ["restaurant_payment_refunds", "restaurant_event_outbox"]:
                if name not in self.installed_tables:
                    if name == "restaurant_payment_refunds":
                        raise AssertionError("Refund history missing")
                    continue
                result[name] = sorted(
                    (dict(r) for r in conn.execute(select(Base.metadata.tables[name])).mappings()),
                    key=lambda r: str(r.get("id", "")),
                )
        self.invariant_tables = sorted(result)
        return json.dumps(result, sort_keys=True, default=str)
