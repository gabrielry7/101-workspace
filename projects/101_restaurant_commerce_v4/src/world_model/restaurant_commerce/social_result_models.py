"""Versioned manual receipts and immutable sourced outcome/decision records."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Publication(Base):
    __tablename__ = "social_publications"
    __table_args__ = (
        UniqueConstraint("business_id", "identity_key"),
        UniqueConstraint("business_id", "native_key"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    pack_id: Mapped[str] = mapped_column(ForeignKey("social_packs.id"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"))
    identity_key: Mapped[str] = mapped_column(String(64))
    native_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[int]
    event_sequence: Mapped[int] = mapped_column(default=0)
    request_json: Mapped[str] = mapped_column(Text)


class PublicationVersion(Base):
    __tablename__ = "social_publication_versions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    publication_id: Mapped[str] = mapped_column(ForeignKey("social_publications.id"), index=True)
    document: Mapped[str] = mapped_column(Text)


class ResultEvent(Base):
    __tablename__ = "social_result_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    pack_id: Mapped[str] = mapped_column(ForeignKey("social_packs.id"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"))
    publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_publications.id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(24))
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_result_events.id"), nullable=True
    )
    sequence: Mapped[int]
    actor_id: Mapped[str] = mapped_column(String(64))
    document: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float]


TABLES = {"social_publications", "social_publication_versions", "social_result_events"}
