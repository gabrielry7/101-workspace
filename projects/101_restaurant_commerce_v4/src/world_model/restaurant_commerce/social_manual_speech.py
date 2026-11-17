"""Owner-supplied source-timed captions. No inferred words, timings or ASR receipt."""

# ruff: noqa: B008 -- FastAPI dependencies
import hashlib
import time
from uuid import UUID

from fastapi import Depends
from pydantic import Field, model_validator
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from .models import StaffAccount, utcnow
from .social_production import Asset, canonical, require
from .social_speech_contracts import Correction
from .social_speech_models import Transcript
from .social_video_contracts import Strict


class ManualSegment(Correction):
    # Captions retain actual source ranges supplied by the owner; no word alignment is inferred.
    start: int = Field(ge=0, le=30000, strict=True)
    end: int = Field(ge=1, le=30000, strict=True)


class ManualInput(Strict):
    request_id: UUID
    segments: list[ManualSegment] = Field(min_length=1, max_length=40)
    confirmed: bool

    @model_validator(mode="after")
    def complete(self):
        if not self.confirmed or [s.index for s in self.segments] != list(
            range(len(self.segments))
        ):
            raise ValueError("manual_captions_review_required")
        return self


def ranges(words, duration):
    # Probe tolerance admits 30.1s files; the editable EDL ends at 30s.
    duration = min(duration, 30000)
    previous = 0
    for word in words:
        require(
            previous <= word["start"] < word["end"] <= duration, "manual_caption_times_invalid", 422
        )
        require(word["end"] - word["start"] >= 80, "subtitle_timing_too_short", 422)
        previous = word["end"]


def create(session, business, asset_id, payload, principal):
    from .social_job_models import ProductionAttempt, ProductionJob
    from .social_jobs import usage
    from .social_speech import check_row, view
    from .social_subtitles import layout
    from .social_video import clip_check
    from .social_video_contracts import Segment

    started = time.monotonic()
    # Same source lock as withdrawal; a late source deletion cannot leave fresh text behind.
    session.execute(update(Asset).where(Asset.id == asset_id).values(revoked=Asset.revoked))
    _, meta = clip_check(session, business, asset_id)
    require(meta["shot_id"] == "process", "speech_answer_slot_required", 422)
    require(meta["media"]["has_audio"], "speech_audio_missing_rerecord", 422)
    words = [
        {**s.model_dump(), "probability": None, "uncertain": True, "owner_supplied": True}
        for s in payload.segments
    ]
    ranges(words, meta["media"]["duration_ms"])
    # Check glyphs/line fit before saving; these are caption segments, never guessed word times.
    layout(
        words,
        Segment(
            shot_id="process",
            asset_id=asset_id,
            source_in=0,
            source_out=min(meta["media"]["duration_ms"], 30000),
            timeline_start=0,
        ),
        granularity="segments",
    )
    account = session.get(StaffAccount, principal.actor_id)
    require(account is not None and account.active, "staff_account_required", 403)
    request_hash = hashlib.sha256(canonical(payload.model_dump(mode="json")).encode()).hexdigest()
    identifier = hashlib.sha256(
        canonical([business, asset_id, str(payload.request_id)]).encode()
    ).hexdigest()[:32]
    old = session.get(ProductionJob, identifier)
    if old:
        require(
            old.business_id == business
            and old.asset_id == asset_id
            and old.input_hash == request_hash,
            "manual_transcript_idempotency_conflict",
        )
        return view(session, check_row(session, business, identifier))
    now = time.time()
    inputs = {
        "source_sha256": meta["sha256"],
        "source_asset_id": asset_id,
        "recipe_version": "owner-caption-intake-v1",
        "input_method": "owner_supplied_segments",
        "request_id": str(payload.request_id),
    }
    # This is a completed synchronous validation operation, not a pretend recognition job.
    job = ProductionJob(
        id=identifier,
        business_id=business,
        asset_id=asset_id,
        pack_id=None,
        base_revision=0,
        kind="subtitle_manual",
        request_key=identifier,
        input_hash=request_hash,
        input_json=canonical(inputs),
        actor_id=principal.actor_id,
        auth_version=account.auth_version,
        state="succeeded",
        generation=1,
        created_at=now,
        updated_at=now,
    )
    source = {
        "schema_version": "1",
        "language": "es",
        "words": words,
        "origin": "owner_supplied",
        "granularity": "segments",
        "quality": "owner_supplied_unverified",
        "uncertainty": "not_automatically_transcribed",
        "source_sha256": meta["sha256"],
        "actor_id": principal.actor_id,
        "recorded_at": utcnow().isoformat(),
        "runtime": None,
    }
    record = usage()
    record.update(
        recipe_version=inputs["recipe_version"],
        input_method="owner_supplied_segments",
        elapsed_ms=round((time.monotonic() - started) * 1000),
        output_bytes=len(canonical(source).encode()),
        asr_dispatch_started=False,
        provider_cost_basis="owner_input_no_provider_call",
    )
    session.add(job)
    session.flush()
    session.add(
        ProductionAttempt(
            id=identifier + ":1",
            job_id=identifier,
            generation=1,
            worker="synchronous_owner_caption_validation",
            state="succeeded",
            started_at=now,
            finished_at=time.time(),
            usage_json=canonical(record),
        )
    )
    session.add(
        Transcript(
            id=identifier,
            business_id=business,
            asset_id=asset_id,
            source_sha256=meta["sha256"],
            machine_json=canonical(source),
            raw_json=canonical({"origin": "owner_supplied", "request_id": str(payload.request_id)}),
            revision=0,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        old = session.get(ProductionJob, identifier)
        require(
            old is not None and old.input_hash == request_hash,
            "manual_transcript_idempotency_conflict",
        )
    return view(session, check_row(session, business, identifier))


def register(app, root, get_session, write):
    @app.post(root + "/video/takes/{asset_id}/manual-subtitles")
    def save(
        business_id: str,
        asset_id: str,
        payload: ManualInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        return create(session, business_id, asset_id, payload, principal)
