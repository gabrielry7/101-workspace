"""Scoped, versioned research projection; not canonical business/query identity."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class ResearchBoard(Base):
    __tablename__ = "social_research_boards"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision: Mapped[int] = mapped_column(default=0)


class ResearchVersion(Base):
    __tablename__ = "social_research_versions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    board_id: Mapped[str] = mapped_column(ForeignKey("social_research_boards.id"), index=True)
    document: Mapped[str] = mapped_column(Text)


class AutomatedReview(Base):
    __tablename__ = "social_automated_reviews"
    id: Mapped[str] = mapped_column(ForeignKey("social_production_jobs.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    pack_id: Mapped[str] = mapped_column(ForeignKey("social_packs.id"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"))
    mode: Mapped[str] = mapped_column(String(16))
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_json: Mapped[str | None] = mapped_column(Text, nullable=True)


TABLES = {"social_research_boards", "social_research_versions", "social_automated_reviews"}
