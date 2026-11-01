"""Leased sandbox lookup jobs, independent of browser callbacks and process life."""

import hashlib
import json
import secrets
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from .errors import NotFoundError, PaymentError
from .models import Order, Payment, WompiSandboxLookup, utcnow
from .schemas import PaymentWebhookIn
from .wompi_sandbox import IDENTIFIER, NAME, WompiSandboxProvider


def enqueue(service, transaction_id, expected_order_id=None, *, event_key=""):
    # Event checksum creates a fresh query for each signed state update.
    if not isinstance(transaction_id, str) or not IDENTIFIER.fullmatch(transaction_id):
        raise ValueError("Invalid sandbox transaction identifier")
    adapter = service.payment_providers.get(NAME)
    if not isinstance(adapter, WompiSandboxProvider):
        raise PaymentError("Sandbox is not configured")
    if expected_order_id:
        order = service.session.get(Order, expected_order_id)
        payment = service.session.scalar(
            select(Payment).where(Payment.order_id == expected_order_id)
        )
        if (
            not order
            or order.business_id != adapter.business_id
            or not payment
            or payment.provider != NAME
        ):
            raise NotFoundError("Sandbox order not found")
    key = hashlib.sha256(
        f"{expected_order_id or 'event'}:{transaction_id}:{event_key}".encode()
    ).hexdigest()
    row = service.session.get(WompiSandboxLookup, key)
    if row is None:
        try:
            with service.session.begin_nested():
                service.session.add(
                    WompiSandboxLookup(
                        id=key, transaction_id=transaction_id, expected_order_id=expected_order_id
                    )
                )
                service.session.flush()
        except IntegrityError:
            if service.session.get(WompiSandboxLookup, key) is None:
                raise
    service._commit()  # Receipt survives process termination before provider lookup.
    return key


def process(service, key):
    adapter = service.payment_providers.get(NAME)
    if not isinstance(adapter, WompiSandboxProvider):
        return
    session = service.session
    now, token = utcnow(), secrets.token_hex(24)
    claimed = session.execute(
        update(WompiSandboxLookup)
        .where(
            WompiSandboxLookup.id == key,
            WompiSandboxLookup.state == "pending",
            WompiSandboxLookup.next_attempt_at <= now,
            or_(WompiSandboxLookup.lease_until.is_(None), WompiSandboxLookup.lease_until <= now),
        )
        .values(
            lease_token=token,
            lease_until=now + timedelta(seconds=60),
            attempts=WompiSandboxLookup.attempts + 1,
        ),
        execution_options={"synchronize_session": False},
    ).rowcount
    if not claimed:
        session.rollback()
        return
    service._commit()
    session.expire_all()
    row = session.get(WompiSandboxLookup, key)
    transaction_id, expected, attempts = row.transaction_id, row.expected_order_id, row.attempts
    single_attempt = row.single_attempt
    session.rollback()
    result, error, state = None, None, "pending"
    try:
        if attempts > (1 if single_attempt else 12):
            raise PaymentError("Sandbox lookup budget exhausted after interrupted claim")
        result = adapter.transaction(transaction_id)
        if expected and result["order_id"] != expected:
            raise ValueError("Wrong order")
    except ValueError:
        error, state = "invalid_or_unbound_provider_evidence", "review_required"
    except PaymentError:
        error = "sandbox_lookup_unavailable"
    # Reacquire/fence before using evidence. No SQL transaction was held over HTTP.
    fenced = session.execute(
        update(WompiSandboxLookup)
        .where(
            WompiSandboxLookup.id == key,
            WompiSandboxLookup.lease_token == token,
        )
        .values(
            lease_token=None,
            lease_until=None,
            last_error=error,
            state=state,
            next_attempt_at=utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(attempts, 7))),
        ),
        execution_options={"synchronize_session": False},
    ).rowcount
    if not fenced:
        session.rollback()
        return
    session.expire_all()
    row = session.get(WompiSandboxLookup, key)
    if result is not None and not error:
        payment = session.scalar(
            select(Payment)
            .where(
                Payment.provider_reference == result["reference"],
                Payment.provider == NAME,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order = session.get(Order, result["order_id"])
        if (
            not payment
            or not order
            or payment.order_id != order.id
            or order.business_id != adapter.business_id
            or payment.amount_minor != result["amount_minor"]
            or payment.currency != result["currency"]
        ):
            row.state, row.last_error = "review_required", "immutable_payment_mismatch"
            if (
                payment
                and order
                and payment.order_id == order.id
                and order.business_id == adapter.business_id
            ):
                service._reconciliation(
                    order,
                    "wompi_payment_mismatch",
                    {
                        "transaction_id": transaction_id,
                        "reason": row.last_error,
                    },
                )
        else:
            row.order_id = order.id
            row.result_json = json.dumps(result, sort_keys=True)
            if result["status"] == "review_required" or (
                result["status"] == "pending" and attempts >= 12 and not single_attempt
            ):
                row.state = "review_required"
                row.last_error = (
                    "provider_refund_observed"
                    if result.get("refunds_observed")
                    else "unsupported_provider_status"
                    if result["status"] == "review_required"
                    else "pending_attempt_budget_exhausted"
                )
                service._reconciliation(
                    order,
                    "wompi_provider_review",
                    {
                        "transaction_id": transaction_id,
                        "reason": row.last_error,
                    },
                )
                service._commit()
                return
            if result["status"] == "paid":
                previous = session.scalars(
                    select(WompiSandboxLookup).where(
                        WompiSandboxLookup.order_id == order.id,
                        WompiSandboxLookup.transaction_id != transaction_id,
                        WompiSandboxLookup.result_json.is_not(None),
                    )
                ).all()
                if any(json.loads(r.result_json).get("status") == "paid" for r in previous):
                    service._reconciliation(
                        order,
                        "multiple_wompi_transactions",
                        {
                            "transaction_id": transaction_id,
                            "provider_reference": result["reference"],
                        },
                    )
            row.state = (
                ("observed" if single_attempt else "pending")
                if result["status"] == "pending"
                else "processed"
            )
            # Job completion and the normalized inbox receipt are persisted together;
            # the existing inbox worker can finish settlement after interruption.
            service.receive_payment_notification(
                NAME,
                PaymentWebhookIn(
                    provider_reference=result["reference"],
                    event_id=f"wompi:{transaction_id}:{result['status']}",
                    status=result["status"],
                    amount_minor=result["amount_minor"],
                    currency=result["currency"],
                ),
            )
            return
    if single_attempt and row.state == "pending":
        row.state = "observed"  # Next bounded discovery pass obtains fresh evidence.
    if attempts >= 12 and row.state == "pending":
        row.state, row.last_error = "review_required", error or "lookup_attempt_budget_exhausted"
        # Only an authenticated order binding may create a financial hold here.
        # Untrusted arbitrary webhook IDs must not hold someone else's order.
        if expected:
            order = session.get(Order, expected)
            if order and order.business_id == adapter.business_id:
                service._reconciliation(
                    order,
                    "wompi_lookup_exhausted",
                    {
                        "transaction_id": transaction_id,
                        "reason": row.last_error,
                    },
                )
    service._commit()


def recover(service, limit=10):
    if NAME not in service.payment_providers:
        return 0  # Old installations do not query this optional sandbox table.
    receiver = getattr(service.payment_providers[NAME], "receiver", None)
    if receiver is not None:
        try:
            receiver.drain(service)
        except PaymentError:
            service.session.rollback()  # Reference discovery remains independent.
    from .wompi_discovery import recover as discover

    discovered = discover(service, limit=min(limit, 5))
    now = utcnow()
    ids = list(
        service.session.scalars(
            select(WompiSandboxLookup.id)
            .where(
                WompiSandboxLookup.state == "pending",
                WompiSandboxLookup.next_attempt_at <= now,
                or_(
                    WompiSandboxLookup.lease_until.is_(None), WompiSandboxLookup.lease_until <= now
                ),
            )
            .order_by(WompiSandboxLookup.next_attempt_at)
            .limit(limit)
        )
    )
    for key in ids:
        try:
            process(service, key)
        except Exception:  # rollback + durable retry, no provider/credential contents in logs
            service.session.rollback()
    return len(ids) + discovered
