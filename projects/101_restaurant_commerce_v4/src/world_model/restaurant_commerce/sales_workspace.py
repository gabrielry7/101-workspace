"""Small read projections for Sales; existing service/PATCH owns every mutation."""

from collections import defaultdict
from typing import Literal
from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import JSON, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session
from .models import Customer, Order, Payment, PaymentReconciliation
from .enums import ORDER_TRANSITIONS, OrderStatus
from .errors import InvalidTransitionError
from .refunds import refunded_total
from .service import RestaurantCommerceService


def listing(
    session, business, q="", status="active", offset=0, limit=25, selected=None, online_only=False, currency=None, payment_status="all"
):
    service = RestaurantCommerceService(session)
    from .workspace_period import clauses

    base = select(Order).where(
        Order.business_id == business, *clauses(Order.created_at, selected)
    )
    if online_only:
        paid = select(Payment.order_id).where(Payment.status.in_(["paid","refunded"]),Payment.provider.notin_(["simulated","cash_at_pickup"]))
        if currency: paid = paid.where(Payment.currency==currency)
        base=base.where(Order.id.in_(paid))
    counts = dict(
        session.execute(
            select(Order.status, func.count())
            .where(Order.business_id == business, *clauses(Order.created_at, selected))
            .group_by(Order.status)
        ).all()
    )
    if status == "active":
        base = base.where(Order.status.notin_(["completed", "cancelled"]))
    elif status != "all":
        base = base.where(Order.status == status)
    if payment_status != "all":
        base = base.where(Order.payment_status == payment_status)
    if q:
        term = (
            "%"
            + q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        # Match the displayed historical contact. A present snapshot with no name
        # must not inherit a later/current Customer name. Filter before pagination.
        snapshot_name = (func.json_extract(Order.customer_snapshot_json, "$.name")
                         if session.bind.dialect.name == "sqlite" else
                         cast(Order.customer_snapshot_json, JSON)["name"].as_string())
        name = case((and_(Order.customer_snapshot_json.is_not(None), Order.customer_snapshot_json != ""),
                     snapshot_name), else_=Customer.name)
        base = base.outerjoin(Customer, Order.customer_id == Customer.id).where(or_(
            func.lower(Order.public_code).like(term, escape="\\"),
            func.lower(name).like(term, escape="\\"),
        ))
    count = session.scalar(select(func.count()).select_from(base.subquery()))
    rows = list(
        session.scalars(
            base.order_by(Order.created_at.desc(), Order.id).offset(offset).limit(limit)
        )
    )
    return {
        "items": [
            {
                **{
                    k: getattr(o, k)
                    for k in (
                        "id",
                        "public_code",
                        "status",
                        "payment_status",
                        "fulfillment_type",
                        "total_minor",
                        "currency",
                        "created_at",
                        "version",
                    )
                },
                "customer_name": service._contact(o).get("name"),
            }
            for o in rows
        ],
        "count": count,
        "offset": offset,
        "limit": limit,
        "counts": counts,
        "review_count": session.scalar(
            select(func.count(func.distinct(Order.id)))
            .join(PaymentReconciliation, PaymentReconciliation.order_id == Order.id)
            .where(
                Order.business_id == business, PaymentReconciliation.status == "open"
            )
        ),
    }


def detail(session, business, order_id):
    service = RestaurantCommerceService(session)
    order = session.scalar(
        service._orders_stmt().where(
            Order.business_id == business, Order.id == order_id
        )
    )
    if not order:
        raise HTTPException(404, "Order not found")
    data = service._order_to_out(order).model_dump(mode="json")
    actions = []
    for target in sorted(
        ORDER_TRANSITIONS[OrderStatus(order.status)], key=lambda s: s.value
    ):
        # Awaiting payment is advanced by the trusted payment workflow.
        if target.value == "placed":
            continue
        try:
            cash = service.validate_order_transition(order, target.value)
            actions.append(
                {
                    "status": target.value,
                    "allowed": True,
                    "reason": None,
                    "confirmation": "cash_received"
                    if target.value == "completed"
                    and cash
                    and order.payment_status != "paid"
                    else None,
                }
            )
        except InvalidTransitionError as exc:
            actions.append(
                {
                    "status": target.value,
                    "allowed": False,
                    "reason": str(exc),
                    "confirmation": None,
                }
            )
    money = defaultdict(
        lambda: {"captured_minor": 0, "refunded_minor": 0, "net_minor": 0}
    )
    for p in order.payments:
        if p.status not in ("paid", "refunded"):
            continue
        scope = (
            "test"
            if p.provider == "simulated"
            else "cash"
            if p.provider == "cash_at_pickup"
            else "provider"
        )
        row = money[(scope, p.currency)]
        row["captured_minor"] += p.amount_minor
        row["refunded_minor"] += refunded_total(session, p)
        row["net_minor"] = row["captured_minor"] - row["refunded_minor"]
    return {
        **data,
        "actions": actions,
        "money": [
            {"scope": scope, "currency": currency, **values}
            for (scope, currency), values in money.items()
        ],
        "identity_verified": service._contact(order).get("identity_verified") is True,
    }


def register(app, get_session, scoped_staff):
    from .delivery_workspace import register as register_deliveries
    from .finance_workspace import register as register_finance
    register_deliveries(app, get_session, scoped_staff)
    register_finance(app, get_session, scoped_staff)
    from .reservation_workspace import register as register_reservations
    register_reservations(app, get_session, scoped_staff)
    root = "/api/operator/restaurants/{business_id}/sales"

    def read(
        business_id: str, request: Request, session: Session = Depends(get_session)
    ):
        return scoped_staff(request, session, business_id, "operations.read")

    @app.get(root, dependencies=[Depends(read)])
    def sales(
        business_id: str,
        q: str = Query("", max_length=80),
        date_from: str | None = None,
        date_to: str | None = None,
        online_only: bool = False,
        currency: str | None = None,
        payment_status: Literal["all", "paid", "pending", "unpaid", "refunded", "failed"] = "all",
        status: Literal[
            "active",
            "all",
            "awaiting_payment",
            "placed",
            "accepted",
            "preparing",
            "ready",
            "completed",
            "cancelled",
        ] = "active",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
        session: Session = Depends(get_session),
    ):
        from .workspace_period import period
        from .models import RestaurantCommerceProfile
        from .sales_metrics import money_totals

        result = listing(
            session,
            business_id,
            q.strip(),
            status,
            offset,
            limit,
            period(date_from, date_to, timezone_name=session.get(RestaurantCommerceProfile, business_id).timezone),
            online_only, currency, payment_status,
        )

        result["money"] = money_totals(session, business_id, period(date_from, date_to, timezone_name=session.get(RestaurantCommerceProfile, business_id).timezone))
        return result

    @app.get(root + "/{order_id}", dependencies=[Depends(read)])
    def sale(business_id: str, order_id: str, session: Session = Depends(get_session)):
        return detail(session, business_id, order_id)
