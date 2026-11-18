"""Read projections for the merchant customer workspace. No second customer store.

Money comes only from confirmed canonical payments/refunds. Associated guest
orders are not proof of customer identity; test money is never mixed with other
provider observations. Reads never create loyalty accounts or memberships.
"""

import json
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, func, inspect, or_, select
from sqlalchemy.orm import Session

from .campaign_models import ContactPermission
from .customer_signup_models import CustomerAccount, CustomerMembership
from .models import Customer, Order, Payment
from .refunds import PaymentRefund


def contact(row):
    return {
        k: getattr(row, k)
        for k in ("id", "name", "email", "phone", "created_at", "last_order_at")
    }


def tables(session):
    return set(inspect(session.get_bind()).get_table_names())


def customer_list(
    session, business, q="", kind="all", offset=0, limit=25, selected=None
):
    installed = tables(session)
    membership_ready = CustomerMembership.__tablename__ in installed
    member = select(CustomerMembership.customer_id).where(
        CustomerMembership.business_id == business
    )
    base = select(Customer).where(Customer.business_id == business)
    total = session.scalar(select(func.count()).select_from(base.subquery()))
    registered = (
        session.scalar(
            select(func.count())
            .select_from(CustomerMembership)
            .where(CustomerMembership.business_id == business)
        )
        if membership_ready
        else None
    )
    from .workspace_period import clauses

    base = base.where(*clauses(Customer.created_at, selected))
    if q:
        # Treat %, _ and backslashes as ordinary search text, not SQL wildcards.
        term = (
            "%"
            + q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        base = base.where(
            or_(
                *(
                    func.lower(c).like(term, escape="\\")
                    for c in (Customer.name, Customer.email, Customer.phone)
                )
            )
        )
    if kind == "registered":
        base = (
            base.where(Customer.id.in_(member))
            if membership_ready
            else base.where(False)
        )
    elif kind == "email":
        base = base.where(Customer.email.is_not(None), Customer.email != "")
    elif kind == "phone":
        base = base.where(Customer.phone.is_not(None), Customer.phone != "")
    count = session.scalar(select(func.count()).select_from(base.subquery()))
    rows = list(
        session.scalars(
            base.order_by(Customer.created_at.desc(), Customer.id)
            .offset(offset)
            .limit(limit)
        )
    )
    ids = [r.id for r in rows]
    memberships = (
        {
            m.customer_id: m
            for m in session.scalars(
                select(CustomerMembership).where(
                    CustomerMembership.business_id == business,
                    CustomerMembership.customer_id.in_(ids),
                )
            )
        }
        if ids and membership_ready
        else {}
    )
    return {
        "items": [
            {
                **contact(r),
                "registered": r.id in memberships,
                "source": memberships[r.id].source if r.id in memberships else None,
            }
            for r in rows
        ],
        "count": count,
        "total": total,
        "registered": registered,
        "offset": offset,
        "limit": limit,
        "membership_available": membership_ready,
    }


def customer_detail(session, business, customer_id):
    c = session.scalar(
        select(Customer).where(
            Customer.business_id == business, Customer.id == customer_id
        )
    )
    if not c:
        raise HTTPException(404, "Customer not found")
    installed = tables(session)
    membership = None
    if CustomerMembership.__tablename__ in installed:
        pair = session.execute(
            select(CustomerMembership, CustomerAccount)
            .join(CustomerAccount)
            .where(
                CustomerMembership.business_id == business,
                CustomerMembership.customer_id == c.id,
            )
        ).first()
        if pair:
            m, a = pair
            membership = {
                "source": m.source,
                "created_at": m.created_at,
                "channel": a.channel,
                "verified_at": a.verified_at,
                "scope": a.scope,
            }
    permissions = []
    if ContactPermission.__tablename__ in installed:
        permissions = [
            {
                k: getattr(p, k)
                for k in (
                    "channel",
                    "purpose",
                    "scope",
                    "state",
                    "source",
                    "reason",
                    "at",
                )
            }
            for p in session.scalars(
                select(ContactPermission)
                .where(
                    ContactPermission.business_id == business,
                    ContactPermission.customer_id == c.id,
                    ContactPermission.purpose == "marketing",
                )
                .order_by(ContactPermission.scope, ContactPermission.channel)
            )
        ]
    order_filter = (Order.business_id == business, Order.customer_id == c.id)
    refund = (
        select(
            PaymentRefund.payment_id,
            func.sum(PaymentRefund.amount_minor).label("amount"),
        )
        .group_by(PaymentRefund.payment_id)
        .subquery()
    )
    scope = case((Payment.provider == "simulated", "test"), else_="provider")
    refunded = case(
        (Payment.status == "refunded", Payment.amount_minor),
        else_=func.coalesce(refund.c.amount, 0),
    )
    money = session.execute(
        select(
            scope.label("scope"),
            Payment.currency,
            func.count(func.distinct(Order.id)).label("paid_orders"),
            func.sum(Payment.amount_minor).label("captured"),
            func.sum(refunded).label("refunded"),
        )
        .join(Order, Payment.order_id == Order.id)
        .outerjoin(refund, refund.c.payment_id == Payment.id)
        .where(*order_filter, Payment.status.in_(["paid", "refunded"]))
        .group_by(scope, Payment.currency)
    ).all()
    orders = []
    for o in session.scalars(
        select(Order)
        .where(*order_filter)
        .order_by(Order.created_at.desc(), Order.id)
        .limit(20)
    ):
        try:
            verified = (
                json.loads(o.customer_snapshot_json or "{}").get("identity_verified")
                is True
            )
        except (ValueError, AttributeError):
            verified = False
        orders.append(
            {
                "id": o.id,
                "code": o.public_code,
                "created_at": o.created_at,
                "status": o.status,
                "payment_status": o.payment_status,
                "total_minor": o.total_minor,
                "currency": o.currency,
                "identity_verified": verified,
            }
        )
    return {
        **contact(c),
        "membership": membership,
        "permissions": permissions,
        "permission_available": ContactPermission.__tablename__ in installed,
        "orders": orders,
        "order_count": session.scalar(
            select(func.count()).select_from(Order).where(*order_filter)
        ),
        "money": [
            {
                "scope": m.scope,
                "currency": m.currency,
                "paid_orders": m.paid_orders,
                "captured_minor": m.captured,
                "refunded_minor": m.refunded,
                "net_minor": m.captured - m.refunded,
            }
            for m in money
        ],
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/customers"

    def read(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "growth.read")

    @app.get(root, dependencies=[Depends(read)])
    def customers(
        business_id: str,
        q: str = Query("", max_length=120),
        date_from: str | None = None,
        date_to: str | None = None,
        kind: Literal["all", "registered", "email", "phone"] = "all",
        offset: int = Query(0, ge=0, le=1000000),
        limit: int = Query(25, ge=1, le=100),
        session: Session = Depends(get_session),
    ):
        from .workspace_period import period

        return customer_list(
            session,
            business_id,
            q.strip(),
            kind,
            offset,
            limit,
            period(date_from, date_to),
        )

    @app.get(root + "/{customer_id}", dependencies=[Depends(read)])
    def detail(
        business_id: str, customer_id: str, session: Session = Depends(get_session)
    ):
        return customer_detail(session, business_id, customer_id)

    web = Path(__file__).parent / "web" / "workspace"

    @app.get("/workspace")
    @app.get("/workspace/login")
    @app.get("/workspace/customers")
    @app.get("/workspace/sales")
    @app.get("/workspace/home")
    @app.get("/workspace/social")
    @app.get("/workspace/campaigns")
    @app.get("/workspace/reports")
    @app.get("/workspace/analytics")
    @app.get("/workspace/onboarding")
    @app.get("/workspace/settings")
    def workspace_page():
        return FileResponse(web / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/workspace/identity")
    def internal_identity_page():
        if app.state.environment != "internal":
            raise HTTPException(404, "Not found")
        return workspace_page()

    class ImmutableAssets(StaticFiles):
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if response.status_code == 200:
                response.headers["Cache-Control"] = (
                    "public, max-age=31536000, immutable"
                )
            return response

    app.mount(
        "/workspace-assets/assets",
        ImmutableAssets(directory=web / "assets", check_dir=False),
        name="workspace-assets",
    )
