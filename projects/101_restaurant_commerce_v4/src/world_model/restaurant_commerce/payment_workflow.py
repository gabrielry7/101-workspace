"""Durable checkout processing; provider IO is outside the fenced DB transaction."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from .enums import OrderStatus, PaymentStatus
from .errors import (
    IdempotencyConflictError,
    NotFoundError,
    PaymentError,
    RetryableProviderError,
    ValidationError,
)
from .growth import RestaurantGrowthService
from .models import (
    Order,
    Payment,
    PaymentIntent,
    PaymentNotificationInbox,
    PaymentReconciliation,
    utcnow,
)
from .reliability import request_fingerprint, stage_event
from .schemas import PaymentNotificationAccepted, PaymentWebhookIn

RECOVERY_TTL_SECONDS = 24 * 60 * 60


class PaymentWorkflowMixin:
    def _reconciliation(self, order, reason, evidence):
        row = self.session.scalar(
            select(PaymentReconciliation).where(
                PaymentReconciliation.order_id == order.id,
                PaymentReconciliation.reason == reason,
            )
        )
        if row is not None:
            if (
                row.status == "open"
                and row.reason != "refund_evidence_review"
                and self._refund_evidence_review(row)
            ):
                # Retain legacy refund provenance before refreshing a generic hold.
                self._reconciliation(order, "refund_evidence_review", json.loads(row.evidence_json))
            if row.status != "open" or json.loads(row.evidence_json) != evidence:
                self._financial_audit(order, "system:provider", "reconciliation.updated", reason,
                    {"previous_evidence": json.loads(row.evidence_json), "new_evidence": evidence})
                row.status = "open"
                row.evidence_json = json.dumps(evidence, sort_keys=True)
                row.created_at = utcnow()  # Current episode; original history is retained in audit.
            return row
        row = PaymentReconciliation(
            order_id=order.id,
            business_id=order.business_id,
            reason=reason,
            evidence_json=json.dumps(evidence, sort_keys=True),
        )
        try:
            with self.session.begin_nested():
                self.session.add(row)
                self.session.flush()
                stage_event(
                    self.session,
                    kind="payment.reconciliation_required",
                    business_id=order.business_id,
                    entity_id=row.id,
                    payload={"order_id": order.id, "reason": reason},
                    dedupe_key=f"reconciliation:{order.id}:{reason}",
                )
        except IntegrityError:
            row = self.session.scalar(
                select(PaymentReconciliation).where(
                    PaymentReconciliation.order_id == order.id,
                    PaymentReconciliation.reason == reason,
                )
            )
            if row is None:
                raise
        return row

    def list_payment_reconciliation(self, business_id):
        rows = self.session.scalars(
            select(PaymentReconciliation)
            .where(
                PaymentReconciliation.business_id == business_id,
                PaymentReconciliation.status == "open",
            )
            .order_by(PaymentReconciliation.created_at)
            .limit(100)
        ).all()
        return [
            {
                "id": row.id,
                "order_id": row.order_id,
                "reason": row.reason,
                "status": row.status,
                "created_at": row.created_at,
                "evidence": json.loads(row.evidence_json),
            }
            for row in rows
        ]

    def recover_order(self, business_id, key, secret):
        intent = self.session.scalar(
            select(PaymentIntent)
            .join(Order, Order.id == PaymentIntent.order_id)
            .where(Order.business_id == business_id, Order.idempotency_key == key)
        )
        digest = hashlib.sha256(secret.encode()).hexdigest()
        if (
            not intent
            or not intent.recovery_secret_hash
            or not secrets.compare_digest(intent.recovery_secret_hash, digest)
        ):
            raise NotFoundError("Checkout recovery not found")
        order = self.session.get(Order, intent.order_id)
        created = intent.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if (
            order.access_token_version
            or (utcnow() - created).total_seconds() > RECOVERY_TTL_SECONDS
        ):
            # API maps this explicitly to410; valid recovery authority must not mint renewed access.
            raise CheckoutRecoveryExpired("Checkout recovery expired or was revoked")
        return self.order_out(order.id)

    def process_payment_intent(self, order_id, *, background=False):
        self.session.expire_all()
        intent = self.session.scalar(
            select(PaymentIntent).where(PaymentIntent.order_id == order_id)
        )
        if not intent or intent.state == "ready":
            return self.order_out(order_id)
        if intent.state in {"review_required", "cancelled"}:
            raise PaymentError(
                "Checkout requires staff review; do not submit a new order"
            )
        provider = self.payment_providers.get(intent.provider)
        now = utcnow()
        token = secrets.token_hex(24)
        conditions = [
            PaymentIntent.id == intent.id,
            PaymentIntent.state.in_(["pending", "unknown", "processing"]),
            or_(PaymentIntent.lease_until.is_(None), PaymentIntent.lease_until <= now),
        ]
        if background:
            conditions.append(
                or_(
                    PaymentIntent.next_attempt_at.is_(None),
                    PaymentIntent.next_attempt_at <= now,
                )
            )
        claimed = self.session.execute(
            update(PaymentIntent)
            .where(*conditions)
            .values(
                state="processing",
                lease_token=token,
                lease_until=now + timedelta(seconds=self.payment_lease_seconds),
                attempts=PaymentIntent.attempts + 1,
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if not claimed:
            self.session.rollback()
            if not background:
                # Another request/recovery worker owns this same durable intent.
                # Return its truthful pending/ready state, never a false conflict
                # or a second provider attempt. The caller already checked replay
                # authority and the immutable request fingerprint.
                return self.order_out(order_id)
            raise IdempotencyConflictError(
                "Checkout is processing; recover the existing order shortly"
            )
        self._commit()
        self.session.expire_all()
        intent = self.session.scalar(
            select(PaymentIntent).where(PaymentIntent.order_id == order_id)
        )
        order = self.session.get(Order, order_id)
        request = json.loads(intent.request_json)
        if provider is None:
            self._unknown_intent(order_id, token, "provider_unavailable", review=True)
            raise PaymentError(
                "Payment provider unavailable; durable checkout requires review"
            )
        # Never initiate a new checkout for an already cancelled order. Without a
        # provider lookup contract an uncertain cancelled attempt needs human review.
        if order.status == OrderStatus.CANCELLED.value:
            self._unknown_intent(
                order_id, token, "cancelled_checkout_unknown", review=True
            )
            raise PaymentError("Cancelled checkout requires review")
        if intent.attempts > 1 and not getattr(
            provider, "supports_idempotent_checkout", False
        ):
            self._unknown_intent(
                order_id, token, "provider_replay_not_supported", review=True
            )
            raise PaymentError("Provider cannot safely replay an uncertain checkout")
        # End read transaction before network IO, including PostgreSQL MVCC snapshot.
        self.session.rollback()

        def invoke():
            try:
                return provider.create_checkout(**request)
            except RetryableProviderError as exc:
                if not getattr(provider, "supports_idempotent_checkout", False):
                    raise PaymentError("Provider cannot safely retry checkout") from exc
                raise

        try:
            checkout = self.provider_executor.call(
                provider.name, "create_checkout", invoke
            )
        except Exception as exc:
            self._unknown_intent(order_id, token, type(exc).__name__)
            raise PaymentError(
                "Payment outcome unknown; recover the existing checkout"
            ) from exc

        try:
            status = PaymentStatus(checkout.status.lower())
            for value in (checkout.provider_reference, checkout.checkout_url):
                if value is not None:
                    if (
                        not isinstance(value, str)
                        or "\x00" in value
                        or len(value) > 4096
                    ):
                        raise ValueError("invalid provider text")
                    value.encode("utf-8", errors="strict")
            if (
                not isinstance(checkout.amount_minor, int)
                or isinstance(checkout.amount_minor, bool)
                or not isinstance(checkout.order_may_proceed, bool)
            ):
                raise TypeError("invalid provider scalar")
            if (
                checkout.provider != provider.name
                or not checkout.provider_reference.strip()
                or len(checkout.provider_reference) > 160
                or "\x00" in checkout.provider_reference
                or checkout.amount_minor != request["amount_minor"]
                or checkout.currency != request["currency"]
                or status
                in {PaymentStatus.FAILED, PaymentStatus.REFUNDED, PaymentStatus.UNPAID}
            ):
                raise ValueError("invalid checkout response")
        except (ValueError, AttributeError, TypeError) as exc:
            self._unknown_intent(
                order_id, token, "invalid_provider_response", review=True
            )
            raise PaymentError(
                "Invalid provider response; durable checkout requires review"
            ) from exc

        # Fence every local completion. A delayed previous owner must not write.
        fenced = self.session.execute(
            update(PaymentIntent)
            .where(
                PaymentIntent.order_id == order_id,
                PaymentIntent.lease_token == token,
                PaymentIntent.state == "processing",
            )
            .values(
                state="ready",
                lease_token=None,
                lease_until=None,
                next_attempt_at=None,
                last_error=None,
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if not fenced:
            self.session.rollback()
            raise IdempotencyConflictError("Checkout was recovered by another worker")
        self.session.expire_all()
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        payment = Payment(
            order_id=order.id,
            provider=checkout.provider,
            provider_reference=checkout.provider_reference,
            status=status.value,
            amount_minor=checkout.amount_minor,
            currency=checkout.currency,
            checkout_url=checkout.checkout_url,
        )
        self.session.add(payment)
        order.payment_status = status.value
        if order.status == OrderStatus.AWAITING_PAYMENT.value and (
            status == PaymentStatus.PAID or checkout.order_may_proceed
        ):
            order.status = OrderStatus.PLACED.value
        if status == PaymentStatus.PAID:
            if order.status == OrderStatus.CANCELLED.value:
                self._reconciliation(
                    order,
                    "paid_after_cancellation",
                    {"provider_reference": checkout.provider_reference},
                )
            else:
                growth = RestaurantGrowthService(self.session)
                growth.finalize_reward(order.id)
                growth.finalize_promotion(order.id)
        try:
            self._commit_event(
                kind="order.created",
                business_id=order.business_id,
                entity_id=order.id,
                payload={
                    "public_code": order.public_code,
                    "total_minor": order.total_minor,
                    "fulfillment_type": order.fulfillment_type,
                    "delivery_fee_minor": order.delivery_fee_minor,
                    "payment_provider": payment.provider,
                },
                dedupe_key=f"order-created:{order.id}",
            )
        except IntegrityError as exc:
            self.session.rollback()
            self._unknown_intent(
                order_id, token, "provider_reference_conflict", review=True
            )
            raise PaymentError(
                "Provider reference conflicts with another payment; review required"
            ) from exc
        self.drain_payment_notifications(provider_reference=checkout.provider_reference)
        return self.order_out(order.id)

    def _unknown_intent(self, order_id, token, error, *, review=False):
        self.session.rollback()
        changed = self.session.execute(
            update(PaymentIntent)
            .where(
                PaymentIntent.order_id == order_id, PaymentIntent.lease_token == token
            )
            .values(
                state="review_required" if review else "unknown",
                lease_token=None,
                lease_until=None,
                last_error=error[:120],
                next_attempt_at=utcnow()
                + timedelta(seconds=self.payment_retry_seconds),
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if changed and review:
            order = self.session.get(Order, order_id)
            self._reconciliation(order, error, {"order_id": order_id})
        self._commit()

    def recover_payments(self, *, limit=25):
        now = utcnow()
        ids = list(
            self.session.scalars(
                select(PaymentIntent.order_id)
                .where(
                    PaymentIntent.state.in_(["pending", "unknown", "processing"]),
                    or_(
                        PaymentIntent.lease_until.is_(None),
                        PaymentIntent.lease_until <= now,
                    ),
                    or_(
                        PaymentIntent.next_attempt_at.is_(None),
                        PaymentIntent.next_attempt_at <= now,
                    ),
                )
                .order_by(
                    func.coalesce(
                        PaymentIntent.next_attempt_at, PaymentIntent.created_at
                    ),
                    PaymentIntent.id,
                )
                .limit(limit)
            )
        )
        self.session.rollback()
        result = {"examined": len(ids), "recovered": 0, "deferred": 0}
        for order_id in ids:
            try:
                self.process_payment_intent(order_id, background=True)
                result["recovered"] += 1
            except (PaymentError, IdempotencyConflictError):
                self.session.rollback()
                result["deferred"] += 1
        result["notifications"] = self.drain_payment_notifications(limit=limit)
        return result

    def receive_payment_notification(self, provider, payload: PaymentWebhookIn):
        # Additive optional refund fields must not change historical callback identity.
        body = payload.model_dump(mode="json", exclude_none=True)
        fingerprint = request_fingerprint(body)
        row = self.session.scalar(
            select(PaymentNotificationInbox).where(
                PaymentNotificationInbox.provider == provider,
                PaymentNotificationInbox.event_id == payload.event_id,
            )
        )
        if row is None:
            try:
                with self.session.begin_nested():
                    row = PaymentNotificationInbox(
                        provider=provider,
                        event_id=payload.event_id,
                        provider_reference=payload.provider_reference,
                        payload_sha256=fingerprint,
                        payload_json=json.dumps(body, sort_keys=True),
                    )
                    self.session.add(row)
                    self.session.flush()
            except IntegrityError:
                row = self.session.scalar(
                    select(PaymentNotificationInbox).where(
                        PaymentNotificationInbox.provider == provider,
                        PaymentNotificationInbox.event_id == payload.event_id,
                    )
                )
                if row is None:
                    raise
        if row.payload_sha256 != fingerprint:
            raise IdempotencyConflictError(
                "Webhook event ID was reused with a different payload"
            )
        row_id = row.id
        self._commit()
        try:
            return self._process_payment_notification(row_id)
        except NotFoundError:
            self.session.rollback()
            return PaymentNotificationAccepted(notification_id=row_id)

    def _process_payment_notification(self, row_id):
        row = self.session.get(PaymentNotificationInbox, row_id)
        body = json.loads(row.payload_json)
        if body['status'] == 'partially_refunded':
            from .refunds import record_refund
            result = record_refund(self, row.provider, body, row.payload_json)
        else:
            result = self.apply_payment_status(
                body["provider_reference"],
                body["status"],
                provider=row.provider,
                event_id=row.event_id,
                amount_minor=body["amount_minor"],
                currency=body["currency"],
                raw_event_json=row.payload_json,
            )
        row = self.session.get(PaymentNotificationInbox, row_id)
        row.state = "processed"
        row.processed_at = utcnow()
        self._commit()
        return result

    def drain_payment_notifications(self, *, provider_reference=None, limit=25):
        stmt = (
            select(PaymentNotificationInbox.id)
            .join(
                Payment,
                (
                    Payment.provider_reference
                    == PaymentNotificationInbox.provider_reference
                )
                & (Payment.provider == PaymentNotificationInbox.provider),
            )
            .where(PaymentNotificationInbox.state == "pending")
        )
        if provider_reference:
            stmt = stmt.where(
                PaymentNotificationInbox.provider_reference == provider_reference
            )
        ids = list(
            self.session.scalars(
                stmt.order_by(PaymentNotificationInbox.created_at).limit(limit)
            )
        )
        processed = 0
        for row_id in ids:
            try:
                self._process_payment_notification(row_id)
                processed += 1
            except NotFoundError:
                self.session.rollback()
            except (PaymentError, ValidationError, IdempotencyConflictError) as exc:
                self.session.rollback()
                row = self.session.get(PaymentNotificationInbox, row_id)
                row.state = "review_required"
                row.last_error = type(exc).__name__
                payment = self.session.scalar(
                    select(Payment).where(
                        Payment.provider == row.provider,
                        Payment.provider_reference == row.provider_reference,
                    )
                )
                if payment:
                    order = self.session.get(Order, payment.order_id)
                    self._reconciliation(
                        order,
                        "invalid_payment_notification",
                        {"notification_id": row.id, "error": row.last_error},
                    )
                self._commit()
        return processed


class CheckoutRecoveryExpired(Exception):
    pass
