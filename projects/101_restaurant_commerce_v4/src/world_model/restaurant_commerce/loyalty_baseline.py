"""Ordinary loyalty compensation using the existing Order, account and ledger.

Callers own the Payment/Order lock. Policy is captured at checkout; refund counters
are a mutable projection in the existing order snapshot, never a second balance.
Unknown historical policy or delivery attribution holds redemption for review.
"""

import json

from sqlalchemy import select

from .errors import ValidationError
from .models import (
    LoyaltyLedgerEntry as Ledger,
)
from .models import (
    LoyaltyRefundDebt,
    Order,
    Payment,
    PromotionRedemption,
    RewardRedemption,
    utcnow,
)
from .refunds import PaymentRefund


def policy(program):
    return {
        "version": "baseline-paid-food-v1",
        "enabled": program.enabled,
        "spend_minor_per_point": program.spend_minor_per_point,
        "redemption_compensation": "cumulative_paid_food_proportion_v1",
    }


def data(order):
    return json.loads(order.customer_snapshot_json or "{}")


def save(order, snapshot, state):
    snapshot["baseline_refund_state"] = state
    order.customer_snapshot_json = json.dumps(snapshot, sort_keys=True)


def rows(session, order):
    return session.scalars(
        select(PaymentRefund).join(Payment).where(Payment.order_id == order.id)
    ).all()


def remaining(session, order, *, full=False):
    if full or order.payment_status == "refunded":
        return 0
    original = max(0, order.total_minor - order.delivery_fee_minor)
    refunds = rows(session, order)
    if not refunds:
        return original
    snapshot = data(order)
    if "baseline_policy" not in snapshot:
        return None
    allocations = snapshot.get("baseline_refund_state", {}).get("allocations", {})
    food_refunded = 0
    for refund in refunds:
        if not order.delivery_fee_minor:
            food_refunded += refund.amount_minor
        elif refund.id in allocations:
            food_refunded += (
                refund.amount_minor
                - allocations[refund.id]["document"]["delivery_fee_minor"]
            )
        else:
            return None
    return max(0, original - food_refunded)


def pending(session, account):
    orders = (
        session.scalars(
            select(Order)
            .join(Payment)
            .join(PaymentRefund)
            .where(
                Order.business_id == account.business_id,
                Order.customer_id == account.customer_id,
                Payment.status != "refunded",
            )
        )
        .unique()
        .all()
    )
    return any(
        data(order).get("identity_verified")
        and not data(order).get("loyalty_execution_version")
        and remaining(session, order) is None
        for order in orders
    )


def allocation_for(order, refund_id):
    return (
        data(order)
        .get("baseline_refund_state", {})
        .get("allocations", {})
        .get(refund_id)
    )


def allocate(session, order, refund, allocation, *, actor):
    snapshot = data(order)
    if not snapshot.get("baseline_policy"):
        raise ValidationError(
            "Historical baseline policy is missing; full refund or financial review required"
        )
    if (
        not isinstance(allocation, dict)
        or set(allocation) != {"lines", "delivery_fee_minor"}
        or not isinstance(allocation["lines"], dict)
    ):
        raise ValidationError("Refund allocation requires lines and delivery_fee_minor")
    values = [*allocation["lines"].values(), allocation["delivery_fee_minor"]]
    if (
        any(type(x) is not int or x < 0 for x in values)
        or sum(values) != refund.amount_minor
    ):
        raise ValidationError("Allocation must exactly match confirmed refund amount")
    if set(allocation["lines"]) - {line.id for line in order.items}:
        raise ValidationError("Allocation includes a foreign order line")
    state = snapshot.get("baseline_refund_state", {})
    allocations = state.setdefault("allocations", {})
    previous = allocations.get(refund.id)
    if previous:
        if previous["document"] != allocation:
            raise ValidationError("Confirmed refund allocation is immutable")
        return
    allocations[refund.id] = {"document": allocation, "actor": actor}
    fee = sum(a["document"]["delivery_fee_minor"] for a in allocations.values())
    food = sum(sum(a["document"]["lines"].values()) for a in allocations.values())
    # Baseline has no excluded products: only total paid food versus delivery is
    # financially relevant. Do not invent tax/discount allocations to line items.
    if (
        fee > order.delivery_fee_minor
        or food > order.total_minor - order.delivery_fee_minor
    ):
        raise ValidationError(
            "Cumulative refund allocation exceeds original consideration"
        )
    save(order, snapshot, state)


def earn(growth, order):
    session = growth.session
    snapshot = data(order)
    if not snapshot.get("identity_verified"):
        return 0
    existing = session.scalar(
        select(Ledger).where(Ledger.idempotency_key == "order-complete:" + order.id)
    )
    if existing:
        return existing.delta_points
    eligible = remaining(session, order)
    if eligible is None:
        return 0
    frozen = snapshot.get("baseline_policy")
    if frozen is None:
        # For an unrefunded historical order, completion is the first established
        # earning-policy observation. Never backfill a refunded order from today.
        frozen = policy(growth.ensure_program(order.business_id))
        snapshot["baseline_policy"] = frozen
        snapshot["baseline_policy_recorded_at"] = "completion"
        save(order, snapshot, snapshot.get("baseline_refund_state", {}))
    rate = frozen["spend_minor_per_point"]
    points = eligible // rate if frozen["enabled"] and rate > 0 else 0
    if points <= 0:
        return 0
    from .loyalty_wallet import entry, expire

    account = growth.ensure_account(
        order.business_id, order.customer_id, for_update=True
    )
    expire(session, account)
    account.available_points += points
    account.lifetime_earned_points += points
    entry(
        session,
        account,
        key="order-complete:" + order.id,
        reason="order.completed",
        points=points,
        order_id=order.id,
    )
    growth._settle_refund_debt(account, order.id, "earning")
    return points


def compensate(growth, order, *, full=False):
    session = growth.session
    if not order.customer_id:
        return
    left = remaining(session, order, full=full)
    if left is None:
        return  # Confirmed money persists; pending() blocks further redemption.
    snapshot = data(order)
    state = snapshot.get("baseline_refund_state", {})
    earned = session.scalar(
        select(Ledger).where(Ledger.idempotency_key == "order-complete:" + order.id)
    )
    issued = earned.delta_points if earned else 0
    frozen = snapshot.get("baseline_policy")
    if not full and issued and frozen is None:
        return
    desired = (
        min(issued, left // frozen["spend_minor_per_point"]) if left and issued else 0
    )
    reversed_target = issued - desired
    reverse = reversed_target - state.get("reversed_points", 0)
    redemption = session.scalar(
        select(RewardRedemption)
        .where(RewardRedemption.order_id == order.id)
        .execution_options(populate_existing=True)
    )
    original = max(0, order.total_minor - order.delivery_fee_minor)
    target = state.get("restored_points", 0)
    if redemption and redemption.status in {"reserved", "applied"}:
        target = (
            redemption.points_spent
            if full
            else (
                redemption.points_spent * (original - left) // original
                if original
                else 0
            )
        )
    credit = target - state.get("restored_points", 0)
    if reverse < 0 or credit < 0:
        raise ValidationError("Refund compensation cannot move backwards")
    key = f"baseline-refund:{order.id}:{int(full)}:{reversed_target}:{target}"
    if session.scalar(select(Ledger.id).where(Ledger.idempotency_key == key)):
        return
    # Respect pre-upgrade completed full-refund compensation.
    if session.scalar(
        select(Ledger.id).where(Ledger.idempotency_key == "order-refund:" + order.id)
    ):
        return
    from .loyalty_wallet import consume, entry, expire, restore

    account = growth.ensure_account(
        order.business_id, order.customer_id, for_update=True
    )
    expire(session, account)
    account.available_points += credit
    account.lifetime_redeemed_points -= credit
    credited = entry(
        session,
        account,
        key=key,
        reason="refund.reward_credit",
        points=credit,
        order_id=order.id,
    )
    if credit:
        restore(
            session,
            account,
            credited,
            "reward-reserve:" + redemption.id,
            state.get("restored_points", 0),
            target,
        )
    recovered = min(reverse, account.available_points)
    account.available_points -= recovered
    account.lifetime_earned_points -= reverse
    debit = entry(
        session,
        account,
        key=key + ":reverse",
        reason="order.refunded",
        points=-recovered,
        order_id=order.id,
    )
    consume(session, account, debit, recovered)
    if recovered < reverse:
        debt = session.scalar(
            select(LoyaltyRefundDebt)
            .where(LoyaltyRefundDebt.order_id == order.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if debt is None:
            debt = LoyaltyRefundDebt(
                order_id=order.id, account_id=account.id, remaining_points=0
            )
            session.add(debt)
        debt.remaining_points += reverse - recovered
    state.update(reversed_points=reversed_target, restored_points=target)
    save(order, snapshot, state)
    if full:
        if redemption and redemption.status in {"reserved", "applied"}:
            redemption.status, redemption.released_at = "released", utcnow()
        promotion = session.scalar(
            select(PromotionRedemption).where(PromotionRedemption.order_id == order.id)
        )
        if promotion and promotion.status in {"reserved", "applied"}:
            promotion.status, promotion.released_at = "released", utcnow()
    session.flush()
    growth._settle_refund_debt(account, order.id, key)
