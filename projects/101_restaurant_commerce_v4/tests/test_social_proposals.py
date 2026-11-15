"""Scoped N05 context → proposal → explicit reviewed copy → N04 production."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import copy
import io
import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_social_context import context_payload, save_context
from test_social_creative import board_payload
from test_social_jobs import queue
from test_social_production import BUSINESS, OTHER, ROOT, approval, env, factory, photo, social
from world_model.restaurant_commerce import social_jobs as jobs
from world_model.restaurant_commerce.social_production import canonical
from world_model.restaurant_commerce.social_proposal_models import Proposal
from world_model.restaurant_commerce.social_proposals import (
    Claim,
    ProposalInput,
    assemble,
    check_copy,
    preview,
    validate_output,
)


def setup(q, mode="preview"):
    c = save_context(q, context_payload())
    bp = board_payload()
    b = q.client.put(ROOT + "/creative", json=bp, headers=q.headers)
    assert b.status_code == 200, b.text
    p = {
        "request_id": str(uuid4()),
        "expected_context_revision": c["revision"],
        "expected_brand_revision": b.json()["revision"],
        "asset_id": photo(q).json()["id"],
        "fact_ids": ["price", "description"],
        "mode": mode,
        "question": "¿Cuál es el precio del producto de prueba?",
        "reference_ids": ["writing"],
    }
    return p, c


def create(q, p):
    r = q.client.post(ROOT + "/proposals", json=p, headers=q.headers)
    assert r.status_code == 200, r.text
    return r.json()


def run(q, p):
    r = create(q, p)
    assert jobs.dispatch_one(q.factory, q.client.app)
    result = q.client.get(ROOT + "/proposals/" + r["id"]).json()
    assert result["state"] == "succeeded", result
    return result


def review(q, p, **changes):
    value = {
        "request_id": str(uuid4()),
        "digest": p["digest"],
        "choice": "conversational",
        "reason_kind": "selection",
        "reason": "Synthetic owner review",
        "reviewed_claims": True,
        "reviewed_entire_copy": True,
    }
    value.update(changes)
    return q.client.post(
        ROOT + "/proposals/" + p["id"] + "/decisions", json=value, headers=q.headers
    )


def test_preview_to_reviewed_caption_to_approved_real_package(queue):
    q = queue
    p, c = setup(q)
    r = create(q, p)
    assert create(q, p)["id"] == r["id"]
    assert jobs.dispatch_one(q.factory, q.client.app)
    r = q.client.get(ROOT + "/proposals/" + r["id"]).json()
    assert r["state"] == "succeeded", r
    assert r["mode"] == "preview" and r["input"]["search_volume"] is None
    assert len(r["output"]["copy_options"]) == 2
    assert review(q, r, reviewed_entire_copy=False).status_code == 409
    edited = "Una respuesta para ayudarte a elegir.\n\nPrecio: 12000 COP.\n\nProducto de prueba."
    decision = review(q, r, edited_text=edited)
    assert decision.status_code == 200, decision.text
    produce = q.client.post(
        ROOT + "/proposals/" + r["id"] + "/produce",
        json={"decision_id": decision.json()["id"]},
        headers=q.headers,
    )
    assert produce.status_code == 200, produce.text
    assert jobs.dispatch_one(q.factory, q.client.app)
    pack = q.client.get(ROOT + "/packs/" + produce.json()["pack_id"]).json()
    assert pack["document"]["caption"] == edited
    assert pack["document"]["copy_mode"] == "reviewed_proposal"
    assert pack["document"]["proposal_snapshot"]["decision_id"] == decision.json()["id"]
    assert approval(q, pack).status_code == 200
    result = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert result.status_code == 200
    import zipfile

    with zipfile.ZipFile(io.BytesIO(result.content)) as z:
        assert z.read("caption.txt").decode() == edited
    old_context = q.client.get(ROOT + "/creative").json()
    assert old_context["voice_rules"] == r["input"]["voice_rules"]
    # Rejection records its own reason and cannot be used to produce content.
    rejected = review(
        q,
        r,
        choice="reject",
        reviewed_claims=False,
        reviewed_entire_copy=False,
        reason_kind="strategy",
    )
    assert rejected.status_code == 200
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
    assert q.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    assert (
        q.client.post(
            ROOT + "/proposals/" + r["id"] + "/produce",
            json={"decision_id": rejected.json()["id"]},
            headers=q.headers,
        ).status_code
        == 409
    )


def test_missing_context_wrong_scope_stale_facts_and_unsupported_claims(queue):
    q = queue
    p, c = setup(q)
    assert q.client.post(ROOT + "/proposals", json=p).status_code == 403
    assert q.client.post(
        ROOT.replace(BUSINESS, OTHER) + "/proposals", json=p, headers=q.headers
    ).status_code in (403, 404, 409)
    for changes in (
        {"fact_ids": ["foreign"]},
        {"fact_ids": ["price", "price"]},
        {"expected_context_revision": 0},
        {"question_id": "not-a-question"},
    ):
        assert q.client.post(
            ROOT + "/proposals", json={**p, **changes}, headers=q.headers
        ).status_code in (404, 409, 422)
    r = run(q, p)
    assert review(q, r, edited_text="Precio: 15000 COP. Producto de prueba.").status_code == 409
    assert review(q, r, edited_text="El más vendido. Precio: 12000 COP.").status_code == 409
    assert review(q, r, edited_text="Precio: 12000 USD.").status_code == 409
    payload = context_payload()
    payload["expected_revision"] = 1
    payload["facts"][0]["value"] = "15000"
    save_context(q, payload)
    current = q.client.get(ROOT + "/proposals/" + r["id"]).json()
    assert current["stale"]
    assert review(q, r).status_code == 409


class FakeGenerator:
    def __init__(self, business, answer=None, crash=False):
        self.business = business
        self.calls = 0
        self.answer = answer
        self.crash = crash

    def allowed(self, business):
        return business == self.business

    def reserve(self, s, job, c, schema, system):
        return {
            "provider": "fixture",
            "model": "fixture-model",
            "actual_provider_microusd": None,
            "reserved_provider_microusd": 100,
            "model_calls": 1,
        }

    def generate(self, c, schema, system):
        self.calls += 1
        if self.crash:
            raise TimeoutError("uncertain transport")
        # Restore the omitted external reference list only for deterministic fixture construction.
        c = {**c, "references": []}
        return self.answer or preview(c).model_dump(mode="json"), {
            "complete": True,
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

    def settle(self, s, job, receipt):
        return {"actual_provider_microusd": 50, "usage": receipt["usage"]}


def test_model_disabled_then_fixture_adapter_and_uncertain_no_resend(queue):
    q = queue
    p, _ = setup(q, mode="model")
    assert q.client.post(ROOT + "/proposals", json=p, headers=q.headers).status_code == 503
    fake = FakeGenerator(BUSINESS)
    q.client.app.state.social_generator = fake
    r = run(q, p)
    assert fake.calls == 1 and r["mode"] == "model"
    assert q.client.get(ROOT + "/jobs/" + r["job_id"]).json()["cost"]["provider_microusd"] == 50
    # A later timeout is explicitly uncertain and never retried by the local worker.
    p["request_id"] = str(uuid4())
    fake.crash = True
    r = create(q, p)
    assert jobs.dispatch_one(q.factory, q.client.app)
    state = q.client.get(ROOT + "/jobs/" + r["job_id"]).json()
    assert state["state"] == "uncertain" and state["cost"]["provider_microusd"] is None
    assert jobs.claim(q.factory, job_id=r["job_id"]) is None
    assert (
        q.client.post(ROOT + "/jobs/" + r["job_id"] + "/retry", headers=q.headers).status_code
        == 409
    )
    assert fake.calls == 2


def test_invalid_model_response_preserves_charge_and_never_retries(queue):
    q = queue
    p, _ = setup(q, mode="model")
    fake = FakeGenerator(BUSINESS, answer={"wrong": "schema"})
    q.client.app.state.social_generator = fake
    r = create(q, p)
    assert jobs.dispatch_one(q.factory, q.client.app)
    state = q.client.get(ROOT + "/jobs/" + r["job_id"]).json()
    assert state["state"] == "needs_input"
    with q.factory() as s:
        job = s.get(jobs.Job, r["job_id"])
        assert job.checkpoint and job.result_bytes
    assert state["cost"]["provider_microusd"] == 50
    assert (
        q.client.post(ROOT + "/jobs/" + r["job_id"] + "/retry", headers=q.headers).status_code
        == 409
    )
    assert fake.calls == 1


def test_reference_only_material_never_in_model_context_and_deletion_purges(queue):
    from world_model.restaurant_commerce.social_proposals import model_context

    q = queue
    p, _ = setup(q)
    with q.factory() as s:
        c = assemble(s, BUSINESS, ProposalInput.model_validate(p), q.client.app)
    wire = model_context(c)
    assert "references" not in wire and "excerpt" not in json.dumps(wire)
    r = run(q, p)
    q.client.delete(ROOT + "/assets/" + p["asset_id"], headers=q.headers)
    current = q.client.get(ROOT + "/proposals/" + r["id"]).json()
    assert current["stale"] and current["output"] is None


def test_model_crash_marker_blocks_reclaim_and_received_checkpoint_recovers(queue):
    q = queue
    p, _ = setup(q, mode="model")
    fake = FakeGenerator(BUSINESS)
    q.client.app.state.social_generator = fake
    r = create(q, p)
    pair = jobs.claim(q.factory, job_id=r["job_id"])
    # A process disappearing after dispatch cannot safely send this request again.
    with q.factory() as s:
        job = s.get(jobs.Job, pair[0])
        attempt = s.get(jobs.Attempt, f"{job.id}:{job.generation}")
        attempt.usage_json = canonical({"dispatch_started": True})
        job.lease_until = 0
        s.commit()
    assert jobs.claim(q.factory, job_id=r["job_id"]) is None
    assert q.client.get(ROOT + "/jobs/" + r["job_id"]).json()["state"] == "uncertain"
    assert fake.calls == 0
    # A received paid response survives worker death and is reused, never resent.
    p["request_id"] = str(uuid4())
    r = create(q, p)
    pair = jobs.claim(q.factory, job_id=r["job_id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    with q.factory() as s:
        s.get(jobs.Job, pair[0]).lease_until = 0
        s.commit()
    replacement = jobs.claim(q.factory, job_id=r["job_id"])
    jobs.checkpoint(q.factory, q.client.app, *replacement)
    jobs.complete(q.factory, q.client.app, *replacement)
    assert fake.calls == 1
    info = q.client.get(ROOT + "/jobs/" + r["job_id"]).json()
    assert info["state"] == "succeeded" and info["cost"]["provider_microusd"] == 50
    assert info["attempts"][-1]["usage"]["checkpoint_reused"]


def test_qualification_preservation_and_changed_sources_block_paid_response(queue):
    q = queue
    p, _ = setup(q, mode="model")
    fake = FakeGenerator(BUSINESS)
    q.client.app.state.social_generator = fake
    r = create(q, p)
    pair = jobs.claim(q.factory, job_id=r["job_id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    payload = context_payload()
    payload["expected_revision"] = 1
    payload["facts"][0]["value"] = "15000"
    save_context(q, payload)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        jobs.complete(q.factory, q.client.app, *pair)
    info = q.client.get(ROOT + "/jobs/" + r["job_id"]).json()
    assert info["cost"]["provider_microusd"] == 50 and fake.calls == 1
    with q.factory() as s:
        context = json.loads(s.get(Proposal, r["id"]).input_json)["context"]
    context["facts"][1]["text"] = "Solo por encargo. No disponible los domingos."
    flags = check_copy(
        "Disponible los domingos.",
        [Claim(text="Disponible los domingos.", fact_ids=["description"])],
        context,
    )
    assert "qualification_missing" in flags
