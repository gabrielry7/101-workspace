"""Business-scoped native retention reads; original growth service owns all writes."""

# ruff: noqa: B008 -- existing FastAPI dependency convention
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .growth import RestaurantGrowthService
from .models import Order, OutboundMessage, RestaurantCommerceProfile


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/growth-workspace"

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, "growth.read")

    @app.get(root, dependencies=[Depends(read)])
    def context(business_id: str, session: Session = Depends(get_session)):
        profile = session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise HTTPException(404, "Business not found")
        currencies = session.scalars(
            select(Order.currency)
            .where(
                Order.business_id == business_id,
                Order.status == "completed",
                Order.payment_status == "paid",
            )
            .distinct()
            .order_by(Order.currency)
        ).all()
        return {
            "currency": profile.currency,
            "currencies": currencies,
            "timezone": profile.timezone,
            "winback_days": profile.winback_days,
            "analytics": RestaurantGrowthService(session).analytics(business_id),
            "basis": (
                "all_history_completed_currently_paid_orders_without_partial_refund_adjustment"
            ),
        }

    @app.get(root + "/outbox", dependencies=[Depends(read)])
    def outbox(
        business_id: str,
        status: Literal["all", "queued", "handed_off", "suppressed", "sent", "failed"] = "all",
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0, le=100000),
        session: Session = Depends(get_session),
    ):
        stmt = select(OutboundMessage).where(OutboundMessage.business_id == business_id)
        if status != "all":
            stmt = stmt.where(OutboundMessage.status == status)
        count = session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = session.scalars(
            stmt.order_by(OutboundMessage.scheduled_at, OutboundMessage.id)
            .offset(offset)
            .limit(limit)
        )
        growth = RestaurantGrowthService(session)
        return {"items": [growth._message_out(row) for row in rows], "count": count}
