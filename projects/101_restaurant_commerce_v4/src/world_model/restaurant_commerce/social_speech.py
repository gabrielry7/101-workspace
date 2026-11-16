"""Durable source-bound Spanish ASR and separate immutable owner corrections."""

# ruff: noqa: B008
import copy
import hashlib
import json
import time

from fastapi import Depends
from sqlalchemy import select, update

from .models import utcnow
from .social_production import canonical, owned, require
from .social_speech_contracts import EditInput, Machine
from .social_speech_models import Transcript, TranscriptEdit


def capability(app, business=None):
    adapter = getattr(app.state, "social_transcriber", None)
    authorized = adapter is not None and (business is None or adapter.authorize(business))
    return {
        "state": "configured" if authorized else "blocked",
        "reason": (
            None
            if authorized
            else "speech_runtime_unavailable"
            if adapter is None
            else "speech_processing_not_authorized"
        ),
        "runtime": adapter.identity if adapter else None,
        "live_verified": False,
        "quality": "requires_word_and_meaning_review",
        "language": "es",
        "paid_fallback": False,
    }


def check_row(session, business, identifier, *, lock=False):
    from .social_video import clip_check

    row = owned(session, Transcript, identifier, business)
    if lock:
        session.execute(
            update(Transcript).where(Transcript.id == row.id).values(revision=Transcript.revision)
        )
        session.refresh(row)
    _, meta = clip_check(session, business, row.asset_id)
    require(
        row.source_sha256 == meta["sha256"] and bool(row.machine_json),
        "transcript_source_unavailable",
    )
    return row


def view(session, row, revision=None):
    revision = row.revision if revision is None else revision
    require(0 <= revision <= row.revision, "transcript_revision_missing", 404)
    machine = json.loads(row.machine_json)
    edit = session.get(TranscriptEdit, f"{row.id}:{revision}") if revision else None
    corrected = (
        json.loads(edit.document)
        if edit
        else {"words": machine["words"], "revision": 0, "actor_id": None}
    )
    history = [
        json.loads(e.document)
        for e in session.scalars(
            select(TranscriptEdit)
            .where(TranscriptEdit.transcript_id == row.id)
            .order_by(TranscriptEdit.id)
        )
    ]
    history.sort(key=lambda x: x["revision"])
    return {
        "id": row.id,
        "asset_id": row.asset_id,
        "source_sha256": row.source_sha256,
        "revision": revision,
        "current_revision": row.revision,
        "machine": machine,
        "words": corrected["words"],
        "history": history,
        "review_required": True,
    }


def snapshot(session, business, timeline, *, lock=False, current=True):
    if not timeline.speech:
        return None
    row = check_row(session, business, timeline.speech.transcript_id, lock=lock)
    require(row.asset_id == timeline.clips[1].asset_id, "transcript_take_mismatch")
    require(not current or row.revision == timeline.speech.revision, "transcript_changed")
    value = view(session, row, timeline.speech.revision)
    from .social_subtitles import layout

    value["subtitle_plan"] = layout(value["words"], timeline.clips[1], timeline.speech.size)
    # Freeze only the selected revision's history. Later corrections cannot mutate an old snapshot.
    value["history"] = [h for h in value["history"] if h["revision"] <= value["revision"]]
    value.pop("current_revision")
    return value


def prepare(session, business, asset_id, app):
    from .social_video import clip_check

    _, meta = clip_check(session, business, asset_id)
    require(meta["shot_id"] == "process", "speech_answer_slot_required", 422)
    require(meta["media"]["has_audio"], "speech_audio_missing_rerecord", 422)
    adapter = getattr(app.state, "social_transcriber", None)
    require(adapter is not None, "speech_runtime_unavailable", 503)
    require(adapter.authorize(business), "speech_processing_not_authorized", 403)
    return {
        "speech_runtime": copy.deepcopy(adapter.identity),
        "duration_ms": meta["media"]["duration_ms"],
    }


def still_current(session, job, app):
    inputs = json.loads(job.input_json)
    state = prepare(session, job.business_id, job.asset_id, app)
    require(state == {k: inputs[k] for k in state}, "speech_runtime_changed")


def validate_result(data, duration_ms):
    result = Machine.model_validate(data)
    previous = 0
    for i, w in enumerate(result.words):
        require(
            w.index == i and w.start >= previous and w.end <= duration_ms + 50,
            "speech_timestamps_invalid",
            422,
        )
        previous = w.end
    return result.model_dump(mode="json")


def checkpoint(factory, app, jid, token):
    from . import social_jobs as jobs
    from .social_speech_audio import extract

    started = time.monotonic()
    with factory() as session:
        job = jobs.leased(session, jid, token)
        raw, inputs = jobs.input_check(session, job, app)
        if (
            job.checkpoint
            and job.result_json
            and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint
        ):
            attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
            usage = json.loads(attempt.usage_json)
            usage["checkpoint_reused"] = True
            attempt.usage_json = canonical(usage)
            session.commit()
            return
        session.rollback()
    audio, audio_info = extract(raw)
    # The adapter only receives normalized authorized audio, never credentials or archive paths.
    with factory() as session:
        job = jobs.leased(session, jid, token)
        jobs.input_check(session, job, app)
        attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        usage.update(
            model=inputs["speech_runtime"],
            model_calls=1,
            asr_dispatch_started=True,
            processing="self_hosted_asr",
            provider_cost_basis="self_hosted_no_provider_charge",
        )
        attempt.usage_json = canonical(usage)
        session.commit()
    try:
        response = app.state.social_transcriber.transcribe(audio, inputs["duration_ms"])
    finally:
        with factory() as session:
            job = jobs.leased(session, jid, token)
            attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
            usage = json.loads(attempt.usage_json)
            usage["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            attempt.usage_json = canonical(usage)
            session.commit()
    machine = validate_result(response["transcript"], inputs["duration_ms"])
    machine.update(
        runtime=inputs["speech_runtime"],
        audio=audio_info,
        source_sha256=inputs["source_sha256"],
        recorded_at=utcnow().isoformat(),
        quality="automatic_unverified",
    )
    raw_json = canonical(response.get("raw", {}))
    require(len(raw_json.encode()) <= 2 * 1024 * 1024, "speech_result_limit", 422)
    report = {
        "machine": machine,
        "raw": json.loads(raw_json),
        "metrics": response.get("metrics", {}),
    }
    data = canonical(report).encode()
    with factory() as session:
        job = jobs.leased(session, jid, token)
        jobs.input_check(session, job, app)
        job.result_bytes, job.result_json, job.checkpoint = (
            data,
            canonical({"bytes": len(data)}),
            hashlib.sha256(data).hexdigest(),
        )
        attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        usage.update(
            model=inputs["speech_runtime"],
            elapsed_ms=round((time.monotonic() - started) * 1000),
            output_bytes=len(data),
            processing="local_self_hosted_asr",
            runtime_metrics=report["metrics"],
            provider_cost_basis="self_hosted_no_provider_charge",
        )
        attempt.usage_json = canonical(usage)
        job.lease_until = time.time() + jobs.lease_seconds(job)
        session.commit()


def complete(session, job):
    value = json.loads(job.result_bytes)
    session.add(
        Transcript(
            id=job.id,
            business_id=job.business_id,
            asset_id=job.asset_id,
            source_sha256=json.loads(job.input_json)["source_sha256"],
            machine_json=canonical(value["machine"]),
            raw_json=canonical(value["raw"]),
            revision=0,
        )
    )
    job.result_bytes, job.result_json = b"", None


def purge(session, business, asset_id):
    for row in session.scalars(
        select(Transcript).where(
            Transcript.business_id == business, Transcript.asset_id == asset_id
        )
    ):
        row.machine_json, row.raw_json = "", ""
        for edit in session.scalars(
            select(TranscriptEdit).where(TranscriptEdit.transcript_id == row.id)
        ):
            edit.document = "{}"


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social"

    @app.get(root + "/speech/capability", dependencies=[Depends(read)])
    def caps(business_id: str):
        return capability(app, business_id)

    @app.post(root + "/video/takes/{asset_id}/transcriptions")
    def create(
        business_id: str, asset_id: str, principal=Depends(write), session=Depends(get_session)
    ):
        from .social_jobs import JobInput, enqueue

        return enqueue(
            session,
            business_id,
            JobInput(kind="speech_transcribe", asset_id=asset_id),
            principal,
            app,
        )

    @app.get(root + "/video/takes/{asset_id}/transcriptions", dependencies=[Depends(read)])
    def listing(business_id: str, asset_id: str, session=Depends(get_session)):
        from .social_video import clip_check

        clip_check(session, business_id, asset_id)
        rows = session.scalars(
            select(Transcript).where(
                Transcript.business_id == business_id, Transcript.asset_id == asset_id
            )
        ).all()
        return {"transcripts": [view(session, r) for r in rows if r.machine_json]}

    @app.get(root + "/transcripts/{identifier}", dependencies=[Depends(read)])
    def get(business_id: str, identifier: str, session=Depends(get_session)):
        return view(session, check_row(session, business_id, identifier))

    @app.post(root + "/transcripts/{identifier}/corrections")
    def correct(
        business_id: str,
        identifier: str,
        payload: EditInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        row = check_row(session, business_id, identifier, lock=True)
        key = str(payload.request_id)
        for edit in session.scalars(
            select(TranscriptEdit).where(TranscriptEdit.transcript_id == row.id)
        ):
            old = json.loads(edit.document)
            if old.get("request_id") == key:
                require(
                    old["request"] == payload.model_dump(mode="json"),
                    "transcript_idempotency_conflict",
                )
                return view(session, row)
        require(row.revision == payload.expected_revision, "transcript_revision_conflict")
        require(row.revision < 100, "transcript_edit_limit", 429)
        words = copy.deepcopy(view(session, row)["words"])
        for change in payload.changes:
            require(change.index < len(words), "speech_word_missing", 422)
            words[change.index].update(text=change.text, owner_corrected=True)
        revision = row.revision + 1
        updated = session.execute(
            update(Transcript)
            .where(Transcript.id == row.id, Transcript.revision == payload.expected_revision)
            .values(revision=revision)
        )
        require(updated.rowcount == 1, "transcript_revision_conflict")
        session.add(
            TranscriptEdit(
                id=f"{row.id}:{revision}",
                transcript_id=row.id,
                document=canonical(
                    {
                        "revision": revision,
                        "words": words,
                        "actor_id": principal.actor_id,
                        "recorded_at": utcnow().isoformat(),
                        "reason": payload.reason,
                        "request_id": key,
                        "request": payload.model_dump(mode="json"),
                    }
                ),
            )
        )
        session.commit()
        session.refresh(row)
        return view(session, row)
