from __future__ import annotations

from enum import StrEnum


class OrderStatus(StrEnum):
    AWAITING_PAYMENT = "awaiting_payment"
    PLACED = "placed"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReservationStatus(StrEnum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class FulfillmentType(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class DeliveryStatus(StrEnum):
    QUOTED = "quoted"
    REQUESTED = "requested"
    COURIER_ASSIGNED = "courier_assigned"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


PAYMENT_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.UNPAID: {PaymentStatus.PENDING, PaymentStatus.PAID, PaymentStatus.FAILED},
    PaymentStatus.PENDING: {PaymentStatus.PAID, PaymentStatus.FAILED},
    PaymentStatus.PAID: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}


RESERVATION_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.REQUESTED: {ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED},
    ReservationStatus.CONFIRMED: {ReservationStatus.SEATED, ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW},
    ReservationStatus.SEATED: {ReservationStatus.COMPLETED},
    ReservationStatus.COMPLETED: set(),
    ReservationStatus.CANCELLED: set(),
    ReservationStatus.NO_SHOW: set(),
}


DELIVERY_TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.QUOTED: {DeliveryStatus.REQUESTED, DeliveryStatus.COURIER_ASSIGNED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED},
    DeliveryStatus.REQUESTED: {DeliveryStatus.COURIER_ASSIGNED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED},
    DeliveryStatus.COURIER_ASSIGNED: {DeliveryStatus.PICKED_UP, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED},
    DeliveryStatus.PICKED_UP: {DeliveryStatus.DELIVERED, DeliveryStatus.FAILED},
    DeliveryStatus.DELIVERED: set(),
    DeliveryStatus.CANCELLED: set(),
    DeliveryStatus.FAILED: set(),
}


ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.AWAITING_PAYMENT: {OrderStatus.PLACED, OrderStatus.CANCELLED},
    OrderStatus.PLACED: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}
