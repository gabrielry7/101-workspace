"""Shared confirmed-payment projection; order-created cohort, current refunds."""

from sqlalchemy import case, func, select

from .models import Order, Payment
from .refunds import PaymentRefund
from .workspace_period import clauses


def money_totals(session, business, selected):
    refund = (
        select(
            PaymentRefund.payment_id,
            func.sum(PaymentRefund.amount_minor).label("total"),
        )
        .group_by(PaymentRefund.payment_id)
        .subquery()
    )
    scope = case(
        (Payment.provider == "simulated", "test"),
        (Payment.provider == "cash_at_pickup", "cash"),
        else_="provider",
    )
    refunded = case(
        (Payment.status == "refunded", Payment.amount_minor),
        else_=func.coalesce(refund.c.total, 0),
    )
    rows = session.execute(
        select(
            Payment.currency,
            scope.label("scope"),
            func.sum(Payment.amount_minor).label("captured"),
            func.sum(refunded).label("refunds"),
            func.count(func.distinct(Payment.order_id)).label("paid_orders"),
        )
        .join(Order, Payment.order_id == Order.id)
        .outerjoin(refund, refund.c.payment_id == Payment.id)
        .where(
            Order.business_id == business,
            *clauses(Order.created_at, selected),
            Payment.status.in_(["paid", "refunded"]),
        )
        .group_by(Payment.currency, scope)
    ).all()
    money = [
        {
            "currency": r.currency,
            "scope": r.scope,
            "captured": r.captured,
            "refunds": r.refunds,
            "net": r.captured - r.refunds,
            "paid_orders": r.paid_orders,
        }
        for r in rows
    ]
    return money
