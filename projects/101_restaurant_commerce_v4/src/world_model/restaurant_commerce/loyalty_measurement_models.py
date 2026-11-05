"""Append-only financial evidence. Canonical orders/cohorts remain their owners."""

from datetime import datetime

from sqlalchemy import (
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


class LoyaltyFinancialEvidence(Base):
    __tablename__ = "restaurant_loyalty_financial_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("restaurant_orders.id"), nullable=True, index=True
    )
    variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("restaurant_loyalty_experiment_variants.id"),
        nullable=True,
        index=True,
    )
    target: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(Integer)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("restaurant_loyalty_financial_evidence.id"),
        nullable=True,
        unique=True,
    )
    request_key: Mapped[str] = mapped_column(String(100))
    request_digest: Mapped[str] = mapped_column(String(64))
    financial_digest: Mapped[str] = mapped_column(String(64))
    document: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(500))
    actor_id: Mapped[str] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("business_id", "request_key"),
        UniqueConstraint("business_id", "target", "revision"),
        CheckConstraint("revision > 0", name="ck_loyalty_evidence_revision"),
        CheckConstraint(
            "(order_id IS NULL) <> (variant_id IS NULL)",
            name="ck_loyalty_evidence_target",
        ),
    )


MEASUREMENT_TABLES = frozenset({LoyaltyFinancialEvidence.__tablename__})
