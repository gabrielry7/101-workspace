"""Loopback-only loyalty console fixture. All contacts and payments are fictitious."""

import argparse
from pathlib import Path

from sqlalchemy import select

from .workspace_demo import app_for_demo as workspace_app
from .campaign_demo import BUSINESS
from .db import init_schema, make_engine
from .loyalty_assignment import LoyaltyAssignmentService
from .loyalty_assignment_migrations import upgrade_loyalty_assignment
from .loyalty_config import LoyaltyConfigurationService
from .loyalty_execution import ExecutionSelection
from .loyalty_execution_migrations import upgrade_loyalty_execution
from .loyalty_migrations import upgrade_loyalty_configuration
from .loyalty_models import LoyaltyStrategy
from .loyalty_schemas import ExperimentCreate, Publish, StrategyCreate
from .models import Customer, utcnow
from .schemas import CreateOrderRequest
from .service import RestaurantCommerceService


def app_for_demo(database_url, origin="http://127.0.0.1:8810", size=80):
    from datetime import timedelta

    engine = make_engine(database_url)
    init_schema(engine)
    upgrade_loyalty_configuration(engine)
    upgrade_loyalty_execution(engine)
    upgrade_loyalty_assignment(engine)
    # Extend the shared local app: one login, campaign transports and commerce fixtures.
    app = workspace_app(
        database_url,
        origin,
        engine=engine,
        loyalty_configuration_enabled=True,
        size=size,
    )
    with app.state.session_factory() as session:
        if session.scalar(
            select(LoyaltyStrategy.id).where(
                LoyaltyStrategy.business_id == BUSINESS,
                LoyaltyStrategy.request_key == "synthetic-loyalty-console",
            )
        ):
            return app  # Restarting never publishes or edits an operator's draft.
        config = LoyaltyConfigurationService(session, "synthetic-demo")
        program = config.create(
            "programs",
            BUSINESS,
            StrategyCreate.model_validate(
                {
                    "request_key": "synthetic-loyalty-console",
                    "document": {
                        "name": "Puntos para la próxima visita",
                        "description": "Ejemplo ficticio para revisar reglas y costos.",
                        "currency": "COP",
                        "earning": {
                            "type": "points",
                            "spend_minor_per_point": 1000,
                            "points_per_unit": 2,
                        },
                        "reward": {
                            "type": "fixed_value",
                            "points_cost": 10,
                            "discount_minor": 1000,
                        },
                        "maximum_reward_minor": 10000,
                        "per_customer_budget_minor": 50000,
                        "campaign_budget_minor": 1000000,
                        "estimated_cost_per_point_minor": 10,
                        "expiration_days": 30,
                    },
                }
            ),
        )
        version = config.publish(
            "programs",
            BUSINESS,
            program["id"],
            Publish(expected_revision=program["revision"], digest=program["digest"]),
        )
        customer = session.get(Customer, "workspace-demo-00001")
        service = RestaurantCommerceService(
            session,
            verified_customer_id=customer.id,
            loyalty_execution=ExecutionSelection(
                version["version_id"], False, True, "synthetic_tax_exclusive"
            ),
        )
        item = next(
            i
            for m in service.storefront(BUSINESS).menus
            for c in m.categories
            for i in c.items
            if not i.modifier_groups
        )
        order = service.create_order(
            BUSINESS,
            CreateOrderRequest.model_validate(
                {
                    "customer": {"name": customer.name, "phone": customer.phone},
                    "items": [{"menu_item_id": item.id, "quantity": 1}],
                    "idempotency_key": "synthetic-loyalty-order",
                }
            ),
        )
        service.apply_payment_status(order.payments[0].provider_reference, "paid")
        for status in ["accepted", "preparing", "ready", "completed"]:
            service.transition_order(order.id, status)
        # A genuine confirmed synthetic refund, intentionally awaiting allocation.
        from .refunds import record_refund

        record_refund(
            service,
            "simulated",
            {
                "provider_reference": order.payments[0].provider_reference,
                "amount_minor": order.total_minor,
                "currency": order.currency,
                "refund_reference": "synthetic-loyalty-refund",
                "refund_amount_minor": 1000,
                "event_id": "synthetic-loyalty-refund",
            },
            '{"source":"synthetic loyalty console"}',
        )
        now = utcnow()
        experiment = config.create(
            "experiments",
            BUSINESS,
            ExperimentCreate.model_validate(
                {
                    "request_key": "synthetic-loyalty-experiment",
                    "document": {
                        "name": "Próxima visita · comparación inicial",
                        "currency": "COP",
                        "description": "Demostración de control y oferta adicional; no mide resultados reales.",
                        "enrollment_start": now,
                        "enrollment_end": now + timedelta(days=30),
                        "exclusion_group": "loyalty",
                        "observation_days": 60,
                        "analysis_plan": "Comparar la contribución por cliente asignado durante 60 días, incluidos quienes no compren.",
                        "variants": [
                            {"name": "Control", "allocation_bps": 5000},
                            {
                                "name": "Puntos adicionales",
                                "allocation_bps": 5000,
                                "strategy_version_id": version["version_id"],
                            },
                        ],
                    },
                }
            ),
        )
        ev = config.publish(
            "experiments",
            BUSINESS,
            experiment["id"],
            Publish(
                expected_revision=experiment["revision"], digest=experiment["digest"]
            ),
        )
        LoyaltyAssignmentService(
            session, "synthetic-demo", enabled=True, mode="synthetic"
        ).enroll(
            BUSINESS,
            ev["version_id"],
            verified_customer_id=customer.id,
            identity_evidence_ref="synthetic-demo-identity",
            request_key="synthetic-console-enrollment",
        )
        session.commit()
    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--port", type=int, default=8810)
    args = parser.parse_args()
    origin = f"http://127.0.0.1:{args.port}"
    app = app_for_demo("sqlite:///" + str(Path(args.db).resolve()), origin)
    print("LOCAL FICTITIOUS DEMO:", origin + "/workspace/customers?view=loyalty")
    print("101 / 101 (temporary local demo login)")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
