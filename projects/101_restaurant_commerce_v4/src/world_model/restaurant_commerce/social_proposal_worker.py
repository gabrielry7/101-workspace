"""Proposal jobs: preview or an injected grant-bound model transport, never blind retry."""

import hashlib
import json
import time

from .social_job_models import ProductionAttempt as Attempt
from .social_production import canonical, require
from .social_proposal_models import Proposal
from .social_proposals import (
    PROMPT_VERSION,
    SYSTEM,
    ProposalOutput,
    model_context,
    preview,
    still_current,
    validate_output,
)


def checkpoint(factory, app, jid, token):
    from .social_jobs import input_check, leased

    with factory() as s:
        job = leased(s, jid, token)
        input_check(s, job, app)
        row = s.get(Proposal, jid)
        context = still_current(s, row, app)
        attempt = s.get(Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        if job.checkpoint and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint:
            usage["checkpoint_reused"] = True
            attempt.usage_json = canonical(usage)
            s.commit()
            return
        mode = row.mode
        generator = getattr(app.state, "social_generator", None)
        if mode == "model":
            require(
                generator is not None and generator.allowed(job.business_id),
                "proposal_model_not_enabled",
                503,
            )
            # Budget reservation and dispatch marker commit BEFORE the physical request.
            usage.update(
                generator.reserve(
                    s, job, model_context(context), ProposalOutput.model_json_schema(), SYSTEM
                )
            )
            usage.update(dispatch_started=True, prompt_version=PROMPT_VERSION)
            attempt.usage_json = canonical(usage)
            job.lease_until = time.time() + 120
            s.commit()
        else:
            usage.update(prompt_version=PROMPT_VERSION, mode="deterministic_preview")
            attempt.usage_json = canonical(usage)
            s.commit()
    started = time.monotonic()
    if mode == "model":
        # Exactly one request. The adapter must not retry HTTP internally.
        raw, receipt = generator.generate(
            model_context(context), ProposalOutput.model_json_schema(), SYSTEM
        )
    else:
        raw, receipt = (
            preview(context).model_dump(mode="json"),
            {"model": None, "provider": "none", "model_calls": 0, "actual_provider_microusd": 0},
        )
    encoded = canonical({"output": raw, "receipt": receipt}).encode()
    require(len(encoded) < 256 * 1024, "proposal_response_too_large")
    with factory() as s:
        job = leased(s, jid, token)
        attempt = s.get(Attempt, f"{jid}:{job.generation}")
        usage = json.loads(attempt.usage_json)
        if mode == "model":
            usage.update(generator.settle(s, job, receipt))
        usage.update(
            elapsed_ms=round((time.monotonic() - started) * 1000), output_bytes=len(encoded)
        )
        attempt.usage_json = canonical(usage)
        # Retain received output/cost BEFORE current-source validation or parsing.
        job.result_bytes = encoded
        job.checkpoint = hashlib.sha256(encoded).hexdigest()
        job.result_json = canonical({"prompt_version": PROMPT_VERSION, "mode": mode})
        job.lease_until = time.time() + 120
        job.updated_at = time.time()
        s.commit()


def complete(session, job, app):
    row = session.get(Proposal, job.id)
    context = still_current(session, row, app)
    require(
        job.checkpoint and hashlib.sha256(job.result_bytes).hexdigest() == job.checkpoint,
        "checkpoint_required",
    )
    value = json.loads(job.result_bytes)
    try:
        require(value["receipt"].get("complete", True), "proposal_incomplete_model_response")
        output, report = validate_output(value["output"], context, row.mode)
    except Exception:
        row.report_json = canonical(
            {
                "mode": row.mode,
                "contract": "invalid_model_response",
                "semantic_support": "unverified",
            }
        )
        # Keep received response in the private job checkpoint; never automatically resend.
        raise
    row.output_json, row.report_json = canonical(output), canonical(report)
    job.result_revision = row.id
