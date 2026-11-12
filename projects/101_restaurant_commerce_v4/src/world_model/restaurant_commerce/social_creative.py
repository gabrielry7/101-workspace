"""Owner-curated brand references and sourced questions, never measured demand.

Independent of business assertions. Models do not fetch URLs, infer permission,
copy reference assets into output, or learn style from a factual correction.
"""

# ruff: noqa: B008 -- FastAPI dependencies
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import AwareDatetime, Field, HttpUrl, model_validator
from sqlalchemy import ForeignKey, String, Text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, utcnow
from .social_context import read_context, scope_id
from .social_production import Asset, Strict, canonical, future, require

TABLES = {"social_creative_boards", "social_creative_versions"}
QUESTION_SOURCES = Literal[
    "owner_suggestion", "customer_question", "platform_observation", "manual_research", "hypothesis"
]


class CreativeBoard(Base):
    __tablename__ = "social_creative_boards"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(
        ForeignKey("restaurant_commerce_profiles.business_id"), index=True
    )
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision: Mapped[int] = mapped_column(default=0)


class CreativeVersion(Base):
    __tablename__ = "social_creative_versions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    board_id: Mapped[str] = mapped_column(ForeignKey("social_creative_boards.id"), index=True)
    document: Mapped[str] = mapped_column(Text)


class Sourced(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    source: str = Field(min_length=1, max_length=500)
    observed_at: AwareDatetime
    valid_until: AwareDatetime
    status: Literal["active", "withdrawn"] = "active"

    @model_validator(mode="after")
    def dates(self):
        if self.observed_at > datetime.now(UTC) or self.valid_until <= self.observed_at:
            raise ValueError("invalid_observation_dates")
        return self


class Reference(Sourced):
    title: str = Field(min_length=1, max_length=150)
    kind: Literal["photography", "layout", "writing", "video"]
    judgment: Literal["positive", "negative", "borderline"]
    purpose: Literal["local_competitor", "remote_comparable", "creative_reference", "own_brand"]
    reason: str = Field(min_length=1, max_length=600)
    permission: str = Field(min_length=8, max_length=600)
    allowed_use: Literal["internal_reference_only"] = "internal_reference_only"
    url: HttpUrl | None = None
    excerpt: str = Field(default="", max_length=1200)
    asset_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def material(self):
        if not (self.url or self.excerpt.strip() or self.asset_id):
            raise ValueError("reference_material_required")
        if self.url and (self.url.username or self.url.password):
            raise ValueError("reference_url_credentials_forbidden")
        return self


class Question(Sourced):
    text: str = Field(min_length=1, max_length=300)
    source_kind: QUESTION_SOURCES
    intent: Literal[
        "local_discovery", "product_understanding", "comparison", "buying_occasion", "how_to_buy"
    ]
    answer_fact_ids: list[str] = Field(default_factory=list, max_length=12)
    next_action: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def answers(self):
        if len(set(self.answer_fact_ids)) != len(self.answer_fact_ids):
            raise ValueError("duplicate_answer_fact")
        return self


class CreativeInput(Strict):
    expected_revision: int = Field(ge=0)
    location_id: UUID | None = None
    visual_direction: str = Field(default="", max_length=600)
    voice_rules: str = Field(default="", max_length=600)
    references: list[Reference] = Field(default_factory=list, max_length=30)
    questions: list[Question] = Field(default_factory=list, max_length=30)
    change_kind: Literal["brand_preference", "reference_review", "question_research"]
    change_reason: str = Field(min_length=1, max_length=500)
    confirmed: Literal[True]

    @model_validator(mode="after")
    def unique(self):
        for entries in (self.references, self.questions):
            if len({r.id for r in entries}) != len(entries):
                raise ValueError("duplicate_creative_id")
        return self


def read_board(session, business, location=None, *, lock=False):
    query = select(CreativeBoard).where(CreativeBoard.id == scope_id(business, location))
    if lock:
        query = query.with_for_update()
    board = session.scalar(query)
    if not board:
        return {
            "revision": 0,
            "style_revision": 0,
            "business_id": business,
            "location_id": location,
            "visual_direction": "",
            "voice_rules": "",
            "references": [],
            "questions": [],
        }
    return json.loads(session.get(CreativeVersion, f"{board.id}:{board.revision}").document)


def reference_available(session, business, ref, now):
    require(ref["status"] == "active", "reference_withdrawn")
    require(future(ref["valid_until"], now), "reference_expired")
    if ref.get("asset_id"):
        asset = session.get(Asset, ref["asset_id"])
        require(
            asset is not None and asset.business_id == business, "reference_asset_not_found", 404
        )
        require(not asset.revoked and bool(asset.original), "reference_asset_revoked")
        require(
            future(json.loads(asset.metadata_json)["expires_at"], now), "reference_asset_expired"
        )


def snapshot(session, business, payload, now):
    """Resolve only the selected version/items, and compare relevant current content."""
    vid = payload.creative_version_id
    require(vid or not (payload.reference_ids or payload.question_id), "creative_version_required")
    if not vid:
        return None
    version = session.get(CreativeVersion, vid)
    require(version is not None, "creative_version_not_found", 404)
    board = session.get(CreativeBoard, version.board_id)
    location = str(payload.location_id) if payload.location_id else None
    require(
        board.business_id == business and board.location_id == location,
        "creative_scope_mismatch",
        404,
    )
    old = json.loads(version.document)
    current = read_board(session, business, location, lock=True)
    require(
        old["style_revision"] == current["style_revision"],
        "brand_direction_changed",
    )
    references = []
    for identifier in payload.reference_ids:
        previous = next((r for r in old["references"] if r["id"] == identifier), None)
        latest = next((r for r in current["references"] if r["id"] == identifier), None)
        require(previous is not None and previous == latest, "reference_changed")
        reference_available(session, business, previous, now)
        references.append(previous)
    question = None
    if payload.question_id:
        question = next((q for q in old["questions"] if q["id"] == payload.question_id), None)
        latest = next((q for q in current["questions"] if q["id"] == payload.question_id), None)
        require(question is not None and question == latest, "question_changed")
        require(
            question["status"] == "active" and future(question["valid_until"], now),
            "question_unavailable",
        )
        require(question["answer_fact_ids"], "question_needs_confirmed_answer")
        require(
            set(question["answer_fact_ids"]) <= {r.fact_id for r in payload.fact_refs},
            "answer_facts_not_selected",
        )
        require(
            payload.question == question["text"]
            and payload.question_source == question["source_kind"]
            and payload.question_evidence == question["source"],
            "question_source_mismatch",
        )
    return {
        "version_id": vid,
        "visual_direction": old["visual_direction"],
        "voice_rules": old["voice_rules"],
        "references": references,
        "question": question,
        "search_volume": None,
        "demand_reason": "not_measured",
        "authority": "owner_curated_reference_not_business_fact",
    }


def stale_reasons(session, business, document, now):
    if not document["brief"].get("creative_version_id"):
        return []
    from .social_production import Brief

    try:
        snapshot(session, business, Brief.model_validate(document["brief"]), now)
        return []
    except HTTPException as error:
        return [{"reason": error.detail}]


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social/creative"

    def scope(business, location):
        if location:
            resolver = getattr(app.state, "social_location_belongs_to_business", None)
            require(resolver is not None, "canonical_location_validation_unavailable", 503)
            require(resolver(business, location), "location_not_in_business", 404)

    @app.get(root, dependencies=[Depends(read)])
    def get(business_id: str, location_id: UUID | None = None, session=Depends(get_session)):
        location = str(location_id) if location_id else None
        scope(business_id, location)
        result = read_board(session, business_id, location)
        # Measured demand is absent, including for manually observed platform queries.
        return {**result, "search_volume": None, "demand_reason": "not_measured"}

    @app.put(root)
    def put(
        business_id: str,
        payload: CreativeInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        location = str(payload.location_id) if payload.location_id else None
        scope(business_id, location)
        previous = read_board(session, business_id, location)
        require(previous["revision"] == payload.expected_revision, "creative_revision_conflict")
        now = utcnow()
        fact_ids = {f["id"] for f in read_context(session, business_id, location)["facts"]}
        for question in payload.questions:
            require(set(question.answer_fact_ids) <= fact_ids, "answer_fact_not_in_business", 422)
        for ref in payload.references:
            if ref.status == "active":
                reference_available(session, business_id, ref.model_dump(mode="json"), now)
        value = payload.model_dump(
            mode="json", exclude={"expected_revision", "confirmed", "location_id"}
        )
        # Independent item revisions prevent old approvals reviving after withdrawal/re-add.
        for group in ("references", "questions"):
            old_items = {r["id"]: r for r in previous[group]}
            current_ids = {r["id"] for r in value[group]}
            for item in value[group]:
                old = old_items.get(item["id"])
                unchanged = old and all(old.get(k) == v for k, v in item.items())
                item["revision"] = (
                    old["revision"] if unchanged else (old["revision"] + 1 if old else 1)
                )
                item["reviewed_by"] = old["reviewed_by"] if unchanged else principal.actor_id
                item["reviewed_at"] = old["reviewed_at"] if unchanged else now.isoformat()
            value[group] += [
                {
                    **r,
                    "status": "withdrawn",
                    "revision": r["revision"] + (r["status"] != "withdrawn"),
                }
                for r in previous[group]
                if r["id"] not in current_ids
            ]
        value["style_revision"] = previous["style_revision"] + int(
            any(previous[key] != value[key] for key in ("visual_direction", "voice_rules"))
        )
        cid = scope_id(business_id, location)
        board = session.get(CreativeBoard, cid)
        if board:
            result = session.execute(
                update(CreativeBoard)
                .where(CreativeBoard.id == cid, CreativeBoard.revision == payload.expected_revision)
                .values(revision=CreativeBoard.revision + 1)
            )
            require(result.rowcount == 1, "creative_revision_conflict")
            session.refresh(board)
        else:
            board = CreativeBoard(id=cid, business_id=business_id, location_id=location, revision=1)
            session.add(board)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "creative_revision_conflict") from None
        vid = f"{cid}:{board.revision}"
        value.update(
            id=vid,
            revision=board.revision,
            business_id=business_id,
            location_id=location,
            reviewed_by=principal.actor_id,
            reviewed_at=now.isoformat(),
        )
        session.add(CreativeVersion(id=vid, board_id=cid, document=canonical(value)))
        session.commit()
        return {**value, "search_volume": None, "demand_reason": "not_measured"}

    @app.get(root + "/history", dependencies=[Depends(read)])
    def history(business_id: str, location_id: UUID | None = None, session=Depends(get_session)):
        location = str(location_id) if location_id else None
        scope(business_id, location)
        return {
            "versions": [
                json.loads(v.document)
                for v in session.scalars(
                    select(CreativeVersion)
                    .where(CreativeVersion.board_id == scope_id(business_id, location))
                    .order_by(CreativeVersion.id)
                )
            ]
        }
