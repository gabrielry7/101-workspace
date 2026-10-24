from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .cache import TTLCache
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
    secure_compare,
    sign_resource,
    verify_resource_token,
    verify_webhook,
)
from .seed import DEMO_BUSINESS_ID, seed_demo
from .service import RestaurantCommerceService

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
    delivery_providers: dict[str, DeliveryProvider] | None = None,
    event_sink: EventSink | None = None,
    rate_limit_per_minute: int = 120,
    max_body_bytes: int = 1_048_576,
    storefront_cache_ttl_seconds: float = 15.0,
    auto_init_schema: bool | None = None,
) -> FastAPI:
    environment = (environment or os.getenv("COMMERCE_ENV", "development")).lower()
    production = environment == "production"
    demo_mode = (not production) if demo_mode is None else demo_mode
    auto_init_schema = (not production) if auto_init_schema is None else auto_init_schema
    if production and seed:
        raise RuntimeError("Demo seed data is forbidden in production")
    if production and demo_mode:
        raise RuntimeError("Demo mode is forbidden in production")

    token = operator_token or os.getenv("COMMERCE_OPERATOR_TOKEN")
    if not token:
        if production:
            raise RuntimeError("COMMERCE_OPERATOR_TOKEN is required in production")
        token = "dev-operator"
    if production and (len(token) < 32 or token == "dev-operator"):
        raise RuntimeError("Production operator token must be at least 32 characters and non-default")

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

    app = FastAPI(title="101 Restaurant Commerce", version="0.4.0")
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
            elapsed_ms = (time.perf_counter() - started) * 1000
            metrics.record_request(request.method, path, 500, elapsed_ms)
            logger.exception(
                "Unhandled restaurant commerce request failure",
                extra={"request_id": request_id, "method": request.method, "path": path},
            )
            response = JSONResponse(
                {"detail": "Internal server error", "request_id": request_id}, status_code=500
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        route_obj = request.scope.get("route")
        route = getattr(route_obj, "path", path)
        if response.status_code != 500 or not isinstance(response, JSONResponse):
            metrics.record_request(request.method, route, response.status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.3f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
            "object-src 'none'; img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'"
        )
        if production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if (
            path.startswith("/api/operator/")
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
        return RestaurantCommerceService(
            session,
            payment_providers=payment_providers,
            delivery_providers=delivery_providers,
            event_sink=event_sink,
            provider_executor=provider_executor,
            storefront_cache=storefront_cache,
        )

    def get_growth(session: Session = Depends(get_session)) -> RestaurantGrowthService:
        return RestaurantGrowthService(session)

    def require_operator(x_101_operator_token: str | None = Header(default=None)) -> None:
        if not secure_compare(token, x_101_operator_token):
            raise HTTPException(status_code=401, detail="Missing or invalid operator token")

    def require_order_access(
        order_id: str,
        x_101_order_token: str | None = Header(default=None),
    ) -> None:
        if not verify_resource_token(
            access_secret, x_101_order_token, kind="order", resource_id=order_id
        ):
            raise HTTPException(status_code=401, detail="Missing or invalid order access token")

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
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        if not database_ready(engine):
            return JSONResponse({"status": "not_ready", "database": "down"}, status_code=503)
        return {"status": "ready", "database": "ok"}

    @app.get("/")
    def storefront_page():
        return FileResponse(WEB_DIR / "index.html")

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
        return service.quote(
            business_id,
            request.items,
            promo_code=request.promo_code,
            customer_phone=request.customer_phone,
            reward_id=request.reward_id,
        )

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
        service: RestaurantCommerceService = Depends(get_service),
    ):
        # Public browser traffic cannot self-assert acquisition/channel attribution.
        # Authenticated integrations should use a dedicated server-side boundary.
        request = request.model_copy(update={"source_channel": "web", "external_source_ref": None})
        order = service.create_order(business_id, request)
        return order.model_copy(
            update={"access_token": sign_resource(access_secret, kind="order", resource_id=order.id)}
        )

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
        return service.create_reservation(business_id, request)

    @app.post("/api/webhooks/payments/{provider}", response_model=OrderOut)
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
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        return service.apply_payment_status(
            payload.provider_reference,
            payload.status,
            provider=provider,
            event_id=payload.event_id,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            raw_event_json=body.decode("utf-8", errors="replace"),
        )

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
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
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
        service: RestaurantCommerceService = Depends(get_service),
    ):
        return service.list_orders(business_id, status=status)

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
        return service.transition_order(order_id, patch.status)

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
        return growth.mark_sent(message_id, sent_at=request.sent_at)

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
