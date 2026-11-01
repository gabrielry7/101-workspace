"""Audited, read-only Wompi sandbox financial evidence.

The current refund API contradicts its published simulator contract and does not
provide proven idempotent submission/recovery. No refund POST exists here. Reads
of refund evidence never promote a payment to refunded while refund writes remain unqualified.
"""

import re

from .errors import PaymentError
from .financial_providers import PaymentObservation
from .wompi_sandbox import NAME, WompiSandboxProvider


class WompiSandboxFinancialProvider:
    name = NAME
    controlled = True
    sandbox_only = True
    refund_enabled = False
    supports_idempotent_refund = False
    refund_block_reason = "wompi_refund_contract_unverified"
    max_financial_attempts = 6
    retry_delay_seconds = 5
    max_recovery_operations = 1

    def __init__(self, payments):
        if not isinstance(payments, WompiSandboxProvider):
            raise ValueError("A sandbox payment adapter is required")
        self.payments = payments
        self.business_id = payments.business_id

    def _bound(self, txid, order_id, reference):
        expected = self.payments.reference(order_id)
        if reference is not None and reference != expected:
            raise ValueError("Financial reference mismatch")
        tx = self.payments.transaction(txid)
        if tx["order_id"] != order_id or tx["reference"] != expected:
            raise ValueError("Financial transaction does not belong to order")
        return tx

    @staticmethod
    def _observation(tx, **extra):
        return PaymentObservation(
            order_id=tx["order_id"],
            provider_reference=tx["reference"],
            amount_minor=tx["amount_minor"],
            currency=tx["currency"],
            status=tx["status"],
            evidence_id="wompi:transaction:" + tx["id"],
            **extra,
        )

    def lookup_payment(self, *, order_id, idempotency_key, provider_reference):
        if provider_reference is not None and provider_reference != self.payments.reference(
            order_id
        ):
            raise ValueError("Financial reference mismatch")
        ids = self.payments.transactions_for_order(order_id)
        if not ids:
            return None  # Empty evidence never authorizes a failed payment.
        if len(ids) != 1:
            raise ValueError("Multiple transactions require investigation")
        tx = self._bound(ids[0], order_id, provider_reference)
        reason = None
        if tx["status"] == "review_required":
            reason = (
                "refund_evidence_requires_review"
                if tx["refunds_observed"]
                else "unsupported_provider_status"
            )
        return self._observation(tx, review_reason=reason)

    def inspect_refund(self, *, order_id, provider_reference, refund_reference):
        if not isinstance(refund_reference, str) or not re.fullmatch(
            r"[1-9][0-9]{0,19}", refund_reference
        ):
            raise ValueError("Invalid refund identifier")
        data = self.payments._get("/refunds/" + refund_reference)
        identifier = data.get("id")
        if type(identifier) not in (int, str) or str(identifier) != refund_reference:
            raise ValueError("Refund identifier mismatch")
        tx = self._bound(data.get("transaction_id"), order_id, provider_reference)
        cents, status, sandbox = (
            data.get("amount_in_cents"),
            data.get("status"),
            data.get("is_sandbox"),
        )
        if (
            type(cents) is not int
            or cents <= 0
            or cents % 100
            or not isinstance(status, str)
            or status not in {"APPROVED", "PENDING", "DECLINED", "ERROR", "CANCELLED"}
            or (sandbox is not None and type(sandbox) is not bool)
        ):
            raise ValueError("Invalid refund evidence")
        reason = (
            "refund_environment_unverified"
            if sandbox is not True
            else "refund_amount_mismatch"
            if cents != tx["amount_minor"] * 100
            else "wompi_refund_contract_unverified"
        )
        # A reported APPROVED refund is visible evidence, not settlement authority.
        tx = {**tx, "status": "review_required"}
        return self._observation(
            tx,
            review_reason=reason,
            refund_reference=refund_reference,
            refund_amount_minor=cents // 100,
            refund_status=status,
            refund_sandbox=sandbox,
        )

    def lookup_refund(self, *, idempotency_key):
        raise PaymentError("Wompi refund recovery by local key is not qualified")

    def refund(self, **kwargs):
        raise PaymentError(
            "Wompi refund writes are disabled pending provider contract verification"
        )
