# ruff: noqa: B008 -- FastAPI dependencies
"""Explicit quality judgments and exact-artifact approval; no learned taste score."""

from __future__ import annotations

import hashlib
import io
import json
import secrets
import time
from types import SimpleNamespace
from typing import Literal
from uuid import UUID

from fastapi import Depends
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, update

from .social_review_models import Comparison, ReviewEvent

CONTRACT = "social-review-v1"
DIMS = ("technical", "factual", "craft", "brand_fit", "purpose")
TAGS = (
    "crowded_type",
    "weak_hierarchy",
    "awkward_crop",
    "unnatural_color",
    "generic_copy",
    "unclear_action",
    "brand_mismatch",
    "clear_message",
    "balanced_layout",
    "natural_appearance",
    "useful_explanation",
    "other",
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criterion(Strict):
    verdict: Literal["acceptable", "needs_changes", "uncertain"]
    reason: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def explanation(self):
        if self.verdict != "acceptable" and not self.reason.strip():
            raise ValueError("explain_nonacceptance")
        return self


class Assessment(Strict):
    request_id: UUID
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    outcome: Literal["ready", "changes_requested", "rejected"]
    technical: Criterion
    factual: Criterion
    craft: Criterion
    brand_fit: Criterion
    purpose: Criterion
    reason: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def ready(self):
        if not self.reason.strip():
            raise ValueError("review_reason_required")
        if self.outcome == "ready" and any(getattr(self, d).verdict != "acceptable" for d in DIMS):
            raise ValueError("unresolved_review_criterion")
        return self


class PairInput(Strict):
    request_id: UUID
    a_revision: int = Field(ge=1)
    b_revision: int = Field(ge=1)
    a_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    b_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    criterion: Literal["craft", "brand_fit", "purpose"]


class Vote(Strict):
    request_id: UUID
    context_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    choice: Literal["a", "b", "tie", "both_unacceptable", "insufficient_context"]
    reason: str = Field(min_length=1, max_length=1000)
    tags: list[
        Literal[
            "crowded_type",
            "weak_hierarchy",
            "awkward_crop",
            "unnatural_color",
            "generic_copy",
            "unclear_action",
            "brand_mismatch",
            "clear_message",
            "balanced_layout",
            "natural_appearance",
            "useful_explanation",
            "other",
        ]
    ] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def reason_required(self):
        if not self.reason.strip() or len(set(self.tags)) != len(self.tags):
            raise ValueError("review_reason_or_tags_invalid")
        return self


def current_time():
    # Use the existing production clock for all validity and action boundaries.
    from .social_production import utcnow

    return utcnow()


def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(v):
    return hashlib.sha256(canonical(v).encode()).hexdigest()


def require(condition, reason, status=409):
    from .social_production import require as check

    check(condition, reason, status)


def latest(session, revision_id, kind):
    return session.scalar(
        select(ReviewEvent)
        .where(ReviewEvent.revision_id == revision_id, ReviewEvent.kind == kind)
        .order_by(ReviewEvent.sequence.desc())
        .limit(1)
    )


def events(session, revision_id):
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "sequence": r.sequence,
            "actor_id": r.actor_id,
            "at": r.created_at,
            **json.loads(r.document),
        }
        for r in session.scalars(
            select(ReviewEvent)
            .where(ReviewEvent.revision_id == revision_id)
            .order_by(ReviewEvent.sequence)
        )
    ]


def scope(rev, doc):
    return {
        "business_id": doc["business_id"],
        "revision_id": rev.id,
        "digest": rev.digest,
        "image_sha256": hashlib.sha256(rev.image).hexdigest(),
        "caption_sha256": hashlib.sha256(doc["caption"].encode()).hexdigest(),
        "editable_sha256": hashlib.sha256(rev.document.encode()).hexdigest(),
        "asset_id": doc["brief"]["asset_id"],
        "source_sha256": doc["asset_sha256"],
        "facts_sha256": digest([doc["brief"]["facts"], doc["brief"].get("fact_refs", [])]),
        "brand_sha256": digest(doc.get("creative_snapshot")),
        "scene_sha256": doc.get("design", {}).get("sha256") if doc.get("design") else None,
        "intended_action": doc["intended_action"],
        "destination": doc.get("destination_account"),
    }


def technical(rev):
    defects = []
    try:
        with Image.open(io.BytesIO(rev.image)) as im:
            im.load()
            if im.size != (1080, 1350) or im.format != "JPEG":
                defects.append("image_dimensions_or_format")
    except (UnidentifiedImageError, OSError, ValueError):
        defects.append("image_decode")
    if (
        hashlib.sha256((rev.document + hashlib.sha256(rev.image).hexdigest()).encode()).hexdigest()
        != rev.digest
    ):
        defects.append("artifact_digest_changed")
    if json.loads(rev.report).get("technical") != "passed":
        defects.append("renderer_checks_not_passed")
    return {
        "status": "passed" if not defects else "blocked",
        "defects": defects,
        "source": "deterministic_output_checks",
        "renderer_report": json.loads(rev.report),
    }


def effective_approval(session, rev, doc):
    from .social_production import Approval

    assessment = latest(session, rev.id, "assessment")
    approved = latest(session, rev.id, "approval")
    if assessment:
        if not approved:
            return None
        a, b = json.loads(assessment.document), json.loads(approved.document)
        if (
            a["outcome"] != "ready"
            or b["review_id"] != assessment.id
            or b["scope"] != scope(rev, doc)
        ):
            return None
        return SimpleNamespace(
            actor_id=approved.actor_id,
            digest=rev.digest,
            approved_at=b["approved_at"],
            review_id=assessment.id,
            event_id=approved.id,
            scope=b["scope"],
            mode="structured",
        )
    if doc.get("review_contract") == CONTRACT:
        return None
    old = session.get(Approval, rev.id)
    return old if old and old.digest == rev.digest else None


def ever_approved(session, revision_id):
    from .social_production import Approval

    return (
        session.get(Approval, revision_id) is not None
        or latest(session, revision_id, "approval") is not None
    )


def state(session, rev, doc, stale=False):
    assessment = latest(session, rev.id, "assessment")
    if stale:
        return "needs_input"
    if effective_approval(session, rev, doc):
        return "approved"
    if assessment:
        return {
            "ready": "ready_to_approve",
            "changes_requested": "changes_requested",
            "rejected": "rejected",
        }[json.loads(assessment.document)["outcome"]]
    return "ready_for_review"


def record(session, rev, business, actor, kind, key, payload):
    # Caller locks the current Pack/Revision first: sequence is independent of wall-clock order.
    identifier = digest([business, rev.id, actor, kind, str(key)])[:32]
    old = session.get(ReviewEvent, identifier)
    if old:
        require(old.document == canonical(payload), "review_idempotency_conflict")
        return old
    sequence = (
        session.scalar(
            select(func.max(ReviewEvent.sequence)).where(ReviewEvent.revision_id == rev.id)
        )
        or 0
    ) + 1
    row = ReviewEvent(
        id=identifier,
        business_id=business,
        revision_id=rev.id,
        sequence=sequence,
        kind=kind,
        actor_id=actor,
        document=canonical(payload),
        created_at=time.time(),
    )
    session.add(row)
    session.flush()
    return row


def lock_context(session, doc):
    from .social_context import Context, ContextVersion

    version_id = doc["brief"].get("context_version_id")
    if version_id:
        version = session.get(ContextVersion, version_id)
        if version:
            session.scalar(
                select(Context)
                .where(Context.id == version.context_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )


def locked_current(session, business, pack_id):
    from .social_production import Asset, Pack, Revision, current, owned

    # Match render's context -> brand -> pack ordering. A material edit cannot
    # race past a ready/approval/export decision; old revision history stays intact.
    candidate = owned(session, Pack, pack_id, business)
    lock_context(
        session, json.loads(session.get(Revision, f"{pack_id}:{candidate.revision}").document)
    )
    pack, revision, doc, _ = current(session, business, pack_id, current_time())
    expected = pack.revision
    session.scalar(
        select(Asset)
        .where(Asset.id == doc["brief"]["asset_id"])
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session.execute(
        update(Pack)
        .where(Pack.id == pack_id, Pack.business_id == business)
        .values(revision=Pack.revision)
    )
    session.expire_all()
    result = current(session, business, pack_id, current_time())
    require(result[0].revision == expected, "review_version_changed")
    return result


def approve(session, business, pack_id, payload, principal):

    pack, rev, doc, old = locked_current(session, business, pack_id)
    require(rev.digest == payload.digest, "approval_changed")
    assessment = latest(session, rev.id, "assessment")
    if doc.get("review_contract") == CONTRACT or assessment:
        require(
            assessment is not None and payload.review_id == assessment.id,
            "structured_review_required",
        )
        value = json.loads(assessment.document)
        require(
            value["outcome"] == "ready" and value["scope"] == scope(rev, doc), "review_not_ready"
        )
        require(technical(rev)["status"] == "passed", "technical_review_blocked")
        if not (old and getattr(old, "review_id", None) == assessment.id):
            record(
                session,
                rev,
                business,
                principal.actor_id,
                "approval",
                assessment.id,
                {
                    "review_id": assessment.id,
                    "scope": scope(rev, doc),
                    "approved_at": current_time().isoformat(),
                },
            )
    else:
        require(
            payload.craft_reviewed and payload.brand_reviewed and payload.purpose_reviewed,
            "legacy_review_required",
        )
        if old is None:
            from .social_production import Approval

            session.add(
                Approval(
                    revision_id=rev.id,
                    actor_id=principal.actor_id,
                    digest=rev.digest,
                    approved_at=current_time().isoformat(),
                )
            )
    session.commit()


def preference_context(doc):
    b = doc["brief"]
    return {
        "business_id": doc["business_id"],
        "location_id": b.get("location_id"),
        "brief": {
            k: b.get(k)
            for k in [
                "objective",
                "hypothesis",
                "question",
                "question_source",
                "question_evidence",
                "primary_measure",
                "context_version_id",
                "creative_version_id",
                "reference_ids",
                "question_id",
                "handoff",
            ]
        },
        "facts": [f for f in b["facts"] if not f["id"].startswith("design_owned_")],
        "fact_refs": b.get("fact_refs", []),
        "business_brief": doc.get("business_brief"),
        "brand": doc.get("creative_snapshot"),
        "intended_action": doc["intended_action"],
        "destination": doc.get("destination_account"),
    }


def validate_pair_source(session, business, rev):
    from .social_context import stale_reasons
    from .social_creative import stale_reasons as brand_stale
    from .social_production import asset_check, future

    doc = json.loads(rev.document)
    lock_context(session, doc)
    now = current_time()
    asset_check(session, doc["brief"]["asset_id"], business, now)
    require(
        not stale_reasons(session, business, doc, now)
        and not brand_stale(session, business, doc, now),
        "comparison_context_changed",
    )
    require(
        all(future(f["valid_until"], now) for f in doc["brief"]["facts"]), "comparison_fact_expired"
    )
    require(technical(rev)["status"] == "passed", "comparison_output_changed")
    return doc


def pair_info(row):
    return {
        "id": row.id,
        "reviewer_id": row.actor_id,
        **json.loads(row.document),
        "vote": json.loads(row.vote_json) if row.vote_json else None,
    }


def register(app, get_session, read, write):
    from .social_production import Pack, Revision, document, owned

    root = "/api/operator/restaurants/{business_id}/social"

    @app.get(root + "/review-queue", dependencies=[Depends(read)])
    def queue(business_id: str, cursor: str | None = None, session=Depends(get_session)):
        query = select(Pack).where(Pack.business_id == business_id).order_by(Pack.id).limit(21)
        if cursor:
            query = query.where(Pack.id > cursor)
        rows = list(session.scalars(query))
        items = []
        for row in rows[:20]:
            p = document(session, business_id, row.id, current_time())
            items.append(
                {
                    "id": row.id,
                    "revision": row.revision,
                    "title": p["document"]["brief"]["question"],
                    "status": p["review_state"],
                }
            )
        return {
            "items": items,
            "next_cursor": rows[19].id if len(rows) > 20 else None,
            "coverage": "page_of_saved_work",
        }

    @app.get(root + "/packs/{pack_id}/reviews", dependencies=[Depends(read)])
    def reviews(business_id: str, pack_id: str, session=Depends(get_session)):
        p = document(session, business_id, pack_id, current_time())
        rev = session.get(Revision, f"{pack_id}:{p['revision']}")
        return {
            "revision": p["revision"],
            "digest": p["digest"],
            "scope": scope(rev, p["document"]),
            "state": p["review_state"],
            "technical": technical(rev),
            "events": events(session, rev.id),
            "commercial": {"value": None, "reason": "not_measured", "source": None},
            "reason_tags": TAGS,
            "legacy_approval": p["approved"]
            and not p["document"].get("review_contract")
            and not latest(session, rev.id, "assessment"),
        }

    @app.post(root + "/packs/{pack_id}/reviews")
    def assess(
        business_id: str,
        pack_id: str,
        payload: Assessment,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        _, rev, doc, _ = locked_current(session, business_id, pack_id)
        require(payload.digest == rev.digest, "review_version_changed")
        check = technical(rev)
        if payload.outcome == "ready":
            require(check["status"] == "passed", "technical_review_blocked")
        value = payload.model_dump(mode="json")
        value.update(
            scope=scope(rev, doc),
            technical_checks=check,
            commercial={"value": None, "reason": "not_measured"},
        )
        row = record(
            session, rev, business_id, principal.actor_id, "assessment", payload.request_id, value
        )
        session.commit()
        return {"id": row.id, "state": state(session, rev, doc)}

    @app.get(root + "/packs/{pack_id}/comparisons", dependencies=[Depends(read)])
    def comparisons(business_id: str, pack_id: str, session=Depends(get_session)):
        owned(session, Pack, pack_id, business_id)
        return {
            "comparisons": [
                pair_info(r)
                for r in session.scalars(
                    select(Comparison)
                    .where(Comparison.business_id == business_id, Comparison.pack_id == pack_id)
                    .order_by(Comparison.created_at.desc())
                    .limit(20)
                )
            ]
        }

    @app.post(root + "/packs/{pack_id}/comparisons")
    def present(
        business_id: str,
        pack_id: str,
        payload: PairInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        pack = owned(session, Pack, pack_id, business_id)
        require(payload.a_revision != payload.b_revision, "distinct_comparison_required")
        revisions = [
            session.get(Revision, f"{pack_id}:{n}")
            for n in [payload.a_revision, payload.b_revision]
        ]
        require(all(revisions), "comparison_revision_not_found", 404)
        raw_contexts = [preference_context(json.loads(r.document)) for r in revisions]
        require(raw_contexts[0] == raw_contexts[1], "comparison_brief_mismatch")
        docs = [validate_pair_source(session, business_id, r) for r in revisions]
        from .social_production import Asset

        for asset_id in sorted({d["brief"]["asset_id"] for d in docs}):
            session.scalar(
                select(Asset)
                .where(Asset.id == asset_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        session.execute(update(Pack).where(Pack.id == pack.id).values(revision=Pack.revision))
        docs = [validate_pair_source(session, business_id, r) for r in revisions]
        require(
            [r.digest for r in revisions] == [payload.a_digest, payload.b_digest],
            "comparison_output_changed",
        )
        context = preference_context(docs[0])
        require(context == preference_context(docs[1]), "comparison_brief_mismatch")
        require(
            digest([hashlib.sha256(revisions[0].image).hexdigest(), docs[0]["caption"]])
            != digest([hashlib.sha256(revisions[1].image).hexdigest(), docs[1]["caption"]]),
            "distinct_comparison_required",
        )
        identifier = digest([business_id, pack_id, principal.actor_id, str(payload.request_id)])[
            :32
        ]
        old = session.get(Comparison, identifier)
        if old:
            require(
                json.loads(old.document)["request"] == payload.model_dump(mode="json"),
                "comparison_idempotency_conflict",
            )
            return pair_info(old)
        order = [0, 1] if secrets.randbits(1) == 0 else [1, 0]
        sides = [
            {
                "revision": int(revisions[i].id.rsplit(":", 1)[1]),
                "digest": revisions[i].digest,
                "caption": docs[i]["caption"],
                "asset_id": docs[i]["brief"]["asset_id"],
                "source_sha256": docs[i]["asset_sha256"],
            }
            for i in order
        ]
        value = {
            "request": payload.model_dump(mode="json"),
            "criterion": payload.criterion,
            "context": context,
            "context_sha256": digest(context),
            "a": sides[0],
            "b": sides[1],
            "presentation_order": "randomized",
            "blinding": (
                "Version choices and recognizable content remain visible; not a blind study"
            ),
            "allowed_use": "private_workspace_review_only",
            "brief_id": pack_id,
            "recorded_at": current_time().isoformat(),
        }
        row = Comparison(
            id=identifier,
            business_id=business_id,
            pack_id=pack_id,
            actor_id=principal.actor_id,
            document=canonical(value),
            created_at=time.time(),
        )
        session.add(row)
        session.commit()
        return pair_info(row)

    @app.post(root + "/comparisons/{comparison_id}/vote")
    def vote(
        business_id: str,
        comparison_id: str,
        payload: Vote,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        row = owned(session, Comparison, comparison_id, business_id)
        session.execute(
            update(Comparison)
            .where(Comparison.id == row.id)
            .values(created_at=Comparison.created_at)
        )
        session.refresh(row)
        require(row.actor_id == principal.actor_id, "comparison_reviewer_mismatch", 403)
        pair = json.loads(row.document)
        require(payload.context_sha256 == pair["context_sha256"], "comparison_context_changed")
        revisions = [
            session.get(Revision, f"{row.pack_id}:{pair[side]['revision']}") for side in ["a", "b"]
        ]
        docs = [validate_pair_source(session, business_id, rev) for rev in revisions]
        from .social_production import Asset

        for asset_id in sorted({doc["brief"]["asset_id"] for doc in docs}):
            session.scalar(
                select(Asset)
                .where(Asset.id == asset_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        for side in ["a", "b"]:
            ref = pair[side]
            rev = session.get(Revision, f"{row.pack_id}:{ref['revision']}")
            doc = validate_pair_source(session, business_id, rev)
            require(
                rev.digest == ref["digest"]
                and digest(preference_context(doc)) == pair["context_sha256"],
                "comparison_context_changed",
            )
        value = payload.model_dump(mode="json")
        value.update(
            reviewer_id=principal.actor_id, acceptance_scope="this_business_brief_and_pair_only"
        )
        if row.vote_json:
            require(row.vote_json == canonical(value), "comparison_already_voted")
        else:
            row.vote_json = canonical(value)
            session.commit()
        return pair_info(row)
