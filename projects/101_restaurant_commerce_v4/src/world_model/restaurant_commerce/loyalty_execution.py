"""Controlled Stage-3 adapter. Callers own the transaction; no provider side effects.

Only trusted simulated checkout may select a version in this stage. Public activation,
identity adapters and experiment assignment are separate release gates.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select

from .errors import ValidationError
from .loyalty_config import digest
from .loyalty_execution_migrations import installed
from .loyalty_execution_models import LoyaltyBudget as Budget
from .loyalty_execution_models import LoyaltyExecutionEvent as Event
from .loyalty_execution_models import LoyaltyOrderSnapshot as Snapshot
from .loyalty_execution_models import LoyaltyOrderState as State
from .loyalty_execution_models import LoyaltyPointLot as Lot
from .loyalty_execution_models import LoyaltyRefundAllocation as Allocation
from .loyalty_models import LoyaltyStrategy, LoyaltyStrategyVersion
from .loyalty_rules import MAX_POINTS, PreviewScenario, allocate_discount, evaluate_rules
from .loyalty_schemas import StrategyDocument
from .loyalty_wallet import consume, entry, expire, restore
from .models import LoyaltyLedgerEntry as Ledger
from .models import (
    LoyaltyRefundDebt,
    Order,
    Payment,
    PromotionRedemption,
    RewardDefinition,
    RewardRedemption,
    utcnow,
)
from .refunds import PaymentRefund


@dataclass(frozen=True)
class ExecutionSelection:
    version_id: str
    redeem_reward: bool = False
    enabled: bool = False
    # Current commerce prices have no tax decomposition. Synthetic fixtures must
    # explicitly attest their tax-free price basis; real checkout remains gated.
    price_basis: str | None = None


def selected(service, selection=None):
    selection = selection if selection is not None else service.loyalty_execution
    if selection is not None:
        if not selection.enabled or selection.price_basis != "synthetic_tax_exclusive":
            raise ValidationError(
                "Execution requires explicit enablement and synthetic tax-exclusive prices"
            )
        if not installed(service.session):
            raise ValidationError("Offline loyalty execution upgrade required")
    return selection


def marked(order):
    return bool(
        order.customer_snapshot_json
        and json.loads(order.customer_snapshot_json).get("loyalty_execution_version")
    )


def state_for(session, order):
    if not marked(order):
        return None
    snapshot = session.get(Snapshot, order.id)
    state = session.scalar(
        select(State)
        .where(State.order_id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not snapshot or not state or digest(snapshot.document) != snapshot.digest:
        raise ValidationError("Loyalty execution history is missing or corrupt")
    if json.loads(order.customer_snapshot_json)["loyalty_execution_version"] != snapshot.version_id:
        raise ValidationError("Order version binding mismatch")
    return snapshot, state, json.loads(snapshot.document)


def pending_refunds(session, account):
    return (
        session.scalar(
            select(PaymentRefund.id)
            .join(Payment)
            .join(Order, Order.id == Payment.order_id)
            .join(Snapshot, Snapshot.order_id == Order.id)
            .outerjoin(Allocation, Allocation.refund_id == PaymentRefund.id)
            .where(
                Order.customer_id == account.customer_id,
                Order.business_id == account.business_id,
                Payment.status != "refunded",
                Allocation.refund_id.is_(None),
            )
            .limit(1)
        )
        is not None
    )


def calculate(
    service,
    business_id,
    items,
    promotion_minor,
    *,
    lock=False,
    selection=None,
    allow_historical=False,
    strict=True,
):
    selection = selected(service, selection)
    from .growth import RestaurantGrowthService

    growth = RestaurantGrowthService(service.session)
    version = service.session.get(LoyaltyStrategyVersion, selection.version_id)
    if (
        not version
        or version.business_id != business_id
        or digest(version.document) != version.digest
    ):
        raise ValidationError(
            "Published version does not belong to this business or has invalid digest"
        )
    strategy = service.session.scalar(
        select(LoyaltyStrategy)
        .where(LoyaltyStrategy.id == version.strategy_id)
        .execution_options(populate_existing=True)
    )
    if strategy.state not in ({"published", "draft"} if allow_historical else {"published"}):
        raise ValidationError("Program is paused or unavailable for new orders")
    document = StrategyDocument.model_validate_json(version.document)
    if document.earning and document.estimated_cost_per_point_minor <= 0:
        raise ValidationError("Execution requires a positive explicit point cost estimate")
    if not service.verified_customer_id:
        raise ValidationError("Verified customer required for loyalty execution")
    account = growth.ensure_account(business_id, service.verified_customer_id, for_update=lock)
    if lock:
        expire(service.session, account)
    # Quotes do not expire or reserve points. Subtract due lots for the preview.
    expired = service.session.scalar(
        select(func.coalesce(func.sum(Lot.available_points), 0)).where(
            Lot.account_id == account.id, Lot.expires_at <= utcnow()
        )
    )
    debts = service.session.scalar(
        select(func.coalesce(func.sum(LoyaltyRefundDebt.remaining_points), 0)).where(
            LoyaltyRefundDebt.account_id == account.id
        )
    )
    if selection.redeem_reward and pending_refunds(service.session, account):
        if strict:
            raise ValidationError("Refund allocation review required before redemption")
        debts = max(debts, 1)
    weights = {str(i): item.line_total_minor for i, item in enumerate(items)}
    promotions = allocate_discount(promotion_minor, weights)
    scenario = PreviewScenario(
        currency=document.currency,
        at=utcnow(),
        customer_id=service.verified_customer_id,
        assume_verified_identity=True,
        assumed_available_points=max(0, account.available_points - expired),
        assumed_refund_debt_points=debts,
        redeem_reward=selection.redeem_reward,
        lines=[
            dict(
                line_id=str(i),
                product_id=item.menu_item_id,
                subtotal_minor=item.line_total_minor,
                promotion_discount_minor=promotions[str(i)],
            )
            for i, item in enumerate(items)
        ],
    )
    result = evaluate_rules(document, scenario)
    if strict and (not result.supported or not result.eligible_by_rules):
        raise ValidationError("Program cannot execute: " + ", ".join(result.reasons))
    if strict and selection.redeem_reward and not result.redemption.eligible_by_rules:
        raise ValidationError("Reward cannot execute: " + ", ".join(result.redemption.reasons))
    return version, document, account, result


def budgets(session, version, customer_id, *, require_published=False, allow_historical=False):
    # Serializes creation plus all-version caps. Always account -> strategy -> buckets.
    strategy = session.scalar(
        select(LoyaltyStrategy)
        .where(LoyaltyStrategy.id == version.strategy_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if require_published and strategy.state not in (
        {"published", "draft"} if allow_historical else {"published"}
    ):
        raise ValidationError("Program paused before reservation")
    result = []
    for scope in ("*", customer_id):
        bucket = session.scalar(
            select(Budget)
            .where(Budget.strategy_id == version.strategy_id, Budget.scope == scope)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if bucket is None:
            bucket = Budget(
                strategy_id=version.strategy_id, scope=scope, reserved_minor=0, committed_minor=0
            )
            session.add(bucket)
            session.flush()
        result.append(bucket)
    return result


def event(session, snapshot, ledger, **details):
    session.add(
        Event(
            order_id=snapshot.order_id,
            version_id=snapshot.version_id,
            ledger_id=ledger.id,
            details=json.dumps(details, sort_keys=True),
        )
    )


def reserve(service, order, quote, order_items, *, selection=None, allow_historical=False):
    version, document, account, result = calculate(
        service,
        order.business_id,
        quote.items,
        order.promotion_discount_minor,
        lock=True,
        selection=selection,
        allow_historical=allow_historical,
    )
    if (
        result.redemption.discount_minor != order.reward_discount_minor
        or result.order_total_minor_after_reward + order.delivery_fee_minor != order.total_minor
    ):
        raise ValidationError("Reward quote changed; obtain a new quote")
    from .growth import RestaurantGrowthService

    baseline = RestaurantGrowthService(service.session).ensure_program(order.business_id)
    service.session.refresh(baseline)
    amount = (
        result.earning.points * document.estimated_cost_per_point_minor
        + result.redemption.discount_minor
    )
    locked_budgets = budgets(
        service.session,
        version,
        order.customer_id,
        require_published=True,
        allow_historical=allow_historical,
    )
    if allow_historical:
        from .loyalty_assignment_checkout import validate_reservation

        validate_reservation(service)
    for bucket, cap in zip(
        locked_budgets,
        (document.campaign_budget_minor, document.per_customer_budget_minor),
        strict=True,
    ):
        if bucket.reserved_minor + bucket.committed_minor + amount > cap:
            raise ValidationError("Loyalty budget exhausted")
        bucket.reserved_minor += amount
    payload = {
        "calculation": result.model_dump(mode="json"),
        "version_digest": version.digest,
        "price_basis": (selection or service.loyalty_execution).price_basis,
        "baseline": {
            "enabled": baseline.enabled,
            "spend_minor_per_point": baseline.spend_minor_per_point,
        },
        "line_ids": {str(i): item.id for i, item in enumerate(order_items)},
        "delivery_fee_minor": order.delivery_fee_minor,
        "allocation_policy": "largest-remainder-line-id-v1",
        "refund_policy": "remaining-paid-consideration-v1",
    }
    document_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    snapshot = Snapshot(
        order_id=order.id,
        version_id=version.id,
        document=document_json,
        digest=digest(document_json),
    )
    service.session.add(snapshot)
    service.session.flush()
    service.session.add(State(order_id=order.id, reserved_minor=amount))
    redemption = None
    if result.redemption.points_spent:
        bridge_id = str(uuid5(NAMESPACE_URL, "101-loyalty-version:" + version.id))
        bridge = service.session.get(RewardDefinition, bridge_id)
        if bridge is None:
            # Strategy lock above serializes this bridge. Disabled: legacy checkout
            # cannot redeem it without the versioned checks and budget reservation.
            bridge = RewardDefinition(
                id=bridge_id,
                business_id=order.business_id,
                name=document.name,
                points_cost=result.redemption.points_spent,
                discount_minor=document.reward.discount_minor,
                enabled=False,
            )
            service.session.add(bridge)
            service.session.flush()
        redemption = RewardRedemption(
            business_id=order.business_id,
            customer_id=order.customer_id,
            reward_id=bridge_id,
            order_id=order.id,
            points_spent=result.redemption.points_spent,
            discount_minor=result.redemption.discount_minor,
            status="reserved",
        )
        service.session.add(redemption)
        service.session.flush()
        if account.lifetime_redeemed_points + redemption.points_spent > MAX_POINTS:
            raise ValidationError("Lifetime redeemed point limit exceeded")
        account.available_points -= redemption.points_spent
        account.lifetime_redeemed_points += redemption.points_spent
    ledger = entry(
        service.session,
        account,
        key="loyalty-reserve:" + order.id,
        reason="loyalty.reserved",
        points=-result.redemption.points_spent,
        order_id=order.id,
        redemption_id=redemption.id if redemption else None,
    )
    consume(service.session, account, ledger, result.redemption.points_spent)
    event(service.session, snapshot, ledger, reserved_minor=amount)
    service.session.flush()


def adjust_budget(session, snapshot, state, order, reserved_delta, committed_delta):
    version = session.get(LoyaltyStrategyVersion, snapshot.version_id)
    for bucket in budgets(session, version, order.customer_id):
        bucket.reserved_minor += reserved_delta
        bucket.committed_minor += committed_delta
    state.reserved_minor += reserved_delta
    state.committed_minor += committed_delta


def lifecycle(growth, order, action):
    found = state_for(growth.session, order)
    if found is None:
        return False
    snapshot, state, data = found
    session = growth.session
    account = growth.ensure_account(order.business_id, order.customer_id, for_update=True)
    # The order lock is owned by checkout/payment/fulfillment/refund callers.
    redemption = session.scalar(
        select(RewardRedemption).where(RewardRedemption.order_id == order.id)
    )
    if action == "apply" and state.status == "reserved":
        discount = data["calculation"]["redemption"]["discount_minor"]
        adjust_budget(session, snapshot, state, order, -discount, discount)
        state.status = "applied"
        if redemption:
            redemption.status, redemption.applied_at = "applied", utcnow()
        row = entry(
            session,
            account,
            key="loyalty-apply:" + order.id,
            reason="loyalty.applied",
            points=0,
            order_id=order.id,
        )
        event(session, snapshot, row, committed_minor=discount)
    elif action == "release" and state.status == "reserved":
        points = data["calculation"]["redemption"]["points_spent"]
        account.available_points += points
        account.lifetime_redeemed_points -= points
        row = entry(
            session,
            account,
            key="loyalty-release:" + order.id,
            reason="loyalty.released",
            points=points,
            order_id=order.id,
        )
        restore(session, account, row, "loyalty-reserve:" + order.id, 0, points)
        event(session, snapshot, row, released_minor=state.reserved_minor)
        adjust_budget(session, snapshot, state, order, -state.reserved_minor, 0)
        state.status = "released"
        state.restored_points = points
        if redemption:
            redemption.status, redemption.released_at = "released", utcnow()
        growth._settle_refund_debt(account, order.id, "loyalty-release")
    elif action == "earn" and not state.completed and state.status == "applied":
        rules = StrategyDocument.model_validate_json(
            session.get(LoyaltyStrategyVersion, snapshot.version_id).document
        )
        calc = data["calculation"]
        # Refunds observed before fulfillment must already constrain entitlement.
        remaining = remaining_spend(session, order, data)
        if remaining is None:
            return True  # Held for allocation review; resolver can complete later.
        earned = entitlement(rules, remaining[0], remaining[3])
        baseline = baseline_entitlement(data, remaining[1])
        if (
            max(account.available_points, account.lifetime_earned_points) + earned + baseline
            > MAX_POINTS
        ):
            raise ValidationError("Account point limit exceeded")
        account.available_points += earned + baseline
        account.lifetime_earned_points += earned + baseline
        row = entry(
            session,
            account,
            key="loyalty-earn:" + order.id,
            reason="loyalty.earned",
            points=earned,
            order_id=order.id,
        )
        if earned:
            session.add(
                Lot(
                    account_id=account.id,
                    ledger_id=row.id,
                    version_id=snapshot.version_id,
                    order_id=order.id,
                    original_points=earned,
                    available_points=earned,
                    cost_per_point_minor=rules.estimated_cost_per_point_minor,
                    redemption_bps=rules.expected_redemption_bps,
                    expires_at=datetime.fromisoformat(calc["earning"]["expires_at"])
                    if calc["earning"]["expires_at"]
                    else None,
                )
            )
        entry(
            session,
            account,
            key="order-complete:" + order.id,
            reason="order.completed",
            points=baseline,
            order_id=order.id,
        )
        event(
            session,
            snapshot,
            row,
            issued_points=earned,
            baseline_points=baseline,
            committed_minor=earned * rules.estimated_cost_per_point_minor,
        )
        adjust_budget(
            session,
            snapshot,
            state,
            order,
            -state.reserved_minor,
            earned * rules.estimated_cost_per_point_minor,
        )
        state.issued_points, state.baseline_points, state.completed = earned, baseline, True
        session.flush()
        expire(session, account)
        growth._settle_refund_debt(account, order.id, "loyalty-earning")
    session.flush()
    return True


def baseline_entitlement(data, remaining):
    baseline = data["baseline"]
    rate = baseline["spend_minor_per_point"]
    return remaining // rate if baseline["enabled"] and rate > 0 else 0


def entitlement(rules, remaining, qualifying):
    if (
        rules.earning is None
        or remaining <= 0
        or qualifying < rules.eligibility.minimum_purchase_minor
    ):
        return 0
    return remaining // rules.earning.spend_minor_per_point * rules.earning.points_per_unit


def remaining_spend(session, order, data, *, full=False):
    lines = {data["line_ids"][line["line_id"]]: line for line in data["calculation"]["lines"]}
    refunded = dict.fromkeys(lines, 0)
    rows = session.execute(
        select(PaymentRefund, Allocation)
        .join(Payment, Payment.id == PaymentRefund.payment_id)
        .outerjoin(Allocation, Allocation.refund_id == PaymentRefund.id)
        .where(Payment.order_id == order.id)
    ).all()
    if full:
        return 0, 0, sum(line["earning_basis_minor"] for line in lines.values()), 0
    for _refund, allocation in rows:
        if allocation is None:
            return None
        for key, amount in json.loads(allocation.document)["lines"].items():
            refunded[key] += amount
    eligible_remaining = total_remaining = eligible_refunded = qualifying = 0
    for key, line in lines.items():
        paid = line["net_item_minor"] - line["reward_discount_minor"]
        if refunded[key] > paid:
            raise ValidationError("Cumulative refund allocation exceeds original paid line")
        total_remaining += paid - refunded[key]
        if line["included"]:
            eligible_remaining += paid - refunded[key]
            eligible_refunded += refunded[key]
            # The original reward discount is retired proportionally to paid
            # consideration. Cumulative floor avoids refund-chunk rounding drift.
            discount_retired = line["reward_discount_minor"] * refunded[key] // paid if paid else 0
            qualifying += line["net_item_minor"] - refunded[key] - discount_retired
    return eligible_remaining, total_remaining, eligible_refunded, qualifying


def allocate_refund(session, order, refund, allocation, *, actor):
    found = state_for(session, order)
    if found is None:
        return
    snapshot, state, data = found
    if (
        not isinstance(allocation, dict)
        or set(allocation) != {"lines", "delivery_fee_minor"}
        or not isinstance(allocation["lines"], dict)
    ):
        raise ValidationError("Refund allocation requires lines and delivery_fee_minor")
    amounts = [*allocation["lines"].values(), allocation["delivery_fee_minor"]]
    if (
        any(type(value) is not int or value < 0 for value in amounts)
        or sum(amounts) != refund.amount_minor
    ):
        raise ValidationError("Allocation must exactly match confirmed refund amount")
    if set(allocation["lines"]) - set(data["line_ids"].values()):
        raise ValidationError("Allocation includes a foreign order line")
    serialized = json.dumps(allocation, sort_keys=True)
    existing = session.get(Allocation, refund.id)
    if existing:
        if existing.document != serialized:
            raise ValidationError("Confirmed refund allocation is immutable")
        return
    session.add(
        Allocation(refund_id=refund.id, order_id=order.id, document=serialized, actor=actor)
    )
    session.flush()
    # Validate ALL known allocations even while another refund awaits review.
    known = session.scalars(select(Allocation).where(Allocation.order_id == order.id)).all()
    totals = {}
    fee = 0
    for row in known:
        values = json.loads(row.document)
        fee += values["delivery_fee_minor"]
        for line, amount in values["lines"].items():
            totals[line] = totals.get(line, 0) + amount
    paid = {
        data["line_ids"][line["line_id"]]: line["net_item_minor"] - line["reward_discount_minor"]
        for line in data["calculation"]["lines"]
    }
    if fee > order.delivery_fee_minor or any(amount > paid[key] for key, amount in totals.items()):
        raise ValidationError("Cumulative refund allocation exceeds original consideration")


def compensate(growth, order, *, full=False):
    found = state_for(growth.session, order)
    if found is None:
        return False
    session = growth.session
    snapshot, state, data = found
    account = growth.ensure_account(order.business_id, order.customer_id, for_update=True)
    remaining = remaining_spend(session, order, data, full=full)
    if remaining is None:
        return True  # Durable confirmed refund remains visible, no invented allocation.
    rules = StrategyDocument.model_validate_json(
        session.get(LoyaltyStrategyVersion, snapshot.version_id).document
    )
    desired = min(state.issued_points, entitlement(rules, remaining[0], remaining[3]))
    baseline = min(state.baseline_points, baseline_entitlement(data, remaining[1]))
    reverse = state.issued_points - desired - state.reversed_points
    reverse_base = state.baseline_points - baseline - state.reversed_baseline
    spent = data["calculation"]["redemption"]["points_spent"]
    denominator = data["calculation"]["eligible_item_spend_minor_after_reward"]
    target = spent if full else spent * remaining[2] // denominator if denominator else 0
    if state.status == "released":
        target = state.restored_points  # Cancellation already returned the reservation.
    credit = target - state.restored_points
    if reverse < 0 or reverse_base < 0 or credit < 0:
        raise ValidationError("Refund compensation cannot move backwards")
    # One deterministic cumulative identity, independent of callback chunking.
    key = (
        f"loyalty-refund:{order.id}:{int(full)}:{state.reversed_points + reverse}:"
        f"{state.reversed_baseline + reverse_base}:{target}"
    )
    if session.scalar(select(Ledger.id).where(Ledger.idempotency_key == key)):
        return True
    account.available_points += credit
    account.lifetime_redeemed_points -= credit
    row = entry(
        session, account, key=key, reason="loyalty.refund_credit", points=credit, order_id=order.id
    )
    restore(session, account, row, "loyalty-reserve:" + order.id, state.restored_points, target)
    expired_source = session.scalar(
        select(func.coalesce(func.sum(Lot.expired_points), 0)).where(Lot.order_id == order.id)
    )
    retired = min(reverse, max(0, expired_source - state.retired_reversal_points))
    reversed_total = reverse + reverse_base
    recoverable = reversed_total - retired
    recovered = min(recoverable, account.available_points)
    account.available_points -= recovered
    account.lifetime_earned_points -= reversed_total
    debit = entry(
        session,
        account,
        key=key + ":reverse",
        reason="loyalty.refund_reversal",
        points=-recovered,
        order_id=order.id,
    )
    consume(session, account, debit, recovered, preferred_order=order.id)
    if recovered < recoverable:
        debt = session.scalar(
            select(LoyaltyRefundDebt)
            .where(LoyaltyRefundDebt.order_id == order.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if debt is None:
            debt = LoyaltyRefundDebt(order_id=order.id, account_id=account.id, remaining_points=0)
            session.add(debt)
        debt.remaining_points += recoverable - recovered
    state.retired_reversal_points += retired
    state.reversed_points += reverse
    state.reversed_baseline += reverse_base
    state.restored_points = target
    event(session, snapshot, row, restored_points=credit)
    event(
        session,
        snapshot,
        debit,
        reversed_points=reverse,
        reversed_baseline=reverse_base,
        debt_points=recoverable - recovered,
        retired_points=retired,
    )
    if full:
        adjust_budget(session, snapshot, state, order, -state.reserved_minor, 0)
        state.status = "refunded"
        redemption = session.scalar(
            select(RewardRedemption).where(RewardRedemption.order_id == order.id)
        )
        if redemption:
            redemption.status, redemption.released_at = "released", utcnow()
        promotion = session.scalar(
            select(PromotionRedemption).where(PromotionRedemption.order_id == order.id)
        )
        if promotion:
            promotion.status, promotion.released_at = "released", utcnow()
    session.flush()
    growth._settle_refund_debt(account, order.id, key)
    session.flush()
    return True


def resolve_refund_allocation(service, refund_id, allocation, *, business_id, actor):
    """Trusted financial-owner adapter; callers must authorize actor and own commit."""
    refund = service.session.get(PaymentRefund, refund_id)
    if not refund:
        raise ValidationError("Confirmed refund not found")
    payment = service.session.scalar(
        select(Payment)
        .where(Payment.id == refund.payment_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = service.session.scalar(
        select(Order)
        .where(Order.id == payment.order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order.business_id != business_id or not actor or not marked(order):
        raise ValidationError("Refund allocation scope or actor invalid")
    allocate_refund(service.session, order, refund, allocation, actor=actor)
    from .growth import RestaurantGrowthService

    growth = RestaurantGrowthService(service.session)
    compensate(growth, order, full=payment.status == "refunded")
    if order.status == "completed":
        lifecycle(growth, order, "earn")
