"""Explicit local Sales fixtures over canonical records. No provider calls."""

import argparse
import json
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select
from .customer_workspace_demo import app_for_demo as customer_app
from .campaign_demo import BUSINESS, OTHER, CLOCK, PASSWORD
from .models import (
    Customer,
    Order,
    OrderItem,
    Payment,
    PaymentReconciliation,
    StaffAccount,
)
from .staff import provision


def seed_sales(session):
    if session.get(Order, "workspace-sale-000"):
        return
    customers = list(
        session.scalars(
            select(Customer)
            .where(Customer.business_id == BUSINESS)
            .order_by(Customer.created_at.desc(), Customer.id)
        )
    )
    statuses = [
        "placed",
        "preparing",
        "ready",
        "accepted",
        "awaiting_payment",
        "completed",
    ]
    for i in range(30):
        customer = customers[(i + 3) % len(customers)]
        status = statuses[i % len(statuses)]
        cash = i in (8, 14)
        paid = status != "awaiting_payment" and not cash
        qty = 1 + i % 3
        subtotal = 24900 * qty
        discount = 1000 if i % 4 == 0 else 0
        order = Order(
            id=f"workspace-sale-{i:03}",
            public_code=f"DEMO-{201 + i}",
            business_id=BUSINESS,
            customer_id=customer.id,
            customer_snapshot_json=json.dumps(
                {
                    "name": customer.name,
                    "phone": customer.phone or "",
                    "identity_verified": False,
                }
            ),
            status=status,
            payment_status="paid" if paid else "unpaid",
            fulfillment_type="delivery" if i == 20 else "pickup",
            subtotal_minor=subtotal,
            promotion_discount_minor=discount,
            discount_minor=discount,
            total_minor=subtotal - discount,
            prep_minutes=15,
            currency="COP",
            created_at=CLOCK - timedelta(minutes=7 * i),
            notes="Pedido ficticio para revisar el flujo." if i == 0 else None,
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                name_snapshot="Producto de prueba",
                quantity=qty,
                unit_base_price_minor=24900,
                line_total_minor=subtotal,
            )
        )
        session.add(
            Payment(
                order_id=order.id,
                provider="cash_at_pickup" if cash else "simulated",
                provider_reference=f"workspace-sale-payment-{i:03}",
                status="paid" if paid else "pending",
                amount_minor=order.total_minor,
                currency="COP",
            )
        )
        if i == 12:
            session.add(
                PaymentReconciliation(
                    order_id=order.id,
                    business_id=BUSINESS,
                    reason="synthetic-review",
                    evidence_json='{"source":"local fixture"}',
                )
            )
    foreign = session.scalar(select(Customer).where(Customer.business_id == OTHER))
    session.add(
        Order(
            id="workspace-foreign-sale",
            public_code="OTHER-01",
            business_id=OTHER,
            customer_id=foreign.id,
            status="placed",
            payment_status="unpaid",
            subtotal_minor=100,
            total_minor=100,
            prep_minutes=0,
        )
    )
    session.commit()
    if not session.scalar(
        select(StaffAccount).where(StaffAccount.username == "sales.viewer")
    ):
        provision(
            session,
            "sales.viewer",
            PASSWORD,
            BUSINESS,
            "viewer",
            actor="synthetic-fixture",
        )


def app_for_demo(database_url, origin="http://127.0.0.1:8808"):
    app = customer_app(database_url, origin)
    with app.state.session_factory() as session:
        seed_sales(session)
    return app


def main():
    import uvicorn

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="/tmp/101-sales-demo.db")
    p.add_argument("--port", type=int, default=8808)
    args = p.parse_args()
    origin = f"http://127.0.0.1:{args.port}"
    app = app_for_demo("sqlite:///" + str(Path(args.db).resolve()), origin)
    print("DEMO ONLY:", origin + "/workspace/sales", "; campaign.manager /", PASSWORD)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
