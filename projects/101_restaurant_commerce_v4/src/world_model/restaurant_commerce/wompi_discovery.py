"""Bounded, leased reference discovery; provider lists never settle money directly."""

import hashlib
import secrets
from datetime import UTC, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from .errors import PaymentError
from .models import Order, Payment, WompiSandboxDiscovery, utcnow
from .wompi_sandbox import NAME, WompiSandboxProvider


def recover(service, limit=5):
    adapter = service.payment_providers.get(NAME)
    if not isinstance(adapter, WompiSandboxProvider):
        return 0
    session = service.session
    # Recover scheduling after a crash between checkout commit and the next tick.
    candidates = list(
        session.scalars(
            select(Payment.order_id)
            .join(Order)
            .where(
                Payment.provider == NAME,
                Order.business_id == adapter.business_id,
                Payment.created_at <= utcnow() - timedelta(seconds=60),
                ~select(WompiSandboxDiscovery.order_id)
                .where(WompiSandboxDiscovery.order_id == Payment.order_id)
                .exists(),
            )
            .order_by(Payment.created_at)
            .limit(limit)
        )
    )
    for order_id in candidates:
        try:
            with session.begin_nested():
                session.add(WompiSandboxDiscovery(order_id=order_id))
                session.flush()
        except IntegrityError:
            if session.get(WompiSandboxDiscovery, order_id) is None:
                raise
    service._commit()
    ids = list(
        session.scalars(
            select(WompiSandboxDiscovery.order_id)
            .join(Order)
            .where(
                Order.business_id == adapter.business_id,
                WompiSandboxDiscovery.state == "pending",
                WompiSandboxDiscovery.next_attempt_at <= utcnow(),
                or_(
                    WompiSandboxDiscovery.lease_until.is_(None),
                    WompiSandboxDiscovery.lease_until <= utcnow(),
                ),
            )
            .order_by(WompiSandboxDiscovery.next_attempt_at)
            .limit(limit)
        )
    )
    for order_id in ids:
        try:
            process(service, order_id)
        except Exception:
            session.rollback()  # Durable lease retries; no provider body in logs.
    return len(ids)


def process(service, order_id):
    session = service.session
    adapter = service.payment_providers[NAME]
    token, now = secrets.token_hex(24), utcnow()
    claimed = session.execute(
        update(WompiSandboxDiscovery)
        .where(
            WompiSandboxDiscovery.order_id == order_id,
            WompiSandboxDiscovery.state == "pending",
            WompiSandboxDiscovery.next_attempt_at <= now,
            or_(
                WompiSandboxDiscovery.lease_until.is_(None),
                WompiSandboxDiscovery.lease_until <= now,
            ),
        )
        .values(
            lease_token=token,
            lease_until=now + timedelta(seconds=60),
            attempts=WompiSandboxDiscovery.attempts + 1,
        ),
        execution_options={"synchronize_session": False},
    ).rowcount
    if not claimed:
        session.rollback()
        return
    service._commit()
    session.expire_all()
    order = session.get(Order, order_id)
    payment = session.scalar(
        select(Payment).where(Payment.order_id == order_id, Payment.provider == NAME)
    )
    if not order or order.business_id != adapter.business_id or not payment:
        raise ValueError("Invalid discovery binding")
    created = payment.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    attempts = session.get(WompiSandboxDiscovery, order_id).attempts
    unresolved = payment.status == "pending"
    expired = now >= created + timedelta(hours=48)
    session.rollback()  # Never hold a database transaction over provider IO.
    ids, error = [], None
    if not expired and attempts <= 60:
        try:
            ids = adapter.transactions_for_order(order_id)
        except (ValueError, PaymentError):
            error = "reference_lookup_unavailable_or_ambiguous"
    fenced = session.execute(
        update(WompiSandboxDiscovery)
        .where(
            WompiSandboxDiscovery.order_id == order_id,
            WompiSandboxDiscovery.lease_token == token,
        )
        .values(lease_token=None, lease_until=None),
        execution_options={"synchronize_session": False},
    ).rowcount
    if not fenced:
        session.rollback()
        return
    session.expire_all()
    row = session.get(WompiSandboxDiscovery, order_id)
    row.last_error = error
    row.next_attempt_at = utcnow() + timedelta(seconds=min(3600, 60 * 2 ** min(row.attempts, 6)))
    if expired or row.attempts >= 60:
        row.state = "review_required" if unresolved or error else "complete"
        if row.state == "review_required":
            order = session.get(Order, order_id)
            service._reconciliation(
                order,
                "wompi_discovery_exhausted",
                {
                    "reason": error or "no_final_provider_evidence",
                    "attempts": row.attempts,
                },
            )
    # Persist every ID atomically with the discovery schedule. A restart must not
    # lose any IDs if this scan was the last one before its budget expired.
    from .models import WompiSandboxLookup

    for transaction_id in ids:
        key = hashlib.sha256(
            f"discovery:{order_id}:{row.attempts}:{transaction_id}".encode()
        ).hexdigest()
        if session.get(WompiSandboxLookup, key) is None:
            try:
                with session.begin_nested():
                    session.add(
                        WompiSandboxLookup(
                            id=key,
                            transaction_id=transaction_id,
                            expected_order_id=order_id,
                            single_attempt=True,
                        )
                    )
                    session.flush()
            except IntegrityError:
                if session.get(WompiSandboxLookup, key) is None:
                    raise
    service._commit()
