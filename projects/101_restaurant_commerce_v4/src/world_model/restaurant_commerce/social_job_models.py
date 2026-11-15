"""Durable local production queue: existing SQL lease/generation pattern."""

from sqlalchemy import ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class ProductionJob(Base):
    __tablename__ = "social_production_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("social_assets.id"), index=True)
    pack_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_revision: Mapped[int]
    kind: Mapped[str] = mapped_column(String(32))
    request_key: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("business_id", "request_key"),)
    input_hash: Mapped[str] = mapped_column(String(64))
    input_json: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(String(64))
    auth_version: Mapped[int]
    state: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation: Mapped[int] = mapped_column(default=0)
    lease: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[float]
    updated_at: Mapped[float]
    result_bytes: Mapped[bytes] = mapped_column(LargeBinary, default=b"")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_revision: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ProductionAttempt(Base):
    __tablename__ = "social_production_attempts"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("social_production_jobs.id"), index=True)
    generation: Mapped[int]
    worker: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(24))
    started_at: Mapped[float]
    finished_at: Mapped[float | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usage_json: Mapped[str] = mapped_column(Text)


class ProductionEffort(Base):
    __tablename__ = "social_production_effort"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("social_production_jobs.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))
    seconds: Mapped[int]
    recorded_at: Mapped[float]


TABLES = {"social_production_jobs", "social_production_attempts", "social_production_effort"}
