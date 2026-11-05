"""Scoped read-only results; only financial staff may supply cost evidence."""

# FastAPI resolves these dependency defaults per request.
# ruff: noqa: B008
import csv
import io

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from .loyalty_analytics import report
from .loyalty_measurement_evidence import OperatingCost, OrderCosts, context, record
from .loyalty_read_snapshot import committed_snapshot


def csv_report(result):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "report_version",
            result["report_version"],
            "as_of",
            result["as_of"],
            "data_revision",
            result["data_revision"],
        ]
    )
    writer.writerow(
        [
            "currency",
            result["currency"],
            "observation_days",
            result["observation_days"],
            "warnings",
            ";".join(result["warnings"]),
        ]
    )
    writer.writerow(
        [
            "variant",
            "control",
            "assigned",
            "mature",
            "nonbuyers",
            "net_revenue_minor",
            "profit_per_assigned_minor",
            "incremental_profit_per_assigned_minor",
            "ci_lower_minor",
            "ci_upper_minor",
            "suppression_reasons",
        ]
    )
    comparisons = {c["variant_id"]: c for c in result["comparisons"]}
    for arm in result["arms"]:
        comparison = comparisons.get(arm["variant_id"], {})
        interval = comparison.get("confidence_interval") or {}
        name = arm["name"]
        if name.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            name = "'" + name
        writer.writerow(
            [
                name,
                arm["control"],
                arm["assigned_customers"],
                arm["mature_customers"],
                arm["nonbuyers"],
                arm["net_revenue_minor"],
                arm["profit_per_assigned_minor"],
                comparison.get("incremental_profit_per_assigned_minor"),
                interval.get("lower_minor"),
                interval.get("upper_minor"),
                ";".join(comparison.get("suppression_reasons", [])),
            ]
        )
    return out.getvalue()


def register(app, get_session, scoped_staff):
    def read(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "growth.read")

    def finance(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "finance.resolve")

    root = "/api/operator/restaurants/{business_id}/loyalty-config"

    @app.get(root + "/experiments/{experiment_id}/report", dependencies=[Depends(read)])
    def loyalty_profit_report(
        business_id: str, experiment_id: str, session: Session = Depends(get_session)
    ):
        return report(session, business_id, experiment_id)

    @app.get(
        root + "/experiments/{experiment_id}/report.csv", dependencies=[Depends(read)]
    )
    def loyalty_profit_export(
        business_id: str, experiment_id: str, session: Session = Depends(get_session)
    ):
        return Response(
            csv_report(report(session, business_id, experiment_id)),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="loyalty-experiment.csv"',
                "Cache-Control": "no-store",
            },
        )

    @app.get(root + "/analytics/orders/{target_id}", dependencies=[Depends(read)])
    def loyalty_order_cost_context(
        business_id: str, target_id: str, session: Session = Depends(get_session)
    ):
        with committed_snapshot(session) as snapshot:
            return context(snapshot, business_id, "orders", target_id)

    @app.post(root + "/analytics/orders/{target_id}")
    def loyalty_record_order_cost(
        business_id: str,
        target_id: str,
        payload: OrderCosts,
        principal=Depends(finance),
        session: Session = Depends(get_session),
    ):
        return record(
            session, business_id, "orders", target_id, payload, principal.actor_id
        )

    @app.get(root + "/analytics/variants/{target_id}", dependencies=[Depends(read)])
    def loyalty_operating_cost_context(
        business_id: str, target_id: str, session: Session = Depends(get_session)
    ):
        with committed_snapshot(session) as snapshot:
            return context(snapshot, business_id, "variants", target_id)

    @app.post(root + "/analytics/variants/{target_id}")
    def loyalty_record_operating_cost(
        business_id: str,
        target_id: str,
        payload: OperatingCost,
        principal=Depends(finance),
        session: Session = Depends(get_session),
    ):
        return record(
            session, business_id, "variants", target_id, payload, principal.actor_id
        )
