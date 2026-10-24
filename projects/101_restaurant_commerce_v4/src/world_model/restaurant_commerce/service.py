from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import secrets
from typing import Iterable

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.exc import StaleDataError

from .cache import TTLCache
from .enums import (
    DELIVERY_TRANSITIONS,
    DeliveryStatus,
    FulfillmentType,
    ORDER_TRANSITIONS,
    PAYMENT_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    OrderStatus,
    PaymentStatus,
    ReservationStatus,
)
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
from .events import CommerceEvent, EventSink, NullEventSink
from .growth import RestaurantGrowthService
from .deliveries import (
    DeliveryAddress,
    DeliveryProvider,
    MensajerosUrbanosDeliveryProvider,
    SimulatedDeliveryProvider,
    UberDirectDeliveryProvider,
)
from .models import (
    CommerceEventOutbox,
    IdempotencyRecord,
    Customer,
    Delivery,
    DeliveryEvent,
    DeliveryQuote,
    Menu,
    MenuCategory,
    MenuItem,
    ModifierGroup,
    ModifierOption,
    Order,
    OrderItem,
    OrderItemModifier,
    Payment,
    Reservation,
    RestaurantCommerceProfile,
    WebhookReceipt,
    utcnow,
)
from .reliability import (
    ProviderExecutor,
    acquire_idempotency,
    acquire_webhook_receipt,
    complete_idempotency,
    request_fingerprint,
    stage_event,
)
from .payments import (
    CashAtPickupPaymentProvider,
    PaymentProvider,
    SimulatedPaymentProvider,
    WompiPaymentProvider,
)
from .schemas import (
    CartItemIn,
    DeliveryAddressIn,
    DeliveryOut,
    DeliveryQuoteOut,
    DeliveryTrackingOut,
    CommerceCapabilityOut,
    CreateOrderRequest,
    CreateReservationRequest,
    CustomerSummaryOut,
    MenuCategoryOut,
    MenuItemOut,
    MenuOut,
    ModifierGroupOut,
    ModifierOptionOut,
    OrderItemModifierOut,
    OrderItemOut,
    OrderOut,
    PaymentOut,
    QuoteResponse,
    QuotedItem,
    QuotedModifier,
    ReservationOut,
    StorefrontOut,
)


def _public_code(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(3).upper()}"


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    prefix = "+" if phone.startswith("+") else ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 5:
        raise ValidationError("A valid customer phone is required")
    return prefix + digits


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class RestaurantCommerceService:
    def __init__(
        self,
        session: Session,
        *,
        payment_providers: dict[str, PaymentProvider] | None = None,
        delivery_providers: dict[str, DeliveryProvider] | None = None,
        event_sink: EventSink | None = None,
        provider_executor: ProviderExecutor | None = None,
        storefront_cache: TTLCache[StorefrontOut] | None = None,
    ) -> None:
        self.session = session
        self.payment_providers: dict[str, PaymentProvider] = payment_providers or {
            "simulated": SimulatedPaymentProvider(),
            "cash_at_pickup": CashAtPickupPaymentProvider(),
            "wompi": WompiPaymentProvider(configured=False),
        }
        self.delivery_providers: dict[str, DeliveryProvider] = delivery_providers or {
            "simulated_delivery": SimulatedDeliveryProvider(),
            "uber_direct": UberDirectDeliveryProvider(configured=False),
            "mensajeros_urbanos": MensajerosUrbanosDeliveryProvider(configured=False),
        }
        self.event_sink = event_sink or NullEventSink()
        self.provider_executor = provider_executor or ProviderExecutor()
        self.storefront_cache = storefront_cache

    def _commit_event(
        self,
        *,
        kind: str,
        business_id: str,
        entity_id: str,
        payload: dict[str, object],
        occurred_at: datetime | None = None,
        dedupe_key: str | None = None,
    ) -> None:
        self._commit_events([dict(
            kind=kind,
            business_id=business_id,
            entity_id=entity_id,
            payload=payload,
            occurred_at=occurred_at,
            dedupe_key=dedupe_key,
        )])

    def _commit_events(self, events: list[dict[str, object]]) -> None:
        rows: list[CommerceEventOutbox] = []
        for event in events:
            rows.append(stage_event(self.session, **event))
        try:
            self.session.commit()
        except StaleDataError as exc:
            self.session.rollback()
            raise ConcurrencyConflictError("Concurrent update detected; reload and retry") from exc
        for row in rows:
            self._publish_outbox_row(row.id)

    def _commit(self) -> None:
        try:
            self.session.commit()
        except StaleDataError as exc:
            self.session.rollback()
            raise ConcurrencyConflictError("Concurrent update detected; reload and retry") from exc

    def _publish_outbox_row(self, row_id: str, *, lease_seconds: int = 30) -> bool:
        """Publish one outbox row with a DB-backed lease.

        Commerce state is already committed before this runs. A lease prevents
        two workers from publishing the same row concurrently; an expired lease
        is recoverable after a worker crash. Delivery is at-least-once, so sinks
        receive ``event_id``/``dedupe_key`` and should deduplicate.
        """
        now = utcnow()
        claim = self.session.execute(
            update(CommerceEventOutbox)
            .where(
                CommerceEventOutbox.id == row_id,
                or_(
                    CommerceEventOutbox.status == "pending",
                    and_(
                        CommerceEventOutbox.status == "publishing",
                        CommerceEventOutbox.lease_until.is_not(None),
                        CommerceEventOutbox.lease_until <= now,
                    ),
                ),
            )
            .values(
                status="publishing",
                lease_until=now + timedelta(seconds=max(1, lease_seconds)),
                publish_attempts=CommerceEventOutbox.publish_attempts + 1,
            )
        )
        self._commit()
        if claim.rowcount != 1:
            row = self.session.get(CommerceEventOutbox, row_id)
            return bool(row and row.status == "published")

        row = self.session.get(CommerceEventOutbox, row_id)
        if not row:
            return False
        try:
            payload = json.loads(row.payload_json)
            self.event_sink.publish(
                CommerceEvent(
                    kind=row.kind,
                    business_id=row.business_id,
                    entity_id=row.entity_id,
                    occurred_at=_aware_utc(row.occurred_at),
                    payload=payload,
                    event_id=row.id,
                    dedupe_key=row.dedupe_key,
                )
            )
        except Exception as exc:  # external event sinks must never roll back committed commerce state
            row.status = "pending"
            row.lease_until = None
            row.last_error = f"{type(exc).__name__}: {exc}"[:2000]
            self._commit()
            return False
        row.status = "published"
        row.published_at = utcnow()
        row.lease_until = None
        row.last_error = None
        self._commit()
        return True

    def drain_event_outbox(self, *, limit: int = 100) -> dict[str, int]:
        now = utcnow()
        ids = self.session.scalars(
            select(CommerceEventOutbox.id)
            .where(
                or_(
                    CommerceEventOutbox.status == "pending",
                    and_(
                        CommerceEventOutbox.status == "publishing",
                        CommerceEventOutbox.lease_until.is_not(None),
                        CommerceEventOutbox.lease_until <= now,
                    ),
                )
            )
            .order_by(CommerceEventOutbox.occurred_at.asc())
            .limit(min(max(limit, 1), 1000))
        ).all()
        published = 0
        failed = 0
        for row_id in ids:
            if self._publish_outbox_row(row_id):
                published += 1
            else:
                failed += 1
        return {"attempted": len(ids), "published": published, "failed": failed}

    # ------------------------------------------------------------------
    # Profiles / menus
    # ------------------------------------------------------------------
    def storefront(self, business_id: str) -> StorefrontOut:
        if self.storefront_cache is not None:
            cached = self.storefront_cache.get(business_id)
            if cached is not None:
                return cached
        stmt = (
            select(RestaurantCommerceProfile)
            .where(RestaurantCommerceProfile.business_id == business_id)
            .options(
                selectinload(RestaurantCommerceProfile.menus)
                .selectinload(Menu.categories)
                .selectinload(MenuCategory.items)
                .selectinload(MenuItem.modifier_groups)
                .selectinload(ModifierGroup.options)
            )
        )
        profile = self.session.scalar(stmt)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")

        menus: list[MenuOut] = []
        for menu in sorted(profile.menus, key=lambda x: x.display_order):
            if not menu.enabled:
                continue
            categories: list[MenuCategoryOut] = []
            for category in sorted(menu.categories, key=lambda x: x.display_order):
                if not category.enabled:
                    continue
                items: list[MenuItemOut] = []
                for item in sorted(category.items, key=lambda x: x.display_order):
                    if not item.enabled:
                        continue
                    groups = []
                    for group in sorted(item.modifier_groups, key=lambda x: x.display_order):
                        groups.append(
                            ModifierGroupOut(
                                id=group.id,
                                name=group.name,
                                required=group.required,
                                min_selections=group.min_selections,
                                max_selections=group.max_selections,
                                options=[
                                    ModifierOptionOut(
                                        id=option.id,
                                        name=option.name,
                                        price_delta_minor=option.price_delta_minor,
                                        enabled=option.enabled,
                                    )
                                    for option in sorted(group.options, key=lambda x: x.display_order)
                                    if option.enabled
                                ],
                            )
                        )
                    items.append(
                        MenuItemOut(
                            id=item.id,
                            name=item.name,
                            description=item.description,
                            base_price_minor=item.base_price_minor,
                            currency=item.currency,
                            image_url=item.image_url,
                            available=not item.sold_out,
                            modifier_groups=groups,
                        )
                    )
                categories.append(
                    MenuCategoryOut(
                        id=category.id,
                        name=category.name,
                        description=category.description,
                        items=items,
                    )
                )
            menus.append(MenuOut(id=menu.id, name=menu.name, categories=categories))

        output = StorefrontOut(
            business_id=profile.business_id,
            slug=profile.slug,
            display_name=profile.display_name,
            currency=profile.currency,
            timezone=profile.timezone,
            ordering_enabled=profile.ordering_enabled,
            payment_provider=profile.payment_provider,
            cash_at_pickup_enabled=profile.cash_at_pickup_enabled,
            pickup_enabled=profile.pickup_enabled,
            delivery_enabled=profile.delivery_enabled,
            accepts_reservations=profile.accepts_reservations,
            default_prep_minutes=profile.default_prep_minutes,
            pickup_instructions=profile.pickup_instructions,
            delivery_provider=profile.delivery_provider if profile.delivery_enabled else None,
            delivery_max_distance_meters=profile.delivery_max_distance_meters,
            loyalty_enabled=profile.loyalty_enabled,
            menus=menus,
        )
        if self.storefront_cache is not None:
            self.storefront_cache.set(business_id, output)
        return output

    def capability(self, business_id: str) -> CommerceCapabilityOut:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")
        return CommerceCapabilityOut(
            business_id=business_id,
            ordering_enabled=profile.ordering_enabled,
            payment_provider=profile.payment_provider,
            cash_at_pickup_enabled=profile.cash_at_pickup_enabled,
            pickup_enabled=profile.pickup_enabled,
            delivery_enabled=profile.delivery_enabled,
            accepts_reservations=profile.accepts_reservations,
            loyalty_enabled=profile.loyalty_enabled,
            marketing_automation_enabled=profile.marketing_automation_enabled,
            review_requests_enabled=profile.review_requests_enabled,
            storefront_endpoint=f"/api/restaurants/{business_id}/storefront",
            quote_endpoint=f"/api/restaurants/{business_id}/orders/quote",
            order_endpoint=f"/api/restaurants/{business_id}/orders",
            reservation_endpoint=f"/api/restaurants/{business_id}/reservations",
            loyalty_endpoint=f"/api/restaurants/{business_id}/loyalty",
            analytics_endpoint=f"/api/operator/restaurants/{business_id}/analytics",
            delivery_quote_endpoint=f"/api/restaurants/{business_id}/delivery/quote",
            delivery_tracking_endpoint_template="/api/orders/{order_id}/delivery/tracking",
        )

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------
    def quote(
        self,
        business_id: str,
        cart_items: Iterable[CartItemIn],
        *,
        promo_code: str | None = None,
        customer_phone: str | None = None,
        reward_id: str | None = None,
    ) -> QuoteResponse:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")
        if not profile.ordering_enabled:
            raise ValidationError("Direct ordering is disabled for this restaurant")

        cart_items = list(cart_items)
        if not cart_items:
            raise ValidationError("Cart cannot be empty")
        if len(cart_items) > 100:
            raise ValidationError("Cart contains too many line items")

        requested_ids = {cart.menu_item_id for cart in cart_items}
        loaded_items = self.session.scalars(
            select(MenuItem)
            .where(MenuItem.id.in_(requested_ids))
            .options(
                selectinload(MenuItem.category).selectinload(MenuCategory.menu),
                selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.options),
            )
        ).all()
        item_map = {item.id: item for item in loaded_items}
        missing = requested_ids - set(item_map)
        if missing:
            raise NotFoundError(f"Menu item not found: {sorted(missing)[0]}")

        quoted_items: list[QuotedItem] = []
        subtotal = 0
        max_total_minor = 2_000_000_000

        for cart_item in cart_items:
            item = item_map[cart_item.menu_item_id]
            if item.category.menu.business_id != business_id:
                raise ValidationError("Menu item does not belong to this restaurant")
            if not item.enabled or item.sold_out or not item.category.enabled or not item.category.menu.enabled:
                raise ValidationError(f"Menu item is unavailable: {item.name}")
            if item.currency != profile.currency:
                raise ValidationError("Menu item currency does not match restaurant currency")

            requested_by_group: dict[str, list[str]] = {}
            for selection in cart_item.modifiers:
                if selection.group_id in requested_by_group:
                    raise ValidationError(f"Duplicate modifier group submitted for {item.name}: {selection.group_id}")
                requested_by_group[selection.group_id] = selection.option_ids
            known_group_ids = {group.id for group in item.modifier_groups}
            unknown_groups = set(requested_by_group) - known_group_ids
            if unknown_groups:
                raise ValidationError(f"Unknown modifier group(s) for {item.name}: {sorted(unknown_groups)}")

            quoted_modifiers: list[QuotedModifier] = []
            modifier_unit_total = 0
            for group in item.modifier_groups:
                selected_ids = requested_by_group.get(group.id, [])
                if len(selected_ids) != len(set(selected_ids)):
                    raise ValidationError(f"Duplicate modifier option selected in {group.name}")

                min_required = max(group.min_selections, 1 if group.required else 0)
                if len(selected_ids) < min_required:
                    raise ValidationError(
                        f"{item.name}: choose at least {min_required} option(s) for {group.name}"
                    )
                if len(selected_ids) > group.max_selections:
                    raise ValidationError(
                        f"{item.name}: choose at most {group.max_selections} option(s) for {group.name}"
                    )

                option_map = {option.id: option for option in group.options}
                for option_id in selected_ids:
                    option = option_map.get(option_id)
                    if not option or not option.enabled:
                        raise ValidationError(f"Unavailable modifier option: {option_id}")
                    modifier_unit_total += option.price_delta_minor
                    quoted_modifiers.append(
                        QuotedModifier(
                            group_id=group.id,
                            group_name=group.name,
                            option_id=option.id,
                            option_name=option.name,
                            price_delta_minor=option.price_delta_minor,
                        )
                    )

            unit_total = item.base_price_minor + modifier_unit_total
            if unit_total < 0:
                raise ValidationError(f"Modifiers cannot reduce {item.name} below zero")
            line_total = unit_total * cart_item.quantity
            if line_total > max_total_minor or subtotal + line_total > max_total_minor:
                raise ValidationError("Cart total exceeds supported transaction limit")
            subtotal += line_total
            quoted_items.append(
                QuotedItem(
                    menu_item_id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    unit_base_price_minor=item.base_price_minor,
                    unit_modifier_price_minor=modifier_unit_total,
                    line_total_minor=line_total,
                    modifiers=quoted_modifiers,
                )
            )

        customer_id = None
        if customer_phone:
            normalized_phone = _normalize_phone(customer_phone)
            customer = self.session.scalar(
                select(Customer).where(Customer.business_id == business_id, Customer.phone == normalized_phone)
            )
            customer_id = customer.id if customer else None
        discounts = RestaurantGrowthService(self.session).preview_discounts(
            business_id,
            subtotal=subtotal,
            promo_code=promo_code,
            customer_id=customer_id,
            reward_id=reward_id,
        )
        return QuoteResponse(
            business_id=business_id,
            currency=profile.currency,
            subtotal_minor=subtotal,
            total_minor=max(0, subtotal - discounts.total_discount_minor),
            items=quoted_items,
            discounts=discounts,
        )

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------
    def _upsert_customer(
        self, business_id: str, *, name: str, phone: str, email: str | None,
        whatsapp_opt_in: bool | None = None, marketing_opt_in: bool | None = None,
        consent_source: str | None = None,
    ) -> Customer:
        phone = _normalize_phone(phone)
        stmt = select(Customer).where(Customer.business_id == business_id, Customer.phone == phone)
        customer = self.session.scalar(stmt)

        if not customer:
            candidate = Customer(
                business_id=business_id, phone=phone, name=name, email=email,
                whatsapp_opt_in=bool(whatsapp_opt_in),
                whatsapp_opt_in_at=utcnow() if whatsapp_opt_in else None,
                marketing_opt_in=bool(marketing_opt_in),
                marketing_opt_in_at=utcnow() if marketing_opt_in else None,
                marketing_opt_in_source=consent_source if marketing_opt_in else None,
            )
            try:
                with self.session.begin_nested():
                    self.session.add(candidate)
                    self.session.flush()
                customer = candidate
            except IntegrityError:
                # Another request may have created the same business+phone at the
                # same instant. The unique constraint wins; converge on that row.
                customer = self.session.scalar(stmt)
                if not customer:
                    raise ConcurrencyConflictError("Concurrent customer creation could not be reconciled")

        customer.name = name or customer.name
        if email:
            customer.email = email
        if whatsapp_opt_in is not None and whatsapp_opt_in != customer.whatsapp_opt_in:
            customer.whatsapp_opt_in = whatsapp_opt_in
            customer.whatsapp_opt_in_at = utcnow() if whatsapp_opt_in else None
        if marketing_opt_in is not None and marketing_opt_in != customer.marketing_opt_in:
            customer.marketing_opt_in = marketing_opt_in
            customer.marketing_opt_in_at = utcnow() if marketing_opt_in else None
            customer.marketing_opt_in_source = consent_source if marketing_opt_in else None
        customer.updated_at = utcnow()
        return customer

    def customer_summary(self, business_id: str, customer_id: str) -> CustomerSummaryOut:
        customer = self.session.get(Customer, customer_id)
        if not customer or customer.business_id != business_id:
            raise NotFoundError("Customer not found")
        stmt = select(func.count(Order.id), func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.business_id == business_id,
            Order.customer_id == customer_id,
            Order.status == OrderStatus.COMPLETED.value,
            Order.payment_status == PaymentStatus.PAID.value,
        )
        order_count, lifetime_value = self.session.execute(stmt).one()
        return CustomerSummaryOut(
            id=customer.id,
            name=customer.name,
            phone=customer.phone,
            email=customer.email,
            order_count=int(order_count or 0),
            lifetime_value_minor=int(lifetime_value or 0),
            last_order_at=customer.last_order_at,
            whatsapp_opt_in=customer.whatsapp_opt_in,
            marketing_opt_in=customer.marketing_opt_in,
            loyalty_points=RestaurantGrowthService(self.session).ensure_account(business_id, customer_id).available_points,
        )

    # ------------------------------------------------------------------
    # Delivery quotes / fulfillment
    # ------------------------------------------------------------------
    def _profile_origin(self, profile: RestaurantCommerceProfile) -> DeliveryAddress:
        if (
            not profile.delivery_origin_address
            or profile.delivery_origin_latitude is None
            or profile.delivery_origin_longitude is None
        ):
            raise ValidationError("Restaurant delivery origin is not configured")
        return DeliveryAddress(
            address_line=profile.delivery_origin_address,
            city="Bogotá",
            latitude=profile.delivery_origin_latitude,
            longitude=profile.delivery_origin_longitude,
        )

    def create_delivery_quote(
        self, business_id: str, destination: DeliveryAddressIn
    ) -> DeliveryQuoteOut:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")
        if not profile.ordering_enabled or not profile.delivery_enabled:
            raise ValidationError("Direct delivery ordering is disabled")
        provider = self.delivery_providers.get(profile.delivery_provider)
        if not provider:
            raise ValidationError(f"Unsupported delivery provider: {profile.delivery_provider}")

        origin = self._profile_origin(profile)
        target = DeliveryAddress(
            address_line=destination.address_line.strip(),
            city=destination.city.strip(),
            latitude=destination.latitude,
            longitude=destination.longitude,
            instructions=destination.instructions,
        )
        try:
            result = self.provider_executor.call(
                provider.name,
                "quote",
                lambda: provider.quote(
                    business_id=business_id,
                    origin=origin,
                    destination=target,
                    currency=profile.currency,
                    prep_minutes=profile.default_prep_minutes,
                ),
            )
        except (DeliveryError, ProviderCircuitOpenError):
            raise
        except Exception as exc:
            raise DeliveryError(f"Delivery quote failed via {provider.name}") from exc

        if result.provider != provider.name:
            raise DeliveryError("Delivery quote provider identity mismatch")
        if not result.provider_quote_reference.strip():
            raise DeliveryError("Delivery provider returned an empty quote reference")
        if result.currency != profile.currency:
            raise DeliveryError("Delivery quote currency does not match restaurant currency")
        if result.distance_meters is not None and result.distance_meters < 0:
            raise DeliveryError("Delivery provider returned an invalid negative distance")
        if (
            profile.delivery_max_distance_meters is not None
            and result.distance_meters is not None
            and result.distance_meters > profile.delivery_max_distance_meters
        ):
            raise ValidationError(
                f"Destination is outside the configured delivery radius of {profile.delivery_max_distance_meters} meters"
            )
        if result.fee_minor < 0:
            raise DeliveryError("Delivery provider returned an invalid negative fee")
        if _aware_utc(result.expires_at) <= datetime.now(timezone.utc):
            raise DeliveryError("Delivery provider returned an already-expired quote")

        quote = DeliveryQuote(
            business_id=business_id,
            provider=result.provider,
            provider_quote_reference=result.provider_quote_reference,
            currency=result.currency,
            fee_minor=result.fee_minor,
            distance_meters=result.distance_meters,
            origin_address=origin.address_line,
            origin_latitude=origin.latitude,
            origin_longitude=origin.longitude,
            destination_address=target.address_line,
            destination_city=target.city,
            destination_latitude=target.latitude,
            destination_longitude=target.longitude,
            destination_instructions=target.instructions,
            estimated_pickup_at=result.estimated_pickup_at,
            estimated_dropoff_at=result.estimated_dropoff_at,
            expires_at=result.expires_at,
            raw_quote_json=result.raw_payload,
        )
        self.session.add(quote)
        self.session.flush()
        self._commit_event(
            kind="delivery.quote_created",
            business_id=business_id,
            entity_id=quote.id,
            payload={"provider": quote.provider, "fee_minor": quote.fee_minor},
            dedupe_key=f"delivery-quote-created:{quote.id}",
        )
        return self.delivery_quote_out(quote.id)

    def delivery_quote_out(self, quote_id: str) -> DeliveryQuoteOut:
        quote = self.session.get(DeliveryQuote, quote_id)
        if not quote:
            raise NotFoundError("Delivery quote not found")
        return DeliveryQuoteOut(
            id=quote.id,
            business_id=quote.business_id,
            provider=quote.provider,
            currency=quote.currency,
            fee_minor=quote.fee_minor,
            distance_meters=quote.distance_meters,
            estimated_pickup_at=quote.estimated_pickup_at,
            estimated_dropoff_at=quote.estimated_dropoff_at,
            expires_at=quote.expires_at,
            destination_address=quote.destination_address,
            destination_city=quote.destination_city,
        )

    def _validate_delivery_quote(self, business_id: str, quote_id: str | None) -> DeliveryQuote:
        if not quote_id:
            raise ValidationError("A delivery_quote_id is required for delivery orders")
        quote = self.session.get(DeliveryQuote, quote_id)
        if not quote or quote.business_id != business_id:
            raise ValidationError("Delivery quote does not belong to this restaurant")
        if quote.consumed_at is not None:
            raise ValidationError("Delivery quote has already been used")
        if _aware_utc(quote.expires_at) <= datetime.now(timezone.utc):
            raise ValidationError("Delivery quote has expired; request a new quote")
        return quote

    def _delivery_to_out(self, delivery: Delivery) -> DeliveryOut:
        return DeliveryOut(
            id=delivery.id,
            order_id=delivery.order_id,
            quote_id=delivery.quote_id,
            provider=delivery.provider,
            provider_delivery_reference=delivery.provider_delivery_reference,
            status=delivery.status,
            currency=delivery.currency,
            fee_minor=delivery.fee_minor,
            destination_address=delivery.destination_address,
            destination_city=delivery.destination_city,
            destination_latitude=delivery.destination_latitude,
            destination_longitude=delivery.destination_longitude,
            destination_instructions=delivery.destination_instructions,
            tracking_url=delivery.tracking_url,
            courier_name=delivery.courier_name,
            courier_phone=delivery.courier_phone,
            estimated_pickup_at=delivery.estimated_pickup_at,
            estimated_dropoff_at=delivery.estimated_dropoff_at,
            dispatched_at=delivery.dispatched_at,
            picked_up_at=delivery.picked_up_at,
            delivered_at=delivery.delivered_at,
            cancelled_at=delivery.cancelled_at,
            created_at=delivery.created_at,
        )

    def delivery_out(self, delivery_id: str) -> DeliveryOut:
        delivery = self.session.get(Delivery, delivery_id)
        if not delivery:
            raise NotFoundError("Delivery not found")
        return self._delivery_to_out(delivery)

    def delivery_tracking(self, order_id: str) -> DeliveryTrackingOut:
        row = self.session.execute(
            select(Order, Delivery)
            .join(Delivery, Delivery.order_id == Order.id)
            .where(Order.id == order_id)
        ).first()
        if not row:
            order_exists = self.session.get(Order, order_id)
            if not order_exists:
                raise NotFoundError("Order not found")
            raise NotFoundError("Delivery not found for order")
        order, delivery = row
        return DeliveryTrackingOut(
            order_id=order.id,
            public_code=order.public_code,
            status=delivery.status,
            provider=delivery.provider,
            tracking_url=delivery.tracking_url,
            courier_name=delivery.courier_name,
            estimated_pickup_at=delivery.estimated_pickup_at,
            estimated_dropoff_at=delivery.estimated_dropoff_at,
            picked_up_at=delivery.picked_up_at,
            delivered_at=delivery.delivered_at,
        )

    def list_deliveries(self, business_id: str, *, status: str | None = None, limit: int = 100) -> list[DeliveryOut]:
        stmt = select(Delivery).join(Order, Delivery.order_id == Order.id).where(Order.business_id == business_id)
        if status:
            try:
                DeliveryStatus(status)
            except ValueError as exc:
                raise ValidationError(f"Unknown delivery status: {status}") from exc
            stmt = stmt.where(Delivery.status == status)
        stmt = stmt.order_by(Delivery.created_at.desc()).limit(min(max(limit, 1), 500))
        return [self._delivery_to_out(delivery) for delivery in self.session.scalars(stmt).all()]

    def dispatch_delivery(self, order_id: str) -> DeliveryOut:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.customer), selectinload(Order.delivery).selectinload(Delivery.quote))
        )
        order = self.session.scalar(stmt)
        if not order:
            raise NotFoundError("Order not found")
        if order.fulfillment_type != FulfillmentType.DELIVERY.value or not order.delivery:
            raise ValidationError("Order is not a delivery order")
        if order.payment_status != PaymentStatus.PAID.value:
            raise ValidationError("Delivery cannot be dispatched before payment is confirmed")
        if OrderStatus(order.status) not in {OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY}:
            raise ValidationError("Restaurant must accept the order before dispatching delivery")
        delivery = order.delivery
        if delivery.provider_delivery_reference:
            return self.delivery_out(delivery.id)
        if DeliveryStatus(delivery.status) != DeliveryStatus.QUOTED:
            raise InvalidTransitionError(f"Cannot dispatch delivery from {delivery.status}")

        claim = acquire_idempotency(
            self.session,
            scope=f"delivery.dispatch:{order.id}",
            key="dispatch",
            fingerprint=request_fingerprint({
                "order_id": order.id,
                "delivery_id": delivery.id,
                "provider": delivery.provider,
                "quote_id": delivery.quote_id,
            }),
        )
        if not claim.acquired:
            return self.delivery_out(claim.entity_id or delivery.id)

        provider = self.delivery_providers.get(delivery.provider)
        if not provider:
            raise ValidationError(f"Unsupported delivery provider: {delivery.provider}")
        origin = DeliveryAddress(
            delivery.origin_address,
            "Bogotá",
            delivery.origin_latitude,
            delivery.origin_longitude,
        )
        destination = DeliveryAddress(
            delivery.destination_address,
            delivery.destination_city,
            delivery.destination_latitude,
            delivery.destination_longitude,
            delivery.destination_instructions,
        )
        provider_idempotency_key = f"delivery:{order.id}"
        try:
            result = self.provider_executor.call(
                provider.name,
                "create_delivery",
                lambda: provider.create_delivery(
                    order_id=order.id,
                    public_code=order.public_code,
                    origin=origin,
                    destination=destination,
                    currency=delivery.currency,
                    fee_minor=delivery.fee_minor,
                    provider_quote_reference=delivery.quote.provider_quote_reference,
                    prep_minutes=order.prep_minutes,
                    customer_name=order.customer.name or "Cliente",
                    customer_phone=order.customer.phone,
                    idempotency_key=provider_idempotency_key,
                ),
            )
        except (DeliveryError, ProviderCircuitOpenError):
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise DeliveryError(f"Delivery dispatch failed via {provider.name}") from exc

        if result.provider != provider.name:
            self.session.rollback()
            raise DeliveryError("Delivery provider identity mismatch")
        if not result.provider_delivery_reference.strip():
            self.session.rollback()
            raise DeliveryError("Delivery provider returned an empty reference")
        try:
            target_status = DeliveryStatus(result.status)
        except ValueError as exc:
            self.session.rollback()
            raise DeliveryError(f"Delivery provider returned unsupported status: {result.status}") from exc
        if target_status not in DELIVERY_TRANSITIONS[DeliveryStatus.QUOTED]:
            self.session.rollback()
            raise DeliveryError(f"Delivery provider returned invalid initial status: {result.status}")

        delivery.provider_delivery_reference = result.provider_delivery_reference
        delivery.tracking_url = result.tracking_url
        delivery.courier_name = result.courier_name
        delivery.courier_phone = result.courier_phone
        delivery.estimated_pickup_at = result.estimated_pickup_at or delivery.estimated_pickup_at
        delivery.estimated_dropoff_at = result.estimated_dropoff_at or delivery.estimated_dropoff_at
        delivery.dispatched_at = utcnow()
        delivery.raw_status_json = result.raw_payload
        self.session.flush()
        self._record_delivery_status(
            delivery,
            target_status.value,
            provider_status=result.status,
            raw_event_json=result.raw_payload,
            dedupe_key=f"dispatch:{delivery.id}:{result.provider_delivery_reference}",
        )
        complete_idempotency(self.session, claim.record_id, entity_id=delivery.id)
        self._commit_event(
            kind="delivery.dispatched",
            business_id=order.business_id,
            entity_id=delivery.id,
            payload={"order_id": order.id, "provider": delivery.provider},
            dedupe_key=f"delivery-dispatched:{delivery.id}",
        )
        return self.delivery_out(delivery.id)

    def _record_delivery_status(
        self,
        delivery: Delivery,
        status: str,
        *,
        provider_status: str | None = None,
        occurred_at: datetime | None = None,
        raw_event_json: str | None = None,
        dedupe_key: str | None = None,
    ) -> bool:
        try:
            current = DeliveryStatus(delivery.status)
            target = DeliveryStatus(status)
        except ValueError as exc:
            raise ValidationError(f"Unknown delivery status: {status}") from exc
        when = _aware_utc(occurred_at) if occurred_at else utcnow()
        if current == target:
            return False
        # Courier webhooks can arrive out of order. Older events are ignored rather
        # than allowed to move the fulfillment state backwards.
        if delivery.updated_at and _aware_utc(delivery.updated_at) > when:
            return False
        if target not in DELIVERY_TRANSITIONS[current]:
            raise InvalidTransitionError(f"Cannot transition delivery from {current.value} to {target.value}")

        order = self.session.get(Order, delivery.order_id)
        if not order:
            raise NotFoundError("Order not found for delivery")
        if target == DeliveryStatus.PICKED_UP and OrderStatus(order.status) != OrderStatus.READY:
            raise InvalidTransitionError("Order must be ready before courier pickup")
        if target == DeliveryStatus.DELIVERED and OrderStatus(order.status) != OrderStatus.READY:
            raise InvalidTransitionError("Order must remain ready/in-transit before delivery completion")

        delivery.status = target.value
        delivery.updated_at = when
        if target == DeliveryStatus.PICKED_UP:
            delivery.picked_up_at = when
        elif target == DeliveryStatus.DELIVERED:
            delivery.delivered_at = when
        elif target == DeliveryStatus.CANCELLED:
            delivery.cancelled_at = when

        event_key = dedupe_key or f"status:{delivery.id}:{target.value}:{int(when.timestamp())}"
        existing = self.session.scalar(select(DeliveryEvent).where(DeliveryEvent.dedupe_key == event_key))
        if not existing:
            self.session.add(
                DeliveryEvent(
                    delivery_id=delivery.id,
                    provider_status=provider_status or target.value,
                    normalized_status=target.value,
                    occurred_at=when,
                    dedupe_key=event_key,
                    raw_event_json=raw_event_json,
                )
            )
        return True

    def apply_delivery_status(
        self,
        provider_delivery_reference: str,
        status: str,
        *,
        provider: str | None = None,
        event_id: str | None = None,
        occurred_at: datetime | None = None,
        raw_event_json: str | None = None,
    ) -> DeliveryOut:
        delivery = self.session.scalar(
            select(Delivery)
            .where(Delivery.provider_delivery_reference == provider_delivery_reference)
            .options(selectinload(Delivery.order))
        )
        if not delivery:
            raise NotFoundError("Delivery not found")
        if provider and provider != delivery.provider:
            raise ValidationError("Delivery provider does not match provider reference")

        receipt = None
        if event_id:
            receipt_provider = provider or delivery.provider
            fingerprint = request_fingerprint({
                "provider_delivery_reference": provider_delivery_reference,
                "status": status.lower(),
                "occurred_at": occurred_at.isoformat() if occurred_at else None,
            })
            receipt, acquired = acquire_webhook_receipt(
                self.session, provider=receipt_provider, event_id=event_id, fingerprint=fingerprint
            )
            if not acquired:
                return self.delivery_out(delivery.id)

        old_delivery_status = delivery.status
        order = delivery.order
        if not order:
            raise NotFoundError("Order not found for delivery")
        old_order_status = order.status
        changed = self._record_delivery_status(
            delivery,
            status.lower(),
            provider_status=status,
            occurred_at=occurred_at,
            raw_event_json=raw_event_json,
            dedupe_key=(f"provider:{delivery.provider}:{event_id}" if event_id else None),
        )

        order_completed = False
        completed_at = utcnow()
        if changed and delivery.status == DeliveryStatus.DELIVERED.value:
            if order.status != OrderStatus.READY.value:
                raise InvalidTransitionError("Delivery arrived while order was not in ready/in-transit state")
            order.status = OrderStatus.COMPLETED.value
            order.completed_at = completed_at
            customer = self.session.get(Customer, order.customer_id)
            if customer:
                customer.last_order_at = completed_at
            growth = RestaurantGrowthService(self.session)
            growth.finalize_reward(order.id)
            growth.award_completed_order(order)
            growth.queue_order_completed_automations(order)
            order_completed = True

        if receipt:
            receipt.processed_at = utcnow()

        if not changed:
            self._commit()
            return self.delivery_out(delivery.id)

        events: list[dict[str, object]] = [
            dict(
                kind="delivery.status_changed",
                business_id=order.business_id,
                entity_id=delivery.id,
                occurred_at=occurred_at or utcnow(),
                payload={"order_id": delivery.order_id, "from": old_delivery_status, "status": delivery.status},
                dedupe_key=(f"delivery-webhook:{delivery.provider}:{event_id}" if event_id else None),
            )
        ]
        if order_completed:
            events.append(dict(
                kind="order.status_changed",
                business_id=order.business_id,
                entity_id=order.id,
                occurred_at=completed_at,
                payload={"from": old_order_status, "to": OrderStatus.COMPLETED.value, "cause": "delivery.delivered"},
                dedupe_key=f"order-completed-by-delivery:{order.id}",
            ))
        self._commit_events(events)
        return self.delivery_out(delivery.id)

    def cancel_delivery(self, order_id: str) -> DeliveryOut:
        delivery = self.session.scalar(
            select(Delivery).where(Delivery.order_id == order_id).options(selectinload(Delivery.order))
        )
        if not delivery:
            raise NotFoundError("Delivery not found for order")
        current = DeliveryStatus(delivery.status)
        if current == DeliveryStatus.DELIVERED:
            raise InvalidTransitionError("Delivered fulfillment cannot be cancelled")
        if current == DeliveryStatus.PICKED_UP:
            raise InvalidTransitionError("Delivery cannot be cancelled after courier pickup")
        if current == DeliveryStatus.CANCELLED:
            return self.delivery_out(delivery.id)
        provider = self.delivery_providers.get(delivery.provider)
        if not provider:
            raise ValidationError(f"Unsupported delivery provider: {delivery.provider}")
        target = DeliveryStatus.CANCELLED.value
        if delivery.provider_delivery_reference:
            try:
                target = self.provider_executor.call(
                    provider.name,
                    "cancel_delivery",
                    lambda: provider.cancel_delivery(
                        provider_delivery_reference=delivery.provider_delivery_reference
                    ),
                )
            except (DeliveryError, ProviderCircuitOpenError):
                raise
            except Exception as exc:
                raise DeliveryError(f"Delivery cancellation failed via {provider.name}") from exc
        changed = self._record_delivery_status(
            delivery,
            target,
            provider_status=target,
            dedupe_key=f"cancel:{delivery.id}:{delivery.provider_delivery_reference or 'undispatched'}",
        )
        if changed:
            order = delivery.order or self.session.get(Order, delivery.order_id)
            self._commit_event(
                kind="delivery.status_changed",
                business_id=order.business_id if order else "unknown",
                entity_id=delivery.id,
                payload={"order_id": delivery.order_id, "from": current.value, "status": delivery.status},
                dedupe_key=f"delivery-cancelled:{delivery.id}",
            )
        else:
            self._commit()
        return self.delivery_out(delivery.id)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def create_order(self, business_id: str, request: CreateOrderRequest) -> OrderOut:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")
        if not profile.ordering_enabled:
            raise ValidationError("Direct ordering is disabled")
        try:
            fulfillment = FulfillmentType(request.fulfillment_type)
        except ValueError as exc:
            raise ValidationError(f"Unsupported fulfillment type: {request.fulfillment_type}") from exc
        if fulfillment == FulfillmentType.PICKUP and not profile.pickup_enabled:
            raise ValidationError("Direct pickup ordering is disabled")
        if fulfillment == FulfillmentType.DELIVERY and not profile.delivery_enabled:
            raise ValidationError("Direct delivery ordering is disabled")

        claim = None
        if request.idempotency_key:
            scope = f"order.create:{business_id}"
            fingerprint = request_fingerprint(request.model_dump(mode="json"))
            ledger_row = self.session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.scope == scope,
                    IdempotencyRecord.key == request.idempotency_key,
                )
            )
            if ledger_row is None:
                # Backward compatibility only for genuine V1-V3 rows that predate
                # the fingerprint ledger. Never let this path bypass a V4 record.
                legacy = self.session.scalar(
                    select(Order).where(
                        Order.business_id == business_id,
                        Order.idempotency_key == request.idempotency_key,
                    )
                )
                if legacy:
                    return self.order_out(legacy.id)
            claim = acquire_idempotency(
                self.session, scope=scope, key=request.idempotency_key, fingerprint=fingerprint
            )
            if not claim.acquired:
                if not claim.entity_id:
                    raise IdempotencyConflictError("Idempotent order request is not complete")
                return self.order_out(claim.entity_id)

        delivery_quote = None
        if fulfillment == FulfillmentType.DELIVERY:
            delivery_quote = self._validate_delivery_quote(business_id, request.delivery_quote_id)
        elif request.delivery_quote_id:
            raise ValidationError("delivery_quote_id is only valid for delivery orders")

        customer = self._upsert_customer(
            business_id,
            name=request.customer.name,
            phone=request.customer.phone,
            email=request.customer.email,
            whatsapp_opt_in=request.customer.whatsapp_opt_in,
            marketing_opt_in=request.customer.marketing_opt_in,
            consent_source=request.customer.consent_source or request.source_channel,
        )
        quote = self.quote(
            business_id,
            request.items,
            promo_code=request.promo_code,
            customer_phone=customer.phone,
            reward_id=request.reward_id,
        )
        growth = RestaurantGrowthService(self.session)

        if request.payment_provider == "cash_at_pickup":
            if not profile.cash_at_pickup_enabled:
                raise ValidationError("Cash at pickup is disabled for this restaurant")
        elif request.payment_provider != profile.payment_provider:
            raise ValidationError(
                f"Payment provider {request.payment_provider!r} is not enabled for this restaurant"
            )
        provider = self.payment_providers.get(request.payment_provider)
        if not provider:
            raise ValidationError(f"Unsupported payment provider: {request.payment_provider}")

        delivery_fee = delivery_quote.fee_minor if delivery_quote else 0
        order = Order(
            public_code=_public_code("O"),
            business_id=business_id,
            customer_id=customer.id,
            status=OrderStatus.AWAITING_PAYMENT.value,
            fulfillment_type=fulfillment.value,
            payment_status=PaymentStatus.PENDING.value,
            currency=quote.currency,
            subtotal_minor=quote.subtotal_minor,
            promotion_discount_minor=quote.discounts.promotion_discount_minor,
            reward_discount_minor=quote.discounts.reward_discount_minor,
            discount_minor=quote.discounts.total_discount_minor,
            promotion_code_snapshot=quote.discounts.promotion_code,
            reward_name_snapshot=quote.discounts.reward_name,
            delivery_fee_minor=delivery_fee,
            total_minor=quote.total_minor + delivery_fee,
            prep_minutes=profile.default_prep_minutes,
            requested_pickup_at=request.requested_pickup_at,
            notes=request.notes,
            source_channel=request.source_channel,
            external_source_ref=request.external_source_ref,
            idempotency_key=request.idempotency_key,
        )
        self.session.add(order)
        self.session.flush()

        if delivery_quote:
            if delivery_quote.currency != order.currency:
                raise ValidationError("Delivery quote currency does not match order currency")
            # This write is protected by the quote->delivery unique constraint.
            # Concurrent consumers cannot both commit the same quote.
            delivery_quote.consumed_at = utcnow()
            self.session.add(
                Delivery(
                    order_id=order.id,
                    quote_id=delivery_quote.id,
                    provider=delivery_quote.provider,
                    status=DeliveryStatus.QUOTED.value,
                    currency=delivery_quote.currency,
                    fee_minor=delivery_quote.fee_minor,
                    origin_address=delivery_quote.origin_address,
                    origin_latitude=delivery_quote.origin_latitude,
                    origin_longitude=delivery_quote.origin_longitude,
                    destination_address=delivery_quote.destination_address,
                    destination_city=delivery_quote.destination_city,
                    destination_latitude=delivery_quote.destination_latitude,
                    destination_longitude=delivery_quote.destination_longitude,
                    destination_instructions=delivery_quote.destination_instructions,
                    estimated_pickup_at=delivery_quote.estimated_pickup_at,
                    estimated_dropoff_at=delivery_quote.estimated_dropoff_at,
                )
            )

        promotion_discount, promotion = growth.preview_promotion(
            business_id, request.promo_code, quote.subtotal_minor, customer.id
        )
        growth.record_promotion(promotion, order, customer.id, promotion_discount)
        growth.reserve_reward(
            business_id=business_id, customer_id=customer.id, reward_id=request.reward_id, order=order
        )

        for quoted in quote.items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=quoted.menu_item_id,
                name_snapshot=quoted.name,
                quantity=quoted.quantity,
                unit_base_price_minor=quoted.unit_base_price_minor,
                unit_modifier_price_minor=quoted.unit_modifier_price_minor,
                line_total_minor=quoted.line_total_minor,
            )
            self.session.add(order_item)
            self.session.flush()
            for modifier in quoted.modifiers:
                self.session.add(
                    OrderItemModifier(
                        order_item_id=order_item.id,
                        modifier_option_id=modifier.option_id,
                        group_name_snapshot=modifier.group_name,
                        option_name_snapshot=modifier.option_name,
                        price_delta_minor=modifier.price_delta_minor,
                    )
                )

        provider_idempotency_key = f"checkout:{business_id}:{request.idempotency_key or order.id}"
        try:
            checkout = self.provider_executor.call(
                provider.name,
                "create_checkout",
                lambda: provider.create_checkout(
                    order_id=order.id,
                    public_code=order.public_code,
                    amount_minor=order.total_minor,
                    currency=order.currency,
                    customer_email=request.customer.email,
                    idempotency_key=provider_idempotency_key,
                ),
            )
        except (PaymentError, ProviderCircuitOpenError):
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise PaymentError(f"Payment checkout failed via {provider.name}") from exc

        if checkout.provider != provider.name:
            self.session.rollback()
            raise PaymentError("Payment provider identity mismatch")
        if not checkout.provider_reference.strip():
            self.session.rollback()
            raise PaymentError("Payment provider returned an empty reference")
        if checkout.amount_minor != order.total_minor or checkout.currency != order.currency:
            self.session.rollback()
            raise PaymentError("Payment provider returned amount/currency that does not match the order")
        try:
            checkout_status = PaymentStatus(checkout.status.lower())
        except ValueError as exc:
            self.session.rollback()
            raise PaymentError(f"Payment provider returned unsupported status: {checkout.status}") from exc
        if checkout_status in {PaymentStatus.FAILED, PaymentStatus.REFUNDED}:
            self.session.rollback()
            raise PaymentError(f"Payment checkout was created in invalid status: {checkout_status.value}")

        order.payment_status = checkout_status.value
        if checkout_status == PaymentStatus.PAID or checkout.order_may_proceed:
            order.status = OrderStatus.PLACED.value

        payment = Payment(
            order_id=order.id,
            provider=checkout.provider,
            provider_reference=checkout.provider_reference,
            status=checkout_status.value,
            amount_minor=checkout.amount_minor,
            currency=checkout.currency,
            checkout_url=checkout.checkout_url,
        )
        self.session.add(payment)

        if claim:
            complete_idempotency(self.session, claim.record_id, entity_id=order.id)

        self._commit_event(
            kind="order.created",
            business_id=business_id,
            entity_id=order.id,
            payload={
                "public_code": order.public_code,
                "total_minor": order.total_minor,
                "fulfillment_type": fulfillment.value,
                "delivery_fee_minor": delivery_fee,
                "payment_provider": payment.provider,
            },
            dedupe_key=f"order-created:{order.id}",
        )
        return self.order_out(order.id)

    def apply_payment_status(
        self,
        provider_reference: str,
        status: str,
        *,
        provider: str | None = None,
        event_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
        raw_event_json: str | None = None,
    ) -> OrderOut:
        payment = self.session.scalar(select(Payment).where(Payment.provider_reference == provider_reference))
        if not payment:
            raise NotFoundError("Payment not found")
        if provider and payment.provider != provider:
            raise ValidationError("Payment provider does not match provider reference")
        if amount_minor is not None and amount_minor != payment.amount_minor:
            raise PaymentError("Webhook payment amount does not match stored payment")
        if currency is not None and currency.upper() != payment.currency.upper():
            raise PaymentError("Webhook payment currency does not match stored payment")

        normalized = status.lower()
        try:
            target = PaymentStatus(normalized)
            current = PaymentStatus(payment.status)
        except ValueError as exc:
            raise ValidationError(f"Unsupported payment status: {status}") from exc

        receipt = None
        if event_id:
            receipt_provider = provider or payment.provider
            fingerprint = request_fingerprint({
                "provider_reference": provider_reference,
                "status": normalized,
                "amount_minor": amount_minor,
                "currency": currency.upper() if currency else None,
            })
            receipt, acquired = acquire_webhook_receipt(
                self.session, provider=receipt_provider, event_id=event_id, fingerprint=fingerprint
            )
            if not acquired:
                return self.order_out(payment.order_id)

        if current == target:
            if receipt:
                receipt.processed_at = utcnow()
                self._commit()
            return self.order_out(payment.order_id)
        if target not in PAYMENT_TRANSITIONS[current]:
            raise InvalidTransitionError(
                f"Cannot transition payment from {current.value} to {target.value}"
            )

        payment.status = target.value
        payment.raw_status_json = raw_event_json or json.dumps({"status": target.value}, sort_keys=True)
        order = self.session.get(Order, payment.order_id)
        if not order:
            raise NotFoundError("Order not found for payment")
        order.payment_status = target.value

        if target == PaymentStatus.PAID and order.status == OrderStatus.AWAITING_PAYMENT.value:
            order.status = OrderStatus.PLACED.value
        elif target == PaymentStatus.FAILED and order.status == OrderStatus.AWAITING_PAYMENT.value:
            order.status = OrderStatus.CANCELLED.value
            delivery = self.session.scalar(select(Delivery).where(Delivery.order_id == order.id))
            if delivery and DeliveryStatus(delivery.status) == DeliveryStatus.QUOTED:
                self._record_delivery_status(
                    delivery,
                    DeliveryStatus.CANCELLED.value,
                    dedupe_key=f"payment-failed:{delivery.id}",
                )

        growth = RestaurantGrowthService(self.session)
        if target == PaymentStatus.PAID:
            growth.finalize_reward(order.id)
            growth.finalize_promotion(order.id)
        elif target == PaymentStatus.FAILED:
            growth.release_reward(order.id)
            growth.release_promotion(order.id)

        if receipt:
            receipt.processed_at = utcnow()

        self._commit_event(
            kind="payment.updated",
            business_id=order.business_id,
            entity_id=payment.id,
            payload={"order_id": order.id, "from": current.value, "status": target.value, "provider": payment.provider},
            dedupe_key=(f"payment-webhook:{payment.provider}:{event_id}" if event_id else f"payment-status:{payment.id}:{current.value}:{target.value}"),
        )
        return self.order_out(order.id)

    def transition_order(self, order_id: str, new_status: str) -> OrderOut:
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.payments), selectinload(Order.delivery))
        )
        if not order:
            raise NotFoundError("Order not found")
        try:
            current = OrderStatus(order.status)
            target = OrderStatus(new_status)
        except ValueError as exc:
            raise ValidationError(f"Unknown order status: {new_status}") from exc

        if current == target:
            return self.order_out(order.id)
        if target not in ORDER_TRANSITIONS[current]:
            raise InvalidTransitionError(f"Cannot transition order from {current.value} to {target.value}")

        payments = order.payments
        deferred_payment = any(p.provider == "cash_at_pickup" for p in payments)
        if target in {OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.COMPLETED}:
            if order.payment_status != PaymentStatus.PAID.value and not deferred_payment:
                raise InvalidTransitionError("Order cannot advance before payment is confirmed")

        delivery = order.delivery
        if order.fulfillment_type == FulfillmentType.DELIVERY.value and target == OrderStatus.COMPLETED:
            if not delivery or delivery.status != DeliveryStatus.DELIVERED.value:
                raise InvalidTransitionError("Delivery orders complete only after the courier marks them delivered")

        if target == OrderStatus.CANCELLED:
            if order.payment_status == PaymentStatus.PAID.value:
                raise InvalidTransitionError("Paid orders require a refund workflow before cancellation")
            if delivery:
                delivery_status = DeliveryStatus(delivery.status)
                if delivery_status in {DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERED}:
                    raise InvalidTransitionError("Order cannot be cancelled after courier pickup")
                if delivery.provider_delivery_reference and delivery_status not in {DeliveryStatus.CANCELLED, DeliveryStatus.FAILED}:
                    raise InvalidTransitionError("Cancel the dispatched delivery before cancelling the order")
                if delivery_status == DeliveryStatus.QUOTED:
                    self._record_delivery_status(
                        delivery,
                        DeliveryStatus.CANCELLED.value,
                        dedupe_key=f"order-cancel:{delivery.id}",
                    )

        now = utcnow()
        order.status = target.value
        if target == OrderStatus.ACCEPTED:
            order.accepted_at = now
        elif target == OrderStatus.READY:
            order.ready_at = now
        elif target == OrderStatus.COMPLETED:
            # Cash-at-pickup becomes paid exactly when the fulfilled order closes.
            if order.payment_status != PaymentStatus.PAID.value and deferred_payment:
                for payment in payments:
                    if payment.provider == "cash_at_pickup" and payment.status != PaymentStatus.PAID.value:
                        payment.status = PaymentStatus.PAID.value
                        payment.raw_status_json = json.dumps({"status": "paid", "cause": "order.completed"}, sort_keys=True)
                order.payment_status = PaymentStatus.PAID.value
            order.completed_at = now
            customer = self.session.get(Customer, order.customer_id)
            if customer:
                customer.last_order_at = now
            growth = RestaurantGrowthService(self.session)
            growth.finalize_reward(order.id)
            growth.finalize_promotion(order.id)
            growth.award_completed_order(order)
            growth.queue_order_completed_automations(order)
        elif target == OrderStatus.CANCELLED:
            growth = RestaurantGrowthService(self.session)
            growth.release_reward(order.id)
            growth.release_promotion(order.id)

        self._commit_event(
            kind="order.status_changed",
            business_id=order.business_id,
            entity_id=order.id,
            occurred_at=now,
            payload={"from": current.value, "to": target.value},
            dedupe_key=f"order-transition:{order.id}:{current.value}:{target.value}",
        )
        return self.order_out(order.id)

    def _order_to_out(self, order: Order) -> OrderOut:
        return OrderOut(
            id=order.id,
            public_code=order.public_code,
            business_id=order.business_id,
            status=order.status,
            payment_status=order.payment_status,
            fulfillment_type=order.fulfillment_type,
            currency=order.currency,
            subtotal_minor=order.subtotal_minor,
            promotion_discount_minor=order.promotion_discount_minor,
            reward_discount_minor=order.reward_discount_minor,
            discount_minor=order.discount_minor,
            delivery_fee_minor=order.delivery_fee_minor,
            promotion_code=order.promotion_code_snapshot,
            reward_name=order.reward_name_snapshot,
            total_minor=order.total_minor,
            prep_minutes=order.prep_minutes,
            requested_pickup_at=order.requested_pickup_at,
            notes=order.notes,
            source_channel=order.source_channel,
            external_source_ref=order.external_source_ref,
            created_at=order.created_at,
            customer_name=order.customer.name,
            customer_phone=order.customer.phone,
            items=[
                OrderItemOut(
                    name=item.name_snapshot,
                    quantity=item.quantity,
                    unit_base_price_minor=item.unit_base_price_minor,
                    unit_modifier_price_minor=item.unit_modifier_price_minor,
                    line_total_minor=item.line_total_minor,
                    modifiers=[
                        OrderItemModifierOut(
                            group_name=modifier.group_name_snapshot,
                            option_name=modifier.option_name_snapshot,
                            price_delta_minor=modifier.price_delta_minor,
                        )
                        for modifier in item.modifiers
                    ],
                )
                for item in order.items
            ],
            delivery=(
                DeliveryTrackingOut(
                    order_id=order.id,
                    public_code=order.public_code,
                    status=order.delivery.status,
                    provider=order.delivery.provider,
                    tracking_url=order.delivery.tracking_url,
                    courier_name=order.delivery.courier_name,
                    estimated_pickup_at=order.delivery.estimated_pickup_at,
                    estimated_dropoff_at=order.delivery.estimated_dropoff_at,
                    picked_up_at=order.delivery.picked_up_at,
                    delivered_at=order.delivery.delivered_at,
                ) if order.delivery else None
            ),
            payments=[
                PaymentOut(
                    provider=payment.provider,
                    provider_reference=payment.provider_reference,
                    status=payment.status,
                    amount_minor=payment.amount_minor,
                    currency=payment.currency,
                    checkout_url=payment.checkout_url,
                )
                for payment in order.payments
            ],
        )

    def _orders_stmt(self):
        return select(Order).options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.modifiers),
            selectinload(Order.payments),
            selectinload(Order.delivery),
        )

    def order_out(self, order_id: str) -> OrderOut:
        order = self.session.scalar(self._orders_stmt().where(Order.id == order_id))
        if not order:
            raise NotFoundError("Order not found")
        return self._order_to_out(order)

    def list_orders(self, business_id: str, *, status: str | None = None, limit: int = 100) -> list[OrderOut]:
        stmt = self._orders_stmt().where(Order.business_id == business_id)
        if status:
            try:
                OrderStatus(status)
            except ValueError as exc:
                raise ValidationError(f"Unknown order status: {status}") from exc
            stmt = stmt.where(Order.status == status)
        stmt = stmt.order_by(Order.created_at.desc()).limit(min(max(limit, 1), 500))
        orders = self.session.scalars(stmt).all()
        return [self._order_to_out(order) for order in orders]

    # ------------------------------------------------------------------
    # Reservations
    # ------------------------------------------------------------------
    def create_reservation(self, business_id: str, request: CreateReservationRequest) -> ReservationOut:
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if not profile:
            raise NotFoundError(f"Restaurant commerce profile not found: {business_id}")
        if not profile.accepts_reservations:
            raise ValidationError("Reservations are disabled")
        if profile.max_party_size and request.party_size > profile.max_party_size:
            raise ValidationError(f"Party exceeds configured maximum of {profile.max_party_size}")

        starts_at = _aware_utc(request.starts_at)
        if starts_at <= datetime.now(timezone.utc):
            raise ValidationError("Reservation must be in the future")
        if starts_at.minute % profile.reservation_slot_minutes != 0 or starts_at.second != 0:
            raise ValidationError(
                f"Reservation time must align to {profile.reservation_slot_minutes}-minute slots"
            )

        claim = None
        if request.idempotency_key:
            claim = acquire_idempotency(
                self.session,
                scope=f"reservation.create:{business_id}",
                key=request.idempotency_key,
                fingerprint=request_fingerprint(request.model_dump(mode="json")),
            )
            if not claim.acquired:
                if not claim.entity_id:
                    raise IdempotencyConflictError("Idempotent reservation request is not complete")
                return self.reservation_out(claim.entity_id)

        customer = self._upsert_customer(
            business_id,
            name=request.customer.name,
            phone=request.customer.phone,
            email=request.customer.email,
            whatsapp_opt_in=request.customer.whatsapp_opt_in,
            marketing_opt_in=request.customer.marketing_opt_in,
            consent_source=request.customer.consent_source or request.source_channel,
        )
        reservation = Reservation(
            public_code=_public_code("R"),
            business_id=business_id,
            customer_id=customer.id,
            starts_at=starts_at,
            party_size=request.party_size,
            status=ReservationStatus.REQUESTED.value,
            notes=request.notes,
            source_channel=request.source_channel,
            external_source_ref=request.external_source_ref,
        )
        self.session.add(reservation)
        self.session.flush()
        if claim:
            complete_idempotency(self.session, claim.record_id, entity_id=reservation.id)
        self._commit_event(
            kind="reservation.created",
            business_id=business_id,
            entity_id=reservation.id,
            payload={"public_code": reservation.public_code, "party_size": reservation.party_size},
            dedupe_key=f"reservation-created:{reservation.id}",
        )
        return self.reservation_out(reservation.id)

    def _reservation_to_out(self, reservation: Reservation) -> ReservationOut:
        return ReservationOut(
            id=reservation.id,
            public_code=reservation.public_code,
            business_id=reservation.business_id,
            status=reservation.status,
            starts_at=reservation.starts_at,
            party_size=reservation.party_size,
            notes=reservation.notes,
            source_channel=reservation.source_channel,
            external_source_ref=reservation.external_source_ref,
            customer_name=reservation.customer.name,
            customer_phone=reservation.customer.phone,
            created_at=reservation.created_at,
        )

    def reservation_out(self, reservation_id: str) -> ReservationOut:
        reservation = self.session.scalar(
            select(Reservation)
            .where(Reservation.id == reservation_id)
            .options(selectinload(Reservation.customer))
        )
        if not reservation:
            raise NotFoundError("Reservation not found")
        return self._reservation_to_out(reservation)

    def list_reservations(self, business_id: str, *, limit: int = 100) -> list[ReservationOut]:
        stmt = (
            select(Reservation)
            .where(Reservation.business_id == business_id)
            .options(selectinload(Reservation.customer))
            .order_by(Reservation.starts_at.asc())
            .limit(min(max(limit, 1), 500))
        )
        return [self._reservation_to_out(row) for row in self.session.scalars(stmt).all()]

    def transition_reservation(self, reservation_id: str, new_status: str) -> ReservationOut:
        reservation = self.session.get(Reservation, reservation_id)
        if not reservation:
            raise NotFoundError("Reservation not found")
        try:
            current = ReservationStatus(reservation.status)
            target = ReservationStatus(new_status)
        except ValueError as exc:
            raise ValidationError(f"Unknown reservation status: {new_status}") from exc
        if current == target:
            return self.reservation_out(reservation.id)
        if target not in RESERVATION_TRANSITIONS[current]:
            raise InvalidTransitionError(
                f"Cannot transition reservation from {current.value} to {target.value}"
            )
        reservation.status = target.value
        self._commit_event(
            kind="reservation.status_changed",
            business_id=reservation.business_id,
            entity_id=reservation.id,
            payload={"from": current.value, "to": target.value},
            dedupe_key=f"reservation-transition:{reservation.id}:{current.value}:{target.value}",
        )
        return self.reservation_out(reservation.id)

