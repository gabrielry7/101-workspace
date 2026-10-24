from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Float,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import DeliveryStatus, FulfillmentType, OrderStatus, PaymentStatus, ReservationStatus


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RestaurantCommerceProfile(Base):
    __tablename__ = "restaurant_commerce_profiles"

    business_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(240))
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Bogota")
    ordering_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_provider: Mapped[str] = mapped_column(String(40), default="simulated")
    cash_at_pickup_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pickup_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_provider: Mapped[str] = mapped_column(String(64), default="simulated_delivery")
    delivery_origin_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_origin_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_origin_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_max_distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True, default=12000)
    accepts_reservations: Mapped[bool] = mapped_column(Boolean, default=True)
    default_prep_minutes: Mapped[int] = mapped_column(Integer, default=25)
    reservation_slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_party_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pickup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    loyalty_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    marketing_automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    review_requests_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    winback_days: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    menus: Mapped[list[Menu]] = relationship(back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("default_prep_minutes >= 0 AND default_prep_minutes <= 720", name="ck_profile_prep_minutes"),
        CheckConstraint("reservation_slot_minutes > 0 AND reservation_slot_minutes <= 1440", name="ck_profile_slot_minutes"),
        CheckConstraint("max_party_size IS NULL OR max_party_size > 0", name="ck_profile_party_size"),
        CheckConstraint("delivery_max_distance_meters IS NULL OR delivery_max_distance_meters > 0", name="ck_profile_delivery_radius"),
        CheckConstraint("winback_days > 0 AND winback_days <= 3650", name="ck_profile_winback_days"),
    )


class Menu(Base):
    __tablename__ = "restaurant_menus"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("restaurant_commerce_profiles.business_id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    profile: Mapped[RestaurantCommerceProfile] = relationship(back_populates="menus")
    categories: Mapped[list[MenuCategory]] = relationship(back_populates="menu", cascade="all, delete-orphan", order_by="MenuCategory.display_order")


class MenuCategory(Base):
    __tablename__ = "restaurant_menu_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    menu_id: Mapped[str] = mapped_column(ForeignKey("restaurant_menus.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    menu: Mapped[Menu] = relationship(back_populates="categories")
    items: Mapped[list[MenuItem]] = relationship(back_populates="category", cascade="all, delete-orphan", order_by="MenuItem.display_order")


class MenuItem(Base):
    __tablename__ = "restaurant_menu_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    category_id: Mapped[str] = mapped_column(ForeignKey("restaurant_menu_categories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sold_out: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[MenuCategory] = relationship(back_populates="items")
    modifier_groups: Mapped[list[ModifierGroup]] = relationship(back_populates="item", cascade="all, delete-orphan", order_by="ModifierGroup.display_order")

    __table_args__ = (
        CheckConstraint("base_price_minor >= 0", name="ck_menu_item_price_nonnegative"),
        Index("ix_restaurant_menu_items_available", "category_id", "enabled", "sold_out"),
    )


class ModifierGroup(Base):
    __tablename__ = "restaurant_modifier_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    item_id: Mapped[str] = mapped_column(ForeignKey("restaurant_menu_items.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_selections: Mapped[int] = mapped_column(Integer, default=0)
    max_selections: Mapped[int] = mapped_column(Integer, default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    item: Mapped[MenuItem] = relationship(back_populates="modifier_groups")
    options: Mapped[list[ModifierOption]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="ModifierOption.display_order")

    __table_args__ = (
        CheckConstraint("min_selections >= 0", name="ck_modifier_group_min_nonnegative"),
        CheckConstraint("max_selections >= 1", name="ck_modifier_group_max_positive"),
        CheckConstraint("max_selections >= min_selections", name="ck_modifier_group_range"),
    )


class ModifierOption(Base):
    __tablename__ = "restaurant_modifier_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("restaurant_modifier_groups.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    price_delta_minor: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[ModifierGroup] = relationship(back_populates="options")


class Customer(Base):
    __tablename__ = "restaurant_customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    phone: Mapped[str] = mapped_column(String(40))
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_opt_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    marketing_opt_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_opt_in_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        UniqueConstraint("business_id", "phone", name="uq_restaurant_customer_business_phone"),
        Index("ix_restaurant_customers_business_last_order", "business_id", "last_order_at"),
    )


class Order(Base):
    __tablename__ = "restaurant_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    public_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.AWAITING_PAYMENT.value, index=True)
    fulfillment_type: Mapped[str] = mapped_column(String(20), default=FulfillmentType.PICKUP.value)
    payment_status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.UNPAID.value, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    subtotal_minor: Mapped[int] = mapped_column(Integer)
    promotion_discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    reward_discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    discount_minor: Mapped[int] = mapped_column(Integer, default=0)
    promotion_code_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reward_name_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_fee_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer)
    prep_minutes: Mapped[int] = mapped_column(Integer)
    requested_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel: Mapped[str] = mapped_column(String(32), default="web")
    external_source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}

    customer: Mapped[Customer] = relationship()
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship(back_populates="order", cascade="all, delete-orphan")
    delivery: Mapped[Delivery | None] = relationship(back_populates="order", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        UniqueConstraint("business_id", "idempotency_key", name="uq_restaurant_order_business_idempotency"),
        CheckConstraint("subtotal_minor >= 0", name="ck_order_subtotal_nonnegative"),
        CheckConstraint("promotion_discount_minor >= 0", name="ck_order_promo_discount_nonnegative"),
        CheckConstraint("reward_discount_minor >= 0", name="ck_order_reward_discount_nonnegative"),
        CheckConstraint("discount_minor >= 0 AND discount_minor <= subtotal_minor", name="ck_order_discount_range"),
        CheckConstraint("discount_minor = promotion_discount_minor + reward_discount_minor", name="ck_order_discount_components"),
        CheckConstraint("delivery_fee_minor >= 0", name="ck_order_delivery_fee_nonnegative"),
        CheckConstraint("total_minor = subtotal_minor - discount_minor + delivery_fee_minor", name="ck_order_total_integrity"),
        CheckConstraint("prep_minutes >= 0 AND prep_minutes <= 720", name="ck_order_prep_minutes"),
        Index("ix_restaurant_orders_business_created", "business_id", "created_at"),
        Index("ix_restaurant_orders_business_status_created", "business_id", "status", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "restaurant_order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="CASCADE"), index=True)
    menu_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name_snapshot: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_base_price_minor: Mapped[int] = mapped_column(Integer)
    unit_modifier_price_minor: Mapped[int] = mapped_column(Integer, default=0)
    line_total_minor: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")
    modifiers: Mapped[list[OrderItemModifier]] = relationship(back_populates="order_item", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 100", name="ck_order_item_quantity"),
        CheckConstraint("unit_base_price_minor >= 0", name="ck_order_item_base_nonnegative"),
        CheckConstraint("line_total_minor >= 0", name="ck_order_item_total_nonnegative"),
    )


class OrderItemModifier(Base):
    __tablename__ = "restaurant_order_item_modifiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_item_id: Mapped[str] = mapped_column(ForeignKey("restaurant_order_items.id", ondelete="CASCADE"), index=True)
    modifier_option_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    group_name_snapshot: Mapped[str] = mapped_column(String(200))
    option_name_snapshot: Mapped[str] = mapped_column(String(200))
    price_delta_minor: Mapped[int] = mapped_column(Integer, default=0)

    order_item: Mapped[OrderItem] = relationship(back_populates="modifiers")


class Payment(Base):
    __tablename__ = "restaurant_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    provider_reference: Mapped[str] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.PENDING.value)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_status_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    order: Mapped[Order] = relationship(back_populates="payments")
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="ck_payment_amount_nonnegative"),
        Index("ix_restaurant_payments_order_status", "order_id", "status"),
    )


class DeliveryQuote(Base):
    __tablename__ = "restaurant_delivery_quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_quote_reference: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    fee_minor: Mapped[int] = mapped_column(Integer)
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_address: Mapped[str] = mapped_column(Text)
    origin_latitude: Mapped[float] = mapped_column(Float)
    origin_longitude: Mapped[float] = mapped_column(Float)
    destination_address: Mapped[str] = mapped_column(Text)
    destination_city: Mapped[str] = mapped_column(String(160))
    destination_latitude: Mapped[float] = mapped_column(Float)
    destination_longitude: Mapped[float] = mapped_column(Float)
    destination_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_dropoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_quote_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("fee_minor >= 0", name="ck_delivery_quote_fee_nonnegative"),
        CheckConstraint("distance_meters IS NULL OR distance_meters >= 0", name="ck_delivery_quote_distance_nonnegative"),
    )


class Delivery(Base):
    __tablename__ = "restaurant_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="CASCADE"), unique=True, index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("restaurant_delivery_quotes.id", ondelete="RESTRICT"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_delivery_reference: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=DeliveryStatus.QUOTED.value, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    fee_minor: Mapped[int] = mapped_column(Integer)
    origin_address: Mapped[str] = mapped_column(Text)
    origin_latitude: Mapped[float] = mapped_column(Float)
    origin_longitude: Mapped[float] = mapped_column(Float)
    destination_address: Mapped[str] = mapped_column(Text)
    destination_city: Mapped[str] = mapped_column(String(160))
    destination_latitude: Mapped[float] = mapped_column(Float)
    destination_longitude: Mapped[float] = mapped_column(Float)
    destination_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    courier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    courier_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_dropoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_status_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("fee_minor >= 0", name="ck_delivery_fee_nonnegative"),
        Index("ix_restaurant_deliveries_provider_status", "provider", "status"),
    )
    __mapper_args__ = {"version_id_col": version}
    order: Mapped[Order] = relationship(back_populates="delivery")
    quote: Mapped[DeliveryQuote] = relationship()
    events: Mapped[list[DeliveryEvent]] = relationship(back_populates="delivery", cascade="all, delete-orphan")


class DeliveryEvent(Base):
    __tablename__ = "restaurant_delivery_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("restaurant_deliveries.id", ondelete="CASCADE"), index=True)
    provider_status: Mapped[str] = mapped_column(String(80))
    normalized_status: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    dedupe_key: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    raw_event_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery: Mapped[Delivery] = relationship(back_populates="events")


class Reservation(Base):
    __tablename__ = "restaurant_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    public_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="RESTRICT"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    party_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=ReservationStatus.REQUESTED.value, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel: Mapped[str] = mapped_column(String(32), default="web")
    external_source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    customer: Mapped[Customer] = relationship()
    __table_args__ = (
        CheckConstraint("party_size > 0 AND party_size <= 100", name="ck_reservation_party_size"),
        Index("ix_restaurant_reservations_business_starts", "business_id", "starts_at"),
    )


class LoyaltyProgram(Base):
    __tablename__ = "restaurant_loyalty_programs"

    business_id: Mapped[str] = mapped_column(ForeignKey("restaurant_commerce_profiles.business_id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    spend_minor_per_point: Mapped[int] = mapped_column(Integer, default=1000)
    minimum_redeem_points: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LoyaltyAccount(Base):
    __tablename__ = "restaurant_loyalty_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="CASCADE"), index=True)
    available_points: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_earned_points: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_redeemed_points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        UniqueConstraint("business_id", "customer_id", name="uq_restaurant_loyalty_account"),
        CheckConstraint("available_points >= 0", name="ck_loyalty_available_nonnegative"),
        CheckConstraint("lifetime_earned_points >= 0", name="ck_loyalty_earned_nonnegative"),
        CheckConstraint("lifetime_redeemed_points >= 0", name="ck_loyalty_redeemed_nonnegative"),
    )


class LoyaltyLedgerEntry(Base):
    __tablename__ = "restaurant_loyalty_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_accounts.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    redemption_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    delta_points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RewardDefinition(Base):
    __tablename__ = "restaurant_rewards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_cost: Mapped[int] = mapped_column(Integer)
    discount_minor: Mapped[int] = mapped_column(Integer)
    minimum_order_minor: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("points_cost > 0", name="ck_reward_points_positive"),
        CheckConstraint("discount_minor >= 0", name="ck_reward_discount_nonnegative"),
        CheckConstraint("minimum_order_minor >= 0", name="ck_reward_minimum_nonnegative"),
    )


class RewardRedemption(Base):
    __tablename__ = "restaurant_reward_redemptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="RESTRICT"), index=True)
    reward_id: Mapped[str] = mapped_column(ForeignKey("restaurant_rewards.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="SET NULL"), nullable=True, unique=True)
    points_spent: Mapped[int] = mapped_column(Integer)
    discount_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="reserved", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Promotion(Base):
    __tablename__ = "restaurant_promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    discount_type: Mapped[str] = mapped_column(String(24), default="fixed")
    value: Mapped[int] = mapped_column(Integer)
    minimum_order_minor: Mapped[int] = mapped_column(Integer, default=0)
    maximum_discount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    per_customer_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_redemption_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("business_id", "code", name="uq_restaurant_promotion_code"),
        CheckConstraint("value >= 0", name="ck_promotion_value_nonnegative"),
        CheckConstraint("minimum_order_minor >= 0", name="ck_promotion_minimum_nonnegative"),
        CheckConstraint("maximum_discount_minor IS NULL OR maximum_discount_minor >= 0", name="ck_promotion_max_discount_nonnegative"),
        CheckConstraint("per_customer_limit IS NULL OR per_customer_limit > 0", name="ck_promotion_per_customer_limit"),
        CheckConstraint("total_redemption_limit IS NULL OR total_redemption_limit > 0", name="ck_promotion_total_limit"),
    )


class PromotionRedemption(Base):
    __tablename__ = "restaurant_promotion_redemptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    promotion_id: Mapped[str] = mapped_column(ForeignKey("restaurant_promotions.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="CASCADE"), unique=True, index=True)
    discount_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="reserved", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AutomationRule(Base):
    __tablename__ = "restaurant_automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    trigger_kind: Mapped[str] = mapped_column(String(80), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    purpose: Mapped[str] = mapped_column(String(32), default="marketing")
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    template_text: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutboundMessage(Base):
    __tablename__ = "restaurant_outbound_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("restaurant_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("restaurant_automation_rules.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    purpose: Mapped[str] = mapped_column(String(32))
    message_kind: Mapped[str] = mapped_column(String(80), index=True)
    destination: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    suppression_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        Index("ix_restaurant_outbox_due", "status", "scheduled_at"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "restaurant_idempotency_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(160))
    key: Mapped[str] = mapped_column(String(160))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="in_progress", index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_restaurant_idempotency_scope_key"),
        Index("ix_restaurant_idempotency_created", "created_at"),
    )


class CommerceEventOutbox(Base):
    __tablename__ = "restaurant_event_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(120), index=True)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(220), nullable=True, unique=True)
    publish_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("publish_attempts >= 0", name="ck_event_outbox_attempts_nonnegative"),
        Index("ix_restaurant_event_outbox_pending", "status", "occurred_at"),
    )


class WebhookReceipt(Base):
    __tablename__ = "restaurant_webhook_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(64))
    event_id: Mapped[str] = mapped_column(String(200))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_restaurant_webhook_provider_event"),
        Index("ix_restaurant_webhook_received", "received_at"),
    )

