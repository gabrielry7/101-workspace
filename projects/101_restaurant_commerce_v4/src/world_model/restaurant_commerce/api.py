from __future__ import annotations

import json
from contextlib import asynccontextmanager
import logging
import os
import re
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .cache import TTLCache
from .readiness import ReadinessProbe
from .db import database_ready, init_schema, make_engine, session_factory
from .deliveries import (
    DeliveryProvider,
    MensajerosUrbanosDeliveryProvider,
    SimulatedDeliveryProvider,
    UberDirectDeliveryProvider,
)
from .enums import PaymentStatus
from .errors import (
    ConcurrencyConflictError,
    DeliveryError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    PaymentError,
    ProviderCircuitOpenError,
    ValidationError,
)
from .events import EventSink, NullEventSink
from .growth import RestaurantGrowthService
from .models import Order, Delivery, Reservation, OutboundMessage, StaffAudit
from . import staff
from .staff_routes import register_staff_routes
from .notifications import format_order_message, format_reservation_message, whatsapp_click_to_chat_url
from .observability import MetricsRegistry
from .payments import (
    CashAtPickupPaymentProvider,
    PaymentProvider,
    SimulatedPaymentProvider,
    WompiPaymentProvider,
)
from .reliability import ProviderExecutor
from .schemas import (
    FinancialActionRequest,
    FinancialResolutionRequest,
    ErrorResponse,
    AutomationRuleCreateIn,
    AutomationRuleOut,
    CommerceCapabilityOut,
    CreateOrderRequest,
    CreateReservationRequest,
    DeliveryOut,
    DeliveryQuoteOut,
    DeliveryQuoteRequest,
    DeliveryStatusPatch,
    DeliveryTrackingOut,
    DeliveryWebhookIn,
    GrowthAnalyticsOut,
    LoyaltyAccountOut,
    MarkMessageSentIn,
    OrderOut,
    OrderStatusPatch,
    OutboundMessageOut,
    PaymentWebhookIn,
    PromotionCreateIn,
    PromotionOut,
    QuoteRequest,
    QuoteResponse,
    ReservationOut,
    ReservationStatusPatch,
    RewardCreateIn,
    RewardOut,
    StorefrontOut,
    WinbackPlanIn,
)
from .security import (
    FixedWindowRateLimiter,
    MaxBodySizeMiddleware,
    sign_resource,
    RESOURCE_TOKEN_TTL_SECONDS,
    verify_resource_token,
    verify_webhook,
)
from .seed import DEMO_BUSINESS_ID, seed_demo
from .service import RestaurantCommerceService
from .payment_workflow import CheckoutRecoveryExpired
from .recovery import start_recovery
from .schemas import RecoverOrderRequest, PaymentNotificationAccepted, LoyaltyRefundAllocationIn

WEB_DIR = Path(__file__).with_name("web")
logger = logging.getLogger("101.restaurant_commerce")


def _default_payment_providers(*, production: bool = False) -> dict[str, PaymentProvider]:
    providers: dict[str, PaymentProvider] = {
        "cash_at_pickup": CashAtPickupPaymentProvider(),
        "wompi": WompiPaymentProvider(configured=False),
    }
    if not production:
        providers["simulated"] = SimulatedPaymentProvider()
    return providers


def _default_delivery_providers(*, production: bool = False) -> dict[str, DeliveryProvider]:
    providers: dict[str, DeliveryProvider] = {
        "uber_direct": UberDirectDeliveryProvider(configured=False),
        "mensajeros_urbanos": MensajerosUrbanosDeliveryProvider(configured=False),
    }
    if not production:
        providers["simulated_delivery"] = SimulatedDeliveryProvider()
    return providers


def create_app(
    *,
    database_url: str | None = None,
    engine: Engine | None = None,
    seed: bool = False,
    operator_token: str | None = None,
    environment: str | None = None,
    demo_mode: bool | None = None,
    public_access_secret: str | None = None,
    webhook_secrets: dict[str, str] | None = None,
    payment_providers: dict[str, PaymentProvider] | None = None,
    financial_providers: dict | None = None,
    wompi_sandbox=None,
    financial_authenticator=None,
    delivery_providers: dict[str, DeliveryProvider] | None = None,
    event_sink: EventSink | None = None,
    rate_limit_per_minute: int = 120,
    max_body_bytes: int = 1_048_576,
    storefront_cache_ttl_seconds: float = 15.0,
    auto_init_schema: bool | None = None,
    payment_recovery_enabled: bool = True,
    provider_recovery_enabled: bool = True,
    payment_recovery_interval_seconds: float = 1.0,
    payment_lease_seconds: int = 30,
    checkout_url_origins: tuple[str, ...] = (),
    tracking_url_origins: tuple[str, ...] = (),
    campaign_options: dict | None = None,
    loyalty_configuration_enabled: bool | None = None,
) -> FastAPI:
    def validated_origins(origins: tuple[str, ...]) -> list[str]:
        result = []
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.path not in ("", "/")
                    or parsed.query or parsed.fragment or "\\" in origin
                    or any(ord(c) <= 32 or ord(c) == 127 for c in origin)):
                raise ValueError("Browser URL policy requires HTTPS origins without credentials or paths")
            # Reject invalid ports and canonicalize the default HTTPS port.
            port = parsed.port
            host = parsed.hostname.encode("idna").decode("ascii")
            if ":" in host:
                host = f"[{host}]"
            result.append(f"https://{host}" + (f":{port}" if port is not None and port != 443 else ""))
        return result

    browser_policy = {"checkout_origins": validated_origins(checkout_url_origins),
                      "tracking_origins": validated_origins(tracking_url_origins)}
    campaign_options = campaign_options or {}
    if loyalty_configuration_enabled is None:
        loyalty_flag = os.getenv("COMMERCE_LOYALTY_CONFIGURATION_ENABLED", "0")
        if loyalty_flag not in {"0", "1"}:
            raise RuntimeError("COMMERCE_LOYALTY_CONFIGURATION_ENABLED must be 0 or 1")
        loyalty_configuration_enabled = loyalty_flag == "1"
    environment = (environment or os.getenv("COMMERCE_ENV", "development")).lower()
    production = environment == "production"
    demo_mode = (not production) if demo_mode is None else demo_mode
    auto_init_schema = (not production) if auto_init_schema is None else auto_init_schema
    if financial_authenticator is not None:
        raise RuntimeError("External financial token authority was removed; use named staff sessions")
    if wompi_sandbox is not None:
        from .wompi_sandbox import CHECKOUT_ORIGIN, NAME, WompiSandboxProvider
        if production or not isinstance(wompi_sandbox, WompiSandboxProvider):
            raise RuntimeError("Wompi sandbox is forbidden in production")
        payment_providers = {**(payment_providers or {}), NAME: wompi_sandbox}
        from .wompi_financial import WompiSandboxFinancialProvider
        # This adapter has no refund POST implementation; financial writes remain gated.
        financial_providers = {**(financial_providers or {}), NAME: WompiSandboxFinancialProvider(wompi_sandbox)}
        browser_policy["checkout_origins"] = list(set(browser_policy["checkout_origins"] + [CHECKOUT_ORIGIN]))
    if production and any(getattr(p, "sandbox_only", False) for p in (payment_providers or {}).values()):
        raise RuntimeError("Sandbox payment providers are forbidden in production")
    if production and financial_providers:
        raise RuntimeError("M3b financial execution is controlled-only; production is gated")
    if production and seed:
        raise RuntimeError("Demo seed data is forbidden in production")
    if production and demo_mode:
        raise RuntimeError("Demo mode is forbidden in production")

    # Retained argument only for caller migration; it never grants authority.
    token = operator_token or os.getenv("COMMERCE_OPERATOR_TOKEN") or "dev-operator"

    access_secret = public_access_secret or os.getenv("COMMERCE_PUBLIC_ACCESS_SECRET")
    if not access_secret:
        if production:
            raise RuntimeError("COMMERCE_PUBLIC_ACCESS_SECRET is required in production")
        access_secret = f"dev-public:{token}"
    if production and len(access_secret) < 32:
        raise RuntimeError("Production public access secret must be at least 32 characters")

    engine = engine or make_engine(database_url)
    if auto_init_schema:
        init_schema(engine)
    if wompi_sandbox is not None:
        from sqlalchemy import inspect
        from .models import WompiSandboxDiscovery, WompiSandboxLookup
        inspector = inspect(engine)
        for table in (WompiSandboxLookup.__table__, WompiSandboxDiscovery.__table__):
            if (table.name not in inspector.get_table_names() or not set(table.columns.keys()).issubset(
                    {c["name"] for c in inspector.get_columns(table.name)})):
                raise RuntimeError("Run explicit offline upgrade-wompi-sandbox before enabling sandbox")
    SessionLocal = session_factory(engine)

    if seed:
        with SessionLocal() as session:
            seed_demo(session)

    provider_executor = ProviderExecutor()
    payment_providers = payment_providers or _default_payment_providers(production=production)
    delivery_providers = delivery_providers or _default_delivery_providers(production=production)
    event_sink = event_sink or NullEventSink()
    storefront_cache: TTLCache[StorefrontOut] = TTLCache(
        ttl_seconds=storefront_cache_ttl_seconds, max_entries=4096
    )
    metrics = MetricsRegistry()
    limiter = FixedWindowRateLimiter(limit=rate_limit_per_minute, window_seconds=60)
    configured_webhook_secrets = dict(webhook_secrets or {})
    for provider in set(payment_providers) | set(delivery_providers):
        env_key = "COMMERCE_WEBHOOK_SECRET_" + re.sub(r"[^A-Z0-9]", "_", provider.upper())
        value = os.getenv(env_key)
        if value and provider not in configured_webhook_secrets:
            configured_webhook_secrets[provider] = value

    if payment_recovery_interval_seconds <= 0 or payment_lease_seconds < 1:
        raise ValueError("Recovery interval/lease must be positive")

    readiness = ReadinessProbe(
        lambda deadline: database_ready(
            engine, require_loyalty=loyalty_configuration_enabled, deadline=deadline
        )
    )

    @asynccontextmanager
    async def lifespan(_app):
        stop = thread = None
        if payment_recovery_enabled:
            stop, thread = start_recovery(SessionLocal, interval_seconds=payment_recovery_interval_seconds,
                service_options={"payment_providers": payment_providers, "delivery_providers": delivery_providers,
                    "event_sink": event_sink, "provider_executor": provider_executor,
                    "payment_lease_seconds": payment_lease_seconds, "financial_providers": financial_providers},
                campaign_options=campaign_options)
        try:
            yield
        finally:
            readiness.close()
            if stop:
                stop.set()
                thread.join(timeout=5)

    app = FastAPI(lifespan=lifespan, title="101 Restaurant Commerce", version="0.18.0",
                  responses={status: {"model": ErrorResponse} for status in
                             (400, 401, 403, 404, 409, 410, 413, 422, 429, 500, 503)})
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=max_body_bytes)
    app.state.engine = engine
    app.state.session_factory = SessionLocal
    app.state.operator_token = token
    app.state.public_access_secret = access_secret
    app.state.provider_executor = provider_executor
    app.state.payment_providers = payment_providers
    app.state.delivery_providers = delivery_providers
    app.state.event_sink = event_sink
    app.state.storefront_cache = storefront_cache
    app.state.metrics = metrics
    app.state.webhook_secrets = configured_webhook_secrets
    app.state.demo_mode = demo_mode
    app.state.environment = environment
    app.state.auto_init_schema = auto_init_schema

    @app.middleware("http")
    async def reliability_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        if len(request_id) > 128:
            request_id = uuid4().hex
        started = time.perf_counter()
        path = request.url.path
        if "\x00" in path or any("\x00" in value or "\x00" in key
                                 for key, value in request.query_params.multi_items()):
            return _json_error(400, "NUL characters are not permitted")
        client_ip = request.client.host if request.client else "unknown"
        is_public_mutation = (
            request.method in {"POST", "PATCH", "PUT", "DELETE"}
            and (
                path.startswith("/api/restaurants/")
                or path.startswith("/api/payments/simulated/")
                or path.startswith("/api/webhooks/")
            )
        )
        if is_public_mutation and not path.startswith("/api/operator/"):
            allowed, retry_after = limiter.allow(client_ip)
            if not allowed:
                response = JSONResponse(
                    {"detail": "Too many requests", "request_id": request_id}, status_code=429
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-Request-ID"] = request_id
                return response

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled restaurant commerce request failure",
                extra={"request_id": request_id, "method": request.method,
                       "route": getattr(request.scope.get("route"), "path", "unmatched")},
            )
            response = JSONResponse(
                {"detail": "Internal server error", "request_id": request_id}, status_code=500
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        route_obj = request.scope.get("route")
        route = getattr(route_obj, "path", "unmatched")
        metrics.record_request(request.method, route, response.status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.3f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
            "object-src 'none'; img-src 'self' data:; form-action 'self'; "
            "script-src 'self'; script-src-attr 'none'; style-src 'self'; "
            "connect-src 'self'"
        )
        if request.scope.get("endpoint") and request.scope["endpoint"].__name__ == "campaign_email_preview":
            # Escaped email renderer only; no scripts, remote images or form actions.
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = getattr(
                request.state, "campaign_preview_csp",
                "default-src 'none'; frame-ancestors 'self'; sandbox",
            )
        if production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if (
            (path.startswith("/api/restaurants/") and request.method == "POST")
            or path.startswith("/api/operator/")
            or path.startswith("/api/staff/")
            or path.startswith("/api/finance/")
            or path.startswith("/api/webhooks/")
            or path.startswith("/api/orders/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    def get_session() -> Iterator[Session]:
        with SessionLocal() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    def get_service(session: Session = Depends(get_session)) -> RestaurantCommerceService:
        service = RestaurantCommerceService(
            session,
            payment_providers=payment_providers,
            financial_providers=financial_providers,
            delivery_providers=delivery_providers,
            event_sink=event_sink,
            provider_executor=provider_executor,
            storefront_cache=storefront_cache,
            payment_lease_seconds=payment_lease_seconds,
        )
        from .operations import quote_binding
        service.quote_validator = lambda business, request, total: verify_resource_token(
            access_secret, request.quote_token, kind="quote", resource_id=quote_binding(business, request, total))
        return service

    def get_growth(session: Session = Depends(get_session)) -> RestaurantGrowthService:
        return RestaurantGrowthService(session)

    staff_cookie = "__Host-commerce_staff" if production else staff.COOKIE
    register_staff_routes(app, get_session, staff_cookie, production)

    def scoped_staff(request, session, business_id, permission):
        account, auth_session = staff.authenticate(session, request.cookies.get(staff_cookie))
        staff.csrf_check(request, auth_session)
        principal = staff.authority(session, account, auth_session, business_id, permission)
        action = request.scope["endpoint"].__name__
        resource = str(request.path_params.get("order_id") or request.path_params.get("delivery_id")
                       or request.path_params.get("reservation_id") or request.path_params.get("message_id")
                       or business_id or "platform")[:200]
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            session.add(StaffAudit(actor_id=account.id, business_id=business_id,
                                  action=action+".authorized", resource=resource))
            session.commit()
        # Service methods own their commits. Capture actor in EACH same transaction,
        # including commits made before a later provider failure; rollback rolls audit back.
        from sqlalchemy import event
        def audit_commit(current):
            current.add(StaffAudit(actor_id=account.id, business_id=business_id,
                                   action=action+".commit", resource=resource))
        event.listen(session, "before_commit", audit_commit)
        return principal

    def require_operator(request: Request, session: Session = Depends(get_session)):
        # Authenticate before resolving IDs, to avoid an unauthenticated existence oracle.
        staff.authenticate(session, request.cookies.get(staff_cookie))
        business_id = request.path_params.get("business_id")
        if not business_id:
            for key, model in (("order_id", Order), ("reservation_id", Reservation),
                               ("delivery_id", Delivery), ("message_id", OutboundMessage)):
                if key in request.path_params:
                    obj = session.get(model, request.path_params[key])
                    if isinstance(obj, Delivery):
                        obj = session.get(Order, obj.order_id)
                    if obj is None:
                        raise HTTPException(404, "Resource not found")
                    business_id = obj.business_id
                    break
        name = request.scope["endpoint"].__name__
        permissions = {
            "operator_orders": "operations.read", "operator_order_detail": "operations.read",
            "operations_settings": "operations.read", "save_operations_settings": "settings.write",
            "save_item_stock": "settings.write", "daily_finance": "finance.read", "operator_deliveries": "operations.read",
            "operator_reservations": "operations.read", "operator_order_status": "operations.write",
            "operator_dispatch_delivery": "operations.write", "operator_cancel_delivery": "operations.write",
            "operator_delivery_status": "operations.write", "operator_reservation_status": "operations.write",
            "revoke_order_access": "operations.write", "order_whatsapp": "contact.read",
            "reservation_whatsapp": "contact.read", "loyalty_account": "growth.read",
            "rewards": "growth.read", "promotions": "growth.read", "automations": "growth.read",
            "outbox": "growth.read", "analytics": "growth.read", "create_reward": "growth.write",
            "create_promotion": "growth.write", "create_automation": "growth.write",
            "plan_winback": "growth.write", "handoff_outbox": "growth.write", "mark_outbox_sent": "growth.write",
            "payment_reconciliation": "finance.read",
            "drain_events": "platform", "recover_payments": "platform", "operator_metrics": "platform",
        }
        permission = permissions.get(name)
        if permission is None:
            raise HTTPException(403, "Route has no staff permission policy")
        return scoped_staff(request, session, business_id, permission)

    def require_order_access(
        order_id: str,
        x_101_order_token: str | None = Header(default=None),
        session: Session = Depends(get_session),
    ) -> None:
        order = session.get(Order, order_id)
        if not order or not order.customer_snapshot_json or not verify_resource_token(
            access_secret, x_101_order_token, kind="order", resource_id=order_id,
            version=order.access_token_version
        ):
            raise HTTPException(status_code=401, detail="Missing or invalid order access token")

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_, exc: RequestValidationError):
        # Do not echo credentials/PII, non-finite numbers or invalid Unicode from
        # hostile input into the error encoder. ASCII escaping also protects loc.
        errors = [{key: value for key, value in error.items()
                   if key in {"type", "loc", "msg"}} for error in exc.errors()]
        return Response(json.dumps({"detail": errors}, ensure_ascii=True),
                        status_code=422, media_type="application/json")

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_, exc: NotFoundError):
        return _json_error(404, str(exc))

    @app.exception_handler(ValidationError)
    async def validation_handler(_, exc: ValidationError):
        return _json_error(422, str(exc))

    async def conflict_handler(_, exc):
        return _json_error(409, str(exc))

    async def dependency_handler(_, exc):
        return _json_error(503, str(exc))

    for exc_type in (InvalidTransitionError, IdempotencyConflictError, ConcurrencyConflictError):
        app.add_exception_handler(exc_type, conflict_handler)
    for exc_type in (PaymentError, DeliveryError, ProviderCircuitOpenError):
        app.add_exception_handler(exc_type, dependency_handler)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", responses={503: {"model": dict[str, str]}})
    async def ready():
        if not await readiness.ready():
            return JSONResponse(
                {"status": "not_ready", "database": "down"}, status_code=503,
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(
            {"status": "ready", "database": "ok"}, headers={"Cache-Control": "no-store"}
        )

    from .campaign_routes import register as register_campaigns
    register_campaigns(app, get_session, scoped_staff, campaign_options, demo_mode)
    if loyalty_configuration_enabled:
        if not database_ready(engine, require_loyalty=True):
            raise RuntimeError("Loyalty configuration requires the explicit offline upgrade")
        from .loyalty_routes import register as register_loyalty
        register_loyalty(app, get_session, scoped_staff)

    from .operations import register_operations
    register_operations(app, get_service, require_operator)

    @app.get("/api/browser-policy")
    def browser_url_policy():
        return {**browser_policy, "demo_mode": demo_mode, "wompi_sandbox": wompi_sandbox is not None}

    @app.get("/assets/{filename}")
    def browser_script(filename: str):
        if filename not in {"brand-ad5abbbd672d1f408b7eb235e06e3f435acad153d08bec2c316f5708037ec730.png", "campaigns.js", "campaigns.css", "shared.js", "staff.js", "index.js", "admin.js", "delivery.js", "growth.js", "boot.js", "theme.css", "growth.css", "delivery.css", "operations.js"}:
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(WEB_DIR / filename, media_type="image/png" if filename.endswith(".png") else "text/css" if filename.endswith(".css") else "text/javascript",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/")
    def storefront_page():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/r/{slug}")
    def merchant_storefront(slug: str, session: Session = Depends(get_session)):
        from sqlalchemy import select
        from urllib.parse import quote as url_quote
        from .models import RestaurantCommerceProfile
        profile = session.scalar(select(RestaurantCommerceProfile).where(RestaurantCommerceProfile.slug == slug))
        if profile is None:
            raise HTTPException(404, "Restaurante no encontrado")
        return RedirectResponse("/?business_id=" + url_quote(profile.business_id, safe=""), status_code=307)

    @app.get("/admin")
    def admin_page():
        return FileResponse(WEB_DIR / "admin.html")

    @app.get("/growth")
    def growth_page():
        return FileResponse(WEB_DIR / "growth.html")

    @app.get("/delivery")
    def delivery_page():
        return FileResponse(WEB_DIR / "delivery.html")

    if demo_mode:
        @app.get("/demo")
        def demo_redirect():
            return RedirectResponse(url=f"/?business_id={DEMO_BUSINESS_ID}")

    @app.get("/api/restaurants/{business_id}/storefront", response_model=StorefrontOut)
    def storefront(business_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.storefront(business_id)

    @app.get("/api/restaurants/{business_id}/capability", response_model=CommerceCapabilityOut)
    def capability(business_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.capability(business_id)

    @app.post("/api/restaurants/{business_id}/orders/quote", response_model=QuoteResponse)
    def quote(business_id: str, request: QuoteRequest, service: RestaurantCommerceService = Depends(get_service)):
        result = service.quote(
            business_id, request.items, promo_code=request.promo_code,
            customer_phone=request.customer_phone, reward_id=request.reward_id,
        )
        from .operations import quote_binding
        expiry = int(time.time()) + 120
        return result.model_copy(update={"quote_token": sign_resource(access_secret, kind="quote",
            resource_id=quote_binding(business_id, request, result.total_minor), expires_at=expiry),
            "expires_at": datetime.fromtimestamp(expiry, timezone.utc)})

    @app.post("/api/restaurants/{business_id}/delivery/quote", response_model=DeliveryQuoteOut)
    def delivery_quote(
        business_id: str,
        request: DeliveryQuoteRequest,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.create_delivery_quote(business_id, request.destination)

    @app.post("/api/restaurants/{business_id}/orders", response_model=OrderOut)
    def create_order(
        business_id: str,
        request: CreateOrderRequest,
        http_request: Request,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        request = request.model_copy(update={"customer": request.customer.model_copy(
            update={"consent_source": "web_checkout:commerce-consent-v1"})})
        # Public browser traffic cannot self-assert acquisition/channel attribution.
        # Authenticated integrations should use a dedicated server-side boundary.
        request = request.model_copy(update={"source_channel": "web", "external_source_ref": None})
        from .models import utcnow
        from .campaigns import checkout_context, digest as campaign_digest
        context = checkout_context(service.session, business_id,
            http_request.cookies.get("campaign_visit_" + campaign_digest(business_id)[:16]),
            campaign_options.get("clock", utcnow)(), demo_mode=demo_mode)
        if context:
            request = request.model_copy(update=context)
        order = service.create_order(business_id, request)
        return with_order_access(order)

    def with_order_access(order):
        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expires_at = int(created_at.timestamp()) + RESOURCE_TOKEN_TTL_SECONDS
        if expires_at <= int(time.time()):
            raise HTTPException(status_code=409, detail="Order access window has expired; contact staff")
        return order.model_copy(update={"access_token": sign_resource(
            access_secret, kind="order", resource_id=order.id, expires_at=expires_at)})

    @app.post("/api/restaurants/{business_id}/orders/recover", response_model=OrderOut)
    def recover_order(business_id: str, request: RecoverOrderRequest,
                      service: RestaurantCommerceService = Depends(get_service)):
        if request.wompi_transaction_id and not provider_recovery_enabled:
            raise HTTPException(503, "Provider recovery is disabled in this deployment")
        try:
            order = service.recover_order(business_id, request.idempotency_key, request.recovery_secret)
        except CheckoutRecoveryExpired as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc
        if request.wompi_transaction_id:
            from .wompi_workflow import enqueue, process
            key = enqueue(service, request.wompi_transaction_id, order.id)
            process(service, key)
            order = service.order_out(order.id)
        return with_order_access(order)

    @app.post("/api/operator/orders/{order_id}/access/revoke", dependencies=[Depends(require_operator)])
    def revoke_order_access(order_id: str, service: RestaurantCommerceService = Depends(get_service)):
        service.revoke_order_access(order_id)
        return {"status": "revoked"}

    @app.get(
        "/api/orders/{order_id}",
        response_model=OrderOut,
        dependencies=[Depends(require_order_access)],
    )
    def get_order(order_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.order_out(order_id)

    @app.get(
        "/api/orders/{order_id}/delivery/tracking",
        response_model=DeliveryTrackingOut,
        dependencies=[Depends(require_order_access)],
    )
    def delivery_tracking(order_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.delivery_tracking(order_id)

    if demo_mode:
        @app.post("/api/payments/simulated/{provider_reference}/complete", response_model=OrderOut)
        def complete_simulated_payment(
            provider_reference: str,
            service: RestaurantCommerceService = Depends(get_service),
        ):
            if not provider_reference.startswith("sim_"):
                raise HTTPException(status_code=400, detail="Only simulated payments may use this endpoint")
            return service.apply_payment_status(provider_reference, PaymentStatus.PAID.value)

    @app.post("/api/restaurants/{business_id}/reservations", response_model=ReservationOut)
    def create_reservation(
        business_id: str,
        request: CreateReservationRequest,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        request = request.model_copy(update={"source_channel": "web", "external_source_ref": None})
        request = request.model_copy(update={"source_channel": "web", "external_source_ref": None,
            "customer": request.customer.model_copy(update={"consent_source": "web_reservation:commerce-consent-v1"})})
        return service.create_reservation(business_id, request)

    @app.post("/api/webhooks/payments/wompi_sandbox")
    def wompi_sandbox_webhook(payload: dict, service: RestaurantCommerceService = Depends(get_service)):
        if wompi_sandbox is None:
            raise HTTPException(status_code=404, detail="Sandbox webhook not configured")
        try:
            transaction_id = wompi_sandbox.verify_event(payload)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid sandbox event") from None
        from .wompi_workflow import enqueue
        enqueue(service, transaction_id, event_key=payload["signature"]["checksum"].lower())
        return {"status": "accepted"}

    @app.post("/api/webhooks/payments/{provider}", response_model=OrderOut,
              responses={202: {"model": PaymentNotificationAccepted}})
    async def payment_webhook(
        provider: str,
        request: Request,
        x_101_webhook_signature: str | None = Header(default=None),
        service: RestaurantCommerceService = Depends(get_service),
    ):
        secret = configured_webhook_secrets.get(provider)
        if not secret:
            raise HTTPException(status_code=404, detail="Webhook provider is not configured")
        body = await request.body()
        if not verify_webhook(secret, body, x_101_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        try:
            payload = PaymentWebhookIn.model_validate_json(body)
        except PydanticValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        result = service.receive_payment_notification(provider, payload)
        if isinstance(result, PaymentNotificationAccepted):
            return JSONResponse(status_code=202, content=result.model_dump(mode="json"))
        return result

    @app.post("/api/webhooks/deliveries/{provider}", response_model=DeliveryOut)
    async def delivery_webhook(
        provider: str,
        request: Request,
        x_101_webhook_signature: str | None = Header(default=None),
        service: RestaurantCommerceService = Depends(get_service),
    ):
        secret = configured_webhook_secrets.get(provider)
        if not secret:
            raise HTTPException(status_code=404, detail="Webhook provider is not configured")
        body = await request.body()
        if not verify_webhook(secret, body, x_101_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        try:
            payload = DeliveryWebhookIn.model_validate_json(body)
        except PydanticValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        return service.apply_delivery_status(
            payload.provider_delivery_reference,
            payload.status,
            provider=provider,
            event_id=payload.event_id,
            occurred_at=payload.occurred_at,
            raw_event_json=body.decode("utf-8", errors="replace"),
        )

    @app.get(
        "/api/operator/restaurants/{business_id}/orders",
        response_model=list[OrderOut],
        dependencies=[Depends(require_operator)],
    )
    def operator_orders(
        business_id: str,
        status: str | None = Query(default=None),
        offset: int = Query(default=0, ge=0, le=100000),
        limit: int = Query(default=50, ge=1, le=100),
        active: bool = Query(default=False),
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.list_orders(business_id, status=status, limit=limit, offset=offset, active=active)

    @app.patch(
        "/api/operator/orders/{order_id}",
        response_model=OrderOut,
        dependencies=[Depends(require_operator)],
    )
    def operator_order_status(
        order_id: str,
        patch: OrderStatusPatch,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.transition_order(order_id, patch.status, expected_version=patch.expected_version, reason=patch.reason)

    @app.get(
        "/api/operator/restaurants/{business_id}/deliveries",
        response_model=list[DeliveryOut],
        dependencies=[Depends(require_operator)],
    )
    def operator_deliveries(
        business_id: str,
        status: str | None = Query(default=None),
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.list_deliveries(business_id, status=status)

    @app.post(
        "/api/operator/orders/{order_id}/delivery/dispatch",
        response_model=DeliveryOut,
        dependencies=[Depends(require_operator)],
    )
    def operator_dispatch_delivery(order_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.dispatch_delivery(order_id)

    @app.post(
        "/api/operator/orders/{order_id}/delivery/cancel",
        response_model=DeliveryOut,
        dependencies=[Depends(require_operator)],
    )
    def operator_cancel_delivery(order_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.cancel_delivery(order_id)

    @app.patch(
        "/api/operator/deliveries/{delivery_id}/status",
        response_model=DeliveryOut,
        dependencies=[Depends(require_operator)],
    )
    def operator_delivery_status(
        delivery_id: str,
        patch: DeliveryStatusPatch,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        if not demo_mode:
            raise HTTPException(status_code=404, detail="Manual delivery status endpoint is disabled")
        delivery = service.delivery_out(delivery_id)
        if delivery.provider != "simulated_delivery":
            raise HTTPException(
                status_code=409,
                detail="Manual delivery status changes are demo-only; production providers require verified webhooks",
            )
        if not delivery.provider_delivery_reference:
            raise HTTPException(status_code=409, detail="Delivery has not been dispatched")
        return service.apply_delivery_status(delivery.provider_delivery_reference, patch.status)

    @app.get(
        "/api/operator/restaurants/{business_id}/reservations",
        response_model=list[ReservationOut],
        dependencies=[Depends(require_operator)],
    )
    def operator_reservations(
        business_id: str,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.list_reservations(business_id)

    @app.patch(
        "/api/operator/reservations/{reservation_id}",
        response_model=ReservationOut,
        dependencies=[Depends(require_operator)],
    )
    def operator_reservation_status(
        reservation_id: str,
        patch: ReservationStatusPatch,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.transition_reservation(reservation_id, patch.status)

    @app.get("/api/operator/orders/{order_id}/whatsapp", dependencies=[Depends(require_operator)])
    def order_whatsapp(
        order_id: str,
        destination_phone: str,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        order = service.order_out(order_id)
        message = format_order_message(order)
        return {"message": message, "url": whatsapp_click_to_chat_url(destination_phone, message)}

    @app.get(
        "/api/operator/reservations/{reservation_id}/whatsapp",
        dependencies=[Depends(require_operator)],
    )
    def reservation_whatsapp(
        reservation_id: str,
        destination_phone: str,
        service: RestaurantCommerceService = Depends(get_service),
    ):
        reservation = service.reservation_out(reservation_id)
        message = format_reservation_message(reservation)
        return {"message": message, "url": whatsapp_click_to_chat_url(destination_phone, message)}

    @app.get(
        "/api/operator/restaurants/{business_id}/customers/{customer_id}/loyalty",
        response_model=LoyaltyAccountOut,
        dependencies=[Depends(require_operator)],
    )
    def loyalty_account(business_id: str, customer_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.loyalty_account(business_id, customer_id)

    @app.get(
        "/api/operator/restaurants/{business_id}/rewards",
        response_model=list[RewardOut],
        dependencies=[Depends(require_operator)],
    )
    def rewards(business_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.list_rewards(business_id)

    @app.post(
        "/api/operator/restaurants/{business_id}/rewards",
        response_model=RewardOut,
        dependencies=[Depends(require_operator)],
    )
    def create_reward(business_id: str, request: RewardCreateIn, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.create_reward(business_id, request)

    @app.get(
        "/api/operator/restaurants/{business_id}/promotions",
        response_model=list[PromotionOut],
        dependencies=[Depends(require_operator)],
    )
    def promotions(business_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.list_promotions(business_id)

    @app.post(
        "/api/operator/restaurants/{business_id}/promotions",
        response_model=PromotionOut,
        dependencies=[Depends(require_operator)],
    )
    def create_promotion(business_id: str, request: PromotionCreateIn, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.create_promotion(business_id, request)

    @app.get(
        "/api/operator/restaurants/{business_id}/automations",
        response_model=list[AutomationRuleOut],
        dependencies=[Depends(require_operator)],
    )
    def automations(business_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.list_rules(business_id)

    @app.post(
        "/api/operator/restaurants/{business_id}/automations",
        response_model=AutomationRuleOut,
        dependencies=[Depends(require_operator)],
    )
    def create_automation(
        business_id: str,
        request: AutomationRuleCreateIn,
        growth: RestaurantGrowthService = Depends(get_growth),
    ):
        return growth.create_rule(business_id, request)

    @app.post(
        "/api/operator/restaurants/{business_id}/winback/plan",
        response_model=list[OutboundMessageOut],
        dependencies=[Depends(require_operator)],
    )
    def plan_winback(
        business_id: str,
        request: WinbackPlanIn,
        growth: RestaurantGrowthService = Depends(get_growth),
    ):
        rows = growth.plan_winback(
            business_id, as_of=request.as_of, dormant_days=request.dormant_days, limit=request.limit
        )
        growth.session.commit()
        return [growth._message_out(row) for row in rows]

    @app.get(
        "/api/operator/restaurants/{business_id}/outbox",
        response_model=list[OutboundMessageOut],
        dependencies=[Depends(require_operator)],
    )
    def outbox(
        business_id: str,
        status: str | None = Query(default=None),
        growth: RestaurantGrowthService = Depends(get_growth),
    ):
        return growth.list_outbox(business_id, status=status)

    @app.post("/api/operator/outbox/{message_id}/handoff", response_model=OutboundMessageOut,
              dependencies=[Depends(require_operator)])
    def handoff_outbox(message_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.mark_handoff(message_id)

    @app.patch(
        "/api/operator/outbox/{message_id}/sent",
        response_model=OutboundMessageOut,
        dependencies=[Depends(require_operator)],
    )
    def mark_outbox_sent(
        message_id: str,
        request: MarkMessageSentIn,
        growth: RestaurantGrowthService = Depends(get_growth),
    ):
        # No provider delivery integration exists yet. Manual clicks are not receipts.
        raise HTTPException(status_code=409, detail="Verified provider send receipt required")

    @app.get(
        "/api/operator/restaurants/{business_id}/analytics",
        response_model=GrowthAnalyticsOut,
        dependencies=[Depends(require_operator)],
    )
    def analytics(business_id: str, growth: RestaurantGrowthService = Depends(get_growth)):
        return growth.analytics(business_id)

    @app.post("/api/operator/events/drain", dependencies=[Depends(require_operator)])
    def drain_events(
        limit: int = Query(default=100, ge=1, le=1000),
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.drain_event_outbox(limit=limit)

    @app.get("/api/operator/restaurants/{business_id}/payment-reconciliation", dependencies=[Depends(require_operator)])
    def payment_reconciliation(business_id: str, service: RestaurantCommerceService = Depends(get_service)):
        return service.list_payment_reconciliation(business_id)

    def financial_authority(permission):
        def dependency(request: Request, business_id: str, session: Session = Depends(get_session)):
            return scoped_staff(request, session, business_id, permission)
        return dependency

    @app.get("/api/finance/restaurants/{business_id}/orders/{order_id}")
    def financial_history(business_id: str, order_id: str,
                          principal=Depends(financial_authority("finance.read")),
                          service: RestaurantCommerceService = Depends(get_service)):
        return service.financial_history(business_id, order_id, principal)

    @app.post("/api/finance/restaurants/{business_id}/orders/{order_id}/lookup")
    def financial_lookup(business_id: str, order_id: str, body: FinancialActionRequest,
                         principal=Depends(financial_authority("finance.lookup")),
                         service: RestaurantCommerceService = Depends(get_service)):
        return service.request_financial_operation(business_id, order_id, "lookup", body.idempotency_key, body.reason, principal, refund_reference=body.refund_reference)

    @app.post("/api/finance/restaurants/{business_id}/orders/{order_id}/refund")
    def financial_refund(business_id: str, order_id: str, body: FinancialActionRequest,
                         principal=Depends(financial_authority("finance.refund")),
                         service: RestaurantCommerceService = Depends(get_service)):
        return service.request_financial_operation(business_id, order_id, "refund", body.idempotency_key, body.reason, principal, refund_reference=body.refund_reference)

    @app.post("/api/finance/restaurants/{business_id}/orders/{order_id}/resolve/{reconciliation_id}")
    def financial_resolve(business_id: str, order_id: str, reconciliation_id: str, body: FinancialResolutionRequest,
                         principal=Depends(financial_authority("finance.resolve")),
                         service: RestaurantCommerceService = Depends(get_service)):
        return service.resolve_financial_review(business_id, order_id, reconciliation_id, body.operation_id, body.reason, principal)

    @app.post("/api/finance/restaurants/{business_id}/loyalty-refunds/{refund_id}/allocation")
    def loyalty_resolve_refund(business_id: str, refund_id: str, body: LoyaltyRefundAllocationIn,
                              principal=Depends(financial_authority("finance.resolve")),
                              service: RestaurantCommerceService = Depends(get_service)):
        from .loyalty_execution import resolve_refund_allocation
        from .loyalty_execution_migrations import installed
        if not installed(service.session):
            raise HTTPException(status_code=409, detail="Loyalty execution schema is not installed")
        resolve_refund_allocation(service, refund_id, body.model_dump(), business_id=business_id,
                                  actor=principal.actor_id)
        service._commit_event(kind="loyalty.refund_allocated", business_id=business_id,
                              entity_id=refund_id, payload={"actor_id": principal.actor_id},
                              dedupe_key="loyalty-refund-allocation:" + refund_id)
        return {"refund_id": refund_id, "allocation_recorded": True}

    @app.post("/api/operator/payments/recover", dependencies=[Depends(require_operator)])
    def recover_payments(limit: int = Query(default=25, ge=1, le=100), service: RestaurantCommerceService = Depends(get_service)):
        return service.recover_payments(limit=limit)

    @app.get("/api/operator/metrics", dependencies=[Depends(require_operator)])
    def operator_metrics():
        return {
            "http": metrics.snapshot(),
            "provider_circuits": provider_executor.snapshot(),
            "storefront_cache_entries": len(storefront_cache),
        }

    return app


def _json_error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"detail": message})
