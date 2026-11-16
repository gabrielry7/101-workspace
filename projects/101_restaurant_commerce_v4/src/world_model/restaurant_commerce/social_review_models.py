"""Immutable scoped review/approval events and private pairwise labels."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class ReviewEvent(Base):
    __tablename__ = "social_review_events"
    __table_args__ = (UniqueConstraint("revision_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"), index=True)
    sequence: Mapped[int]
    kind: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[str] = mapped_column(String(64))
    document: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float]


class Comparison(Base):
    __tablename__ = "social_review_comparisons"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    pack_id: Mapped[str] = mapped_column(ForeignKey("social_packs.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    document: Mapped[str] = mapped_column(Text)
    vote_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float]


TABLES = {"social_review_events", "social_review_comparisons"}
