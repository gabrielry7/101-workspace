"""Fictitious customer directory; loopback only, no message/provider calls."""

import argparse
import json
from datetime import timedelta
from pathlib import Path
from sqlalchemy import func, select
from .signup_demo import app_for_demo as signup_app
from .campaign_demo import BUSINESS, PASSWORD, CLOCK
from .models import Customer, Order, Payment
from .customer_signup_models import CustomerAccount, CustomerMembership
from .refunds import PaymentRefund

NAMES = [
    "Lucía Fernández",
    "Mateo Restrepo",
    "Valentina Rojas",
    "Santiago Mora",
    "Isabella Torres",
    "Nicolás García",
    "Camila Rodríguez",
    "Daniel Martínez",
    "Gabriela López",
    "Sebastián Castro",
    "Mariana Gómez",
    "Alejandro Ruiz",
    "Paula Jiménez",
    "Andrés Vargas",
    "Sofía Ramírez",
    "Tomás Herrera",
    "Catalina Silva",
    "David Moreno",
    "Elena Salazar",
    "Felipe Mejía",
]


def seed(session, size=80):
    if session.scalar(select(Customer).where(Customer.id == "workspace-demo-00000")):
        return
    for old in session.scalars(
        select(Customer).where(Customer.business_id == BUSINESS)
    ):
        old.created_at = CLOCK - timedelta(days=120)
    existing = session.scalar(
        select(func.count())
        .select_from(Customer)
        .where(Customer.business_id == BUSINESS)
    )
    for i in range(max(0, size - existing)):
        c = Customer(
            id=f"workspace-demo-{i:05d}",
            business_id=BUSINESS,
            name=NAMES[i % len(NAMES)]
            + (f" {i // len(NAMES) + 1}" if i >= len(NAMES) else ""),
            email=f"cliente{i:05d}@example.test" if i % 7 or i == 0 else None,
            phone=f"+573010{i:06d}" if i % 5 else None,
            created_at=CLOCK - timedelta(hours=i * 3),
            updated_at=CLOCK,
        )
        session.add(c)
        if i % 3 != 2:
            a = CustomerAccount(
                id=f"workspace-account-{i:05d}",
                channel="email" if c.email else "phone",
                identifier=c.email or c.phone or f"fixture{i}@example.test",
                scope="test",
                verified_at=c.created_at,
            )
            session.add(a)
            session.flush()
            session.add(
                CustomerMembership(
                    account_id=a.id,
                    business_id=BUSINESS,
                    customer_id=c.id,
                    source=["qr", "website", "direct"][i % 3],
                    created_at=c.created_at,
                )
            )
    session.flush()
    c = session.get(Customer, "workspace-demo-00001")
    if c:
        o = Order(
            id="workspace-example-order",
            public_code="DEMO-101",
            business_id=BUSINESS,
            customer_id=c.id,
            customer_snapshot_json=json.dumps({"identity_verified": False}),
            status="completed",
            payment_status="paid",
            currency="COP",
            subtotal_minor=24900,
            total_minor=24900,
            prep_minutes=15,
            created_at=CLOCK,
        )
        session.add(o)
        session.flush()
        p = Payment(
            id="workspace-example-payment",
            order_id=o.id,
            provider="simulated",
            provider_reference="workspace-example-payment",
            status="paid",
            amount_minor=24900,
            currency="COP",
        )
        session.add(p)
        session.flush()
        session.add(
            PaymentRefund(
                payment_id=p.id,
                provider="simulated",
                reference="workspace-example-refund",
                amount_minor=5000,
                evidence_json='{"source":"synthetic customer workspace fixture"}',
            )
        )
    session.commit()


def app_for_demo(database_url, origin="http://127.0.0.1:8806", size=80):
    app = signup_app(database_url, origin)
    with app.state.session_factory() as session:
        seed(session, size)
    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="/tmp/101-customer-workspace.db")
    parser.add_argument("--port", type=int, default=8806)
    parser.add_argument("--customers", type=int, default=80)
    args = parser.parse_args()
    if not 10 <= args.customers <= 100000:
        parser.error("Use 10–100000 fictitious customers")
    origin = f"http://127.0.0.1:{args.port}"
    app = app_for_demo(
        "sqlite:///" + str(Path(args.db).resolve()), origin, args.customers
    )
    print("LOCAL DEMO:", origin + "/workspace/customers")
    print("campaign.manager /", PASSWORD)
    print("Fictitious contacts and payments. Codes shown locally. No provider calls.")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
