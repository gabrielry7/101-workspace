"""Source-bound machine speech and separately versioned owner corrections."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Transcript(Base):
    __tablename__ = "social_transcripts"
    id: Mapped[str] = mapped_column(ForeignKey("social_production_jobs.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("social_assets.id"), index=True)
    source_sha256: Mapped[str] = mapped_column(String(64))
    machine_json: Mapped[str] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(default=0)


class TranscriptEdit(Base):
    __tablename__ = "social_transcript_edits"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("social_transcripts.id"), index=True)
    document: Mapped[str] = mapped_column(Text)


TABLES = {"social_transcripts", "social_transcript_edits"}
