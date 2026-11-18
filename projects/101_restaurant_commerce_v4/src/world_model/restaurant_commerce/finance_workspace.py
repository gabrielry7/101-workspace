"""Read-only finance queue and source-bound refund allocation context."""

# ruff: noqa: B008 -- existing FastAPI dependency convention
import json
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .errors import ValidationError
from .models import Order, Payment, PaymentIntent, PaymentReconciliation, RestaurantCommerceProfile
from .refunds import PaymentRefund


def allocation_context(session, order):
    from .loyalty_baseline import data as baseline_data
    from .loyalty_execution import Allocation, marked, state_for
    from .loyalty_execution_migrations import installed

    allocations = []
    paid = None
    blocker = None
    if marked(order):
        basis = "execution"
        if not installed(session):
            blocker = "Falta instalar el historial de fidelización."
        else:
            try:
                _, _, snapshot = state_for(session, order)
                paid = {
                    snapshot["line_ids"][line["line_id"]]: line["net_item_minor"]
                    - line["reward_discount_minor"]
                    for line in snapshot["calculation"]["lines"]
                }
                allocations = [
                    {"refund_id": a.refund_id, "document": json.loads(a.document)}
                    for a in session.scalars(
                        select(Allocation).where(Allocation.order_id == order.id)
                    )
                ]
            except ValidationError:
                blocker = "No se puede verificar el historial de fidelización de este pedido."
    else:
        basis = "baseline"
        snapshot = baseline_data(order)
        if not snapshot.get("baseline_policy"):
            blocker = "Falta la política histórica de este pedido; se requiere revisión financiera."
        allocations = [
            {"refund_id": rid, "document": a["document"]}
            for rid, a in snapshot.get("baseline_refund_state", {}).get("allocations", {}).items()
        ]
    used = {}
    fee = 0
    for a in allocations:
        fee += a["document"]["delivery_fee_minor"]
        for key, amount in a["document"]["lines"].items():
            used[key] = used.get(key, 0) + amount
    return {
        "basis": basis,
        "blocker": blocker,
        "allocations": allocations,
        "remaining_food_minor": max(
            0, order.total_minor - order.delivery_fee_minor - sum(used.values())
        ),
        "remaining_delivery_fee_minor": max(0, order.delivery_fee_minor - fee),
        "lines": [
            {
                "id": line.id,
                "name": line.name_snapshot,
                "quantity": line.quantity,
                "remaining_minor": max(0, paid[line.id] - used.get(line.id, 0))
                if paid is not None and line.id in paid
                else None,
            }
            for line in order.items
        ],
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/financial-orders"

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, "finance.read")

    @app.get(root, dependencies=[Depends(read)])
    def orders(
        business_id: str,
        scope: Literal["all", "open"] = "open",
        q: str = Query("", max_length=80),
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
        session: Session = Depends(get_session),
    ):
        reviews = (
            select(func.count(PaymentReconciliation.id))
            .where(
                PaymentReconciliation.order_id == Order.id, PaymentReconciliation.status == "open"
            )
            .correlate(Order)
            .scalar_subquery()
        )
        stmt = select(Order, reviews.label("reviews")).where(Order.business_id == business_id)
        if scope == "open":
            stmt = stmt.where(reviews > 0)
        if q:
            term = (
                "%"
                + q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            stmt = stmt.where(func.lower(Order.public_code).like(term, escape="\\"))
        count = session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = session.execute(
            stmt.order_by(Order.created_at.desc(), Order.id).offset(offset).limit(limit)
        )
        return {
            "items": [
                {
                    "id": o.id,
                    "public_code": o.public_code,
                    "status": o.status,
                    "payment_status": o.payment_status,
                    "total_minor": o.total_minor,
                    "currency": o.currency,
                    "open_reviews": n,
                }
                for o, n in rows
            ],
            "count": count,
        }

    @app.get(root + "/{order_id}", dependencies=[Depends(read)])
    def order(business_id: str, order_id: str, session: Session = Depends(get_session)):
        row = session.scalar(
            select(Order)
            .where(Order.business_id == business_id, Order.id == order_id)
            .options(selectinload(Order.items))
        )
        if not row:
            raise HTTPException(404, "Order not found")
        intent = session.scalar(select(PaymentIntent).where(PaymentIntent.order_id == order_id))
        checkout = json.loads(intent.request_json) if intent else {}
        if intent and (
            checkout.get("amount_minor") != row.total_minor
            or checkout.get("currency") != row.currency
        ):
            raise HTTPException(
                409,
                "Los datos actuales difieren del pago original; se requiere revisión financiera.",
            )
        refunds = session.execute(
            select(PaymentRefund, Payment.currency)
            .join(Payment)
            .where(Payment.order_id == order_id)
            .order_by(PaymentRefund.id)
        )
        return {
            "order": {
                "id": row.id,
                "public_code": row.public_code,
                "status": row.status,
                "payment_status": row.payment_status,
                "total_minor": row.total_minor,
                "currency": row.currency,
            },
            "timezone": session.get(RestaurantCommerceProfile, business_id).timezone,
            "full_refund_amount_minor": checkout.get("amount_minor"),
            "full_refund_currency": checkout.get("currency"),
            "refunds": [
                {
                    "id": r.id,
                    "amount_minor": r.amount_minor,
                    "currency": currency,
                    "reference": r.reference,
                }
                for r, currency in refunds
            ],
            "allocation": allocation_context(session, row),
        }
