"""Financial adapter contracts. Only explicitly controlled adapters run in M3b.

Observations must be full-payment/full-refund evidence, not inferred from HTTP200.
None means UNKNOWN, including not-found responses; it never authorizes failure.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentObservation:
    order_id: str
    provider_reference: str
    amount_minor: int
    currency: str
    status: str
    evidence_id: str
    review_reason: str | None = None
    refund_reference: str | None = None
    refund_amount_minor: int | None = None
    refund_status: str | None = None
    refund_sandbox: bool | None = None


@dataclass(frozen=True)
class RefundObservation:
    order_id: str
    provider_reference: str
    amount_minor: int
    currency: str
    status: str
    evidence_id: str
    refund_reference: str


class FinancialProvider(Protocol):
    name: str
    controlled: bool
    supports_idempotent_refund: bool
    refund_enabled: bool

    def lookup_payment(
        self, *, order_id: str, idempotency_key: str, provider_reference: str | None
    ) -> PaymentObservation | None: ...

    def lookup_refund(self, *, idempotency_key: str) -> RefundObservation | None: ...

    def refund(
        self,
        *,
        order_id: str,
        provider_reference: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> RefundObservation: ...
