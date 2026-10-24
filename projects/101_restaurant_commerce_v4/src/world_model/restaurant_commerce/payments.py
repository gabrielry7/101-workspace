from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from .errors import PaymentError


@dataclass(frozen=True)
class PaymentCheckout:
    provider: str
    provider_reference: str
    amount_minor: int
    currency: str
    status: str
    checkout_url: str | None = None
    order_may_proceed: bool = False


class PaymentProvider(Protocol):
    name: str

    def create_checkout(
        self,
        *,
        order_id: str,
        public_code: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        idempotency_key: str = "",
    ) -> PaymentCheckout: ...


class SimulatedPaymentProvider:
    """Deterministic local provider. It never makes network calls."""

    name = "simulated"

    def create_checkout(
        self,
        *,
        order_id: str,
        public_code: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        idempotency_key: str = "",
    ) -> PaymentCheckout:
        reference = f"sim_{order_id}"
        return PaymentCheckout(
            provider=self.name,
            provider_reference=reference,
            amount_minor=amount_minor,
            currency=currency,
            status="pending",
            checkout_url=f"/demo/pay/{reference}",
        )


class CashAtPickupPaymentProvider:
    name = "cash_at_pickup"

    def create_checkout(
        self,
        *,
        order_id: str,
        public_code: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        idempotency_key: str = "",
    ) -> PaymentCheckout:
        return PaymentCheckout(
            provider=self.name,
            provider_reference=f"cash_{order_id}",
            amount_minor=amount_minor,
            currency=currency,
            status="pending",
            checkout_url=None,
            order_may_proceed=True,
        )


class WompiPaymentProvider:
    """Production boundary for Wompi.

    This bundle intentionally does not make live Wompi requests because the exact
    checkout/webhook contract should be wired against 101's secrets/config layer.
    The class exists so commerce code depends on PaymentProvider rather than Wompi.
    """

    name = "wompi"

    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured

    def create_checkout(
        self,
        *,
        order_id: str,
        public_code: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        idempotency_key: str = "",
    ) -> PaymentCheckout:
        if not self.configured:
            raise PaymentError(
                "Wompi is an integration boundary in V4 but is not configured for live calls."
            )
        raise PaymentError(
            "Live Wompi checkout intentionally not implemented in this V4 drop-in bundle."
        )
