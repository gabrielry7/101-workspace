"""Scoped bounded delivery reads; current service and provider authority own writes."""

# ruff: noqa: B008 -- existing FastAPI dependency convention
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .deliveries import SimulatedDeliveryProvider
from .models import (
    Delivery,
    FinancialOperation,
    IdempotencyRecord,
    Order,
    PaymentReconciliation,
    RestaurantCommerceProfile,
)
from .service import RestaurantCommerceService
from .workspace_period import clauses, period


def describe(session, row, app):
    service = RestaurantCommerceService(session)
    order = row.order
    result = service._delivery_to_out(row).model_dump(mode="json")
    # Existing real providers are fail-closed stubs. This migration does not claim
    # a live dispatch/recovery contract merely from a provider's presence.
    supported = isinstance(
        app.state.delivery_providers.get(row.provider), SimulatedDeliveryProvider
    )
    holds = bool(
        session.scalar(
            select(PaymentReconciliation.id)
            .where(
                PaymentReconciliation.order_id == order.id, PaymentReconciliation.status == "open"
            )
            .limit(1)
        )
    )
    refund = bool(
        session.scalar(
            select(FinancialOperation.id)
            .where(
                FinancialOperation.order_id == order.id,
                FinancialOperation.kind == "refund",
                FinancialOperation.state != "withdrawn",
            )
            .limit(1)
        )
    )
    cancelled_request = (
        session.scalar(
            select(IdempotencyRecord.id).where(
                IdempotencyRecord.scope == f"delivery.cancel:{order.id}",
                IdempotencyRecord.key == "cancel",
            )
        )
        is not None
    )
    pending_dispatch = (
        session.scalar(
            select(IdempotencyRecord.id)
            .where(
                IdempotencyRecord.scope == f"delivery.dispatch:{order.id}",
                IdempotencyRecord.status != "completed",
            )
            .limit(1)
        )
        is not None
    )
    actions = []
    if (
        supported
        and row.status == "quoted"
        and not row.provider_delivery_reference
        and not pending_dispatch
        and not holds
        and not refund
        and order.payment_status == "paid"
        and order.status in {"accepted", "preparing", "ready"}
    ):
        actions.append("dispatch")
    if (
        supported
        and row.status not in {"picked_up", "delivered", "cancelled", "failed"}
        and not cancelled_request
        and not pending_dispatch
    ):
        actions.append("cancel")
    if (
        app.state.demo_mode
        and row.provider == "simulated_delivery"
        and row.provider_delivery_reference
        and order.status == "ready"
        and not cancelled_request
    ):
        if row.status == "courier_assigned":
            actions.append("picked_up")
        elif row.status == "picked_up":
            actions.append("delivered")
    return {
        **result,
        "actions": actions,
        "cancellation_requested": cancelled_request,
        "dispatch_pending": pending_dispatch,
        "provider_available": supported,
        "payment_review": holds,
        "refund_intent": refund,
        "timezone": session.get(RestaurantCommerceProfile, order.business_id).timezone,
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/sales-deliveries"

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, "operations.read")

    @app.get(root, dependencies=[Depends(read)])
    def deliveries(
        business_id: str,
        status: Literal[
            "all",
            "active",
            "quoted",
            "requested",
            "courier_assigned",
            "picked_up",
            "delivered",
            "cancelled",
            "failed",
        ] = "active",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
        date_from: str | None = None,
        date_to: str | None = None,
        session: Session = Depends(get_session),
    ):
        profile = session.get(RestaurantCommerceProfile, business_id)
        selected = period(date_from, date_to, timezone_name=profile.timezone)
        stmt = (
            select(Delivery)
            .join(Order)
            .where(Order.business_id == business_id, *clauses(Delivery.created_at, selected))
        )
        if status == "active":
            stmt = stmt.where(Delivery.status.notin_(["delivered", "cancelled", "failed"]))
        elif status != "all":
            stmt = stmt.where(Delivery.status == status)
        count = session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = session.scalars(
            stmt.options(selectinload(Delivery.order))
            .order_by(Delivery.created_at.desc(), Delivery.id)
            .offset(offset)
            .limit(limit)
        )
        return {
            "items": [describe(session, r, app) for r in rows],
            "count": count,
            "offset": offset,
            "limit": limit,
            "timezone": profile.timezone,
            "date_basis": "delivery_created_at",
        }

    @app.get(root + "/{delivery_id}", dependencies=[Depends(read)])
    def delivery(business_id: str, delivery_id: str, session: Session = Depends(get_session)):
        row = session.scalar(
            select(Delivery)
            .join(Order)
            .where(Order.business_id == business_id, Delivery.id == delivery_id)
            .options(selectinload(Delivery.order))
        )
        if not row:
            raise HTTPException(404, "Delivery not found")
        return describe(session, row, app)
