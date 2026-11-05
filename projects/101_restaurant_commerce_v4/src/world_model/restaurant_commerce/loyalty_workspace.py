"""Passive financial projections over the existing wallet and immutable history.

No earning, expiration, reconciliation, enrollment or account creation on reads.
Recorded balances and historical estimated cost are distinct quantities.
"""

import json
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .loyalty_baseline import data
from .loyalty_execution_migrations import installed
from .loyalty_models import LoyaltyStrategy, LoyaltyStrategyVersion
from .models import (
    Customer,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    LoyaltyRefundDebt,
    Order,
    Payment,
    RestaurantCommerceProfile,
    utcnow,
)
from .refunds import PaymentRefund


def overview(session, business_id):
    # Authorization has already read through the request session. Use a separate
    # committed read snapshot so PostgreSQL READ COMMITTED and sqlite3's legacy
    # SELECT behavior cannot mix balances from different earning/refund commits.
    engine = session.get_bind()
    with engine.connect() as connection:
        if connection.dialect.name == "postgresql":
            connection = connection.execution_options(isolation_level="REPEATABLE READ")
        with connection.begin():
            if connection.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN")
            elif connection.dialect.name == "postgresql":
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            with Session(bind=connection, autoflush=False) as snapshot:
                return _overview(snapshot, business_id)


def _overview(session, business_id):
    from .loyalty_execution_models import (
        LoyaltyBudget,
        LoyaltyExecutionEvent,
        LoyaltyPointLot,
    )

    now = utcnow()
    execution = installed(session)
    profile = session.get(RestaurantCommerceProfile, business_id)
    if profile is None:
        from .errors import NotFoundError

        raise NotFoundError("Business not found")
    tracked = defaultdict(int)
    costs = {}
    if execution:
        lots = session.execute(
            select(
                LoyaltyPointLot.account_id,
                LoyaltyPointLot.available_points,
                LoyaltyPointLot.cost_per_point_minor,
                LoyaltyPointLot.redemption_bps,
                LoyaltyPointLot.expires_at,
                Order.currency,
            )
            .join(Order, Order.id == LoyaltyPointLot.order_id)
            .where(
                Order.business_id == business_id, LoyaltyPointLot.available_points > 0
            )
            .execution_options(yield_per=500)
        )
        for account, points, cost, probability, expires, currency in lots:
            from .loyalty_wallet import aware

            due = expires is not None and aware(expires) <= now
            tracked[account] += points
            row = costs.setdefault(
                currency,
                {
                    "currency": currency,
                    "recorded_cost_minor": 0,
                    "expected_cost_numerator": 0,
                    "due_expiry_points": 0,
                    "due_expiry_cost_minor": 0,
                    "tracked_points": 0,
                },
            )
            row["tracked_points"] += points
            row["recorded_cost_minor"] += points * cost
            row["expected_cost_numerator"] += points * cost * probability
            if due:
                row["due_expiry_points"] += points
                row["due_expiry_cost_minor"] += points * cost
    balances = {
        "accounts": 0,
        "available_points": 0,
        "earned_points": 0,
        "redeemed_points": 0,
        "unattributed_points": 0,
        "lot_balance_mismatches": 0,
    }
    for account in session.scalars(
        select(LoyaltyAccount)
        .where(LoyaltyAccount.business_id == business_id)
        .execution_options(yield_per=500)
    ):
        balances["accounts"] += 1
        balances["available_points"] += account.available_points
        balances["earned_points"] += account.lifetime_earned_points
        balances["redeemed_points"] += account.lifetime_redeemed_points
        difference = account.available_points - tracked.get(account.id, 0)
        balances["unattributed_points"] += max(0, difference)
        balances["lot_balance_mismatches"] += int(difference < 0)
    debts = sum(
        session.scalars(
            select(LoyaltyRefundDebt.remaining_points)
            .join(LoyaltyAccount, LoyaltyAccount.id == LoyaltyRefundDebt.account_id)
            .where(LoyaltyAccount.business_id == business_id)
        )
    )
    money = []
    for row in costs.values():
        expected = row.pop("expected_cost_numerator") // 10000
        money.append(
            {
                **{k: str(v) if k != "currency" else v for k, v in row.items()},
                "expected_cost_minor": str(expected),
            }
        )
    # A strategy has one campaign bucket and mirrored customer buckets. Only the
    # '*' bucket is a campaign total; committed issuance is NOT added to lot cost.
    budgets = []
    if execution:
        currencies = defaultdict(set)
        for sid, document in session.execute(
            select(
                LoyaltyStrategyVersion.strategy_id, LoyaltyStrategyVersion.document
            ).where(LoyaltyStrategyVersion.business_id == business_id)
        ):
            currencies[sid].add(json.loads(document)["currency"])
        for bucket, strategy in session.execute(
            select(LoyaltyBudget, LoyaltyStrategy)
            .join(LoyaltyStrategy, LoyaltyStrategy.id == LoyaltyBudget.strategy_id)
            .where(
                LoyaltyStrategy.business_id == business_id, LoyaltyBudget.scope == "*"
            )
        ):
            options = currencies[strategy.id]
            budgets.append(
                {
                    "program_id": strategy.id,
                    "name": json.loads(strategy.draft_json)["name"],
                    "currency": next(iter(options)) if len(options) == 1 else None,
                    "reserved_minor": str(bucket.reserved_minor),
                    "committed_minor": str(bucket.committed_minor),
                }
            )
    ledger_query = (
        select(LoyaltyLedgerEntry, Customer.name, Order.public_code)
        .join(LoyaltyAccount, LoyaltyAccount.id == LoyaltyLedgerEntry.account_id)
        .join(Customer, Customer.id == LoyaltyAccount.customer_id)
        .outerjoin(Order, Order.id == LoyaltyLedgerEntry.order_id)
        .where(LoyaltyAccount.business_id == business_id)
        .order_by(LoyaltyLedgerEntry.created_at.desc(), LoyaltyLedgerEntry.id.desc())
        .limit(20)
    )
    recent = list(session.execute(ledger_query))
    versions = (
        dict(
            session.execute(
                select(
                    LoyaltyExecutionEvent.ledger_id, LoyaltyExecutionEvent.version_id
                ).where(
                    LoyaltyExecutionEvent.ledger_id.in_(
                        [row.id for row, _, _ in recent]
                    )
                )
            ).all()
        )
        if execution
        else {}
    )
    return {
        "as_of": now,
        "currency": profile.currency,
        "wallets": {
            **{k: str(v) for k, v in balances.items()},
            "refund_debt_points": str(debts),
        },
        "costs": sorted(money, key=lambda r: r["currency"]),
        "budgets": budgets,
        "execution_history_available": execution,
        "legacy_cost_minor": None
        if balances["unattributed_points"] or not execution
        else "0",
        "refund_holds": refund_holds(session, business_id, execution),
        "financial_reviews": financial_reviews(session, business_id),
        "ledger": [
            {
                "id": row.id,
                "customer": name or "Sin nombre",
                "order_id": row.order_id,
                "order_code": code,
                "points": row.delta_points,
                "reason": row.reason,
                "at": row.created_at,
                "version_id": versions.get(row.id),
            }
            for row, name, code in recent
        ],
        "ledger_limit": 20,
        "cost_basis": "historical_lot_fulfillment_estimate",
        "cost_is_accounting_provision": False,
        "reads_mutate_wallet": False,
    }


def refund_holds(session, business_id, execution):
    from .loyalty_execution_models import LoyaltyRefundAllocation

    # Bound the review queue. A partial page is explicit; financial totals above
    # are not derived from this limited queue.
    orders = list(
        session.execute(
            select(Order, Customer.name)
            .join(Customer, Customer.id == Order.customer_id)
            .where(
                Order.business_id == business_id,
                Order.id.in_(
                    select(Payment.order_id)
                    .join(PaymentRefund)
                    .where(Payment.status != "refunded")
                ),
            )
            .order_by(Order.created_at.desc(), Order.id)
            .limit(101)
        )
    )
    ids = [order.id for order, _ in orders]
    refunds = defaultdict(list)
    for oid, rid, amount in session.execute(
        select(Payment.order_id, PaymentRefund.id, PaymentRefund.amount_minor)
        .join(PaymentRefund)
        .where(Payment.order_id.in_(ids))
    ):
        refunds[oid].append((rid, amount))
    allocated = (
        set(
            session.scalars(
                select(LoyaltyRefundAllocation.refund_id).where(
                    LoyaltyRefundAllocation.order_id.in_(ids)
                )
            )
        )
        if execution
        else set()
    )
    items = []
    for order, name in orders[:100]:
        snapshot = data(order)
        if not snapshot.get("identity_verified"):
            continue
        reasons = []
        if snapshot.get("loyalty_execution_version"):
            if not execution:
                reasons.append("execution_history_unavailable")
            elif any(rid not in allocated for rid, _ in refunds[order.id]):
                reasons.append("refund_allocation_required")
        elif not snapshot.get("baseline_policy"):
            reasons.append("historical_policy_missing")
        elif order.delivery_fee_minor:
            allocations = snapshot.get("baseline_refund_state", {}).get(
                "allocations", {}
            )
            if any(rid not in allocations for rid, _ in refunds[order.id]):
                reasons.append("refund_allocation_required")
        if reasons:
            items.append(
                {
                    "order_id": order.id,
                    "order_code": order.public_code,
                    "customer": name or "Sin nombre",
                    "currency": order.currency,
                    "refund_minor": str(sum(amount for _, amount in refunds[order.id])),
                    "reasons": reasons,
                }
            )
    return {
        "items": items,
        "orders_scanned": min(len(orders), 100),
        "scan_limit": 100,
        "truncated": len(orders) > 100,
    }


def eligibility_labels(
    session, business_id, kind, resource_id, version_id=None, expected_revision=None
):
    from .errors import ConcurrencyConflictError, NotFoundError
    from .loyalty_config import KINDS, LoyaltyConfigurationService
    from .models import Menu, MenuCategory, MenuItem

    config = LoyaltyConfigurationService(session, "read-projection")
    row = config._get(kind, business_id, resource_id)
    if version_id:
        _, model, _, parent = KINDS[kind]
        version = session.scalar(
            select(model).where(
                model.id == version_id,
                model.business_id == business_id,
                getattr(model, parent) == row.id,
            )
        )
        if version is None:
            raise NotFoundError("Published version not found")
        document = version.document
    else:
        if expected_revision is not None and row.revision != expected_revision:
            raise ConcurrencyConflictError(
                "Configuration changed; reload before review"
            )
        document = row.draft_json
    eligibility = json.loads(document)["eligibility"]
    customers = {
        cid: name or email or phone or "Sin nombre"
        for cid, name, email, phone in session.execute(
            select(Customer.id, Customer.name, Customer.email, Customer.phone).where(
                Customer.business_id == business_id,
                Customer.id.in_(eligibility["customer_ids"]),
            )
        )
    }
    ids = eligibility["included_product_ids"] + eligibility["excluded_product_ids"]
    products = dict(
        session.execute(
            select(MenuItem.id, MenuItem.name)
            .join(MenuCategory, MenuCategory.id == MenuItem.category_id)
            .join(Menu, Menu.id == MenuCategory.menu_id)
            .where(Menu.business_id == business_id, MenuItem.id.in_(ids))
        ).all()
    )
    return {
        "customers": [
            customers.get(cid) or "Cliente no disponible"
            for cid in eligibility["customer_ids"]
        ],
        "included": [
            products.get(pid) or "Producto no disponible"
            for pid in eligibility["included_product_ids"]
        ],
        "excluded": [
            products.get(pid) or "Producto no disponible"
            for pid in eligibility["excluded_product_ids"]
        ],
    }


def financial_reviews(session, business_id):
    from .models import PaymentReconciliation

    base = select(PaymentReconciliation).where(
        PaymentReconciliation.business_id == business_id,
        PaymentReconciliation.status == "open",
    )
    count = session.scalar(select(func.count()).select_from(base.subquery()))
    rows = session.execute(
        select(PaymentReconciliation, Order.public_code)
        .join(Order, Order.id == PaymentReconciliation.order_id)
        .where(
            PaymentReconciliation.business_id == business_id,
            Order.business_id == business_id,
            PaymentReconciliation.status == "open",
        )
        .order_by(PaymentReconciliation.created_at.desc(), PaymentReconciliation.id)
        .limit(20)
    ).all()
    return {
        "count": count,
        "limit": 20,
        "items": [
            {
                "id": r.id,
                "order_id": r.order_id,
                "order_code": code,
                "reason": r.reason,
                "at": r.created_at,
            }
            for r, code in rows
        ],
        "is_confirmed_refund": False,
    }
