"""Retire refunded issuance on return and preserve replacement-point provenance.

All calls hold the account lock. Never acquire another Order/State lock here:
refund writers acquire those before the account. Cross-order facts are appended
against immutable snapshots, with ledger anchors owned by the triggering order.
"""

import json

from sqlalchemy import func, select

from .errors import ValidationError
from .loyalty_execution_models import LoyaltyExecutionEvent as Event
from .loyalty_execution_models import LoyaltyLotMovement as Movement
from .loyalty_execution_models import LoyaltyOrderSnapshot as Snapshot
from .loyalty_execution_models import LoyaltyOrderState as State
from .loyalty_execution_models import LoyaltyPointLot as Lot
from .models import LoyaltyLedgerEntry as Ledger
from .models import LoyaltyRefundDebt as Debt


def facts(session, source):
    return [
        (ledger, json.loads(event.details))
        for event, ledger in session.execute(
            select(Event, Ledger)
            .join(Ledger, Ledger.id == Event.ledger_id)
            .where(Event.order_id == source)
            .order_by(Ledger.created_at.desc(), Ledger.id.desc())
        )
    ]


def external_expired_retired(session, source):
    return sum(
        detail.get("external_expired_retired_points", 0)
        for _, detail in facts(session, source)
    )


def record_repayment(session, debt, ledger):
    from .loyalty_execution_migrations import installed

    if not installed(session):
        return
    snapshot = session.get(Snapshot, debt.order_id)
    if snapshot:
        from .loyalty_execution import event

        event(session, snapshot, ledger, refund_debt_id=debt.id)


def retire_sources(session, account, sources, trigger, valid_returns):
    from .loyalty_execution import event
    from .loyalty_wallet import entry, restore

    pending = set(sources) | set(valid_returns)
    while pending:
        source = pending.pop()
        returned = valid_returns.pop(source, {})
        session.flush()
        # Read columns, without refreshing/locking another writer's mutable ORM
        # state. That writer cannot advance accounting while we own this account.
        state = session.execute(
            select(State.reversed_points, State.retired_reversal_points).where(
                State.order_id == source
            )
        ).first()
        if state is None:
            continue
        history = facts(session, source)
        external = sum(
            detail.get("external_retired_points", 0) for _, detail in history
        )
        expired = session.scalar(
            select(func.coalesce(func.sum(Lot.expired_points), 0)).where(
                Lot.order_id == source, Lot.account_id == account.id
            )
        )
        owed = max(0, state.reversed_points - state.retired_reversal_points - external)
        expired_used = sum(
            detail.get("external_expired_retired_points", 0) for _, detail in history
        )
        expired_amount = min(
            owed, max(0, expired - state.retired_reversal_points - expired_used)
        )
        valid_amount = min(owed - expired_amount, sum(returned.values()))
        amount = expired_amount + valid_amount
        if amount <= 0:
            continue
        snapshot = session.get(Snapshot, source)
        debt = session.scalar(
            select(Debt)
            .where(Debt.order_id == source)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        forgiven = min(amount, debt.remaining_points if debt else 0)
        to_restore = amount - forgiven
        undone = {}
        for _, detail in history:
            if "recovery_ledger_id" in detail:
                key = detail["recovery_ledger_id"]
                undone[key] = undone.get(key, 0) + detail["recovery_restored_points"]
        recoveries = [
            (ledger, detail)
            for ledger, detail in history
            if ledger.reason in {"loyalty.refund_reversal", "refund.debt_repaid"}
        ]
        # Pre-upgrade, non-hashed repayment keys also retain exact debt identity.
        known = {ledger.id for ledger, _ in recoveries}
        if debt:
            for ledger in session.scalars(
                select(Ledger).where(
                    Ledger.account_id == account.id,
                    Ledger.reason == "refund.debt_repaid",
                    Ledger.idempotency_key.endswith(":" + debt.id),
                )
            ):
                if ledger.id not in known:
                    recoveries.append((ledger, {}))
        recoveries.sort(key=lambda pair: (pair[0].created_at, pair[0].id), reverse=True)
        if (
            sum(
                max(0, -ledger.delta_points - undone.get(ledger.id, 0))
                for ledger, _ in recoveries
            )
            < to_restore
        ):
            raise ValidationError(
                "Historical refund repayment provenance requires financial review"
            )
        anchor = entry(
            session,
            account,
            key=f"lot-retire:{trigger.id}:{source}:{external + amount}",
            reason="loyalty.refund_retired",
            points=0,
            order_id=trigger.order_id,
        )
        event(
            session,
            snapshot,
            anchor,
            external_retired_points=amount,
            external_expired_retired_points=expired_amount,
            debt_retired_points=forgiven,
            trigger_ledger_id=trigger.id,
        )
        if valid_amount:
            account.available_points -= valid_amount
            debit = entry(
                session,
                account,
                key="retire-return:" + anchor.id,
                reason="loyalty.refunded_return_retired",
                points=-valid_amount,
                order_id=trigger.order_id,
            )
            event(session, snapshot, debit, returned_source_retired_points=valid_amount)
            left = valid_amount
            for ordinal, (lot_id, returned_points) in enumerate(
                sorted(returned.items())
            ):
                used = min(left, returned_points)
                if not used:
                    break
                lot = session.get(Lot, lot_id)
                lot.available_points -= used
                session.add(
                    Movement(
                        lot_id=lot.id,
                        ledger_id=debit.id,
                        delta_points=-used,
                        ordinal=ordinal,
                    )
                )
                left -= used
        if forgiven:
            debt.remaining_points -= forgiven
        # The most recently recovered value replaces returned source points first;
        # restore suffixes so still-expired original-source value is never revived.
        for ledger, _ in recoveries:
            end = -ledger.delta_points - undone.get(ledger.id, 0)
            restored = min(to_restore, max(0, end))
            if not restored:
                continue
            account.available_points += restored
            credit = entry(
                session,
                account,
                key=f"retire-credit:{anchor.id}:{ledger.id}",
                reason="loyalty.refund_recovery_returned",
                points=restored,
                order_id=trigger.order_id,
            )
            event(
                session,
                snapshot,
                credit,
                recovery_ledger_id=ledger.id,
                recovery_restored_points=restored,
                trigger_ledger_id=trigger.id,
            )
            expired_sources, more_returns = restore(
                session,
                account,
                credit,
                ledger.idempotency_key,
                end - restored,
                end,
                retire=False,
            )
            pending.update(expired_sources)
            pending.update(more_returns)
            for returned_source, lots in more_returns.items():
                target = valid_returns.setdefault(returned_source, {})
                for lot_id, points in lots.items():
                    target[lot_id] = target.get(lot_id, 0) + points
            to_restore -= restored
            if not to_restore:
                break
        session.flush()
