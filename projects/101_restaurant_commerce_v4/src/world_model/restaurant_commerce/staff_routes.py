"""Same-origin login, session recovery and explicit session revocation."""

# ruff: noqa: B008 -- FastAPI dependency declarations follow existing API style.
from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import staff
from .models import (
    RestaurantCommerceProfile,
    StaffAccount,
    StaffAudit,
    StaffMembership,
    StaffSession,
)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=15, max_length=128)


def register_staff_routes(app, get_session, cookie_name, production):
    def identity(request: Request, session: Session = Depends(get_session)):
        account, row = staff.authenticate(session, request.cookies.get(cookie_name))
        staff.csrf_check(request, row)
        return account, row

    @app.post("/api/staff/login")
    def login(
        body: LoginRequest,
        request: Request,
        response: Response,
        session: Session = Depends(get_session),
    ):
        staff.same_origin(request)
        if request.headers.get("x-101-login") != "1":
            raise HTTPException(403, "Same-origin login header required")
        raw = staff.login(
            session,
            body.username,
            body.password,
            request.client.host if request.client else "unknown",
            request.cookies.get(cookie_name),
        )
        response.set_cookie(
            cookie_name,
            raw,
            max_age=8 * 3600,
            httponly=True,
            secure=production,
            samesite="strict",
            path="/",
        )
        return {"authenticated": True}

    @app.get("/api/staff/me")
    def me(auth=Depends(identity), session: Session = Depends(get_session)):
        account, row = auth
        memberships = session.execute(
            select(StaffMembership, RestaurantCommerceProfile.display_name, RestaurantCommerceProfile.slug)
            .join(
                RestaurantCommerceProfile,
                StaffMembership.business_id == RestaurantCommerceProfile.business_id,
            )
            .where(StaffMembership.account_id == account.id)
        ).all()
        return {
            "actor_id": account.id,
            "username": account.username,
            "csrf": row.csrf,
            "expires_at": row.expires_at,
            "platform_admin": account.platform_admin,
            "businesses": [
                {
                    "business_id": m.business_id,
                    "name": name,
                    "slug": slug,
                    "role": m.role,
                    "permissions": sorted(staff.ROLES[m.role]),
                }
                for m, name, slug in memberships
            ],
        }

    @app.post("/api/staff/logout")
    def logout(
        response: Response,
        auth=Depends(identity),
        session: Session = Depends(get_session),
    ):
        account, row = auth
        row.revoked = True
        session.add(
            StaffAudit(actor_id=account.id, action="staff.logout", resource=account.id)
        )
        session.commit()
        response.delete_cookie(
            cookie_name, path="/", secure=production, httponly=True, samesite="strict"
        )
        return {"revoked": True}

    @app.post("/api/staff/logout-all")
    def logout_all(
        response: Response,
        auth=Depends(identity),
        session: Session = Depends(get_session),
    ):
        account, _ = auth
        session.execute(
            update(StaffSession)
            .where(StaffSession.account_id == account.id)
            .values(revoked=True)
        )
        session.execute(
            update(StaffAccount)
            .where(StaffAccount.id == account.id)
            .values(auth_version=StaffAccount.auth_version + 1)
        )
        session.add(
            StaffAudit(
                actor_id=account.id, action="staff.logout_all", resource=account.id
            )
        )
        session.commit()
        response.delete_cookie(
            cookie_name, path="/", secure=production, httponly=True, samesite="strict"
        )
        return {"revoked": True}
