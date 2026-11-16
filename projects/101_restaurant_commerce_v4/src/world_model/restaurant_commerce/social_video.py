"""Guided capture → scoped clips → durable montage → existing review/export."""

# ruff: noqa: B008 -- FastAPI dependency injection
import copy
import hashlib
import json
import time

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select, update

from .models import utcnow
from .social_production import (
    Asset,
    Brief,
    Pack,
    Revision,
    asset_check,
    canonical,
    current,
    future,
    owned,
    pack_state,
    require,
)
from .social_video_contracts import SHOTS, VERSION, ShootInput, Timeline, VideoRenderInput
from .social_video_models import ClipMedia, Shoot, VideoOutput


def hash_value(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def guide_context(doc):
    b = doc["brief"]
    return hash_value(
        {
            "caption": doc["caption"],
            "brand": doc.get("creative_snapshot"),
            "business": doc.get("business_brief"),
            "brief": {
                k: b.get(k)
                for k in (
                    "facts",
                    "fact_refs",
                    "objective",
                    "question",
                    "brand_direction",
                    "context_version_id",
                    "creative_version_id",
                    "reference_ids",
                    "question_id",
                )
            },
        }
    )


def clip_check(session, business, asset_id, shoot_id=None, shot_id=None):
    row, meta = asset_check(session, asset_id, business, utcnow())
    require(meta.get("media_kind") == "video", "video_take_required", 422)
    require(not shoot_id or meta.get("shoot_id") == shoot_id, "video_shoot_mismatch")
    require(not shot_id or meta.get("shot_id") == shot_id, "video_shot_mismatch")
    require(hashlib.sha256(row.original).hexdigest() == meta["sha256"], "video_source_changed")
    return row, meta


def validate_timeline(session, business, timeline, *, pack_id=None, doc=None, lock=False):
    shoot = owned(session, Shoot, timeline.shoot_id, business)
    if pack_id:
        require(shoot.pack_id == pack_id, "video_pack_mismatch")
    if doc:
        require(
            json.loads(shoot.document)["context_hash"] == guide_context(doc),
            "video_guide_context_changed",
        )
    result = []
    for c in timeline.clips:
        if lock:
            session.execute(
                update(Asset).where(Asset.id == c.asset_id).values(revoked=Asset.revoked)
            )
        row, meta = clip_check(session, business, c.asset_id, shoot.id, c.shot_id)
        require(c.source_out <= meta["media"]["duration_ms"], "video_trim_out_of_bounds", 422)
        result.append((row, meta))
    return [
        {
            "asset_id": row.id,
            "sha256": m["sha256"],
            "shot_id": m["shot_id"],
            "expires_at": m["expires_at"],
            "rights_statement": m["rights_statement"],
            "uploaded_at": m["uploaded_at"],
            "captured_at": m.get("captured_at"),
            "fixture": m["fixture"],
            "media": m["media"],
        }
        for row, m in result
    ]


def source_reasons(session, business, doc):
    if not doc["brief"].get("video"):
        return []
    try:
        timeline = Timeline.model_validate(doc["brief"]["video"])
        sources = validate_timeline(session, business, timeline)
        require(sources == doc.get("video_sources"), "video_sources_changed")
        return []
    except HTTPException as e:
        return [{"reason": e.detail, "scope": "video_source"}]


def output(session, rev, doc):
    row = session.get(VideoOutput, rev.id)
    require(row is not None and row.business_id == doc["business_id"], "video_output_missing")
    files = {
        "video.mp4": row.final,
        "preview.mp4": row.preview,
        "cover.jpg": row.cover,
        "post.jpg": rev.image,
    }
    manifest = doc.get("video_output", {}).get("files", {})
    require(set(files) == set(manifest), "video_output_manifest_changed")
    for name, data in files.items():
        require(
            bool(data)
            and manifest[name] == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)},
            "video_output_changed",
        )
    return row


def purge(session, business, asset_id):
    media = session.get(ClipMedia, asset_id)
    if media and media.business_id == business:
        media.analysis, media.poster = b"", b""
    for rev in session.scalars(select(Revision).join(Pack).where(Pack.business_id == business)):
        doc = json.loads(rev.document)
        if doc.get("brief", {}).get("video") and (
            doc["brief"]["asset_id"] == asset_id
            or any(s["asset_id"] == asset_id for s in doc.get("video_sources", []))
        ):
            rev.image = b""
            row = session.get(VideoOutput, rev.id)
            if row:
                row.final, row.preview, row.cover = b"", b"", b""


def sweep(session):
    # Derivatives inherit expiry. Even unselected takes lose their analysis copies.
    for media in session.scalars(
        select(ClipMedia)
        .where(ClipMedia.analysis != b"", ClipMedia.expires_at <= time.time())
        .limit(50)
    ):
        try:
            asset_check(session, media.asset_id, media.business_id, utcnow())
        except HTTPException:
            purge(session, media.business_id, media.asset_id)


def shoot_info(session, shoot):
    doc = json.loads(shoot.document)
    takes = []
    # Read metadata only; a guide must not load every large original into memory.
    for identifier, encoded, revoked in session.execute(
        select(Asset.id, Asset.metadata_json, Asset.revoked).where(
            Asset.business_id == shoot.business_id
        )
    ):
        meta = json.loads(encoded)
        if (
            meta.get("shoot_id") != shoot.id
            or revoked
            or meta.get("permitted_use") != "production"
            or not future(meta["expires_at"], utcnow())
        ):
            continue
        takes.append(
            {
                "id": identifier,
                **{
                    k: meta[k] for k in ("shot_id", "uploaded_at", "fixture", "expires_at", "media")
                },
            }
        )
    takes.sort(key=lambda t: t["uploaded_at"])
    return {
        "id": shoot.id,
        "pack_id": shoot.pack_id,
        "source_revision_id": shoot.revision_id,
        **doc,
        "takes": takes,
        "missing_shots": [
            s["id"] for s in SHOTS if not any(t["shot_id"] == s["id"] for t in takes)
        ],
    }


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social"

    @app.get(root + "/video/capability", dependencies=[Depends(read)])
    def capability(business_id: str):
        from .social_video_media import tools

        try:
            version = tools()[2]
            return {
                "state": "configured",
                "recipe": VERSION,
                "tool": version,
                "live_account_required": False,
                "transcription": "not_built",
                "publishing": "manual_export_only",
            }
        except HTTPException:
            return {"state": "blocked", "reason": "video_tools_unavailable"}

    @app.post(root + "/shoots")
    def create(
        business_id: str,
        payload: ShootInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        identifier = hash_value([business_id, str(payload.request_id)])[:32]
        old = session.get(Shoot, identifier)
        if old:
            owned(session, Shoot, old.id, business_id)
            require(
                old.pack_id == payload.pack_id
                and old.revision_id == f"{payload.pack_id}:{payload.expected_revision}",
                "shoot_idempotency_conflict",
            )
            return shoot_info(session, old)
        pack, rev, doc, _ = current(session, business_id, payload.pack_id, utcnow())
        require(pack.revision == payload.expected_revision, "revision_conflict")
        require(
            (
                session.scalar(
                    select(func.count()).select_from(Shoot).where(Shoot.pack_id == pack.id)
                )
                or 0
            )
            < 20,
            "shoot_limit",
            429,
        )
        row = Shoot(
            id=identifier,
            business_id=business_id,
            pack_id=pack.id,
            revision_id=rev.id,
            document=canonical(
                {
                    "recipe": VERSION,
                    "context_hash": guide_context(doc),
                    "created_at": utcnow().isoformat(),
                    "actor_id": principal.actor_id,
                    "objective": doc["brief"]["objective"],
                    "caption": doc["caption"],
                    "shots": list(SHOTS),
                    "guidance": (
                        "Graba en vertical, 5–10 segundos por toma, con luz de frente y sin mover "
                        "el teléfono. Deja un segundo antes y después de la acción. Usa la cámara "
                        "normal en SDR; conserva el sonido del lugar. "
                        "No necesitas música ni hablar."
                    ),
                    "semantic_review": (
                        "El dueño debe confirmar que las acciones y el producto "
                        "corresponden al texto; no se verifican automáticamente."
                    ),
                }
            ),
        )
        session.add(row)
        session.commit()
        return shoot_info(session, row)

    @app.get(root + "/packs/{pack_id}/shoots", dependencies=[Depends(read)])
    def listing(business_id: str, pack_id: str, session=Depends(get_session)):
        owned(session, Pack, pack_id, business_id)
        return {
            "shoots": [
                shoot_info(session, row)
                for row in session.scalars(
                    select(Shoot)
                    .where(Shoot.business_id == business_id, Shoot.pack_id == pack_id)
                    .limit(20)
                )
            ]
        }

    @app.get(root + "/shoots/{shoot_id}", dependencies=[Depends(read)])
    def get(business_id: str, shoot_id: str, session=Depends(get_session)):
        return shoot_info(session, owned(session, Shoot, shoot_id, business_id))

    @app.get(root + "/video/takes/{asset_id}/{kind}", dependencies=[Depends(read)])
    def take(business_id: str, asset_id: str, kind: str, session=Depends(get_session)):
        row, _ = clip_check(session, business_id, asset_id)
        media = session.get(ClipMedia, row.id)
        require(media is not None, "video_analysis_unavailable")
        require(kind in {"analysis", "poster"}, "not_found", 404)
        data = media.analysis if kind == "analysis" else media.poster
        require(bool(data), "video_analysis_unavailable")
        return Response(
            data,
            media_type="video/mp4" if kind == "analysis" else "image/jpeg",
            headers={"Cache-Control": "no-store"},
        )

    @app.post(root + "/packs/{pack_id}/video")
    def render(
        business_id: str,
        pack_id: str,
        payload: VideoRenderInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        from .social_jobs import JobInput, enqueue

        pack, _, doc, _, reasons, _ = pack_state(session, business_id, pack_id, utcnow())
        # Replace an unavailable take without authorizing the old output or
        # bypassing changed facts/brand/anchor rights. Validate every new take.
        require(
            all(r.get("scope") == "video_source" for r in reasons),
            "video_brief_needs_current_facts",
        )
        require(pack.revision == payload.expected_revision, "revision_conflict")
        validate_timeline(session, business_id, payload.timeline, pack_id=pack_id, doc=doc)
        brief = copy.deepcopy(doc["brief"])
        brief.update(
            video=payload.timeline.model_dump(mode="json"),
            design=None,
            expected_revision=payload.expected_revision,
            request_id=str(payload.request_id),
            revision_reason="layout",
        )
        return enqueue(
            session,
            business_id,
            JobInput(kind="video_render", brief=Brief.model_validate(brief), pack_id=pack_id),
            principal,
            app,
        )

    @app.get(root + "/packs/{pack_id}/video/{kind}", dependencies=[Depends(read)])
    def view(business_id: str, pack_id: str, kind: str, session=Depends(get_session)):
        _, rev, doc, _ = current(session, business_id, pack_id, utcnow())
        require(bool(doc["brief"].get("video")), "not_a_video", 404)
        row = output(session, rev, doc)
        require(kind in {"preview", "final", "cover"}, "not_found", 404)
        data = {"preview": row.preview, "final": row.final, "cover": row.cover}[kind]
        return Response(
            data,
            media_type="image/jpeg" if kind == "cover" else "video/mp4",
            headers={"Cache-Control": "no-store"},
        )

    @app.get(root + "/packs/{pack_id}/revisions/{number}/video", dependencies=[Depends(read)])
    def history(business_id: str, pack_id: str, number: int, session=Depends(get_session)):
        pack = owned(session, Pack, pack_id, business_id)
        require(1 <= number <= pack.revision, "not_found", 404)
        rev = session.get(Revision, f"{pack_id}:{number}")
        require(rev is not None, "not_found", 404)
        doc = json.loads(rev.document)
        asset_check(session, doc["brief"]["asset_id"], business_id, utcnow())
        require(not source_reasons(session, business_id, doc), "video_source_unavailable")
        row = output(session, rev, doc)
        return Response(row.preview, media_type="video/mp4", headers={"Cache-Control": "no-store"})


def job_sources(session, job, inputs):
    timeline = Timeline.model_validate(inputs["brief"]["video"])
    sources = validate_timeline(session, job.business_id, timeline, pack_id=job.pack_id, lock=True)
    require(sources == inputs["snapshot"]["video_sources"], "video_sources_changed")
    return timeline, sources


def checkpoint(factory, app, jid, token):
    import time

    from . import social_jobs as jobs
    from .social_video_media import encode, tools

    start = time.monotonic()
    with factory() as session:
        job = jobs.leased(session, jid, token)
        _, inputs = jobs.input_check(session, job, app)
        require(inputs["video_tool_version"] == tools()[2], "video_tool_changed")
        timeline, sources = job_sources(session, job, inputs)
        if job.checkpoint and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint:
            attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
            usage = json.loads(attempt.usage_json)
            usage.update(
                checkpoint_reused=True,
                recipe_version=VERSION,
                tool_version=tools()[2],
                output_bytes=len(job.result_bytes),
            )
            attempt.usage_json = canonical(usage)
            session.commit()
            return
        originals = [session.get(Asset, c.asset_id).original for c in timeline.clips]
        session.rollback()
    data, report = encode(originals, timeline, [s["media"] for s in sources])
    with factory() as session:
        job = jobs.leased(session, jid, token)
        jobs.input_check(session, job, app)
        job.result_bytes, job.result_json, job.checkpoint = (
            data,
            canonical(report),
            hashlib.sha256(data).hexdigest(),
        )
        job.lease_until = time.time() + jobs.lease_seconds(job)
        attempt = session.get(jobs.Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        usage.update(
            recipe_version=VERSION,
            tool_version=tools()[2],
            output_bytes=len(data),
            elapsed_ms=round((time.monotonic() - start) * 1000),
        )
        attempt.usage_json = canonical(usage)
        session.commit()


def complete(session, job, app, inputs):
    from types import SimpleNamespace

    from .social_video_media import unpack

    files = unpack(job.result_bytes)
    report = json.loads(job.result_json)
    for name, data in files.items():
        require(
            report["files"][name]
            == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            "video_checkpoint_changed",
        )
    result = app.state.social_save(
        job.business_id,
        Brief.model_validate(inputs["brief"]),
        SimpleNamespace(actor_id=job.actor_id),
        session,
        job.pack_id,
        rendered=(files["post.jpg"], report),
        snapshot=inputs["snapshot"],
        commit=False,
        video_files=files,
    )
    job.result_revision = f"{job.pack_id}:{result['revision']}"
    job.result_bytes = b""
