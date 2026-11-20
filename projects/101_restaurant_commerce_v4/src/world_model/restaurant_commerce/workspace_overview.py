"""Read-only home and campaign directory, backed by the current commerce owners."""

import json
from urllib.parse import urlencode
from fastapi import Depends, Query, Request
from sqlalchemy import select, func, inspect, case
from sqlalchemy.orm import Session
from .models import Customer, Order, Payment, RestaurantCommerceProfile
from .campaign_models import Campaign, CampaignRevision
from .connection_models import BusinessConnection
from .refunds import PaymentRefund
from .workspace_period import period, clauses


def campaigns(session, business, selected=None, q="", state="all", offset=0):
    query = (
        select(Campaign, CampaignRevision)
        .join(CampaignRevision, CampaignRevision.id == Campaign.revision_id)
        .where(
            Campaign.business_id == business, *clauses(Campaign.created_at, selected)
        )
    )
    if state != "all":
        query = query.where(Campaign.state == state)
    # Subject filter uses retained document as text; no per-row preview/render.
    if q:
        escaped = (
            q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        query = query.where(
            func.lower(CampaignRevision.document).like("%" + escaped + "%", escape="\\")
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    result = []
    for c, r in session.execute(
        query.order_by(Campaign.created_at.desc(), Campaign.id).offset(offset).limit(25)
    ):
        d = json.loads(r.document)
        result.append(
            {
                "id": c.id,
                "state": c.state,
                "subject": d["content"]["subject"],
                "channel": d["channel"],
                "scope": d["scope"],
                "scheduled_at": d["scheduled_at"],
                "created_at": c.created_at,
                "audience_count": len(d["recipients"]),
            }
        )
    return {"items": result, "count": total, "offset": offset, "limit": 25}


def overview(session, business, selected):
    def link(area, **params):
        return (
            "/workspace/"
            + area
            + "?"
            + urlencode(
                {
                    "business": business,
                    "date_from": selected["from"],
                    "date_to": selected["to"],
                    **params,
                }
            )
        )

    orders = select(Order).where(
        Order.business_id == business, *clauses(Order.created_at, selected)
    )
    customers = select(Customer).where(
        Customer.business_id == business, *clauses(Customer.created_at, selected)
    )
    from .sales_metrics import money_totals
    money = money_totals(session, business, selected)
    attention = []
    activity = []
    for o in session.scalars(
        select(Order)
        .where(Order.business_id == business, Order.status == "placed")
        .order_by(Order.created_at.desc())
        .limit(5)
    ):
        attention.append(
            {
                "id": "order-" + o.id,
                "title": "Pedido #" + o.public_code,
                "detail": "Por aceptar",
                "href": link("sales", order=o.id, status="all"),
                "action": "Abrir pedido",
                "kind": "order",
            }
        )
    for o in session.scalars(
        orders.order_by(Order.created_at.desc(), Order.id).limit(8)
    ):
        activity.append(
            {
                "id": "order-" + o.id,
                "title": "Pedido #" + o.public_code + " creado",
                "at": o.created_at,
                "href": link("sales", order=o.id, status="all"),
                "kind": "order",
            }
        )
    for c in session.scalars(
        customers.order_by(Customer.created_at.desc(), Customer.id).limit(8)
    ):
        activity.append(
            {
                "id": "customer-" + c.id,
                "title": (c.name or "Contacto sin nombre") + " se añadió a Clientes",
                "at": c.created_at,
                "href": link("customers", customer=c.id),
                "kind": "customer",
            }
        )
    tables = set(inspect(session.get_bind()).get_table_names())
    if Campaign.__tablename__ in tables:
        query = (
            select(Campaign, CampaignRevision)
            .join(CampaignRevision, CampaignRevision.id == Campaign.revision_id)
            .where(Campaign.business_id == business)
        )
        for c, r in session.execute(
            query.where(Campaign.state.in_(["draft", "approved"]))
            .order_by(Campaign.created_at.desc())
            .limit(5)
        ):
            doc = json.loads(r.document)
            attention.append(
                {
                    "id": "campaign-" + c.id,
                    "title": doc["content"]["subject"],
                    "detail": "Borrador por revisar"
                    if c.state == "draft"
                    else "Aprobada; falta programar",
                    "href": link("campaigns", campaign=c.id),
                    "action": "Revisar campaña",
                    "kind": "campaign",
                }
            )
        for c, r in session.execute(
            query.where(*clauses(CampaignRevision.created_at, selected))
            .order_by(CampaignRevision.created_at.desc())
            .limit(8)
        ):
            activity.append(
                {
                    "id": "revision-" + r.id,
                    "title": "Versión guardada: "
                    + json.loads(r.document)["content"]["subject"],
                    "at": r.created_at,
                    "href": link("campaigns", campaign=c.id),
                    "kind": "campaign",
                }
            )
    if BusinessConnection.__tablename__ in tables:
        for c in session.scalars(
            select(BusinessConnection)
            .where(
                BusinessConnection.business_id == business,
                BusinessConnection.state.notin_(["connected", "disconnected"]),
            )
            .limit(5)
        ):
            attention.append(
                {
                    "id": "connection-" + c.id,
                    "title": "Conexión con Google",
                    "detail": "Revisar conexión · " + c.state,
                    "href": "/connections?" + urlencode({"business_id": business}),
                    "action": "Abrir conexión",
                    "kind": "connection",
                }
            )
    # Content is reviewed from the same current-work queue as orders and campaigns.
    if {"social_packs", "social_approvals"} <= tables:
        from .social_production import Approval, Pack
        for pack in session.scalars(select(Pack).where(Pack.business_id == business).limit(5)):
            if session.get(Approval, f"{pack.id}:{pack.revision}") is None:
                attention.append({"id": "social-" + pack.id, "title": "Publicación por revisar",
                    "detail": f"Versión {pack.revision} · pendiente de revisión y aprobación",
                    "href": link("social", pack=pack.id), "action": "Revisar publicación", "kind": "social"})
    activity.sort(key=lambda r: str(r["at"]), reverse=True)
    return {
        "period": {"from": selected["from"], "to": selected["to"]},
        "new_customers": session.scalar(
            select(func.count()).select_from(customers.subquery())
        ),
        "orders": session.scalar(select(func.count()).select_from(orders.subquery())),
        "money": money,
        "attention": attention[:12],
        "activity": activity[:6],
        "links": {
            "customers": link("customers"),
            "orders": link("sales", status="all"),
        },
        "accounting": "Pagos confirmados menos devoluciones acumuladas de pedidos creados en el periodo. No es liquidación bancaria ni beneficio.",
        "attention_period": "Pendientes actuales, aunque se hayan creado antes del periodo.",
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/workspace"

    def read(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "growth.read")

    @app.get(root + "/overview", dependencies=[Depends(read)])
    def home(
        business_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
        session: Session = Depends(get_session),
    ):
        return overview(session, business_id, period(date_from, date_to, default=True, timezone_name=session.get(RestaurantCommerceProfile, business_id).timezone))

    @app.get(root + "/campaigns", dependencies=[Depends(read)])
    def listing(
        business_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
        q: str = Query("", max_length=80),
        state: str = Query("all", pattern="^(all|draft|approved|scheduled|cancelled)$"),
        offset: int = Query(0, ge=0, le=100000),
        session: Session = Depends(get_session),
    ):
        return campaigns(
            session, business_id, period(date_from, date_to), q, state, offset
        )
