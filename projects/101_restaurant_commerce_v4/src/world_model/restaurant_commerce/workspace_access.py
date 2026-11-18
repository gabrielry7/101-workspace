"""One staff HTML entry; existing staff/API authority still governs all data.

Legacy views remain accessible until their native replacements are qualified.
Customer, OAuth bridge, webhook and asset routes deliberately do not match here.
"""

# ruff: noqa: B008 -- FastAPI dependency declarations follow the existing routes.

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse

from . import staff
from .models import StaffMembership

LEGACY_PAGES = frozenset(
    {
        "/admin",
        "/delivery",
        "/growth",
        "/campaigns",
        "/whatsapp",
        "/sms",
        "/connections",
        "/customers/signup",
    }
)
WORKSPACE_PAGES = frozenset(
    {
        "/workspace",
        "/workspace/home",
        "/workspace/customers",
        "/workspace/sales",
        "/workspace/campaigns",
        "/workspace/social",
        "/workspace/reports",
        "/workspace/analytics",
        "/workspace/onboarding",
    }
)
RETURN_KEYS = frozenset(
    {
        "business",
        "business_id",
        "customer",
        "order",
        "campaign",
        "q",
        "offset",
        "kind",
        "view",
        "status",
        "state",
        "currency",
        "online_only",
        "date_from",
        "date_to",
        "pairing",
        "invite",
        "loyaltyId",
        "loyaltyTab",
        "loyaltyEdit",
        "loyaltyVersion",
        "setup",
        "setup_offset",
        "setup_q",
        "setup_state",
        "payment_status",
        "reservation",
        "reservation_status",
        "reservation_offset",
    }
)


def safe_destination(value):
    """Allow exact local staff paths and known UI state, never OAuth/secrets/next."""
    fallback = "/workspace/home"
    if not value or len(value) > 4096 or any(ord(c) < 32 for c in value) or "\\" in value:
        return fallback
    try:
        parsed = urlsplit(value)
        values = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=64)
    except ValueError:
        return fallback
    if parsed.scheme or parsed.netloc or parsed.path not in LEGACY_PAGES | WORKSPACE_PAGES:
        return fallback
    if any(k not in RETURN_KEYS or len(v) > 512 for k, v in values):
        return fallback
    if len({k for k, _ in values}) != len(values) or parsed.fragment:
        return fallback
    return urlunsplit(("", "", parsed.path, urlencode(values), ""))


def entry(session, account, destination, business=None):
    destination = safe_destination(destination)
    parsed = urlsplit(destination)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    member_ids = set(
        session.scalars(
            select(StaffMembership.business_id).where(
                StaffMembership.account_id == account.id,
                StaffMembership.role.in_(staff.ROLES),
            )
        )
    )
    requested = (
        business if business is not None else query.get("business", query.get("business_id"))
    )
    if business is not None and business != query.get("business", query.get("business_id")):
        for key in (
            "customer",
            "order",
            "reservation",
            "campaign",
            "loyaltyId",
            "loyaltyEdit",
            "loyaltyVersion",
            "offset",
            "reservation_offset",
        ):
            query.pop(key, None)
    denied = bool(requested and requested not in member_ids)
    selected = requested if requested in member_ids else None
    platform = parsed.path == "/workspace/onboarding" and account.platform_admin
    if not requested and len(member_ids) == 1 and not platform:
        selected = next(iter(member_ids))
    if not member_ids and account.platform_admin and not requested:
        return {"destination": "/workspace/onboarding", "needs_business": False, "denied": False}
    if not selected and not platform:
        return {"destination": None, "needs_business": True, "denied": denied}
    key = "business_id" if parsed.path in LEGACY_PAGES else "business"
    query.pop("business_id" if key == "business" else "business", None)
    if selected:
        query[key] = selected
    return {
        "destination": parsed.path + ("?" + urlencode(query) if query else ""),
        "needs_business": False,
        "denied": False,
    }


def register(app, get_session, cookie):
    @app.get("/api/staff/entry")
    def staff_entry(
        request: Request,
        next: str = Query("/workspace/home", max_length=4096),
        business: str | None = Query(None, max_length=200),
        session: Session = Depends(get_session),
    ):
        account, _ = staff.authenticate(session, request.cookies.get(cookie))
        try:
            return entry(session, account, next, business)
        except ValueError:
            raise HTTPException(400, "Invalid staff destination") from None

    def page_entry(request):
        with app.state.session_factory() as session:
            account, _ = staff.authenticate(session, request.cookies.get(cookie))
            return entry(
                session,
                account,
                request.url.path + ("?" + request.url.query if request.url.query else ""),
            )

    async def staff_html_boundary(request: Request):
        if request.method in {"GET", "HEAD"} and request.url.path in LEGACY_PAGES | WORKSPACE_PAGES:
            destination = safe_destination(
                request.url.path + ("?" + request.url.query if request.url.query else "")
            )
            try:
                result = await run_in_threadpool(page_entry, request)
            except HTTPException as exc:
                if exc.status_code != 401:
                    raise
                result = {"needs_business": True}
            except ValueError:
                result = {"needs_business": True}
            # Workspace chooses natively. Legacy scripts may not silently select a tenant.
            if (
                result["needs_business"] and request.url.path in LEGACY_PAGES
            ) or "destination" not in result:
                return RedirectResponse(
                    "/workspace/login?" + urlencode({"next": destination}),
                    status_code=307,
                    headers={"Cache-Control": "no-store"},
                )
            if not result["needs_business"] and result.get("destination") != destination:
                return RedirectResponse(
                    result["destination"], status_code=307, headers={"Cache-Control": "no-store"}
                )
        return None

    # Run inside the existing reliability/security middleware, so redirects receive
    # the same CSP, framing, referrer and request-observability headers as pages.
    app.state.staff_html_boundary = staff_html_boundary
