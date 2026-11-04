"""Lot attribution under the existing account lock. Never creates a parallel balance."""

from datetime import UTC

from sqlalchemy import func, select

from .errors import ValidationError
from .loyalty_execution_migrations import installed
from .loyalty_execution_models import LoyaltyLotMovement as Movement
from .loyalty_execution_models import LoyaltyPointLot as Lot
from .models import LoyaltyLedgerEntry as Ledger
from .models import utcnow


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def entry(session, account, *, key, reason, points, order_id=None, redemption_id=None):
    row = Ledger(
        account_id=account.id,
        order_id=order_id,
        redemption_id=redemption_id,
        delta_points=points,
        reason=reason,
        idempotency_key=key,
    )
    session.add(row)
    session.flush()
    return row


def consume(session, account, ledger, points, *, preferred_order=None):
    if points <= 0 or not installed(session):
        return
    lots = session.scalars(
        select(Lot)
        .where(Lot.account_id == account.id, Lot.available_points > 0)
        .order_by(Lot.expires_at.asc().nulls_last(), Lot.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    if preferred_order:
        lots.sort(key=lambda lot: lot.order_id != preferred_order)
    for index, lot in enumerate(lots):
        amount = min(points, lot.available_points)
        if not amount:
            break
        lot.available_points -= amount
        session.add(
            Movement(lot_id=lot.id, ledger_id=ledger.id, delta_points=-amount, ordinal=index)
        )
        points -= amount
    session.flush()
    # Remainder is pre-execution points with unknown provenance/expiry.


def restore(session, account, ledger, source_key, old_target, new_target, *, at=None):
    """Restore a monotone prefix of original consumption; expired lots stay expired."""
    if not installed(session) or new_target <= old_target:
        return
    original = session.scalar(select(Ledger).where(Ledger.idempotency_key == source_key))
    if original is None or original.account_id != account.id:
        raise ValidationError("Original redemption ledger is missing")
    movements = session.scalars(
        select(Movement)
        .where(Movement.ledger_id == original.id)
        .order_by(Movement.ordinal, Movement.id)
    ).all()
    offset = 0
    expired = 0
    expired_movements = []
    at = aware(at or utcnow())
    for movement in movements:
        size = -movement.delta_points
        amount = max(0, min(new_target, offset + size) - max(old_target, offset))
        offset += size
        if not amount:
            continue
        lot = session.scalar(
            select(Lot)
            .where(Lot.id == movement.lot_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if lot.expires_at and aware(lot.expires_at) <= at:
            expired += amount
            lot.expired_points += amount
            expired_movements.append((lot.id, amount, movement.ordinal))
        else:
            lot.available_points += amount
        session.add(
            Movement(
                lot_id=lot.id, ledger_id=ledger.id, delta_points=amount, ordinal=movement.ordinal
            )
        )
    if expired:
        account.available_points -= expired
        expiry_entry = entry(
            session,
            account,
            key="restore-expiry:" + ledger.id,
            reason="loyalty.restored_expired",
            points=-expired,
            order_id=ledger.order_id,
        )
        for lot_id, amount, ordinal in expired_movements:
            session.add(
                Movement(
                    lot_id=lot_id, ledger_id=expiry_entry.id, delta_points=-amount, ordinal=ordinal
                )
            )
    session.flush()


def expire(session, account, *, at=None):
    if not installed(session):
        return 0
    at = aware(at or utcnow())
    lots = session.scalars(
        select(Lot)
        .where(Lot.account_id == account.id, Lot.available_points > 0, Lot.expires_at <= at)
        .order_by(Lot.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    total = 0
    for lot in lots:
        points = lot.available_points
        account.available_points -= points
        row = entry(
            session,
            account,
            key="lot-expire:" + lot.id,
            reason="loyalty.expired",
            points=-points,
            order_id=lot.order_id,
        )
        lot.available_points = 0
        lot.expired_points += points
        session.add(Movement(lot_id=lot.id, ledger_id=row.id, delta_points=-points, ordinal=0))
        total += points
    session.flush()
    return total


def reconcile(session, account):
    """Legacy differences are reported, not repaired or assigned invented versions."""
    session.flush()
    session.refresh(account, with_for_update=True)
    ledger_balance = session.scalar(
        select(func.coalesce(func.sum(Ledger.delta_points), 0)).where(
            Ledger.account_id == account.id
        )
    )
    lots = session.scalars(
        select(Lot).where(Lot.account_id == account.id).execution_options(populate_existing=True)
    ).all()
    mismatches = []
    for lot in lots:
        moved = session.scalar(
            select(func.coalesce(func.sum(Movement.delta_points), 0)).where(
                Movement.lot_id == lot.id
            )
        )
        if lot.original_points + moved != lot.available_points:
            mismatches.append(lot.id)
    tracked = sum(lot.available_points for lot in lots)
    return {
        "available_points": account.available_points,
        "ledger_balance": ledger_balance,
        "ledger_difference": account.available_points - ledger_balance,
        "tracked_points": tracked,
        "legacy_unattributed_points": account.available_points - tracked,
        "legacy_cost_minor": None if account.available_points > tracked else 0,
        "cost_coverage": "tracked_lots_only",
        "lot_mismatches": mismatches,
        "estimated_outstanding_cost_minor": sum(
            lot.available_points * lot.cost_per_point_minor for lot in lots
        ),
        "expected_outstanding_cost_minor": sum(
            lot.available_points * lot.cost_per_point_minor * lot.redemption_bps for lot in lots
        )
        // 10000,
        "reconciled": ledger_balance == account.available_points
        and tracked <= account.available_points
        and not mismatches,
    }


def expire_due_accounts(session, *, at=None, limit=100):
    """Bounded maintenance consumer. Caller commits; due reservations remain untouched."""
    from .models import LoyaltyAccount

    if not installed(session):
        return {"accounts": 0, "expired_points": 0}
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValidationError("Expiration batch limit must be between 1 and 1000")
    at = aware(at or utcnow())
    due = select(Lot.account_id).where(Lot.available_points > 0, Lot.expires_at <= at)
    accounts = session.scalars(
        select(LoyaltyAccount)
        .where(LoyaltyAccount.id.in_(due))
        .order_by(LoyaltyAccount.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    ).all()
    return {
        "accounts": len(accounts),
        "expired_points": sum(expire(session, account, at=at) for account in accounts),
    }
