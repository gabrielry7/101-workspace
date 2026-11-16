"""Video derivatives inherit source permission; original media stays in Asset."""

from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class Shoot(Base):
    __tablename__ = "social_shoots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    pack_id: Mapped[str] = mapped_column(ForeignKey("social_packs.id"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"))
    document: Mapped[str] = mapped_column(Text)


class ClipMedia(Base):
    __tablename__ = "social_video_media"
    asset_id: Mapped[str] = mapped_column(ForeignKey("social_assets.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    analysis: Mapped[bytes] = mapped_column(LargeBinary)
    poster: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[float] = mapped_column(index=True)


class VideoOutput(Base):
    __tablename__ = "social_video_outputs"
    revision_id: Mapped[str] = mapped_column(ForeignKey("social_revisions.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    final: Mapped[bytes] = mapped_column(LargeBinary)
    preview: Mapped[bytes] = mapped_column(LargeBinary)
    cover: Mapped[bytes] = mapped_column(LargeBinary)


TABLES = {"social_shoots", "social_video_media", "social_video_outputs"}
