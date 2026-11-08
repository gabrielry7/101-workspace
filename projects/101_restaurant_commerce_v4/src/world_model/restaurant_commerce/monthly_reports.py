"""Saved monthly figures. Provider readers are injected by the application owner."""

import calendar
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import Column, String, Text, inspect, select
from sqlalchemy.orm import Session

from .models import Base, Order, Payment, RestaurantCommerceProfile
from .sales_metrics import money_totals
from .workspace_period import period


class MonthlyReport(Base):
    __tablename__ = "restaurant_monthly_reports"
    id = Column(String(36), primary_key=True)
    business_id = Column(String(64), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)
    digest = Column(String(64), nullable=False)
    document = Column(Text, nullable=False)


TABLES = {MonthlyReport.__tablename__}


def migrate(engine):
    if "restaurant_commerce_profiles" not in inspect(engine).get_table_names():
        raise RuntimeError("Install commerce first")
    MonthlyReport.__table__.create(engine, checkfirst=True)


def month_period(month, zone, now=None):
    now = now or datetime.now(timezone.utc)
    latest = now.astimezone(ZoneInfo(zone)).strftime("%Y-%m")
    try:
        start = datetime.strptime(month, "%Y-%m")
        if start.strftime("%Y-%m") != month or month >= latest:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, "Elige un mes terminado") from None
    end = calendar.monthrange(start.year, start.month)[1]
    return period(month + "-01", f"{month}-{end:02}", timezone_name=zone)


def previous(month):
    year, m = map(int, month.split("-"))
    return f"{year if m > 1 else year - 1:04}-{m - 1 if m > 1 else 12:02}"


def financial(session, business, selected, currency):
    rows = money_totals(session, business, selected)
    row = next((r for r in rows if r["scope"] == "provider" and r["currency"] == currency), None)
    if row is None:
        return dict(
            net=None,
            paid_orders=None,
            average=None,
            captured=None,
            refunds=None,
            coverage="unknown",
            note="Sin registros de pagos en línea; cobertura histórica desconocida.",
        )
    row = dict(row)
    row["average"] = (
        int(
            (Decimal(row["net"]) / row["paid_orders"]).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        if row["paid_orders"]
        else None
    )
    row.update(coverage="unknown", note="Cobertura histórica sin verificar.")
    return row


def campaign_rows(session, business, selected, currency):
    from .campaign_models import (
        Campaign,
        CampaignJob,
        CampaignOrderCredit,
        CampaignRevision,
        CampaignVisit,
    )
    from .refunds import refunded_total

    result = {}
    # Activity establishes records for this campaign/period even without a sale.
    for job, revision, campaign in session.execute(
        select(CampaignJob, CampaignRevision, Campaign)
        .join(CampaignRevision, CampaignRevision.id == CampaignJob.revision_id)
        .join(Campaign, Campaign.id == CampaignRevision.campaign_id)
        .where(
            CampaignJob.business_id == business,
            Campaign.business_id == business,
            CampaignJob.scope == "live",
            CampaignJob.submitted_at >= selected["start"],
            CampaignJob.submitted_at < selected["end"],
        )
    ):
        doc = json.loads(revision.document)
        result.setdefault(
            campaign.id, dict(id=campaign.id, name=doc["content"]["subject"], paid_orders=0, net=0)
        )
    for visit, revision, campaign in session.execute(
        select(CampaignVisit, CampaignRevision, Campaign)
        .join(CampaignJob, CampaignJob.id == CampaignVisit.job_id)
        .join(CampaignRevision, CampaignRevision.id == CampaignJob.revision_id)
        .join(Campaign, Campaign.id == CampaignRevision.campaign_id)
        .where(
            CampaignJob.business_id == business,
            Campaign.business_id == business,
            CampaignJob.scope == "live",
            CampaignVisit.scanner.is_(False),
            CampaignVisit.at >= selected["start"],
            CampaignVisit.at < selected["end"],
        )
    ):
        doc = json.loads(revision.document)
        result.setdefault(
            campaign.id, dict(id=campaign.id, name=doc["content"]["subject"], paid_orders=0, net=0)
        )
    for credit, order, campaign, revision in session.execute(
        select(CampaignOrderCredit, Order, Campaign, CampaignRevision)
        .join(Order, Order.id == CampaignOrderCredit.order_id)
        .join(CampaignRevision, CampaignRevision.id == CampaignOrderCredit.revision_id)
        .join(Campaign, Campaign.id == CampaignRevision.campaign_id)
        .where(
            Order.business_id == business,
            Campaign.business_id == business,
            Order.created_at >= selected["start"],
            Order.created_at < selected["end"],
        )
    ):
        doc = json.loads(revision.document)
        if credit.scope != "live":
            continue
        payments = [
            p
            for p in order.payments
            if p.currency == currency
            and p.provider not in {"simulated", "cash_at_pickup"}
            and p.status in {"paid", "refunded"}
        ]
        if not payments:
            continue
        row = result.setdefault(
            campaign.id, dict(id=campaign.id, name=doc["content"]["subject"], paid_orders=0, net=0)
        )
        row["paid_orders"] += 1
        row["net"] += sum(p.amount_minor - refunded_total(session, p) for p in payments)
    return result


def campaign_activity(session, business, span):
    from sqlalchemy import func

    from .campaign_models import CampaignJob, CampaignVisit

    base = [CampaignJob.business_id == business, CampaignJob.scope == "live"]
    known = session.scalar(select(func.count()).select_from(CampaignJob).where(*base))
    if not known:
        return {"accepted": None, "visits": None}
    accepted = session.scalar(
        select(func.count())
        .select_from(CampaignJob)
        .where(
            *base, CampaignJob.submitted_at >= span["start"], CampaignJob.submitted_at < span["end"]
        )
    )
    visits = session.scalar(
        select(func.count())
        .select_from(CampaignVisit)
        .join(CampaignJob, CampaignJob.id == CampaignVisit.job_id)
        .where(
            *base,
            CampaignVisit.scanner.is_(False),
            CampaignVisit.at >= span["start"],
            CampaignVisit.at < span["end"],
        )
    )
    return {"accepted": accepted, "visits": visits}


def build(session, business, month, currency, website_reader=None, request=None, now=None):
    profile = session.get(RestaurantCommerceProfile, business)
    if not profile:
        raise HTTPException(404)
    month_period(month, profile.timezone, now)
    if month <= "0001-01":
        raise HTTPException(422, "Mes fuera de rango")
    periods = [month, previous(month)]
    selected = [month_period(m, profile.timezone, now) for m in periods]
    currencies = sorted(
        {profile.currency}
        | {
            r[0]
            for r in session.execute(
                select(Payment.currency).join(Order).where(Order.business_id == business)
            )
        }
    )
    currency = currency or profile.currency
    if currency not in currencies:
        raise HTTPException(422, "Moneda no disponible")
    values = []
    for m, span in zip(periods, selected):
        website = {"status": "disconnected", "note": "Sitio web no conectado", "values": {}}
        if website_reader:
            try:
                website = website_reader(request, business, span)
            except HTTPException:
                raise
            except Exception:
                website = {
                    "status": "unavailable",
                    "note": "Analítica web no disponible",
                    "values": {},
                }
        values.append(
            dict(
                activity=campaign_activity(session, business, span),
                month=m,
                start=span["start"].isoformat(),
                end=span["end"].isoformat(),
                sales=financial(session, business, span, currency),
                website=website,
                campaigns=campaign_rows(session, business, span, currency),
            )
        )
    ids = set(values[0]["campaigns"]) | set(values[1]["campaigns"])
    rows = [
        dict(
            name=(values[0]["campaigns"].get(i) or values[1]["campaigns"][i])["name"],
            current=values[0]["campaigns"].get(i, {"net": None, "paid_orders": None}),
            previous=values[1]["campaigns"].get(i, {"net": None, "paid_orders": None}),
        )
        for i in ids
    ]
    rows.sort(key=lambda r: (-(r["current"]["net"] or 0), r["name"]))
    if len(rows) > 5:
        rest = rows[5:]
        rows = rows[:5] + [
            dict(
                name="Otras campañas",
                **{
                    key: {
                        metric: sum(r[key][metric] for r in rest)
                        if all(r[key][metric] is not None for r in rest)
                        else None
                        for metric in ("net", "paid_orders")
                    }
                    for key in ("current", "previous")
                },
            )
        ]
    for v in values:
        v.pop("campaigns")
    return dict(
        version=1,
        business_id=business,
        business_name=profile.display_name,
        month=month,
        comparison=periods[1],
        timezone=profile.timezone,
        currency=currency,
        currencies=currencies,
        periods=values,
        campaigns=rows,
        gaps=[
            "Pedidos agrupados por fecha de creación, con devoluciones registradas hasta esta actualización.",
            "Google y posiciones en buscadores: sin historial mensual conectado.",
        ],
        generated_at=(now or datetime.now(timezone.utc)).isoformat(),
    )


def save(session, document):
    stable = {k: v for k, v in document.items() if k != "generated_at"}
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()
    old = session.scalar(
        select(MonthlyReport).where(
            MonthlyReport.business_id == document["business_id"],
            MonthlyReport.month == document["month"],
            MonthlyReport.digest == digest,
        )
    )
    if old:
        return {"id": old.id, **json.loads(old.document)}
    row = MonthlyReport(
        id=str(uuid.uuid4()),
        business_id=document["business_id"],
        month=document["month"],
        digest=digest,
        document=json.dumps(document),
    )
    session.add(row)
    session.commit()
    return {"id": row.id, **document}


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/reports"

    def authorize(business_id: str, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, "finance.read")
        scoped_staff(request, session, business_id, "growth.read")
        if MonthlyReport.__tablename__ not in inspect(session.get_bind()).get_table_names():
            raise HTTPException(503, "Actualización de informes pendiente")

    @app.get(root, dependencies=[Depends(authorize)])
    def options(business_id: str, session: Session = Depends(get_session)):
        p = session.get(RestaurantCommerceProfile, business_id)
        m = previous(datetime.now(ZoneInfo(p.timezone)).strftime("%Y-%m"))
        months = []
        for _ in range(120):
            months.append(m)
            m = previous(m)
        return {"months": months, "timezone": p.timezone}

    @app.post(root, dependencies=[Depends(authorize)])
    def refresh(
        business_id: str,
        request: Request,
        month: str,
        currency: str | None = None,
        session: Session = Depends(get_session),
    ):
        from .loyalty_read_snapshot import committed_snapshot

        profile = session.get(RestaurantCommerceProfile, business_id)
        span = month_period(month, profile.timezone)
        if month <= "0001-01":
            raise HTTPException(422, "Mes fuera de rango")
        spans = [span, month_period(previous(month), profile.timezone)]
        session.commit()  # Release reads before provider authorization touches session activity.
        reader = getattr(app.state, "monthly_website_reader", None)
        website_data = {}
        if reader:
            for selected in spans:
                try:
                    value = reader(request, business_id, selected)
                except HTTPException:
                    raise
                except Exception:
                    value = {
                        "status": "unavailable",
                        "note": "Analítica web no disponible",
                        "values": {},
                    }
                website_data[selected["from"]] = value

        def cached_reader(request, business, selected):
            return website_data[selected["from"]]

        with committed_snapshot(session) as snapshot:
            document = build(
                snapshot, business_id, month, currency, cached_reader if reader else None, request
            )
        scoped_staff(request, session, business_id, "finance.read")
        scoped_staff(request, session, business_id, "growth.read")
        return save(session, document)

    def saved(session, business_id, report_id):
        row = session.scalar(
            select(MonthlyReport).where(
                MonthlyReport.business_id == business_id, MonthlyReport.id == report_id
            )
        )
        if not row:
            raise HTTPException(404)
        return {"id": row.id, **json.loads(row.document)}

    @app.get(root + "/{report_id}", dependencies=[Depends(authorize)])
    def report(business_id: str, report_id: str, session: Session = Depends(get_session)):
        return saved(session, business_id, report_id)

    @app.get(root + "/{report_id}/pdf", dependencies=[Depends(authorize)])
    def download(business_id: str, report_id: str, session: Session = Depends(get_session)):
        from .monthly_report_pdf import render

        doc = saved(session, business_id, report_id)
        return Response(
            render(doc),
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="informe-{doc["month"]}.pdf"',
            },
        )
