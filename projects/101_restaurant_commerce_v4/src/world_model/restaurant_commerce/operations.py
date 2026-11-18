"""M5 pickup/stock contracts; existing commerce order and staff authority remain owners."""

# ruff: noqa: B008 - FastAPI dependency defaults are intentional
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, Query
from pydantic import Field, model_validator
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError

from .errors import IdempotencyConflictError, NotFoundError, ValidationError
from .models import (
    ItemStock,
    Menu,
    MenuCategory,
    MenuItem,
    Order,
    PaymentReconciliation,
    PickupPolicy,
    RestaurantCommerceProfile,
    utcnow,
)
from .schemas import StrictModel


def quote_binding(business_id, request, total):
    content = {
        "business": business_id,
        "items": [i.model_dump(mode="json") for i in request.items],
        "promo": request.promo_code,
        "reward": request.reward_id,
        "total": total,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


class PickupSettings(StrictModel):
    expected_version: int = Field(ge=0)
    ordering_enabled: bool
    scheduled: bool = False
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), max_length=7)
    opens: int = Field(default=480, ge=0, lt=1440)
    closes: int = Field(default=1200, gt=0, le=1440)
    slot_minutes: int = Field(default=30, ge=15, le=120)
    lead_minutes: int = Field(default=30, ge=5, le=720)
    capacity: int = Field(default=10, ge=1, le=500)
    closed_dates: list[date] = Field(default_factory=list, max_length=90)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def valid_window(self):
        if self.opens >= self.closes or any(d not in range(7) for d in self.weekdays):
            raise ValueError("Horario no válido")
        if len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError("Días repetidos")
        return self


class StockSettings(StrictModel):
    expected_version: int = Field(ge=0)
    remaining: int | None = Field(default=None, ge=0, le=100000)
    sold_out: bool
    reason: str = Field(min_length=1, max_length=500)


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class OperationsMixin:
    def _ops_profile(self, business_id):
        profile = self.session.get(RestaurantCommerceProfile, business_id)
        if profile is None:
            raise NotFoundError("Restaurante no encontrado")
        return profile

    def pickup_slots(self, business_id, *, now=None, requested_at=None):
        profile = self._ops_profile(business_id)
        row = self.session.get(PickupPolicy, business_id)
        result = {
            "timezone": profile.timezone,
            "scheduled": False,
            "version": row.version if row else 0,
            "slots": [],
        }
        if not row or not json.loads(row.policy_json)["scheduled"]:
            return result
        policy = json.loads(row.policy_json)
        result["scheduled"] = True
        now = aware(now or utcnow())
        zone = ZoneInfo(profile.timezone)
        today = now.astimezone(zone).date()
        days = range(7)
        minutes = range(policy["opens"], policy["closes"], policy["slot_minutes"])
        target = None
        if requested_at is not None:
            if requested_at.tzinfo is None:
                return result
            target = aware(requested_at)
            local_target = target.astimezone(zone)
            day_offset = (local_target.date() - today).days
            minute = local_target.hour * 60 + local_target.minute
            if not 0 <= day_offset < 7 or minute not in minutes:
                return result
            # Admission needs one candidate, not the entire seven-day calendar.
            # The common loop below retains DST/fold, lead-time and closure rules.
            days, minutes = (day_offset,), (minute,)
        count_query = select(Order.requested_pickup_at, func.count()).where(
            Order.business_id == business_id,
            Order.status != "cancelled",
            Order.requested_pickup_at >= now,
        )
        if target is not None:
            count_query = count_query.where(Order.requested_pickup_at == target)
        counts = dict(self.session.execute(count_query.group_by(Order.requested_pickup_at)).all())
        counts = {aware(k): v for k, v in counts.items()}
        if not profile.ordering_enabled or not profile.pickup_enabled:
            return result
        for n in days:
            day = today + timedelta(days=n)
            if day.weekday() not in policy["weekdays"] or day.isoformat() in policy["closed_dates"]:
                continue
            for minute in minutes:
                local = datetime.combine(day, time(), zone) + timedelta(minutes=minute)
                instant = local.astimezone(UTC)
                if target is not None and instant != target:
                    continue
                # Reject nonexistent wall-clock times around DST transitions.
                if instant.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
                    continue
                if instant < now + timedelta(minutes=policy["lead_minutes"]):
                    continue
                remaining = policy["capacity"] - counts.get(instant, 0)
                if remaining > 0:
                    result["slots"].append({"at": instant.isoformat(), "remaining": remaining})
        return result

    def operations_settings(self, business_id):
        profile = self._ops_profile(business_id)
        row = self.session.get(PickupPolicy, business_id)
        policy = (
            json.loads(row.policy_json)
            if row
            else PickupSettings(
                expected_version=0, ordering_enabled=profile.ordering_enabled, reason="initial"
            ).model_dump(mode="json", exclude={"reason", "expected_version"})
        )
        items = self.session.scalars(
            select(MenuItem)
            .join(MenuCategory)
            .join(Menu)
            .where(Menu.business_id == business_id)
            .order_by(MenuItem.display_order, MenuItem.id)
        ).all()
        stocks = {
            s.item_id: s
            for s in self.session.scalars(
                select(ItemStock).where(ItemStock.item_id.in_([i.id for i in items]))
            )
        }
        return {
            "version": row.version if row else 0,
            "timezone": profile.timezone,
            "policy": {**policy, "ordering_enabled": profile.ordering_enabled},
            "items": [
                {
                    "id": i.id,
                    "name": i.name,
                    "sold_out": i.sold_out,
                    "remaining": stocks[i.id].remaining if i.id in stocks else None,
                    "version": stocks[i.id].version if i.id in stocks else 0,
                }
                for i in items
            ],
        }

    def save_operations_settings(self, business_id, body, principal):
        # A profile always exists, even before the first policy row. Lock it first
        # so first-time pause/scheduling changes cannot race an admitted checkout.
        profile = self.session.scalar(
            select(RestaurantCommerceProfile)
            .where(RestaurantCommerceProfile.business_id == business_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if profile is None:
            raise NotFoundError("Restaurante no encontrado")
        row = self.session.scalar(
            select(PickupPolicy)
            .where(PickupPolicy.business_id == business_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if body.expected_version != (row.version if row else 0):
            raise IdempotencyConflictError("La configuración cambió. Actualiza antes de guardar.")
        policy = body.model_dump(mode="json", exclude={"reason", "expected_version"})
        previous = json.loads(row.policy_json) if row else None
        if row:
            row.policy_json = json.dumps(policy)
        else:
            self.session.add(PickupPolicy(business_id=business_id, policy_json=json.dumps(policy)))
        profile.ordering_enabled = body.ordering_enabled
        try:
            self._commit_event(
                kind="operations.settings_changed",
                business_id=business_id,
                entity_id=business_id,
                payload={
                    "actor": principal.actor_id,
                    "reason": body.reason,
                    "previous": previous,
                    "policy": policy,
                },
            )
        except IntegrityError:
            self.session.rollback()
            raise IdempotencyConflictError(
                "La configuración cambió. Actualiza antes de guardar."
            ) from None
        if self.storefront_cache is not None:
            self.storefront_cache.invalidate(business_id)
        return self.operations_settings(business_id)

    def save_item_stock(self, business_id, item_id, body, principal):
        item = self.session.scalar(
            select(MenuItem)
            .join(MenuCategory)
            .join(Menu)
            .where(Menu.business_id == business_id, MenuItem.id == item_id)
            .with_for_update(of=MenuItem)
            .execution_options(populate_existing=True)
        )
        if not item:
            raise NotFoundError("Producto no encontrado en este negocio")
        row = self.session.get(ItemStock, item_id)
        previous = {"sold_out": item.sold_out, "remaining": row.remaining if row else None}
        if row:
            changed = self.session.execute(
                update(ItemStock)
                .where(ItemStock.item_id == item_id, ItemStock.version == body.expected_version)
                .values(remaining=body.remaining, version=ItemStock.version + 1)
            ).rowcount
            if not changed:
                raise IdempotencyConflictError(
                    "Las existencias cambiaron. Actualiza antes de guardar."
                )
        else:
            if body.expected_version:
                raise IdempotencyConflictError("Las existencias cambiaron.")
            self.session.add(ItemStock(item_id=item_id, remaining=body.remaining))
        item.sold_out = body.sold_out
        try:
            self._commit_event(
                kind="operations.stock_changed",
                business_id=business_id,
                entity_id=item_id,
                payload={
                    "actor": principal.actor_id,
                    "reason": body.reason,
                    "previous": previous,
                    "stock": body.model_dump(),
                },
            )
        except IntegrityError:
            self.session.rollback()
            raise IdempotencyConflictError(
                "Las existencias cambiaron. Actualiza antes de guardar."
            ) from None
        self.session.expire_all()
        if self.storefront_cache is not None:
            self.storefront_cache.invalidate(business_id)
        return self.operations_settings(business_id)

    def allocate_pickup_and_stock(self, profile, request):
        # Readers may admit independent orders concurrently. Staff edits take the
        # conflicting exclusive profile/item locks; retain these until local commit.
        profile = self.session.scalar(
            select(RestaurantCommerceProfile)
            .where(RestaurantCommerceProfile.business_id == profile.business_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if not profile or not profile.ordering_enabled:
            raise ValidationError("Los pedidos están pausados")
        if request.fulfillment_type == "pickup" and not profile.pickup_enabled:
            raise ValidationError("La recogida no está disponible")
        policy = self.session.scalar(
            select(PickupPolicy)
            .where(PickupPolicy.business_id == profile.business_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if policy and not json.loads(policy.policy_json)["ordering_enabled"]:
            raise ValidationError("Los pedidos están pausados")
        if request.fulfillment_type == "pickup":
            requested = request.requested_pickup_at
            scheduled = bool(policy and json.loads(policy.policy_json)["scheduled"])
            if scheduled and requested and self.session.get_bind().dialect.name == "postgresql":
                # Serialize only one business/UTC slot, not all merchant orders.
                # Hash collisions can only add contention, never bypass capacity.
                key = json.dumps(
                    ["pickup-slot-v1", profile.business_id, aware(requested).isoformat()],
                    separators=(",", ":"),
                )
                lock_id = int.from_bytes(
                    hashlib.sha256(key.encode()).digest()[:8], "big", signed=True
                )
                self.session.execute(select(func.pg_advisory_xact_lock(lock_id)))
            slots = (
                self.pickup_slots(profile.business_id, requested_at=requested)
                if scheduled and requested
                else {"scheduled": scheduled, "slots": []}
            )
            requested = request.requested_pickup_at
            if requested and (requested.tzinfo is None or aware(requested) <= utcnow()):
                raise ValidationError("Selecciona una hora futura con zona horaria")
            if requested and not slots["scheduled"]:
                raise ValidationError(
                    "Este restaurante no publica horarios reservables; "
                    "confirma la recogida con el personal."
                )
            if slots["scheduled"]:
                if not requested or aware(requested).isoformat() not in {
                    s["at"] for s in slots["slots"]
                }:
                    raise ValidationError(
                        "Horario cerrado, completo o vencido. Selecciona otra hora."
                    )
        quantities = Counter()
        for item in request.items:
            quantities[item.menu_item_id] += item.quantity
        # Consistent lock order avoids deadlocks for overlapping carts.
        for item_id, quantity in sorted(quantities.items()):
            item = self.session.scalar(
                select(MenuItem)
                .where(MenuItem.id == item_id)
                .with_for_update(read=True, of=MenuItem)
                .execution_options(populate_existing=True)
            )
            if not item or item.sold_out or not item.enabled:
                raise ValidationError("Un producto ya no está disponible. Actualiza el pedido.")
            stock = self.session.get(ItemStock, item_id)
            if stock and stock.remaining is not None:
                changed = self.session.execute(
                    update(ItemStock)
                    .where(ItemStock.item_id == item_id, ItemStock.remaining >= quantity)
                    .values(remaining=ItemStock.remaining - quantity, version=ItemStock.version + 1)
                ).rowcount
                if not changed:
                    raise ValidationError("No quedan suficientes unidades. Actualiza el pedido.")

    def daily_finance(self, business_id, day, currency=None):
        profile = self._ops_profile(business_id)
        zone = ZoneInfo(profile.timezone)
        if day.year < 1900 or day.year > 9998:
            raise ValidationError("Fecha fuera del rango permitido")
        begin = datetime.combine(day, time(), zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time(), zone).astimezone(UTC)
        cohort = [Order.business_id == business_id, Order.created_at >= begin, Order.created_at < end]
        currencies = list(self.session.scalars(select(Order.currency).where(*cohort).distinct().order_by(Order.currency)))
        if currency:
            cohort.append(Order.currency == currency)
        count, gross, refunds, unconfirmed = self.session.execute(
            select(
                func.count(Order.id),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.payment_status.in_(["paid", "refunded"]), Order.total_minor),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((Order.payment_status == "refunded", Order.total_minor), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (Order.payment_status.not_in(["paid", "refunded", "failed"]), 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(
                *cohort
            )
        ).one()
        holds = self.session.scalar(
            select(func.count())
            .select_from(PaymentReconciliation)
            .where(
                PaymentReconciliation.business_id == business_id,
                PaymentReconciliation.status == "open",
            )
        )
        from .models import Payment
        from .refunds import PaymentRefund

        partial = self.session.scalar(
            select(func.coalesce(func.sum(PaymentRefund.amount_minor), 0))
            .join(Payment, Payment.id == PaymentRefund.payment_id)
            .join(Order, Order.id == Payment.order_id)
            .where(
                *cohort,
                Payment.status == "paid",
            )
        )
        return {
            "date": day.isoformat(),
            "timezone": profile.timezone,
            "currencies": currencies,
            "currency": currency or (currencies[0] if len(currencies) == 1 else profile.currency if not currencies else None),
            "basis": "order_creation_day_current_local_payment_state",
            "orders": count,
            "gross_minor": gross,
            "confirmed_full_refunds_minor": refunds,
            "confirmed_partial_refunds_minor": partial,
            "known_balance_minor": gross - refunds - partial,
            "provider_fees_minor": None,
            "settled_net_minor": None,
            "open_reviews_all_dates": holds,
            "unconfirmed_orders": unconfirmed,
        }


def register_operations(app, get_service, require_operator):
    @app.get("/api/restaurants/{business_id}/pickup-slots")
    def pickup_slots(business_id: str, service=Depends(get_service)):
        return service.pickup_slots(business_id)

    @app.get("/api/operator/restaurants/{business_id}/settings")
    def operations_settings(
        business_id: str, principal=Depends(require_operator), service=Depends(get_service)
    ):
        return service.operations_settings(business_id)

    @app.put("/api/operator/restaurants/{business_id}/settings")
    def save_operations_settings(
        business_id: str,
        body: PickupSettings,
        principal=Depends(require_operator),
        service=Depends(get_service),
    ):
        return service.save_operations_settings(business_id, body, principal)

    @app.put("/api/operator/restaurants/{business_id}/stock/{item_id}")
    def save_item_stock(
        business_id: str,
        item_id: str,
        body: StockSettings,
        principal=Depends(require_operator),
        service=Depends(get_service),
    ):
        return service.save_item_stock(business_id, item_id, body, principal)

    @app.get("/api/operator/orders/{order_id}")
    def operator_order_detail(
        order_id: str, principal=Depends(require_operator), service=Depends(get_service)
    ):
        return service.order_out(order_id)

    @app.get("/api/operator/restaurants/{business_id}/daily-finance")
    def daily_finance(
        business_id: str,
        day: date = Query(),
        currency: str | None = Query(None, pattern=r"^[A-Z]{3}$"),
        principal=Depends(require_operator),
        service=Depends(get_service),
    ):
        return service.daily_finance(business_id, day, currency=currency)
