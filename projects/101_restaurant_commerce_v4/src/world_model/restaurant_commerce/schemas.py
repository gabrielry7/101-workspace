from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DeliveryAddressIn(StrictModel):
    address_line: str = Field(min_length=3, max_length=500)
    city: str = Field(default="Bogotá", min_length=2, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    instructions: str | None = Field(default=None, max_length=1000)


class DeliveryQuoteRequest(StrictModel):
    destination: DeliveryAddressIn


class DeliveryQuoteOut(StrictModel):
    id: str
    business_id: str
    provider: str
    currency: str
    fee_minor: int
    distance_meters: int | None
    estimated_pickup_at: datetime | None
    estimated_dropoff_at: datetime | None
    expires_at: datetime
    destination_address: str
    destination_city: str


class DeliveryTrackingOut(StrictModel):
    order_id: str
    public_code: str
    status: str
    provider: str
    tracking_url: str | None
    courier_name: str | None
    estimated_pickup_at: datetime | None
    estimated_dropoff_at: datetime | None
    picked_up_at: datetime | None
    delivered_at: datetime | None


class DeliveryOut(StrictModel):
    id: str
    order_id: str
    quote_id: str
    provider: str
    provider_delivery_reference: str | None
    status: str
    currency: str
    fee_minor: int
    destination_address: str
    destination_city: str
    destination_latitude: float
    destination_longitude: float
    destination_instructions: str | None
    tracking_url: str | None
    courier_name: str | None
    courier_phone: str | None
    estimated_pickup_at: datetime | None
    estimated_dropoff_at: datetime | None
    dispatched_at: datetime | None
    picked_up_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime


class DeliveryStatusPatch(StrictModel):
    status: str = Field(min_length=2, max_length=32, pattern=r"^[a-z_]+$")


class DeliveryWebhookIn(StrictModel):
    provider_delivery_reference: str
    status: str
    event_id: str = Field(min_length=1, max_length=200)
    occurred_at: datetime | None = None

class ModifierSelectionIn(StrictModel):
    group_id: str
    option_ids: list[str] = Field(default_factory=list, max_length=50)


class CartItemIn(StrictModel):
    menu_item_id: str
    quantity: int = Field(ge=1, le=50)
    modifiers: list[ModifierSelectionIn] = Field(default_factory=list, max_length=50)


class QuoteRequest(StrictModel):
    items: list[CartItemIn] = Field(min_length=1, max_length=100)
    promo_code: str | None = Field(default=None, max_length=80)
    customer_phone: str | None = Field(default=None, max_length=40)
    reward_id: str | None = None


class QuotedModifier(StrictModel):
    group_id: str
    group_name: str
    option_id: str
    option_name: str
    price_delta_minor: int


class QuotedItem(StrictModel):
    menu_item_id: str
    name: str
    quantity: int
    unit_base_price_minor: int
    unit_modifier_price_minor: int
    line_total_minor: int
    modifiers: list[QuotedModifier]


class DiscountOut(StrictModel):
    promotion_code: str | None = None
    promotion_discount_minor: int = 0
    reward_id: str | None = None
    reward_name: str | None = None
    reward_discount_minor: int = 0
    total_discount_minor: int = 0


class QuoteResponse(StrictModel):
    business_id: str
    currency: str
    subtotal_minor: int
    total_minor: int
    items: list[QuotedItem]
    discounts: DiscountOut = Field(default_factory=DiscountOut)


class CustomerIn(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=320)
    whatsapp_opt_in: bool | None = None
    marketing_opt_in: bool | None = None
    consent_source: str | None = Field(default=None, max_length=64)

    @field_validator("phone")
    @classmethod
    def phone_must_contain_digits(cls, value: str) -> str:
        if sum(ch.isdigit() for ch in value) < 5:
            raise ValueError("phone must contain at least 5 digits")
        return value


class CreateOrderRequest(StrictModel):
    customer: CustomerIn
    items: list[CartItemIn] = Field(min_length=1, max_length=100)
    fulfillment_type: Literal["pickup", "delivery"] = "pickup"
    delivery_quote_id: str | None = None
    requested_pickup_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)
    payment_provider: str = Field(default="simulated", min_length=2, max_length=40, pattern=r"^[a-z0-9_:-]+$")
    source_channel: str = Field(default="web", min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9_.:-]+$")
    external_source_ref: str | None = Field(default=None, max_length=160)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)
    promo_code: str | None = Field(default=None, max_length=80)
    reward_id: str | None = None


class CreateReservationRequest(StrictModel):
    customer: CustomerIn
    starts_at: datetime
    party_size: int = Field(ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)
    source_channel: str = Field(default="web", min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9_.:-]+$")
    external_source_ref: str | None = Field(default=None, max_length=160)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class OrderStatusPatch(StrictModel):
    status: str = Field(min_length=2, max_length=32, pattern=r"^[a-z_]+$")


class ReservationStatusPatch(StrictModel):
    status: str = Field(min_length=2, max_length=32, pattern=r"^[a-z_]+$")


class ModifierOptionOut(StrictModel):
    id: str
    name: str
    price_delta_minor: int
    enabled: bool


class ModifierGroupOut(StrictModel):
    id: str
    name: str
    required: bool
    min_selections: int
    max_selections: int
    options: list[ModifierOptionOut]


class MenuItemOut(StrictModel):
    id: str
    name: str
    description: str | None
    base_price_minor: int
    currency: str
    image_url: str | None
    available: bool
    modifier_groups: list[ModifierGroupOut]


class MenuCategoryOut(StrictModel):
    id: str
    name: str
    description: str | None
    items: list[MenuItemOut]


class MenuOut(StrictModel):
    id: str
    name: str
    categories: list[MenuCategoryOut]


class RewardOut(StrictModel):
    id: str
    name: str
    description: str | None
    points_cost: int
    discount_minor: int
    minimum_order_minor: int
    enabled: bool


class StorefrontOut(StrictModel):
    business_id: str
    slug: str
    display_name: str
    currency: str
    timezone: str
    ordering_enabled: bool
    payment_provider: str
    cash_at_pickup_enabled: bool
    pickup_enabled: bool
    delivery_enabled: bool = False
    accepts_reservations: bool
    default_prep_minutes: int
    pickup_instructions: str | None
    delivery_provider: str | None = None
    delivery_max_distance_meters: int | None = None
    loyalty_enabled: bool = False
    menus: list[MenuOut]


class OrderItemModifierOut(StrictModel):
    group_name: str
    option_name: str
    price_delta_minor: int


class OrderItemOut(StrictModel):
    name: str
    quantity: int
    unit_base_price_minor: int
    unit_modifier_price_minor: int
    line_total_minor: int
    modifiers: list[OrderItemModifierOut]


class PaymentOut(StrictModel):
    provider: str
    provider_reference: str
    status: str
    amount_minor: int
    currency: str
    checkout_url: str | None


class OrderOut(StrictModel):
    id: str
    public_code: str
    business_id: str
    status: str
    payment_status: str
    fulfillment_type: str
    currency: str
    subtotal_minor: int
    promotion_discount_minor: int = 0
    reward_discount_minor: int = 0
    discount_minor: int = 0
    delivery_fee_minor: int = 0
    promotion_code: str | None = None
    reward_name: str | None = None
    total_minor: int
    prep_minutes: int
    requested_pickup_at: datetime | None
    notes: str | None
    source_channel: str
    external_source_ref: str | None
    created_at: datetime
    customer_name: str | None
    customer_phone: str
    items: list[OrderItemOut]
    payments: list[PaymentOut]
    delivery: DeliveryTrackingOut | None = None
    access_token: str | None = None


class ReservationOut(StrictModel):
    id: str
    public_code: str
    business_id: str
    status: str
    starts_at: datetime
    party_size: int
    notes: str | None
    source_channel: str
    external_source_ref: str | None
    customer_name: str | None
    customer_phone: str
    created_at: datetime


class CustomerSummaryOut(StrictModel):
    id: str
    name: str | None
    phone: str
    email: str | None
    order_count: int
    lifetime_value_minor: int
    last_order_at: datetime | None
    whatsapp_opt_in: bool = False
    marketing_opt_in: bool = False
    loyalty_points: int = 0


class LoyaltyAccountOut(StrictModel):
    customer_id: str
    business_id: str
    available_points: int
    lifetime_earned_points: int
    lifetime_redeemed_points: int
    rewards: list[RewardOut] = Field(default_factory=list)


class PromotionCreateIn(StrictModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    discount_type: Literal["fixed", "percent"] = "fixed"
    value: int = Field(gt=0)
    minimum_order_minor: int = Field(default=0, ge=0)
    maximum_discount_minor: int | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    per_customer_limit: int | None = Field(default=None, ge=1)
    total_redemption_limit: int | None = Field(default=None, ge=1)


class PromotionOut(StrictModel):
    id: str
    business_id: str
    code: str
    name: str
    discount_type: str
    value: int
    minimum_order_minor: int
    maximum_discount_minor: int | None
    starts_at: datetime | None
    ends_at: datetime | None
    per_customer_limit: int | None
    total_redemption_limit: int | None
    enabled: bool


class RewardCreateIn(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    points_cost: int = Field(gt=0)
    discount_minor: int = Field(gt=0)
    minimum_order_minor: int = Field(default=0, ge=0)


class AutomationRuleCreateIn(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    trigger_kind: Literal["order.completed.review_request", "customer.winback"]
    channel: Literal["whatsapp"] = "whatsapp"
    purpose: Literal["service_followup", "marketing"]
    delay_minutes: int = Field(default=0, ge=0, le=525600)
    template_text: str = Field(min_length=1, max_length=2000)


class AutomationRuleOut(StrictModel):
    id: str
    business_id: str
    name: str
    trigger_kind: str
    channel: str
    purpose: str
    delay_minutes: int
    template_text: str
    enabled: bool


class OutboundMessageOut(StrictModel):
    id: str
    business_id: str
    customer_id: str
    order_id: str | None
    channel: str
    purpose: str
    message_kind: str
    destination: str
    body: str
    scheduled_at: datetime
    status: str
    suppression_reason: str | None
    created_at: datetime
    sent_at: datetime | None


class MarkMessageSentIn(StrictModel):
    sent_at: datetime | None = None


class WinbackPlanIn(StrictModel):
    as_of: datetime | None = None
    dormant_days: int | None = Field(default=None, ge=1, le=3650)
    limit: int = Field(default=100, ge=1, le=1000)


class GrowthAnalyticsOut(StrictModel):
    business_id: str
    as_of: datetime
    completed_orders: int
    gross_revenue_minor: int
    discount_minor: int
    net_revenue_minor: int
    food_net_revenue_minor: int = 0
    delivery_fees_minor: int = 0
    unique_customers: int
    repeat_customers: int
    repeat_customer_rate: float
    average_order_value_minor: int
    loyalty_members: int
    loyalty_points_outstanding: int
    promotion_redemptions: int
    queued_messages: int
    suppressed_messages: int
    dormant_customers: int
    channel_order_counts: dict[str, int]


class PaymentWebhookIn(StrictModel):
    event_id: str = Field(min_length=1, max_length=200)
    provider_reference: str = Field(min_length=1, max_length=160)
    status: str = Field(min_length=2, max_length=32)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")


class CommerceCapabilityOut(StrictModel):
    business_id: str
    ordering_enabled: bool
    payment_provider: str
    cash_at_pickup_enabled: bool
    pickup_enabled: bool
    delivery_enabled: bool = False
    accepts_reservations: bool
    loyalty_enabled: bool = False
    marketing_automation_enabled: bool = False
    review_requests_enabled: bool = False
    storefront_endpoint: str
    quote_endpoint: str
    order_endpoint: str
    reservation_endpoint: str
    loyalty_endpoint: str | None = None
    analytics_endpoint: str | None = None
    delivery_quote_endpoint: str | None = None
    delivery_tracking_endpoint_template: str | None = None
