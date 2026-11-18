"""Bounded reservation read model; canonical service owns transitions/history."""

# ruff: noqa: B008 -- FastAPI dependencies follow the existing route contract.

from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .enums import RESERVATION_TRANSITIONS, ReservationStatus
from .models import Reservation, RestaurantCommerceProfile
from .service import RestaurantCommerceService
from .workspace_period import clauses, period


def describe(session, row):
    return {
        **RestaurantCommerceService(session)._reservation_to_out(row).model_dump(mode="json"),
        "actions": sorted(t.value for t in RESERVATION_TRANSITIONS[ReservationStatus(row.status)]),
    }


def register(app, get_session, scoped_staff):
    root = "/api/operator/restaurants/{business_id}/sales-reservations"

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, "operations.read")

    @app.get(root, dependencies=[Depends(read)])
    def reservations(
        business_id: str,
        status: Literal[
            "all", "active", "requested", "confirmed", "seated", "completed", "cancelled", "no_show"
        ] = "active",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
        date_from: str | None = None,
        date_to: str | None = None,
        session: Session = Depends(get_session),
    ):
        profile = session.get(RestaurantCommerceProfile, business_id)
        selected = period(date_from, date_to, timezone_name=profile.timezone)
        stmt = select(Reservation).where(
            Reservation.business_id == business_id, *clauses(Reservation.starts_at, selected)
        )
        if status == "active":
            stmt = stmt.where(Reservation.status.in_(["requested", "confirmed", "seated"]))
        elif status != "all":
            stmt = stmt.where(Reservation.status == status)
        count = session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = session.scalars(
            stmt.options(selectinload(Reservation.customer))
            .order_by(Reservation.starts_at, Reservation.id)
            .offset(offset)
            .limit(limit)
        )
        return {
            "items": [describe(session, r) for r in rows],
            "count": count,
            "offset": offset,
            "limit": limit,
            "timezone": profile.timezone,
            "date_basis": "starts_at",
        }

    @app.get(root + "/{reservation_id}", dependencies=[Depends(read)])
    def reservation(business_id: str, reservation_id: str, session: Session = Depends(get_session)):
        row = session.scalar(
            select(Reservation)
            .where(Reservation.business_id == business_id, Reservation.id == reservation_id)
            .options(selectinload(Reservation.customer))
        )
        if not row:
            raise HTTPException(404, "Reservation not found")
        return {
            **describe(session, row),
            "timezone": session.get(RestaurantCommerceProfile, business_id).timezone,
        }
