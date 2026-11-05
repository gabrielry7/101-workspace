"""Source-bound cost observations; missing/stale evidence is never zero profit."""

import hashlib
import json
from collections import defaultdict
from datetime import UTC
from typing import Annotated

from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .errors import ConcurrencyConflictError, IdempotencyConflictError, NotFoundError
from .loyalty_assignment_models import LoyaltyAssignment, LoyaltyExperimentRun
from .loyalty_execution_models import LoyaltyPointLot
from .loyalty_measurement_models import LoyaltyFinancialEvidence
from .loyalty_models import LoyaltyExperimentVariant
from .models import (
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    Order,
    Payment,
    PaymentReconciliation,
    RewardRedemption,
)
from .refunds import PaymentRefund
from .schemas import StrictModel
from .staff import aware

SignedMoney = Annotated[int, Field(strict=True, ge=-(2**53 - 1), le=2**53 - 1)]


class EvidenceInput(StrictModel):
    request_key: str = Field(min_length=1, max_length=100)
    expected_revision: Annotated[int, Field(strict=True, ge=0)]
    financial_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_ref: str = Field(min_length=3, max_length=500)
    includes_estimate: bool


class OrderCosts(EvidenceInput):
    variable_cost_minor: SignedMoney
    additional_reward_cost_minor: SignedMoney


class OperatingCost(EvidenceInput):
    operating_cost_minor: Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def batches(values):
    values = list(values)
    for start in range(0, len(values), 400):
        yield values[start : start + 400]


def verified(order):
    try:
        return (
            json.loads(order.customer_snapshot_json or "{}").get("identity_verified")
            is True
        )
    except (ValueError, AttributeError):
        return False


def order_facts(session, orders):
    """Bulk snapshot, including historical full refunds without partial rows."""
    orders = list(orders)
    payments, refunds, ledger, lots, reviews = (defaultdict(list) for _ in range(5))
    # Baseline points have no origin lots. Redemption/restoration can alter an
    # earlier accrual, so review that customer's prior costs conservatively.
    # Ordinary earning alone does not invalidate every preceding purchase.
    adjustments, applied = {}, {}
    businesses = {o.business_id for o in orders}
    for ids in batches({o.customer_id for o in orders}):
        adjustments.update(
            session.execute(
                select(LoyaltyAccount.customer_id, func.count(LoyaltyLedgerEntry.id))
                .join(
                    LoyaltyLedgerEntry,
                    LoyaltyLedgerEntry.account_id == LoyaltyAccount.id,
                )
                .where(
                    LoyaltyAccount.customer_id.in_(ids),
                    LoyaltyAccount.business_id.in_(businesses),
                    LoyaltyLedgerEntry.reason.not_in(
                        ["order.completed", "loyalty.earned"]
                    ),
                )
                .group_by(LoyaltyAccount.customer_id)
            ).all()
        )
        applied.update(
            session.execute(
                select(RewardRedemption.customer_id, func.count(RewardRedemption.id))
                .where(
                    RewardRedemption.customer_id.in_(ids),
                    RewardRedemption.business_id.in_(businesses),
                    RewardRedemption.applied_at.is_not(None),
                )
                .group_by(RewardRedemption.customer_id)
            ).all()
        )
    for ids in batches(o.id for o in orders):
        for row in session.scalars(select(Payment).where(Payment.order_id.in_(ids))):
            payments[row.order_id].append(row)
        for row in session.scalars(
            select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.order_id.in_(ids))
        ):
            ledger[row.order_id].append([row.id, row.delta_points, row.reason])
        for row in session.scalars(
            select(LoyaltyPointLot).where(LoyaltyPointLot.order_id.in_(ids))
        ):
            lots[row.order_id].append(
                [
                    row.id,
                    row.version_id,
                    row.original_points,
                    row.available_points,
                    row.expired_points,
                    row.cost_per_point_minor,
                    row.redemption_bps,
                ]
            )
        for row in session.scalars(
            select(PaymentReconciliation).where(
                PaymentReconciliation.order_id.in_(ids),
                PaymentReconciliation.status == "open",
            )
        ):
            reviews[row.order_id].append(row.id)
    all_payments = [p for rows in payments.values() for p in rows]
    for ids in batches(p.id for p in all_payments):
        for row in session.scalars(
            select(PaymentRefund).where(PaymentRefund.payment_id.in_(ids))
        ):
            refunds[row.payment_id].append([row.id, row.amount_minor])
    result = {}
    for order in orders:
        ps = payments[order.id]
        captured = [p for p in ps if p.status in {"paid", "refunded"}]
        net, gross, flags = 0, 0, []
        for p in captured:
            amount = (
                p.amount_minor
                if p.status == "refunded"
                else sum(r[1] for r in refunds[p.id])
            )
            gross += p.amount_minor
            net += p.amount_minor - amount
            if amount > p.amount_minor or p.currency != order.currency:
                flags.append("payment_inconsistency")
        # There should be exactly one canonical capture per order.
        if not (order.status == "cancelled" and not captured) and (
            gross != order.total_minor or len(captured) != 1
        ):
            flags.append("payment_inconsistency")
        if reviews[order.id]:
            flags.append("financial_review_open")
        document = {
            "format": "loyalty-cost-facts-v1",
            "customer_reward_revision": [
                adjustments.get(order.customer_id, 0),
                applied.get(order.customer_id, 0),
            ],
            "order": [
                order.id,
                order.business_id,
                order.customer_id,
                order.status,
                order.payment_status,
                order.currency,
                order.total_minor,
                order.reward_discount_minor,
                verified(order),
                aware(order.created_at).astimezone(UTC).isoformat(),
                aware(order.completed_at).astimezone(UTC).isoformat()
                if order.completed_at
                else None,
            ],
            "payments": sorted(
                [
                    p.id,
                    p.provider,
                    p.status,
                    p.amount_minor,
                    p.currency,
                    sorted(refunds[p.id]),
                ]
                for p in ps
            ),
            "open_reviews": sorted(reviews[order.id]),
            "ledger": sorted(ledger[order.id]),
            "lots": sorted(lots[order.id]),
        }
        result[order.id] = {
            "financial_digest": digest(document),
            "net_revenue_minor": net,
            "gross_receipts_minor": gross,
            "refund_minor": gross - net,
            "flags": sorted(set(flags)),
            "providers": sorted({p.provider for p in captured}),
            "ledger": ledger[order.id],
            "lots": lots[order.id],
        }
    return result


def latest_evidence(session, business_id, targets):
    result = {}
    for group in batches(targets):
        for row in session.scalars(
            select(LoyaltyFinancialEvidence)
            .where(
                LoyaltyFinancialEvidence.business_id == business_id,
                LoyaltyFinancialEvidence.target.in_(group),
            )
            .order_by(LoyaltyFinancialEvidence.revision.desc())
        ):
            result.setdefault(row.target, row)
    return result


def describe(row):
    if row is None:
        return {"revision": 0, "document": None}
    return {
        "id": row.id,
        "revision": row.revision,
        "supersedes_id": row.supersedes_id,
        "document": json.loads(row.document),
        "source_ref": row.source_ref,
        "actor_id": row.actor_id,
        "recorded_at": aware(row.recorded_at).astimezone(UTC).isoformat(),
        "financial_digest": row.financial_digest,
    }


def operating_digest(assignments, variant_id):
    return digest(
        sorted(
            [
                a.id,
                a.customer_id,
                aware(a.assigned_at).astimezone(UTC).isoformat(),
                aware(a.evaluation_ends_at).astimezone(UTC).isoformat(),
            ]
            for a in assignments
            if a.variant_id == variant_id
        )
    )


def target_context(session, business_id, kind, target_id):
    if kind == "orders":
        order = session.scalar(
            select(Order).where(Order.id == target_id, Order.business_id == business_id)
        )
        if order is None:
            raise NotFoundError("Order not found")
        return "order:" + order.id, order_facts(session, [order])[order.id][
            "financial_digest"
        ]
    variant = session.scalar(
        select(LoyaltyExperimentVariant)
        .join(
            LoyaltyExperimentRun,
            LoyaltyExperimentRun.experiment_version_id
            == LoyaltyExperimentVariant.experiment_version_id,
        )
        .where(
            LoyaltyExperimentVariant.id == target_id,
            LoyaltyExperimentVariant.business_id == business_id,
        )
    )
    if variant is None:
        raise NotFoundError("Frozen experiment variant not found")
    assignments = session.scalars(
        select(LoyaltyAssignment).where(
            LoyaltyAssignment.business_id == business_id,
            LoyaltyAssignment.experiment_version_id == variant.experiment_version_id,
        )
    ).all()
    return "variant:" + variant.id, operating_digest(assignments, variant.id)


def context(session, business_id, kind, target_id):
    target, fingerprint = target_context(session, business_id, kind, target_id)
    row = latest_evidence(session, business_id, [target]).get(target)
    history = session.scalars(
        select(LoyaltyFinancialEvidence)
        .where(
            LoyaltyFinancialEvidence.business_id == business_id,
            LoyaltyFinancialEvidence.target == target,
        )
        .order_by(LoyaltyFinancialEvidence.revision.desc())
        .limit(20)
    ).all()
    return {
        "target": target,
        "financial_digest": fingerprint,
        "latest": describe(row),
        "history": [describe(r) for r in history],
        "stale": bool(row and row.financial_digest != fingerprint),
    }


def record(session, business_id, kind, target_id, payload, actor_id):
    target, fingerprint = target_context(session, business_id, kind, target_id)
    request_digest = digest(
        {"target": target, "request": payload.model_dump(mode="json")}
    )
    existing = session.scalar(
        select(LoyaltyFinancialEvidence).where(
            LoyaltyFinancialEvidence.business_id == business_id,
            LoyaltyFinancialEvidence.request_key == payload.request_key,
        )
    )
    if existing:
        if existing.request_digest != request_digest:
            raise IdempotencyConflictError("Evidence key reused with different values")
        return describe(existing)
    previous = latest_evidence(session, business_id, [target]).get(target)
    if (
        previous.revision if previous else 0
    ) != payload.expected_revision or fingerprint != payload.financial_digest:
        raise ConcurrencyConflictError(
            "Financial evidence changed; review the current snapshot"
        )
    row = LoyaltyFinancialEvidence(
        business_id=business_id,
        target=target,
        order_id=target_id if kind == "orders" else None,
        variant_id=target_id if kind == "variants" else None,
        revision=payload.expected_revision + 1,
        supersedes_id=previous.id if previous else None,
        request_key=payload.request_key,
        request_digest=request_digest,
        financial_digest=fingerprint,
        document=canonical(
            payload.model_dump(
                exclude={
                    "request_key",
                    "expected_revision",
                    "financial_digest",
                    "source_ref",
                }
            )
        ),
        source_ref=payload.source_ref,
        actor_id=actor_id,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # A concurrent identical request can be safely replayed after its commit.
        replay = session.scalar(
            select(LoyaltyFinancialEvidence).where(
                LoyaltyFinancialEvidence.business_id == business_id,
                LoyaltyFinancialEvidence.request_key == payload.request_key,
            )
        )
        if replay and replay.request_digest == request_digest:
            return describe(replay)
        raise ConcurrencyConflictError(
            "Financial evidence changed; reload before retrying"
        ) from exc
    return describe(row)
