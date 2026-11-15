"""Scoped offline production jobs, using the commerce SQL lease/generation pattern.

No external calls. A committed byte checkpoint survives worker death. Completion
checks the lease, current inputs and pack revision in the same result transaction.
"""

# ruff: noqa: B008 -- FastAPI dependencies
import hashlib
import io
import json
import logging
import time
from threading import Event, Thread
from types import SimpleNamespace
from typing import Literal
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageOps
from pydantic import Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import StaffAccount, StaffMembership, utcnow
from .social_job_models import (
    ProductionAttempt as Attempt,
)
from .social_job_models import (
    ProductionEffort as Effort,
)
from .social_job_models import (
    ProductionJob as Job,
)
from .social_production import (
    Asset,
    Brief,
    Pack,
    Strict,
    asset_check,
    canonical,
    document,
    owned,
    render,
    require,
)
from .staff import ROLES

LEASE_SECONDS = 30
MAX_ATTEMPTS = 5
RECIPE = "social-local-production-v1"


class JobInput(Strict):
    kind: Literal["photo_render", "inspect_asset"] = "photo_render"
    brief: Brief | None = None
    pack_id: str | None = Field(default=None, max_length=64)
    asset_id: str | None = Field(default=None, max_length=64)
    # All admitted operations are local. A paid reservation cannot be smuggled in.
    budget_microusd: Literal[0] = 0


class EffortInput(Strict):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    role: Literal["owner", "reviewer"]
    seconds: int = Field(ge=1, le=86400)


def authority(session, job):
    account = session.get(StaffAccount, job.actor_id)
    member = session.get(StaffMembership, (job.actor_id, job.business_id))
    require(
        account is not None
        and account.active
        and account.auth_version == job.auth_version
        and member is not None
        and "growth.write" in ROLES.get(member.role, ()),
        "job_authorization_revoked",
    )


def lock(session, job_id):
    session.execute(update(Job).where(Job.id == job_id).values(updated_at=Job.updated_at))
    return session.get(Job, job_id, populate_existing=True)


def input_check(session, job, app):
    authority(session, job)
    # Same source lock order as asset revocation: serialize source access before result commit.
    session.execute(update(Asset).where(Asset.id == job.asset_id).values(revoked=Asset.revoked))
    asset, meta = asset_check(session, job.asset_id, job.business_id, utcnow())
    inputs = json.loads(job.input_json)
    require(
        inputs["recipe_version"] == RECIPE and inputs["tool_version"] == Image.__version__,
        "job_tool_version_changed",
    )
    require(
        meta["sha256"] == inputs["source_sha256"]
        and hashlib.sha256(asset.original).hexdigest() == meta["sha256"],
        "source_changed",
    )
    if job.kind == "photo_render":
        payload = Brief.model_validate(inputs["brief"])
        current = app.state.social_save(
            job.business_id,
            payload,
            SimpleNamespace(actor_id=job.actor_id),
            session,
            inputs["edit_pack_id"],
            prepare_only=True,
        )
        require(
            all(
                current.get(k) == inputs["snapshot"].get(k)
                for k in (
                    "brief",
                    "business_brief",
                    "creative_snapshot",
                    "asset_sha256",
                    "renderer",
                    "design",
                )
            ),
            "job_inputs_changed",
        )
        if inputs["edit_pack_id"] is None:
            existing = session.get(Pack, job.pack_id)
            require(existing is None, "revision_conflict")
    if job.kind == "proposal_generate":
        from .social_proposal_models import Proposal
        from .social_proposals import still_current

        still_current(session, session.get(Proposal, job.id), app)
    return asset.original, inputs


def usage():
    return {
        "recipe_version": RECIPE,
        "tool_version": Image.__version__,
        "model": None,
        "prompt_version": None,
        "model_calls": 0,
        "reserved_provider_microusd": 0,
        "actual_provider_microusd": 0,
        "provider_cost_basis": "local_only_no_provider",
        "compute_cost_microusd": None,
        "storage_cost_microusd": None,
        "total_cost_microusd": None,
        "cost_reason": "local_resource_prices_not_configured",
        "elapsed_ms": None,
        "output_bytes": None,
        "checkpoint_reused": False,
    }


def info(session, job):
    attempts = session.scalars(
        select(Attempt).where(Attempt.job_id == job.id).order_by(Attempt.generation)
    ).all()
    inputs = json.loads(job.input_json)
    result = {
        "title": inputs.get("brief", {}).get("question", "Revisión del archivo"),
        "id": job.id,
        "kind": job.kind,
        "pack_id": job.pack_id,
        "base_revision": job.base_revision,
        "input_hash": job.input_hash,
        "state": job.state,
        "reason": job.reason,
        "attempt_count": job.generation,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "checkpoint": bool(job.checkpoint),
        "result_revision": job.result_revision,
        "attempts": [
            {
                "number": a.generation,
                "state": a.state,
                "reason": a.reason,
                "started_at": a.started_at,
                "finished_at": a.finished_at,
                "usage": json.loads(a.usage_json),
            }
            for a in attempts
        ],
        "effort": [
            {"role": e.role, "seconds": e.seconds, "recorded_at": e.recorded_at}
            for e in session.scalars(select(Effort).where(Effort.job_id == job.id))
        ],
        "cost": {
            "provider_microusd": 0,
            "total_microusd": None,
            "reason": "local_resource_prices_not_configured",
        },
    }
    if job.kind == "proposal_generate":
        usages = [json.loads(a.usage_json) for a in attempts]
        dispatched = [u for u in usages if u.get("dispatch_started")]
        if dispatched:
            result["cost"] = {
                "provider_microusd": sum(u["actual_provider_microusd"] for u in dispatched)
                if all(u.get("actual_provider_microusd") is not None for u in dispatched)
                else None,
                "total_microusd": None,
                "reason": "model_usage_or_reservation_recorded",
            }
    if job.state == "succeeded":
        try:
            asset_check(session, job.asset_id, job.business_id, utcnow())
            if job.kind == "photo_render":
                p = document(session, job.business_id, job.pack_id, utcnow())
                if p["stale"] or str(p["revision"]) != job.result_revision.rsplit(":", 1)[-1]:
                    result.update(state="superseded", reason="newer_or_changed_inputs")
            elif job.kind == "inspect_asset" and job.result_json:
                result["media"] = json.loads(job.result_json)
        except HTTPException:
            result.update(state="needs_input", reason="source_unavailable")
    return result


def enqueue(session, business, payload, principal, app):
    account = session.get(StaffAccount, principal.actor_id)
    require(account is not None, "staff_account_required", 403)
    require(
        session.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.business_id == business, Job.state.in_(["queued", "running"]))
        )
        < 20,
        "production_queue_limit",
        429,
    )
    if payload.kind == "photo_render":
        require(
            payload.brief is not None and payload.asset_id is None, "render_brief_required", 422
        )
        snapshot = app.state.social_save(
            business, payload.brief, principal, session, payload.pack_id, prepare_only=True
        )
        aid = payload.brief.asset_id
        pack_id = (
            payload.pack_id
            or hashlib.sha256(
                (business + ":" + str(payload.brief.request_id)).encode()
            ).hexdigest()[:32]
        )
        inputs = {
            "brief": payload.brief.model_dump(mode="json"),
            "snapshot": snapshot,
            "edit_pack_id": payload.pack_id,
        }
        base = payload.brief.expected_revision
    else:
        require(
            payload.asset_id is not None and payload.brief is None and payload.pack_id is None,
            "inspection_asset_required",
            422,
        )
        aid, pack_id, inputs, base = payload.asset_id, None, {}, 0
    _, meta = asset_check(session, aid, business, utcnow())
    inputs.update(
        source_sha256=meta["sha256"],
        source_asset_id=aid,
        recipe_version=RECIPE,
        tool_version=Image.__version__,
        provenance={
            "business_id": business,
            "allowed_use": meta["permitted_use"],
            "expires_at": meta["expires_at"],
            "captured_at": meta.get("captured_at"),
            "uploaded_at": meta.get("uploaded_at"),
            "rights_statement": meta["rights_statement"],
        },
    )
    stable = {k: v for k, v in inputs.items() if k != "snapshot"}
    if "snapshot" in inputs:
        stable["snapshot"] = {
            k: v for k, v in inputs["snapshot"].items() if k not in ("confirmed_at", "confirmed_by")
        }
    digest = hashlib.sha256(canonical(stable).encode()).hexdigest()
    jid = hashlib.sha256(
        canonical([business, payload.kind, pack_id, base, digest]).encode()
    ).hexdigest()[:32]
    old = session.get(Job, jid)
    if old:
        return info(session, old)
    # One original request cannot silently become a second pack with different inputs.
    if payload.kind == "photo_render" and not payload.pack_id:
        require(
            not session.scalar(
                select(Job.id).where(Job.business_id == business, Job.pack_id == pack_id)
            ),
            "idempotency_conflict",
        )
        require(session.get(Pack, pack_id) is None, "idempotency_conflict")
    now = time.time()
    job = Job(
        id=jid,
        business_id=business,
        asset_id=aid,
        pack_id=pack_id,
        base_revision=base,
        kind=payload.kind,
        request_key=pack_id if payload.kind == "photo_render" and not payload.pack_id else jid,
        input_hash=digest,
        input_json=canonical(inputs),
        actor_id=principal.actor_id,
        auth_version=account.auth_version,
        state="queued",
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        old = session.get(Job, jid)
        require(old is not None, "job_creation_conflict")
        return info(session, old)
    return info(session, job)


def claim(factory, *, worker="social-local-worker", now=None, job_id=None):
    now = time.time() if now is None else now
    with factory() as session:
        query = (
            select(Job.id)
            .where(or_(Job.state == "queued", (Job.state == "running") & (Job.lease_until <= now)))
            .order_by(Job.created_at)
            .limit(1)
        )
        if job_id:
            query = query.where(Job.id == job_id)
        candidate = session.scalar(query)
        if not candidate:
            return None
        job = lock(session, candidate)
        if not (job.state == "queued" or job.state == "running" and job.lease_until <= now):
            return None
        if job.state == "running":
            attempt = session.get(Attempt, f"{job.id}:{job.generation}")
            if (
                job.kind == "proposal_generate"
                and json.loads(attempt.usage_json).get("dispatch_started")
                and not job.checkpoint
            ):
                job.state, job.reason, job.lease, job.lease_until = (
                    "uncertain",
                    "model_outcome_unknown",
                    None,
                    None,
                )
                attempt.state, attempt.reason, attempt.finished_at = (
                    "uncertain",
                    "model_outcome_unknown",
                    now,
                )
                session.commit()
                return None
            attempt.state, attempt.reason, attempt.finished_at = "interrupted", "lease_expired", now
        if job.generation >= MAX_ATTEMPTS:
            job.state, job.reason, job.lease, job.lease_until = (
                "failed",
                "attempt_limit",
                None,
                None,
            )
            session.commit()
            return None
        token = uuid4().hex
        job.state, job.lease, job.lease_until, job.reason = (
            "running",
            token,
            now + LEASE_SECONDS,
            None,
        )
        job.generation += 1
        job.updated_at = now
        session.add(
            Attempt(
                id=f"{job.id}:{job.generation}",
                job_id=job.id,
                generation=job.generation,
                worker=worker[:100],
                state="running",
                started_at=now,
                usage_json=canonical(usage()),
            )
        )
        session.commit()
        return job.id, token


def leased(session, jid, token):
    job = lock(session, jid)
    require(
        job is not None
        and job.state == "running"
        and job.lease == token
        and job.lease_until > time.time(),
        "job_lease_lost",
    )
    return job


def produce(original, job, inputs):
    if job.kind == "photo_render":
        return render(original, Brief.model_validate(inputs["brief"]))
    # Same bounded EXIF→RGB→thumbnail contract as archive Preparer.image, using owner IDs
    # instead of archive.sqlite paths. No model/runtime/archive files are accessed.
    with Image.open(io.BytesIO(original)) as source:
        require(source.width * source.height <= 24_000_000, "image_pixel_limit", 422)
        image = ImageOps.exif_transpose(source).convert("RGB")
        dimensions = [image.width, image.height]
        image.thumbnail((640, 640))
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=85)
    return out.getvalue(), {
        "schema_version": "1",
        "source_sha256": inputs["source_sha256"],
        "source_asset_id": job.asset_id,
        "source_dimensions": dimensions,
        "width": image.width,
        "height": image.height,
        "transform": "exif_orientation_then_fit_no_upscale",
        "provenance": inputs["provenance"],
        "semantic_analysis": "not_run",
    }


def checkpoint(factory, app, jid, token, *, transform=produce):
    with factory() as probe:
        kind = probe.get(Job, jid).kind
    if kind == "proposal_generate":
        from .social_proposal_worker import checkpoint as generate

        return generate(factory, app, jid, token)
    started = time.monotonic()
    with factory() as session:
        job = leased(session, jid, token)
        original, inputs = input_check(session, job, app)
        if (
            job.checkpoint
            and job.result_json
            and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint
        ):
            a = session.get(Attempt, f"{jid}:{job.generation}")
            u = json.loads(a.usage_json)
            u["checkpoint_reused"] = True
            a.usage_json = canonical(u)
            session.commit()
            return
        # Release database locks during decoding/rendering. Final writes are fenced again.
        selected = SimpleNamespace(kind=job.kind, asset_id=job.asset_id)
        session.rollback()
        data, report = transform(original, selected, inputs)
    require(len(data) <= 4 * 1024 * 1024, "derived_size_limit", 422)
    with factory() as session:
        job = leased(session, jid, token)
        input_check(session, job, app)
        job.result_bytes, job.result_json, job.checkpoint = (
            data,
            canonical(report),
            hashlib.sha256(data).hexdigest(),
        )
        job.updated_at = time.time()
        job.lease_until = time.time() + LEASE_SECONDS
        a = session.get(Attempt, f"{jid}:{job.generation}")
        u = json.loads(a.usage_json)
        u.update(elapsed_ms=round((time.monotonic() - started) * 1000), output_bytes=len(data))
        a.usage_json = canonical(u)
        session.commit()


def complete(factory, app, jid, token):
    with factory() as session:
        job = leased(session, jid, token)
        _, inputs = input_check(session, job, app)
        require(
            job.checkpoint and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint,
            "checkpoint_required",
        )
        if job.kind == "photo_render":
            app.state.social_save(
                job.business_id,
                Brief.model_validate(inputs["brief"]),
                SimpleNamespace(actor_id=job.actor_id),
                session,
                inputs["edit_pack_id"],
                rendered=(job.result_bytes, json.loads(job.result_json)),
                snapshot=inputs["snapshot"],
                commit=False,
            )
            job.result_revision = f"{job.pack_id}:{job.base_revision + 1}"
            job.result_bytes = (
                b""  # Canonical revision owns final pixels; don't retain a duplicate.
            )
        if job.kind == "proposal_generate":
            from .social_proposal_worker import complete as complete_proposal

            complete_proposal(session, job, app)
        job.state, job.reason, job.lease, job.lease_until = "succeeded", None, None, None
        job.updated_at = time.time()
        a = session.get(Attempt, f"{jid}:{job.generation}")
        a.state, a.finished_at = "succeeded", time.time()
        session.commit()


def failed(factory, jid, token, error):
    with factory() as session:
        job = lock(session, jid)
        if not job or job.lease != token or job.state != "running":
            return
        reason = (
            error.detail
            if isinstance(error, HTTPException) and isinstance(error.detail, str)
            else "local_processing_failed"
        )
        # No arbitrary exception contents, source metadata or credentials in UI/logs.
        if reason == "job_lease_lost":
            return
        state = (
            "superseded"
            if reason
            in {"revision_conflict", "job_inputs_changed", "business_brief_changed", "fact_changed"}
            else "needs_input"
            if isinstance(error, HTTPException)
            else "failed"
        )
        if job.kind == "proposal_generate":
            from .social_proposal_models import Proposal

            row = session.get(Proposal, jid)
            a = session.get(Attempt, f"{jid}:{job.generation}")
            if json.loads(a.usage_json).get("dispatch_started") and not job.checkpoint:
                state, reason = "uncertain", "model_outcome_unknown"
            if row.mode == "model" and job.checkpoint and reason not in {"source_deleted_or_revoked", "asset_expired", "reference_only_asset"}:
                state, reason = "needs_input", "proposal_response_needs_review"
            row.report_json = canonical(
                {"mode": row.mode, "reason": reason, "semantic_support": "unverified"}
            )
        job.state, job.reason, job.lease, job.lease_until = state, reason, None, None
        if job.kind != "proposal_generate" or reason in {
            "source_deleted_or_revoked",
            "asset_expired",
        }:
            job.result_bytes, job.result_json, job.checkpoint = b"", None, None
        job.updated_at = time.time()
        a = session.get(Attempt, f"{jid}:{job.generation}")
        a.state, a.reason, a.finished_at = state, reason, time.time()
        session.commit()


def dispatch_one(factory, app):
    pair = claim(factory)
    if not pair:
        return False
    try:
        checkpoint(factory, app, *pair)
        complete(factory, app, *pair)
    except Exception as error:
        failed(factory, *pair, error)
    return True


def purge_asset(session, business, asset_id, reason="source_deleted_or_revoked"):
    for job in session.scalars(
        select(Job).where(Job.business_id == business, Job.asset_id == asset_id)
    ):
        job.result_bytes, job.result_json, job.checkpoint = b"", None, None
        if job.kind == "proposal_generate":
            from .social_proposal_models import Proposal

            row = session.get(Proposal, job.id)
            if row:
                row.output_json, row.report_json = None, None
        if job.state in {"queued", "running", "succeeded"}:
            if job.state == "running":
                a = session.get(Attempt, f"{job.id}:{job.generation}")
                a.state, a.reason, a.finished_at = (
                    "needs_input",
                    reason,
                    time.time(),
                )
            job.state, job.reason, job.lease, job.lease_until = (
                "needs_input",
                reason,
                None,
                None,
            )
        job.updated_at = time.time()


def purge_unavailable(factory):
    with factory() as session:
        candidates = session.scalars(
            select(Job)
            .where(or_(Job.state.in_(["queued", "running", "succeeded"]), Job.result_bytes != b""))
            .order_by(Job.updated_at)
            .limit(100)
        ).all()
        now = time.time()
        for job in candidates:
            try:
                asset_check(session, job.asset_id, job.business_id, utcnow())
            except HTTPException as error:
                purge_asset(session, job.business_id, job.asset_id, str(error.detail))
            # Round-robin the bounded sweep, including valid old completed jobs.
            job.updated_at = now
        session.commit()


def start_worker(factory, app):
    stop = Event()

    def loop():
        from .social_migrations import schema_ready

        while not stop.wait(0.4):
            if getattr(app.state, "social_worker_paused", False):
                continue
            try:
                with factory() as s:
                    if not schema_ready(s.connection()):
                        continue
                purge_unavailable(factory)
                dispatch_one(factory, app)
            except (SQLAlchemyError, HTTPException):
                logging.getLogger(__name__).warning(
                    "Social worker deferred; lease recovery remains available"
                )

    thread = Thread(target=loop, name="commerce-social-production", daemon=True)
    thread.start()
    return stop, thread


def register(app, get_session, read, write, save):
    app.state.social_save = save
    root = "/api/operator/restaurants/{business_id}/social/jobs"

    @app.post(root)
    def create(
        business_id: str, payload: JobInput, principal=Depends(write), session=Depends(get_session)
    ):
        return enqueue(session, business_id, payload, principal, app)

    @app.get(root, dependencies=[Depends(read)])
    def listing(business_id: str, session=Depends(get_session)):
        return {
            "jobs": [
                info(session, j)
                for j in session.scalars(
                    select(Job)
                    .where(Job.business_id == business_id)
                    .order_by(Job.created_at.desc())
                    .limit(50)
                )
            ]
        }

    @app.get(root + "/{job_id}", dependencies=[Depends(read)])
    def get(business_id: str, job_id: str, session=Depends(get_session)):
        return info(session, owned(session, Job, job_id, business_id))

    @app.post(root + "/{job_id}/retry")
    def retry(
        business_id: str, job_id: str, principal=Depends(write), session=Depends(get_session)
    ):
        owned(session, Job, job_id, business_id)
        job = lock(session, job_id)
        require(job.state in {"failed", "needs_input"}, "job_not_retryable")
        if job.kind == "proposal_generate":
            from .social_proposal_models import Proposal

            require(
                session.get(Proposal, job.id).mode != "model",
                "model_retry_requires_new_authorization",
            )
        require(job.generation < MAX_ATTEMPTS, "attempt_limit")
        require(job.actor_id == principal.actor_id, "job_actor_changed", 403)
        input_check(session, job, app)
        job.state, job.reason, job.updated_at = "queued", None, time.time()
        session.commit()
        return info(session, job)

    @app.get(root + "/{job_id}/preview", dependencies=[Depends(read)])
    def preview(business_id: str, job_id: str, session=Depends(get_session)):
        job = owned(session, Job, job_id, business_id)
        asset_check(session, job.asset_id, business_id, utcnow())
        require(
            job.kind == "inspect_asset" and job.state == "succeeded" and bool(job.result_bytes),
            "preview_unavailable",
        )
        return Response(
            job.result_bytes, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
        )

    @app.post(root + "/{job_id}/effort")
    def effort(
        business_id: str,
        job_id: str,
        payload: EffortInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        job = owned(session, Job, job_id, business_id)
        eid = hashlib.sha256(
            canonical([job_id, principal.actor_id, payload.request_id]).encode()
        ).hexdigest()[:32]
        old = session.get(Effort, eid)
        if old:
            require(
                old.role == payload.role and old.seconds == payload.seconds,
                "effort_idempotency_conflict",
            )
        else:
            session.add(
                Effort(
                    id=eid,
                    job_id=job_id,
                    actor_id=principal.actor_id,
                    role=payload.role,
                    seconds=payload.seconds,
                    recorded_at=time.time(),
                )
            )
            session.commit()
        return info(session, job)
