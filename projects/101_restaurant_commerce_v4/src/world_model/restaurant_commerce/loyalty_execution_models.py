"""Execution projections and append-only provenance; the existing wallet is authoritative."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, new_id, utcnow


class LoyaltyOrderSnapshot(Base):
    __tablename__ = "restaurant_loyalty_order_snapshots"
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id"), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_strategy_versions.id"))
    document: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoyaltyOrderState(Base):
    __tablename__ = "restaurant_loyalty_order_states"
    order_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_order_snapshots.order_id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), default="reserved")
    issued_points: Mapped[int] = mapped_column(Integer, default=0)
    baseline_points: Mapped[int] = mapped_column(Integer, default=0)
    reversed_points: Mapped[int] = mapped_column(Integer, default=0)
    retired_reversal_points: Mapped[int] = mapped_column(Integer, default=0)
    reversed_baseline: Mapped[int] = mapped_column(Integer, default=0)
    restored_points: Mapped[int] = mapped_column(Integer, default=0)
    reserved_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    committed_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    completed: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (
        CheckConstraint(
            "issued_points >= reversed_points AND reversed_points >= 0 AND "
            "baseline_points >= reversed_baseline AND reversed_baseline >= 0 AND "
            "retired_reversal_points >= 0 AND retired_reversal_points <= reversed_points AND "
            "restored_points >= 0 AND reserved_minor >= 0 AND committed_minor >= 0",
            name="ck_loyalty_execution_counters",
        ),
        CheckConstraint(
            "status IN ('reserved','applied','released','refunded')",
            name="ck_loyalty_execution_status",
        ),
    )


class LoyaltyBudget(Base):
    __tablename__ = "restaurant_loyalty_budgets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_strategies.id"))
    scope: Mapped[str] = mapped_column(
        String(64)
    )  # '*' or customer ID; same strategy across versions
    reserved_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    committed_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": revision}
    __table_args__ = (
        UniqueConstraint("strategy_id", "scope"),
        CheckConstraint(
            "reserved_minor >= 0 AND committed_minor >= 0", name="ck_loyalty_budget_nonnegative"
        ),
    )


class LoyaltyPointLot(Base):
    __tablename__ = "restaurant_loyalty_point_lots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_accounts.id"), index=True
    )
    ledger_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_ledger.id"), unique=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_strategy_versions.id"))
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id"))
    original_points: Mapped[int] = mapped_column(Integer)
    available_points: Mapped[int] = mapped_column(Integer)
    expired_points: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_point_minor: Mapped[int] = mapped_column(BigInteger)
    redemption_bps: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint(
            "available_points >= 0 AND expired_points >= 0 AND "
            "available_points + expired_points <= original_points",
            name="ck_loyalty_lot_balance",
        ),
    )


class LoyaltyLotMovement(Base):
    __tablename__ = "restaurant_loyalty_lot_movements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    lot_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_point_lots.id"))
    ledger_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_ledger.id"))
    delta_points: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("lot_id", "ledger_id"),)


class LoyaltyExecutionEvent(Base):
    __tablename__ = "restaurant_loyalty_execution_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_order_snapshots.order_id"))
    version_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_strategy_versions.id"))
    ledger_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_ledger.id"), unique=True)
    details: Mapped[str] = mapped_column(Text)


class LoyaltyRefundAllocation(Base):
    __tablename__ = "restaurant_loyalty_refund_allocations"
    refund_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_payment_refunds.id"), primary_key=True
    )
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_order_snapshots.order_id"))
    document: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


EXECUTION_TABLES = frozenset(
    c.__tablename__
    for c in (
        LoyaltyOrderSnapshot,
        LoyaltyOrderState,
        LoyaltyBudget,
        LoyaltyPointLot,
        LoyaltyLotMovement,
        LoyaltyExecutionEvent,
        LoyaltyRefundAllocation,
    )
)
IMMUTABLE_EXECUTION_TABLES = (
    LoyaltyOrderSnapshot.__table__,
    LoyaltyLotMovement.__table__,
    LoyaltyExecutionEvent.__table__,
    LoyaltyRefundAllocation.__table__,
)
