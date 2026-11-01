"""Durable controlled-provider lookup/refund and evidence-bound resolution."""

import json
import re
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from .errors import (
    IdempotencyConflictError,
    NotFoundError,
    PaymentError,
    ValidationError,
)
from .financial_auth import FinancialPrincipal
from .models import (
    FinancialAudit,
    FinancialOperation,
    Order,
    Payment,
    PaymentIntent,
    PaymentReconciliation,
    utcnow,
)


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


class FinancialWorkflowMixin:
    @staticmethod
    def _refund_evidence_review(row):
        # Preserve holds created before the dedicated refund-evidence reason existed.
        return row.reason == "refund_evidence_review" or (
            row.reason == "wompi_provider_review"
            and json.loads(row.evidence_json).get("reason") == "provider_refund_observed"
        )

    def _financial_order(self, business_id, order_id, principal, permission):
        if not isinstance(principal, FinancialPrincipal) or not principal.permits(
            business_id, permission
        ):
            raise ValidationError("Named, scoped financial authority is required")
        order = self.session.get(Order, order_id)
        if not order or order.business_id != business_id:
            raise NotFoundError("Order not found")
        return order

    def _financial_audit(self, order, actor, action, reason, evidence, operation_id=None):
        self.session.add(
            FinancialAudit(
                business_id=order.business_id,
                order_id=order.id,
                actor_id=actor,
                action=action,
                reason=reason,
                evidence_json=_json(evidence),
                operation_id=operation_id,
            )
        )

    def financial_history(self, business_id, order_id, principal):
        order = self._financial_order(business_id, order_id, principal, "finance.read")
        intent = self.session.scalar(
            select(PaymentIntent).where(PaymentIntent.order_id == order_id)
        )
        provider = self.financial_providers.get(intent.provider) if intent else None
        available = bool(
            provider
            and getattr(provider, "controlled", False) is True
            and getattr(provider, "business_id", business_id) == business_id
        )
        operations = self.session.scalars(
            select(FinancialOperation)
            .where(FinancialOperation.order_id == order_id)
            .order_by(FinancialOperation.created_at)
        ).all()
        audits = self.session.scalars(
            select(FinancialAudit)
            .where(FinancialAudit.order_id == order_id)
            .order_by(FinancialAudit.created_at)
        ).all()
        return {
            "capabilities": {
                "lookup": available and principal.permits(business_id, "finance.lookup"),
                "inspect_refund": available
                and callable(getattr(provider, "inspect_refund", None))
                and principal.permits(business_id, "finance.lookup"),
                "refund": available
                and getattr(provider, "refund_enabled", False) is True
                and order.payment_status == "paid"
                and principal.permits(business_id, "finance.refund"),
                "refund_block_reason": getattr(
                    provider, "refund_block_reason", "refund_unavailable"
                )
                if available
                else "financial_provider_unavailable",
            },
            "operations": [self._operation_out(o) for o in operations],
            "reviews": [
                {
                    "id": r.id,
                    "reason": r.reason,
                    "status": r.status,
                    "resolvable": not self._refund_evidence_review(r)
                    or (available and getattr(provider, "refund_enabled", False) is True),
                }
                for r in self.session.scalars(
                    select(PaymentReconciliation).where(PaymentReconciliation.order_id == order_id)
                )
            ],
            "audit": [
                {
                    "id": a.id,
                    "actor_id": a.actor_id,
                    "action": a.action,
                    "reason": a.reason,
                    "evidence": json.loads(a.evidence_json),
                    "created_at": a.created_at,
                }
                for a in audits
            ],
        }

    @staticmethod
    def _operation_out(op):
        return {
            "id": op.id,
            "order_id": op.order_id,
            "kind": op.kind,
            "state": op.state,
            "actor_id": op.actor_id,
            "reason": op.reason,
            "attempts": op.attempts,
            "result": json.loads(op.result_json) if op.result_json else None,
            "created_at": op.created_at,
        }

    def request_financial_operation(
        self, business_id, order_id, kind, key, reason, principal, *, refund_reference=None
    ):
        if kind not in {"lookup", "refund"}:
            raise ValidationError("Unsupported financial operation")
        order = self._financial_order(business_id, order_id, principal, "finance." + kind)
        if refund_reference is not None and (
            kind != "lookup"
            or not isinstance(refund_reference, str)
            or not re.fullmatch(r"[1-9][0-9]{0,19}", refund_reference)
        ):
            raise ValidationError("A numeric refund reference is supported only for lookup")
        if not reason.strip() or len(reason) > 500 or not key or len(key) > 100:
            raise ValidationError("A bounded reason and idempotency key are required")
        # A full refund can have only one intent, regardless of clicks or client keys.
        dedupe = f"refund:{order_id}" if kind == "refund" else f"lookup:{business_id}:{key}"
        existing = self.session.scalar(
            select(FinancialOperation).where(FinancialOperation.dedupe_key == dedupe)
        )
        if existing:
            if (
                existing.order_id != order_id
                or json.loads(existing.request_json).get("refund_reference") != refund_reference
            ):
                raise IdempotencyConflictError("Financial key belongs to another order")
            return self.process_financial_operation(existing.id)
        payment = self.session.scalar(
            select(Payment)
            .where(Payment.order_id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        intent = self.session.scalar(
            select(PaymentIntent)
            .where(PaymentIntent.order_id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not intent:
            raise PaymentError("Historical checkout requires offline provider evidence review")
        provider = self.financial_providers.get(intent.provider)
        if (
            not provider
            or provider.name != intent.provider
            or getattr(provider, "controlled", False) is not True
            or getattr(provider, "business_id", business_id) != business_id
        ):
            raise PaymentError(
                "Controlled financial provider is not configured; live actions are disabled"
            )
        if kind == "refund" and getattr(provider, "refund_enabled", False) is not True:
            raise PaymentError("Refund submission is disabled; inspect provider evidence instead")
        if refund_reference is not None and not callable(getattr(provider, "inspect_refund", None)):
            raise PaymentError("Refund inspection is not supported by this provider")
        if kind == "refund" and (not payment or payment.status != "paid"):
            raise PaymentError("Only a confirmed paid payment can be refunded")
        lease = intent.lease_until
        if lease and (lease.replace(tzinfo=UTC) if lease.tzinfo is None else lease) > utcnow():
            raise IdempotencyConflictError(
                "Checkout is still processing; recover before financial action"
            )
        # Stop ambiguous checkout replay while lookup establishes authoritative state.
        if not payment:
            intent.state = "review_required"
            intent.lease_token = None
            intent.lease_until = None
        request = {
            "order_id": order_id,
            "provider": intent.provider,
            "provider_reference": payment.provider_reference if payment else None,
            "amount_minor": order.total_minor,
            "currency": order.currency,
            "checkout_key": intent.provider_idempotency_key,
            "refund_reference": refund_reference,
        }
        op = FinancialOperation(
            business_id=business_id,
            order_id=order_id,
            kind=kind,
            dedupe_key=dedupe,
            actor_id=principal.actor_id,
            reason=reason.strip(),
            request_json=_json(request),
        )
        self.session.add(op)
        try:
            self.session.flush()
            self._reconciliation(
                order,
                "refund_in_progress" if kind == "refund" else "financial_lookup",
                {"operation_id": op.id},
            )
            self._financial_audit(
                order, principal.actor_id, kind + ".requested", reason, request, op.id
            )
            self._commit()
        except IntegrityError:
            self.session.rollback()
            op = self.session.scalar(
                select(FinancialOperation).where(FinancialOperation.dedupe_key == dedupe)
            )
            if (
                not op
                or op.order_id != order_id
                or json.loads(op.request_json).get("refund_reference") != refund_reference
            ):
                raise IdempotencyConflictError("Concurrent financial request conflict") from None
        return self.process_financial_operation(op.id)

    @staticmethod
    def _validate_observation(result, request, kind):
        data = asdict(result)
        text_fields = {"order_id", "provider_reference", "currency", "status", "evidence_id"}
        if kind == "refund":
            text_fields.add("refund_reference")
        if any(type(data.get(k)) is not str for k in text_fields):
            raise ValueError("Provider evidence identifiers must be text")
        for value in data.values():
            if isinstance(value, str):
                value.encode("utf-8", errors="strict")
                if not value or len(value) > 500 or "\x00" in value:
                    raise ValueError("invalid provider text")
        if (
            type(data["amount_minor"]) is not int
            or data["amount_minor"] != request["amount_minor"]
            or data["currency"] != request["currency"]
            or data["order_id"] != request["order_id"]
            or not data.get("evidence_id")
            or not isinstance(data.get("provider_reference"), str)
            or (
                request["provider_reference"]
                and data["provider_reference"] != request["provider_reference"]
            )
        ):
            raise ValueError("Provider evidence does not match immutable intent")
        allowed = (
            {"succeeded", "pending", "failed"}
            if kind == "refund"
            else {"paid", "pending", "failed", "refunded", "review_required"}
        )
        if data["status"] not in allowed or (
            kind == "refund" and not isinstance(data.get("refund_reference"), str)
        ):
            raise ValueError("Unsupported provider outcome")
        return data

    def process_financial_operation(self, operation_id):
        self.session.expire_all()
        op = self.session.get(FinancialOperation, operation_id)
        if not op:
            raise NotFoundError("Financial operation not found")
        if op.state in {"succeeded", "failed", "review_required", "withdrawn"}:
            return self._operation_out(op)
        configured = self.financial_providers.get(json.loads(op.request_json)["provider"])
        delay = getattr(configured, "retry_delay_seconds", 0)
        due = op.next_attempt_at
        if (
            delay
            and op.attempts
            and due
            and (due.replace(tzinfo=UTC) if due.tzinfo is None else due) > utcnow()
        ):
            return self._operation_out(op)
        now, token = utcnow(), secrets.token_hex(24)
        claimed = self.session.execute(
            update(FinancialOperation)
            .where(
                FinancialOperation.id == op.id,
                FinancialOperation.state.in_(["pending", "unknown", "processing"]),
                or_(
                    not bool(delay),
                    FinancialOperation.attempts == 0,
                    FinancialOperation.next_attempt_at.is_(None),
                    FinancialOperation.next_attempt_at <= now,
                ),
                or_(
                    FinancialOperation.lease_until.is_(None), FinancialOperation.lease_until <= now
                ),
            )
            .values(
                state="processing",
                lease_token=token,
                lease_until=now + timedelta(seconds=self.payment_lease_seconds),
                attempts=FinancialOperation.attempts + 1,
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if not claimed:
            self.session.rollback()
            return self._operation_out(self.session.get(FinancialOperation, operation_id))
        self._commit()
        self.session.expire_all()
        op = self.session.get(FinancialOperation, operation_id)
        request, kind, attempts = json.loads(op.request_json), op.kind, op.attempts
        business_id = op.business_id
        provider = self.financial_providers.get(request["provider"])
        self.session.rollback()  # No DB transaction across provider IO.
        query_started_at = utcnow().isoformat()
        state, data = "unknown", {"error": "provider_unavailable"}
        try:
            if (
                not provider
                or provider.name != request["provider"]
                or getattr(provider, "controlled", False) is not True
                or getattr(provider, "business_id", business_id) != business_id
            ):
                state = "review_required"
            elif attempts > getattr(provider, "max_financial_attempts", 100):
                state, data = "review_required", {"error": "financial_attempt_budget_exhausted"}
            elif kind == "refund" and getattr(provider, "refund_enabled", False) is not True:
                state, data = "review_required", {"error": "refund_submission_disabled"}
            else:
                if kind == "lookup":
                    if request.get("refund_reference"):
                        result = provider.inspect_refund(
                            order_id=request["order_id"],
                            provider_reference=request["provider_reference"],
                            refund_reference=request["refund_reference"],
                        )
                    else:
                        result = provider.lookup_payment(
                            order_id=request["order_id"],
                            idempotency_key=request["checkout_key"],
                            provider_reference=request["provider_reference"],
                        )
                else:
                    provider_key = "refund:" + operation_id
                    result = provider.lookup_refund(idempotency_key=provider_key)
                    if result is None:
                        payment = self.session.scalar(
                            select(Payment)
                            .where(Payment.order_id == request["order_id"])
                            .execution_options(populate_existing=True)
                        )
                        paid = payment is not None and payment.status == "paid"
                        self.session.rollback()
                        if not paid:
                            return self._finish_financial(
                                operation_id,
                                token,
                                "review_required",
                                {
                                    "error": "payment_changed_before_refund",
                                    "query_started_at": query_started_at,
                                },
                            )
                        if (
                            attempts > 1
                            and getattr(provider, "supports_idempotent_refund", False) is not True
                        ):
                            return self._finish_financial(
                                operation_id,
                                token,
                                "review_required",
                                {"error": "refund_replay_unsupported"},
                            )
                        result = provider.refund(
                            order_id=request["order_id"],
                            provider_reference=request["provider_reference"],
                            amount_minor=request["amount_minor"],
                            currency=request["currency"],
                            idempotency_key=provider_key,
                        )
                if result is not None:
                    data = self._validate_observation(result, request, kind)
                    state = (
                        "review_required"
                        if data["status"] == "review_required"
                        else "unknown"
                        if data["status"] == "pending"
                        else "failed"
                        if kind == "refund" and data["status"] == "failed"
                        else "succeeded"
                    )
                else:
                    data = {"error": "provider_outcome_unknown"}
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
            state, data = "review_required", {"error": "invalid_financial_evidence"}
        except Exception as exc:  # noqa: BLE001 - provider uncertainty; retain only exception type.
            data = {"error": type(exc).__name__}
        data["query_started_at"] = query_started_at
        if state == "unknown" and attempts >= getattr(provider, "max_financial_attempts", 100):
            state, data["error"] = "review_required", "financial_attempt_budget_exhausted"
        return self._finish_financial(operation_id, token, state, data)

    def _finish_financial(self, operation_id, token, state, data):
        current = self.session.get(FinancialOperation, operation_id)
        adapter = self.financial_providers.get(json.loads(current.request_json)["provider"])
        delay = max(
            2, min(300, getattr(adapter, "retry_delay_seconds", 0) * 2 ** min(current.attempts, 6))
        )
        # Fence before staging any monetary, benefit, audit or hold changes.
        changed = self.session.execute(
            update(FinancialOperation)
            .where(
                FinancialOperation.id == operation_id,
                FinancialOperation.lease_token == token,
                FinancialOperation.state == "processing",
            )
            .values(
                state=state,
                result_json=_json(data),
                lease_token=None,
                lease_until=None,
                next_attempt_at=utcnow() + timedelta(seconds=delay),
            ),
            execution_options={"synchronize_session": False},
        ).rowcount
        if not changed:
            self.session.rollback()
            return self._operation_out(self.session.get(FinancialOperation, operation_id))
        self.session.expire_all()
        op = self.session.get(FinancialOperation, operation_id)
        request = json.loads(op.request_json)
        payment = self.session.scalar(
            select(Payment)
            .where(Payment.order_id == op.order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order = self.session.scalar(
            select(Order)
            .where(Order.id == op.order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if state == "review_required" and (
            data.get("refund_reference")
            or data.get("review_reason") == "refund_evidence_requires_review"
        ):
            self._reconciliation(order, "refund_evidence_review", {**data, "operation_id": op.id})
        if state == "succeeded":
            target = "refunded" if op.kind == "refund" else data["status"]
            if payment and (
                payment.provider_reference != data["provider_reference"]
                or (payment.status == "refunded" and target != "refunded")
                or (payment.status == "paid" and target not in {"paid", "refunded"})
            ):
                op.state = "review_required"
                self._reconciliation(order, "contradictory_financial_evidence", data)
            else:
                if not payment:
                    # Unique provider reference prevents binding someone else's payment.
                    other = self.session.scalar(
                        select(Payment).where(
                            Payment.provider_reference == data["provider_reference"]
                        )
                    )
                    if other:
                        op.state = "review_required"
                        self._reconciliation(order, "provider_reference_conflict", data)
                    else:
                        payment = Payment(
                            order_id=order.id,
                            provider=request["provider"],
                            provider_reference=data["provider_reference"],
                            amount_minor=request["amount_minor"],
                            currency=request["currency"],
                            status="pending",
                        )
                        self.session.add(payment)
                        self.session.flush()
                if op.state == "succeeded":
                    # Only supported state transitions; a refund with no observed paid
                    # state remains review, rather than guessing historical settlement.
                    from .enums import PAYMENT_TRANSITIONS, PaymentStatus

                    current = PaymentStatus(payment.status)
                    if (
                        target != current.value
                        and PaymentStatus(target) not in PAYMENT_TRANSITIONS[current]
                    ):
                        op.state = "review_required"
                        self._reconciliation(order, "contradictory_financial_evidence", data)
                    else:
                        intent = self.session.scalar(
                            select(PaymentIntent).where(PaymentIntent.order_id == order.id)
                        )
                        intent.state, intent.lease_token, intent.lease_until = "ready", None, None
                        self._financial_audit(
                            order, op.actor_id, op.kind + ".succeeded", op.reason, data, op.id
                        )
                        # apply_payment_status commits these staged operation/audit
                        # writes together with settlement and benefit compensation.
                        self.apply_payment_status(
                            payment.provider_reference,
                            target,
                            provider=payment.provider,
                            event_id="financial:" + op.id,
                            amount_minor=payment.amount_minor,
                            currency=payment.currency,
                            raw_event_json=_json(data),
                        )
                        return self._operation_out(
                            self.session.get(FinancialOperation, operation_id)
                        )
        self._financial_audit(order, op.actor_id, op.kind + "." + op.state, op.reason, data, op.id)
        self._commit()
        return self._operation_out(self.session.get(FinancialOperation, operation_id))

    def recover_financial_operations(self, *, limit=25):
        now = utcnow()
        ids = list(
            self.session.scalars(
                select(FinancialOperation.id)
                .where(
                    FinancialOperation.state.in_(["pending", "unknown", "processing"]),
                    or_(
                        FinancialOperation.lease_until.is_(None),
                        FinancialOperation.lease_until <= now,
                    ),
                    or_(
                        FinancialOperation.next_attempt_at.is_(None),
                        FinancialOperation.next_attempt_at <= now,
                    ),
                )
                .order_by(
                    func.coalesce(FinancialOperation.next_attempt_at, FinancialOperation.created_at)
                )
                .limit(limit)
            )
        )
        dispatched, per_provider = 0, {}
        for operation_id in ids:
            op = self.session.get(FinancialOperation, operation_id)
            provider_name = json.loads(op.request_json)["provider"]
            adapter = self.financial_providers.get(provider_name)
            if per_provider.get(provider_name, 0) >= getattr(
                adapter, "max_recovery_operations", limit
            ):
                continue
            per_provider[provider_name] = per_provider.get(provider_name, 0) + 1
            dispatched += 1
            try:
                self.process_financial_operation(operation_id)
            except Exception:  # noqa: BLE001 - rollback and retry expired durable lease.
                self.session.rollback()
        return dispatched

    def resolve_financial_review(
        self, business_id, order_id, reconciliation_id, operation_id, reason, principal
    ):
        self._financial_order(business_id, order_id, principal, "finance.resolve")
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = self.session.scalar(
            select(PaymentReconciliation)
            .where(
                PaymentReconciliation.id == reconciliation_id,
                PaymentReconciliation.order_id == order_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        op = self.session.get(FinancialOperation, operation_id)
        if not row or not op or op.order_id != order_id:
            raise NotFoundError("Resolution evidence not found")
        evidence = json.loads(op.result_json or "{}")
        withdrawal = (
            op.kind == "refund"
            and op.state in {"failed", "withdrawn"}
            and evidence.get("status") == "failed"
            and row.reason == "refund_in_progress"
        )
        if not reason.strip() or len(reason) > 500 or (op.state != "succeeded" and not withdrawal):
            raise ValidationError("Confirmed provider evidence and a reason are required")
        # A pending checkout or a cancelled+paid order cannot be wished away.
        confirmed = (
            "paid" if withdrawal else "refunded" if op.kind == "refund" else evidence.get("status")
        )
        adapter = self.financial_providers.get(json.loads(op.request_json)["provider"])
        if self._refund_evidence_review(row) and (
            confirmed != "refunded" or getattr(adapter, "refund_enabled", False) is not True
        ):
            raise PaymentError("Unresolved refund evidence requires qualified refund confirmation")
        refund = self.session.scalar(
            select(FinancialOperation).where(
                FinancialOperation.order_id == order_id, FinancialOperation.kind == "refund"
            )
        )
        if refund and confirmed != "refunded" and not withdrawal:
            raise PaymentError("Refund must be confirmed before its financial hold can be resolved")
        if (
            confirmed not in {"paid", "failed", "refunded"}
            or order.payment_status != confirmed
            or (order.status == "cancelled" and confirmed == "paid")
        ):
            raise PaymentError("Financial contradiction remains unresolved")
        try:
            op_time = datetime.fromisoformat(evidence["query_started_at"])
        except (KeyError, ValueError, TypeError):
            raise PaymentError("Provider observation lacks a verified query timestamp") from None
        row_time = (
            row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at
        )
        if op_time < row_time:
            raise PaymentError("Provider evidence predates this review; obtain a new lookup")
        if row.status == "open":
            if withdrawal:
                op.state = "withdrawn"
            row.status = "resolved"
            self._financial_audit(
                order,
                principal.actor_id,
                "reconciliation.resolved",
                reason,
                {"reconciliation_id": row.id, "provider_evidence": evidence},
                op.id,
            )
            self._commit()
        return {"id": row.id, "status": row.status}
