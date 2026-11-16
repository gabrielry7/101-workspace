"""Advisory rules or grant-bound visual review on the normal production queue."""

# ruff: noqa: B008 -- FastAPI injection
import hashlib
import io
import json
import time

from fastapi import Depends, HTTPException
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from .models import StaffAccount
from .social_auto_review_contracts import (
    DIMENSIONS,
    PROMPT_VERSION,
    SYSTEM,
    CheckInput,
    Feedback,
    ReviewOutput,
)
from .social_job_models import ProductionAttempt as Attempt
from .social_job_models import ProductionJob as Job
from .social_production import (
    Pack,
    Revision,
    asset_check,
    canonical,
    current,
    owned,
    require,
)
from .social_research_models import AutomatedReview
from .social_reviews import current_time


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def model_enabled(app, business):
    gen = getattr(app.state, "social_generator", None)
    return bool(gen and getattr(gen, "allowed_review", lambda _: False)(business))


def image_for_model(rev):
    with Image.open(io.BytesIO(rev.image)) as source:
        image = source.convert("RGB")
        image.thumbnail((768, 960))
        for quality in (82, 65, 45):
            buf = io.BytesIO()
            image.save(buf, "JPEG", quality=quality)
            if len(buf.getvalue()) <= 256 * 1024:
                data = buf.getvalue()
                return data, {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "width": image.width,
                    "height": image.height,
                    "byte_length": len(data),
                    "mime_type": "image/jpeg",
                    "transform": "actual_render_thumbnail_768_v1",
                }
    raise HTTPException(422, "creative_review_image_limit")


def context(session, business, pack_id, expected_digest):
    from .social_reviews import technical

    pack, rev, doc, _ = current(session, business, pack_id, current_time())
    require(rev.digest == expected_digest, "creative_review_revision_changed")
    facts = doc["brief"]["facts"]
    rules = doc.get("creative_snapshot") or {}
    return {
        "business_id": business,
        "pack_id": pack.id,
        "revision_id": rev.id,
        "digest": rev.digest,
        "caption": doc["caption"],
        "facts": [{"id": f["id"], "text": f["text"]} for f in facts],
        "fact_refs": doc["brief"].get("fact_refs", []),
        "question": doc["brief"]["question"],
        "question_source": doc["brief"]["question_source"],
        "objective": doc["brief"]["objective"],
        "primary_measure": doc["brief"]["primary_measure"],
        "brand_direction": doc["brief"]["brand_direction"],
        "voice_rules": rules.get("voice_rules", ""),
        "visual_direction": rules.get("visual_direction", ""),
        "reference_judgments": [
            {"id": r["id"], "judgment": r["judgment"], "reason": r["reason"], "kind": r["kind"]}
            for r in rules.get("references", [])
        ],
        "source_asset_id": doc["brief"]["asset_id"],
        "source_family_sha256": doc["asset_sha256"],
        "technical": technical(rev, session),
        "modality": "video" if doc.get("video_output") else "static",
        "search_plan": doc.get("proposal_snapshot", {}).get("search_plan")
        if doc.get("proposal_snapshot")
        else None,
        "research_source_ids": [
            p["id"]
            for group in ("posts", "searches")
            for p in doc.get("research_snapshot", {}).get(group, [])
        ],
        "prompt_version": PROMPT_VERSION,
        "fixture": doc["fixture"],
    }


def still_current(session, row):
    saved = json.loads(row.input_json)
    value = context(session, row.business_id, row.pack_id, saved["context"]["digest"])
    require(value == saved["context"], "creative_review_context_changed")
    return value


def rules_review(ctx):
    criteria = []
    for c in DIMENSIONS:
        verdict = "uncertain"
        reason = "Requiere una revisión humana de la pieza y sus referencias."
        suggestion = (
            "Revisa este aspecto antes de aprobar; no hay una evaluación estética"
            " automática validada."
        )
        checks = []
        if c == "technical":
            ok = ctx["technical"]["status"] == "passed"
            verdict = "no_concern_detected" if ok else "needs_changes"
            checks = ctx["technical"]["defects"]
            reason = (
                "Los archivos y las comprobaciones del render son válidos."
                if ok
                else "El archivo preparado tiene defectos técnicos."
            )
            suggestion = (
                "Comprueba la legibilidad y el encuadre a tamaño real."
                if ok
                else "Vuelve a preparar el archivo antes de revisar y aprobar."
            )
        elif c == "factual":
            checks = ["current_fact_and_source_dependencies"]
            reason = (
                "Las fuentes y los datos seleccionados siguen vigentes; eso no "
                "verifica por sí solo todas las afirmaciones."
            )
            suggestion = (
                "Confirma que el texto y lo que se muestra corresponden al "
                "producto o servicio real."
            )
        elif c == "brand_fit":
            checks = (
                ["saved_brand_rules_present"]
                if ctx["brand_direction"] or ctx["visual_direction"]
                else []
            )
            reason = (
                "Hay instrucciones de estilo guardadas; falta juzgar cómo las aplica esta pieza."
            )
            suggestion = "Compara la pieza con ejemplos aprobados y rechazados del negocio."
        elif c == "purpose":
            plan = ctx.get("search_plan")
            checks = ["question_and_objective_present"]
            if plan:
                checks.append("sourced_question_and_confirmed_answer_links")
                reason = (
                    "La pregunta tiene respuestas vinculadas a datos confirmados;"
                    " falta revisar que la pieza las explique."
                )
                suggestion = (
                    "Comprueba pregunta, respuesta, lo que se muestra y el "
                    "siguiente paso; evita repetir palabras sin ayudar."
                )
            else:
                reason = (
                    "Se guardaron el objetivo y la pregunta; su cumplimiento necesita revisión."
                )
                suggestion = (
                    "Comprueba que el texto responde la pregunta y aclara el siguiente paso útil."
                )
        criteria.append(
            {
                "criterion": c,
                "verdict": verdict,
                "reason": reason,
                "suggestion": suggestion,
                "checks": checks,
                "basis": "deterministic_contract_checks"
                if c == "technical"
                else "limited_rules_not_aesthetic_judgment",
                "confidence": None,
                "evidence": [],
            }
        )
    return {
        "mode": "rules",
        "criteria": criteria,
        "overall_score": None,
        "commercial_performance": None,
        "search_ranking": None,
        "human_review_required": True,
        "evaluated_model_quality": False,
    }


def validate_model(raw, ctx):
    value = ReviewOutput.model_validate(raw).model_dump(mode="json")
    facts = {f["id"]: f["text"] for f in ctx["facts"]}
    brand = "\n".join(
        [ctx["brand_direction"], ctx["voice_rules"], ctx["visual_direction"]]
        + [r["reason"] for r in ctx["reference_judgments"]]
    )
    for judgment in value["criteria"]:
        for ev in judgment["evidence"]:
            if ev["surface"] == "fact":
                require(
                    ev["fact_id"] in facts and ev["quote"] in facts.get(ev["fact_id"], ""),
                    "creative_review_unknown_fact_quote",
                )
            elif ev["surface"] == "caption":
                require(ev["quote"] in ctx["caption"], "creative_review_unknown_caption_quote")
            elif ev["surface"] == "brand_rule":
                require(ev["quote"] in brand, "creative_review_unknown_brand_quote")
        judgment["basis"] = "uncalibrated_model_judgment"
        if judgment["criterion"] == "technical" and ctx["technical"]["status"] != "passed":
            judgment.update(
                verdict="needs_changes",
                reason=(
                    "Las comprobaciones deterministas detectaron un defecto, "
                    "aunque el modelo no lo haya visto."
                ),
            )
    return {
        "mode": "model",
        **value,
        "overall_score": None,
        "commercial_performance": None,
        "search_ranking": None,
        "human_review_required": True,
        "evaluated_model_quality": False,
        "confidence_basis": "uncalibrated_model_estimate",
    }


def info(session, row, app):
    from .social_jobs import info as job_info

    stale = False
    reason = None
    try:
        still_current(session, row)
    except HTTPException as e:
        stale = True
        reason = e.detail
    saved = json.loads(row.input_json)
    job = session.get(Job, row.id)
    return {
        "id": row.id,
        "pack_id": row.pack_id,
        "revision_id": row.revision_id,
        "mode": row.mode,
        "state": job.state,
        "reason": reason or job.reason,
        "stale": stale,
        "digest": saved["context"]["digest"],
        "output": None if stale else json.loads(row.output_json) if row.output_json else None,
        "technical": saved["context"]["technical"],
        "feedback": [] if stale else json.loads(row.feedback_json or "[]"),
        "activity": job_info(session, job),
        "fixture": saved["context"]["fixture"],
        "model_enabled": model_enabled(app, row.business_id),
    }


def enqueue(session, business, pack_id, p, principal, app):
    ctx = context(session, business, pack_id, p.digest)
    if p.mode == "model":
        require(model_enabled(app, business), "creative_review_model_not_enabled", 503)
        require(p.media_processing_confirmed, "creative_review_media_permission_required")
        require(ctx["modality"] == "static", "creative_review_video_needs_temporal_review")
        require(ctx["technical"]["status"] == "passed", "creative_review_render_needs_repair")
    saved = {"request": p.model_dump(mode="json"), "context": ctx}
    identifier = digest([business, pack_id, str(p.request_id)])[:32]
    old = session.get(AutomatedReview, identifier)
    if old:
        require(old.input_json == canonical(saved), "creative_review_idempotency_conflict")
        return info(session, old, app)
    require(
        (
            session.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.business_id == business, Job.state.in_(["queued", "running"]))
            )
            or 0
        )
        < 20,
        "production_queue_limit",
        429,
    )
    require(
        (
            session.scalar(
                select(func.count())
                .select_from(AutomatedReview)
                .where(AutomatedReview.pack_id == pack_id)
            )
            or 0
        )
        < 100,
        "creative_review_history_limit",
        429,
    )
    account = session.get(StaffAccount, principal.actor_id)
    asset, meta = asset_check(session, ctx["source_asset_id"], business, current_time())
    now = time.time()
    try:
        session.add(
            Job(
                id=identifier,
                business_id=business,
                asset_id=asset.id,
                pack_id=pack_id,
                base_revision=int(ctx["revision_id"].rsplit(":", 1)[1]),
                kind="creative_review",
                request_key=identifier,
                input_hash=digest(saved),
                input_json=canonical(
                    {
                        "source_sha256": meta["sha256"],
                        "recipe_version": "social-local-production-v1",
                        "tool_version": Image.__version__,
                        "review_id": identifier,
                    }
                ),
                actor_id=principal.actor_id,
                auth_version=account.auth_version,
                state="queued",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        row = AutomatedReview(
            id=identifier,
            business_id=business,
            pack_id=pack_id,
            revision_id=ctx["revision_id"],
            mode=p.mode,
            input_json=canonical(saved),
        )
        session.add(row)
        session.commit()
    except IntegrityError:
        session.rollback()
        row = session.get(AutomatedReview, identifier)
        require(
            row is not None and row.input_json == canonical(saved),
            "creative_review_idempotency_conflict",
        )
    return info(session, row, app)


def checkpoint(factory, app, jid, token):
    from .social_jobs import input_check, leased

    with factory() as s:
        job = leased(s, jid, token)
        input_check(s, job, app)
        row = s.get(AutomatedReview, jid)
        ctx = still_current(s, row)
        attempt = s.get(Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        if job.checkpoint and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint:
            usage["checkpoint_reused"] = True
            attempt.usage_json = canonical(usage)
            s.commit()
            return
        mode = row.mode
        gen = getattr(app.state, "social_generator", None)
        if mode == "model":
            require(model_enabled(app, job.business_id), "creative_review_model_not_enabled", 503)
            data, meta = image_for_model(s.get(Revision, row.revision_id))
            ctx = {**ctx, "image": meta}
            usage.update(gen.reserve_review(s, job, ctx, ReviewOutput.model_json_schema(), SYSTEM))
            usage.update(dispatch_started=True, prompt_version=PROMPT_VERSION)
            attempt.usage_json = canonical(usage)
            job.lease_until = time.time() + 120
            s.commit()
        else:
            usage.update(mode="rules", prompt_version=PROMPT_VERSION)
            attempt.usage_json = canonical(usage)
            s.commit()
    started = time.monotonic()
    if mode == "model":
        raw, receipt = gen.generate_review(ctx, data, ReviewOutput.model_json_schema(), SYSTEM)
    else:
        raw, receipt = rules_review(ctx), {"model_calls": 0, "provider": "none", "complete": True}
    encoded = canonical({"output": raw, "receipt": receipt}).encode()
    require(len(encoded) < 256 * 1024, "creative_review_response_limit")
    with factory() as s:
        job = leased(s, jid, token)
        attempt = s.get(Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        if mode == "model":
            usage.update(gen.settle(s, job, receipt))
        usage.update(
            elapsed_ms=round((time.monotonic() - started) * 1000), output_bytes=len(encoded)
        )
        attempt.usage_json = canonical(usage)
        job.result_bytes = encoded
        job.result_json = canonical(
            {
                "mode": mode,
                "prompt_version": PROMPT_VERSION,
                "image": meta if mode == "model" else None,
            }
        )
        job.checkpoint = hashlib.sha256(encoded).hexdigest()
        job.lease_until = time.time() + 120
        s.commit()


def complete(session, job, app):
    row = session.get(AutomatedReview, job.id)
    ctx = still_current(session, row)
    value = json.loads(job.result_bytes)
    require(value["receipt"].get("complete", True), "creative_review_incomplete_response")
    report = validate_model(value["output"], ctx) if row.mode == "model" else value["output"]
    row.output_json = canonical(report)
    job.result_revision = "creative-review:" + row.id


def register(app, get_session, read, write):
    root = "/api/operator/restaurants/{business_id}/social"

    @app.get(root + "/packs/{pack_id}/automated-reviews", dependencies=[Depends(read)])
    def listing(business_id: str, pack_id: str, session=Depends(get_session)):
        owned(session, Pack, pack_id, business_id)
        rows = session.scalars(
            select(AutomatedReview)
            .where(AutomatedReview.business_id == business_id, AutomatedReview.pack_id == pack_id)
            .join(Job, Job.id == AutomatedReview.id)
            .order_by(Job.created_at.desc(), AutomatedReview.id.desc())
            .limit(30)
        )
        return {
            "reviews": [info(session, r, app) for r in rows],
            "model_enabled": model_enabled(app, business_id),
            "quality_evaluated": False,
        }

    @app.post(root + "/packs/{pack_id}/automated-reviews")
    def create(
        business_id: str,
        pack_id: str,
        payload: CheckInput,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        return enqueue(session, business_id, pack_id, payload, principal, app)

    @app.post(root + "/automated-reviews/{review_id}/feedback")
    def feedback(
        business_id: str,
        review_id: str,
        payload: Feedback,
        principal=Depends(write),
        session=Depends(get_session),
    ):
        owned(session, AutomatedReview, review_id, business_id)
        session.execute(
            update(AutomatedReview)
            .where(AutomatedReview.id == review_id)
            .values(feedback_json=AutomatedReview.feedback_json)
        )
        row = session.get(AutomatedReview, review_id, populate_existing=True)
        still_current(session, row)
        require(row.output_json is not None, "creative_review_not_ready")
        entries = json.loads(row.feedback_json or "[]")
        key = digest([review_id, principal.actor_id, str(payload.request_id)])[:32]
        old = next((f for f in entries if f["id"] == key), None)
        value = payload.model_dump(mode="json")
        if old:
            require(old["request"] == value, "creative_feedback_idempotency_conflict")
        else:
            require(len(entries) < 50, "creative_feedback_limit", 429)
            entries.append(
                {
                    "id": key,
                    "actor_id": principal.actor_id,
                    "at": current_time().isoformat(),
                    "request": value,
                    "source_family_sha256": json.loads(row.input_json)["context"][
                        "source_family_sha256"
                    ],
                    "training_permission": "not_granted_by_feedback",
                }
            )
            row.feedback_json = canonical(entries)
            session.commit()
        return info(session, row, app)
