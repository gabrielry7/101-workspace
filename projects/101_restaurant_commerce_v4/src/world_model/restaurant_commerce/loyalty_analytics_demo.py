"""Explicit loopback synthetic Stage7 fixture, with real-time incomplete follow-up."""

import argparse
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from .campaign_demo import BUSINESS
from .loyalty_assignment import LoyaltyAssignmentService
from .loyalty_config import LoyaltyConfigurationService
from .loyalty_measurement_evidence import OperatingCost, OrderCosts, context, record
from .loyalty_models import LoyaltyExperiment, LoyaltyStrategyVersion
from .loyalty_schemas import ExperimentCreate, Publish
from .loyalty_workspace_demo import app_for_demo as console_app
from .models import Customer, utcnow
from .schemas import CreateOrderRequest
from .service import RestaurantCommerceService


def app_for_demo(database_url, origin="http://127.0.0.1:8831"):
    app = console_app(database_url, origin, analytics_enabled=True)
    with app.state.session_factory() as s:
        key = "synthetic-profit-analysis-v1"
        if s.scalar(
            select(LoyaltyExperiment.id).where(
                LoyaltyExperiment.business_id == BUSINESS,
                LoyaltyExperiment.request_key == key,
            )
        ):
            return app  # Never overwrite an operator's corrections on restart.
        now = utcnow()
        program = s.scalar(
            select(LoyaltyStrategyVersion)
            .where(LoyaltyStrategyVersion.business_id == BUSINESS)
            .order_by(LoyaltyStrategyVersion.published_at)
        )
        cfg = LoyaltyConfigurationService(s, "synthetic-demo")
        draft = cfg.create(
            "experiments",
            BUSINESS,
            ExperimentCreate.model_validate(
                {
                    "request_key": key,
                    "document": {
                        "name": "Próximas visitas · medición en curso",
                        "description": "Cohorte y costos ficticios. El seguimiento acaba de empezar; todavía no hay una evaluación final.",
                        "currency": "COP",
                        "enrollment_start": now,
                        "enrollment_end": now + timedelta(days=30),
                        "observation_days": 60,
                        "exclusion_group": "analytics-demo",
                        "variants": [
                            {"name": "Control", "allocation_bps": 5000},
                            {
                                "name": "Puntos adicionales",
                                "allocation_bps": 5000,
                                "strategy_version_id": program.id,
                            },
                        ],
                        "analysis_plan": "Comparar la ganancia de contribución por cada cliente originalmente asignado en sesenta días, incluidos quienes no compren. Costos y órdenes son sintéticos.",
                        "analysis_protocol": {
                            "readout_at": now + timedelta(days=90),
                            "minimum_customers_per_arm": 100,
                            "sample_size_rationale": "Cien por grupo es una elección ilustrativa; no un cálculo de potencia para un negocio real.",
                        },
                    },
                }
            ),
        )
        version = cfg.publish(
            "experiments",
            BUSINESS,
            draft["id"],
            Publish(expected_revision=draft["revision"], digest=draft["digest"]),
        )["version_id"]
        customers = s.scalars(
            select(Customer)
            .where(
                Customer.business_id == BUSINESS,
                Customer.id.like("workspace-demo-%"),
                Customer.id != "workspace-demo-00001",
            )
            .order_by(Customer.id)
            .limit(40)
        ).all()
        variants = set()
        for i, customer in enumerate(customers):
            enrolled = LoyaltyAssignmentService(
                s, "synthetic-demo", enabled=True, mode="synthetic"
            ).enroll(
                BUSINESS,
                version,
                verified_customer_id=customer.id,
                identity_evidence_ref="synthetic-demo",
                request_key=key + customer.id,
            )
            s.commit()
            variants.add(enrolled["assignment"]["variant_id"])
            if i % 4:
                continue
            svc = RestaurantCommerceService(s, verified_customer_id=customer.id)
            item = next(
                i
                for m in svc.storefront(BUSINESS).menus
                for c in m.categories
                for i in c.items
                if not i.modifier_groups
            )
            order = svc.create_order(
                BUSINESS,
                CreateOrderRequest.model_validate(
                    {
                        "customer": {
                            "name": customer.name,
                            "phone": customer.phone,
                            "email": customer.email,
                        },
                        "items": [{"menu_item_id": item.id, "quantity": 1}],
                        "idempotency_key": key + customer.id,
                    }
                ),
            )
            svc.apply_payment_status(order.payments[0].provider_reference, "paid")
            for state in ["accepted", "preparing", "ready", "completed"]:
                order = svc.transition_order(order.id, state)
            current = context(s, BUSINESS, "orders", order.id)
            record(
                s,
                BUSINESS,
                "orders",
                order.id,
                OrderCosts(
                    request_key=key + order.id,
                    expected_revision=0,
                    financial_digest=current["financial_digest"],
                    source_ref="synthetic-example-cost-assumption",
                    includes_estimate=True,
                    variable_cost_minor=order.total_minor * 7 // 10,
                    additional_reward_cost_minor=200,
                ),
                "synthetic-demo",
            )
        for variant in variants:
            current = context(s, BUSINESS, "variants", variant)
            record(
                s,
                BUSINESS,
                "variants",
                variant,
                OperatingCost(
                    request_key=key + variant,
                    expected_revision=0,
                    financial_digest=current["financial_digest"],
                    source_ref="synthetic-example-operating-assumption",
                    includes_estimate=True,
                    operating_cost_minor=30000,
                ),
                "synthetic-demo",
            )
    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--port", default=8831, type=int)
    args = parser.parse_args()
    origin = f"http://127.0.0.1:{args.port}"
    app = app_for_demo("sqlite:///" + str(Path(args.db).resolve()), origin)
    print(
        "LOCAL SYNTHETIC DEMO:",
        origin + "/workspace/customers?view=loyalty&loyaltyTab=results",
    )
    print("101 / 101 (temporary local demonstration login)")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
