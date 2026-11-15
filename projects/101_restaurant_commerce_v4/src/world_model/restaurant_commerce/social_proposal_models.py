"""Scoped immutable proposal inputs/output and explicit owner review decisions."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Proposal(Base):
    __tablename__ = "social_proposals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("social_production_jobs.id"), unique=True)
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(24))


class ProposalDecision(Base):
    __tablename__ = "social_proposal_decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("social_proposals.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    document: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float]


TABLES = {"social_proposals", "social_proposal_decisions"}
