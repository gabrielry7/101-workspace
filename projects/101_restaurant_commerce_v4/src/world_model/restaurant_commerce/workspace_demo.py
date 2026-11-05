"""Unified local workspace with fictitious commerce and campaign records only."""

import argparse
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select
from .api import create_app
from .customer_workspace_demo import seed
from .sales_workspace_demo import seed_sales
from .signup_demo import FakePhoneVerifier
from .campaign_delivery import FakeTransport
from .campaign_demo import BUSINESS, OTHER, CLOCK, PASSWORD, seed_campaign_demo
from .campaign_models import Campaign
from .models import Customer
from .campaigns import Draft, save_draft, approve, schedule


def seed_workspace(session):
    if session.scalar(select(Campaign).where(Campaign.business_id == BUSINESS)):
        return
    ids = list(
        session.scalars(
            select(Customer.id).where(
                Customer.business_id == BUSINESS,
                Customer.email.like("persona%@example.test"),
            )
        )
    )
    for i, subject in enumerate(
        [
            "Una invitación para volver",
            "Un saludo de Honorato",
            "Novedades de la semana",
        ]
    ):
        draft = Draft(
            channel="email",
            sender="demostracion@example.test",
            content={
                "subject": subject,
                "title": "Nos vemos por aquí",
                "body": "Este es un mensaje de ejemplo para revisar el diseño y el flujo de una campaña. Puedes escribir tu propio mensaje antes de aprobarlo.",
                "terms": "Contenido ficticio. No hay una oferta comercial ni mensajes reales en esta demostración.",
            },
            customer_ids=ids,
            scheduled_at=CLOCK + timedelta(hours=i),
            expires_at=CLOCK + timedelta(days=2),
            scope="test",
            budget_microusd=1000000,
        )
        result = save_draft(session, BUSINESS, draft, CLOCK)
        if i > 0:
            approve(
                session,
                BUSINESS,
                result["id"],
                result["digest"],
                "synthetic-workspace-fixture",
                CLOCK,
            )
        if i == 2:
            schedule(session, BUSINESS, result["id"], result["digest"], CLOCK)


def app_for_demo(
    database_url,
    origin="http://127.0.0.1:8809",
    *,
    engine=None,
    loyalty_configuration_enabled=False,
    loyalty_analytics_enabled=False,
    size=80,
):
    # Compose the existing fixture owners with their explicit fake transports.
    # The signup-only demo deliberately has no campaign integration configured.
    options = {
        "integrations": {
            "honorato-test": {
                "business_id": BUSINESS,
                "scope": "test",
                "adapter": FakeTransport(),
            },
            "other-test": {
                "business_id": OTHER,
                "scope": "test",
                "adapter": FakeTransport("other-test-secret"),
            },
        },
        "clock": lambda: CLOCK,
        "base_url": origin,
    }
    app = create_app(
        database_url=database_url,
        engine=engine,
        loyalty_configuration_enabled=loyalty_configuration_enabled,
        loyalty_analytics_enabled=loyalty_analytics_enabled,
        demo_mode=True,
        environment="development",
        payment_recovery_enabled=False,
        campaign_options=options,
        webhook_secrets={"simulated": "synthetic-campaign-payment-secret"},
        signup_options={
            "mode": "test",
            "public_origin": origin,
            "adapters": {
                "phone": FakePhoneVerifier(),
                "email": FakePhoneVerifier("synthetic-email-only"),
            },
            "allowed_regions": ["CO", "US", "MX", "ES"],
        },
    )
    app.state.campaign_options = options
    # Temporary local-review shortcut; remove this assignment to retire 101/101.
    app.state.workspace_demo_login = ("campaign.manager", PASSWORD)
    with app.state.session_factory() as s:
        seed_campaign_demo(s)
        seed(s, size)
        seed_sales(s)
        seed_workspace(s)
    return app


def main():
    import uvicorn

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="/tmp/101-workspace-demo.db")
    p.add_argument("--port", type=int, default=8809)
    args = p.parse_args()
    app = app_for_demo(
        "sqlite:///" + str(Path(args.db).resolve()), f"http://127.0.0.1:{args.port}"
    )
    print(
        "TEST ONLY",
        f"http://127.0.0.1:{args.port}/workspace/home",
        "101 / 101 (temporary local demo login)",
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
