"""Immutable enrollment, assignment and observation history. No second customer store."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, new_id, utcnow


class LoyaltyEnrollmentDecision(Base):
    __tablename__ = "restaurant_loyalty_enrollment_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64))
    experiment_version_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str | None] = mapped_column(
        ForeignKey("restaurant_customers.id"), nullable=True
    )
    eligible: Mapped[bool] = mapped_column(Boolean)
    reasons_json: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(String(128))
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["experiment_version_id", "business_id"],
            [
                "restaurant_loyalty_experiment_versions.id",
                "restaurant_loyalty_experiment_versions.business_id",
            ],
        ),
    )


class LoyaltyExperimentRun(Base):
    __tablename__ = "restaurant_loyalty_experiment_runs"
    experiment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(String(64))
    experiment_version_id: Mapped[str] = mapped_column(String(36), unique=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["experiment_id", "business_id"],
            ["restaurant_loyalty_experiments.id", "restaurant_loyalty_experiments.business_id"],
        ),
        ForeignKeyConstraint(
            ["experiment_version_id", "business_id"],
            [
                "restaurant_loyalty_experiment_versions.id",
                "restaurant_loyalty_experiment_versions.business_id",
            ],
        ),
    )


class LoyaltyAssignment(Base):
    __tablename__ = "restaurant_loyalty_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64))
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_experiment_runs.experiment_id")
    )
    experiment_version_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str] = mapped_column(ForeignKey("restaurant_customers.id"), index=True)
    eligibility_decision_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_enrollment_decisions.id"), unique=True
    )
    variant_id: Mapped[str] = mapped_column(ForeignKey("restaurant_loyalty_experiment_variants.id"))
    strategy_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    algorithm: Mapped[str] = mapped_column(String(32))
    bucket: Mapped[int] = mapped_column(Integer)
    exclusion_group: Mapped[str] = mapped_column(String(100), index=True)
    allow_overlap: Mapped[bool] = mapped_column(Boolean)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evaluation_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exclusion_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("business_id", "experiment_id", "customer_id"),
        UniqueConstraint("id", "business_id", "customer_id"),
        ForeignKeyConstraint(
            ["experiment_version_id", "business_id"],
            [
                "restaurant_loyalty_experiment_versions.id",
                "restaurant_loyalty_experiment_versions.business_id",
            ],
        ),
        ForeignKeyConstraint(
            ["strategy_version_id", "business_id"],
            [
                "restaurant_loyalty_strategy_versions.id",
                "restaurant_loyalty_strategy_versions.business_id",
            ],
        ),
        CheckConstraint(
            "algorithm = 'sha256-v1' AND bucket >= 0 AND bucket < 10000",
            name="ck_loyalty_assignment_algorithm",
        ),
        CheckConstraint(
            "assigned_at < evaluation_ends_at AND evaluation_ends_at <= exclusion_ends_at",
            name="ck_loyalty_assignment_windows",
        ),
    )


class LoyaltyAssignmentOverlap(Base):
    __tablename__ = "restaurant_loyalty_assignment_overlaps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    first_assignment_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_assignments.id")
    )
    second_assignment_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_loyalty_assignments.id")
    )
    evidence_json: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("first_assignment_id", "second_assignment_id"),
        CheckConstraint(
            "first_assignment_id < second_assignment_id", name="ck_loyalty_overlap_order"
        ),
    )


class LoyaltyAssignmentExposure(Base):
    __tablename__ = "restaurant_loyalty_assignment_exposures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(64))
    customer_id: Mapped[str] = mapped_column(String(36))
    assignment_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(32))
    surface: Mapped[str] = mapped_column(String(100))
    source_ref: Mapped[str] = mapped_column(String(200))
    warnings_json: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(String(128))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "business_id", "customer_id"],
            [
                "restaurant_loyalty_assignments.id",
                "restaurant_loyalty_assignments.business_id",
                "restaurant_loyalty_assignments.customer_id",
            ],
        ),
        UniqueConstraint("assignment_id", "kind", "surface", "source_ref"),
        CheckConstraint(
            "kind IN ('offer_surface_rendered','control_surface_rendered')",
            name="ck_loyalty_exposure_kind",
        ),
    )


class LoyaltyAssignmentOrder(Base):
    __tablename__ = "restaurant_loyalty_assignment_orders"
    order_id: Mapped[str] = mapped_column(ForeignKey("restaurant_orders.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(String(64))
    customer_id: Mapped[str] = mapped_column(String(36))
    experiment_id: Mapped[str] = mapped_column(String(36))
    assignment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_order_id: Mapped[str | None] = mapped_column(
        ForeignKey("restaurant_loyalty_order_snapshots.order_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(60))
    details_json: Mapped[str] = mapped_column(Text)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "business_id", "customer_id"],
            [
                "restaurant_loyalty_assignments.id",
                "restaurant_loyalty_assignments.business_id",
                "restaurant_loyalty_assignments.customer_id",
            ],
        ),
        ForeignKeyConstraint(
            ["experiment_id", "business_id"],
            ["restaurant_loyalty_experiments.id", "restaurant_loyalty_experiments.business_id"],
        ),
        CheckConstraint(
            "execution_order_id IS NULL OR execution_order_id = order_id",
            name="ck_loyalty_assignment_order_snapshot",
        ),
    )


ASSIGNMENT_TABLES = frozenset(
    c.__tablename__
    for c in (
        LoyaltyEnrollmentDecision,
        LoyaltyExperimentRun,
        LoyaltyAssignment,
        LoyaltyAssignmentOverlap,
        LoyaltyAssignmentExposure,
        LoyaltyAssignmentOrder,
    )
)
