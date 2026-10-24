from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import IdempotencyConflictError, ProviderCircuitOpenError, RetryableProviderError
from .models import CommerceEventOutbox, IdempotencyRecord, WebhookReceipt, utcnow

T = TypeVar("T")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def request_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdempotencyClaim:
    record_id: str
    acquired: bool
    entity_id: str | None = None


def acquire_idempotency(
    session: Session,
    *,
    scope: str,
    key: str,
    fingerprint: str,
) -> IdempotencyClaim:
    """Claim an idempotency key before any external side effect.

    The unique database constraint is the authority. A repeated key with the same
    fingerprint replays the previously completed entity; the same key with a
    different fingerprint is rejected. An in-progress duplicate is surfaced as a
    conflict instead of allowing a second payment/courier call.
    """
    existing = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key == key,
        )
    )
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError("Idempotency key was already used with a different request")
        if existing.status == "completed" and existing.entity_id:
            return IdempotencyClaim(existing.id, False, existing.entity_id)
        raise IdempotencyConflictError("An identical request with this idempotency key is already in progress")

    record = IdempotencyRecord(
        scope=scope,
        key=key,
        request_fingerprint=fingerprint,
        status="in_progress",
    )
    try:
        # SAVEPOINT means a unique-key collision does not poison the caller's
        # outer transaction.
        with session.begin_nested():
            session.add(record)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key == key,
            )
        )
        if existing and existing.request_fingerprint == fingerprint and existing.status == "completed" and existing.entity_id:
            return IdempotencyClaim(existing.id, False, existing.entity_id)
        if existing and existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError("Idempotency key was already used with a different request")
        raise IdempotencyConflictError("An identical request with this idempotency key is already in progress")
    return IdempotencyClaim(record.id, True, None)


def complete_idempotency(session: Session, record_id: str, *, entity_id: str) -> None:
    record = session.get(IdempotencyRecord, record_id)
    if not record:
        raise RuntimeError("Idempotency record disappeared inside active transaction")
    record.status = "completed"
    record.entity_id = entity_id
    record.completed_at = utcnow()



def acquire_webhook_receipt(
    session: Session, *, provider: str, event_id: str, fingerprint: str
) -> tuple[WebhookReceipt, bool]:
    """Insert a webhook receipt exactly once inside the caller transaction.

    Returns ``(receipt, True)`` for the processor that owns the event and
    ``(existing, False)`` for an identical replay. Reusing an event ID with a
    different canonical payload is always rejected.
    """
    existing = session.scalar(
        select(WebhookReceipt).where(
            WebhookReceipt.provider == provider, WebhookReceipt.event_id == event_id
        )
    )
    if existing:
        if existing.payload_sha256 != fingerprint:
            raise IdempotencyConflictError("Webhook event ID was reused with a different payload")
        return existing, False

    receipt = WebhookReceipt(provider=provider, event_id=event_id, payload_sha256=fingerprint)
    try:
        with session.begin_nested():
            session.add(receipt)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(WebhookReceipt).where(
                WebhookReceipt.provider == provider, WebhookReceipt.event_id == event_id
            )
        )
        if not existing:
            raise
        if existing.payload_sha256 != fingerprint:
            raise IdempotencyConflictError("Webhook event ID was reused with a different payload")
        return existing, False
    return receipt, True

def stage_event(
    session: Session,
    *,
    kind: str,
    business_id: str,
    entity_id: str,
    payload: dict[str, object],
    occurred_at: datetime | None = None,
    dedupe_key: str | None = None,
) -> CommerceEventOutbox:
    occurred_at = occurred_at or utcnow()
    if dedupe_key:
        existing = session.scalar(select(CommerceEventOutbox).where(CommerceEventOutbox.dedupe_key == dedupe_key))
        if existing:
            return existing
    row = CommerceEventOutbox(
        kind=kind,
        business_id=business_id,
        entity_id=entity_id,
        occurred_at=occurred_at,
        payload_json=canonical_json(payload),
        status="pending",
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()
    return row


@dataclass
class CircuitState:
    consecutive_failures: int = 0
    opened_until_monotonic: float = 0.0


class ProviderExecutor:
    """Small provider reliability layer: explicit retry + circuit breaker.

    Only RetryableProviderError is retried. Validation/business errors are never
    replayed. This prevents accidental duplicate side effects from broad retries.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_seconds: float = 15.0,
        max_attempts: int = 2,
        base_backoff_seconds: float = 0.03,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_seconds = max(0.1, recovery_seconds)
        self.max_attempts = max(1, max_attempts)
        self.base_backoff_seconds = max(0.0, base_backoff_seconds)
        self._lock = threading.Lock()
        self._state: dict[str, CircuitState] = {}

    def call(self, provider_name: str, operation: str, fn: Callable[[], T]) -> T:
        key = f"{provider_name}:{operation}"
        now = time.monotonic()
        with self._lock:
            state = self._state.setdefault(key, CircuitState())
            if state.opened_until_monotonic > now:
                raise ProviderCircuitOpenError(f"Provider circuit is open for {provider_name}/{operation}")
            if state.opened_until_monotonic and state.opened_until_monotonic <= now:
                state.opened_until_monotonic = 0.0
                state.consecutive_failures = 0

        last_exc: RetryableProviderError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = fn()
            except RetryableProviderError as exc:
                last_exc = exc
                with self._lock:
                    state = self._state.setdefault(key, CircuitState())
                    state.consecutive_failures += 1
                    if state.consecutive_failures >= self.failure_threshold:
                        state.opened_until_monotonic = time.monotonic() + self.recovery_seconds
                if attempt < self.max_attempts:
                    time.sleep(self.base_backoff_seconds * attempt)
                    continue
                raise
            except Exception:
                # Unknown exceptions count toward the breaker but are not retried;
                # broad automatic retries around payments/couriers are dangerous.
                with self._lock:
                    state = self._state.setdefault(key, CircuitState())
                    state.consecutive_failures += 1
                    if state.consecutive_failures >= self.failure_threshold:
                        state.opened_until_monotonic = time.monotonic() + self.recovery_seconds
                raise
            else:
                with self._lock:
                    state = self._state.setdefault(key, CircuitState())
                    state.consecutive_failures = 0
                    state.opened_until_monotonic = 0.0
                return result
        assert last_exc is not None
        raise last_exc

    def snapshot(self) -> dict[str, dict[str, float | int | bool]]:
        now = time.monotonic()
        with self._lock:
            return {
                key: {
                    "consecutive_failures": state.consecutive_failures,
                    "open": state.opened_until_monotonic > now,
                    "recovery_seconds_remaining": max(0.0, state.opened_until_monotonic - now),
                }
                for key, state in self._state.items()
            }
