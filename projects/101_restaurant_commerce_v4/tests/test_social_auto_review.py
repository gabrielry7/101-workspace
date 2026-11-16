"""Advisory review uses real jobs, source/version checks and a fake paid boundary."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import io
import json
import zipfile
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_social_jobs import queue, process, state
from test_social_production import (
    BUSINESS,
    OTHER,
    ROOT,
    approval,
    brief,
    create,
    env,
    factory,
    photo,
    social,
)
from world_model.restaurant_commerce import social_jobs as jobs
from world_model.restaurant_commerce.social_auto_review import (
    DIMENSIONS,
    image_for_model,
    validate_model,
)
from world_model.restaurant_commerce.social_production import Revision
from world_model.restaurant_commerce.social_research_models import AutomatedReview
from world_model.restaurant_commerce.models import StaffMembership


def check(q, pack, **changes):
    p = dict(request_id=str(uuid4()), digest=pack["digest"], mode="rules")
    p.update(changes)
    r = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/automated-reviews", json=p, headers=q.headers
    )
    assert r.status_code == 200, r.text
    return r.json(), p


def reviews(q, pack):
    r = q.client.get(ROOT + "/packs/" + pack["id"] + "/automated-reviews")
    assert r.status_code == 200, r.text
    return r.json()["reviews"]


def model_reply(ctx):
    return {
        "criteria": [
            dict(
                criterion=c,
                verdict="uncertain",
                reason="Synthetic judgment needs human review",
                suggestion="Compare the full post with the actual brief",
                confidence=0.5,
                evidence=[dict(surface="caption", quote=ctx["caption"])],
            )
            for c in DIMENSIONS
        ]
    }


class FakeReview:
    calls = 0
    reservations = 0
    explode = False
    bad = False

    def allowed_review(self, business):
        return business == BUSINESS

    def reserve_review(self, s, job, ctx, schema, system):
        self.reservations += 1
        assert ctx["image"]["byte_length"] <= 256 * 1024
        return dict(
            model="fixture-not-live",
            model_calls=1,
            reserved_provider_microusd=100,
            actual_provider_microusd=None,
            provider_cost_basis="fixture_reservation",
        )

    def generate_review(self, ctx, data, schema, system):
        import hashlib

        self.calls += 1
        assert hashlib.sha256(data).hexdigest() == ctx["image"]["sha256"]
        if self.explode:
            raise RuntimeError("synthetic uncertain delivery")
        value = model_reply(ctx)
        if self.bad:
            value["criteria"][0]["evidence"][0]["quote"] = "Invented quotation"
        return value, dict(complete=True, usage={"input_tokens": 10, "output_tokens": 20})

    def settle(self, s, job, receipt):
        return dict(actual_provider_microusd=20, provider_cost_basis="fixture_observed_usage")


def test_rules_review_job_feedback_export_and_changed_version(queue):
    q = queue
    value, pack = create(q)
    row, p = check(q, pack)
    repeated = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/automated-reviews", json=p, headers=q.headers
    )
    assert repeated.json()["id"] == row["id"]
    assert process(q, row)["state"] == "succeeded"
    result = reviews(q, pack)[0]
    out = result["output"]
    assert result["activity"]["cost"]["provider_microusd"] == 0
    assert len(out["criteria"]) == 5 and out["overall_score"] is None
    assert out["criteria"][0]["verdict"] == "no_concern_detected"
    assert all(c["verdict"] == "uncertain" for c in out["criteria"][1:])
    assert not q.client.get(ROOT + "/packs/" + pack["id"]).json()["approved"]
    fb = dict(
        request_id=str(uuid4()),
        choice="helpful",
        kind="technical",
        reason="This separates the file checks from aesthetic judgment",
    )
    url = ROOT + "/automated-reviews/" + row["id"] + "/feedback"
    for _ in range(2):
        assert q.client.post(url, json=fb, headers=q.headers).status_code == 200
    assert len(reviews(q, pack)[0]["feedback"]) == 1
    assert reviews(q, pack)[0]["feedback"][0]["training_permission"] == "not_granted_by_feedback"
    assert approval(q, pack).status_code == 200
    exported = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as z:
        assert json.loads(z.read("automated-review.json"))["reviews"][0]["id"] == row["id"]
    value.update(
        expected_revision=1,
        request_id=str(uuid4()),
        revision_reason="strategy",
        hypothesis="A different explanation could help.",
    )
    r = q.client.put(ROOT + "/packs/" + pack["id"], json=value, headers=q.headers)
    assert r.status_code == 200, r.text
    old = reviews(q, pack)[0]
    assert old["stale"] and old["output"] is None and old["feedback"] == []
    assert (
        q.client.post(url, json={**fb, "request_id": str(uuid4())}, headers=q.headers).status_code
        == 409
    )


def test_model_disabled_and_explicit_media_permission_and_scope(queue):
    q = queue
    _, pack = create(q)
    url = ROOT + "/packs/" + pack["id"] + "/automated-reviews"
    p = dict(request_id=str(uuid4()), digest=pack["digest"], mode="model")
    assert q.client.post(url, json=p, headers=q.headers).status_code == 503
    q.client.app.state.social_generator = FakeReview()
    assert q.client.post(url, json=p, headers=q.headers).status_code == 409
    assert q.client.post(url.replace(BUSINESS, OTHER), json=p, headers=q.headers).status_code == 403
    assert q.client.post(url, json=p).status_code == 403


@pytest.mark.parametrize("bad,explode", [(False, False), (True, False), (False, True)])
def test_model_checkpoint_no_resend_and_invalid_response_cost_retained(queue, bad, explode):
    q = queue
    _, pack = create(q)
    runtime = FakeReview()
    runtime.bad = bad
    runtime.explode = explode
    q.client.app.state.social_generator = runtime
    row, _ = check(q, pack, mode="model", media_processing_confirmed=True)
    assert jobs.dispatch_one(q.factory, q.client.app)
    status = state(q, row)
    assert runtime.calls == runtime.reservations == 1
    if bad or explode:
        assert status["state"] in {"failed", "uncertain", "needs_input"}, status
        assert (
            q.client.post(ROOT + "/jobs/" + row["id"] + "/retry", headers=q.headers).status_code
            == 409
        )
        assert reviews(q, pack)[0]["output"] is None
    else:
        assert status["state"] == "succeeded", status
        assert reviews(q, pack)[0]["output"]["mode"] == "model"
    if not explode:
        assert status["cost"]["provider_microusd"] == 20
    else:
        assert status["cost"]["provider_microusd"] is None
    assert not jobs.dispatch_one(q.factory, q.client.app)


def test_review_checkpoint_reused_after_worker_death(queue):
    q = queue
    _, pack = create(q)
    runtime = FakeReview()
    q.client.app.state.social_generator = runtime
    row, _ = check(q, pack, mode="model", media_processing_confirmed=True)
    pair = jobs.claim(q.factory, job_id=row["id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    with q.factory() as s:
        s.get(jobs.Job, row["id"]).lease_until = 0
        s.commit()
    replacement = jobs.claim(q.factory, job_id=row["id"])
    jobs.checkpoint(q.factory, q.client.app, *replacement)
    jobs.complete(q.factory, q.client.app, *replacement)
    assert runtime.calls == 1 and reviews(q, pack)[0]["state"] == "succeeded"


def test_unknown_model_delivery_after_worker_loss_is_never_dispatched_again(queue):
    q = queue
    _, pack = create(q)
    runtime = FakeReview()
    runtime.explode = True
    q.client.app.state.social_generator = runtime
    row, _ = check(q, pack, mode="model", media_processing_confirmed=True)
    pair = jobs.claim(q.factory, job_id=row["id"])
    with pytest.raises(RuntimeError):
        jobs.checkpoint(q.factory, q.client.app, *pair)
    # Simulate process death without its exception handler recording failure.
    with q.factory() as s:
        s.get(jobs.Job, row["id"]).lease_until = 0
        s.commit()
    assert jobs.claim(q.factory, job_id=row["id"]) is None
    assert state(q, row)["state"] == "uncertain"
    assert state(q, row)["cost"]["provider_microusd"] is None
    assert runtime.calls == 1


def test_revoked_authority_and_source_deletion_fail_closed(queue):
    q = queue
    _, pack = create(q)
    row, _ = check(q, pack)
    with q.factory() as s:
        j = s.get(jobs.Job, row["id"])
        s.get(StaffMembership, (j.actor_id, BUSINESS)).role = "viewer"
        s.commit()
    assert jobs.dispatch_one(q.factory, q.client.app)
    assert state(q, row)["state"] == "needs_input"
    with q.factory() as s:
        j = s.get(jobs.Job, row["id"])
        s.get(StaffMembership, (j.actor_id, BUSINESS)).role = "manager"
        s.commit()
    row, _ = check(q, pack)
    process(q, row)
    assert (
        q.client.delete(
            ROOT + "/assets/" + pack["document"]["brief"]["asset_id"], headers=q.headers
        ).status_code
        == 200
    )
    with q.factory() as s:
        assert s.get(AutomatedReview, row["id"]).output_json is None
    assert reviews(q, pack)[0]["stale"]


def test_model_cannot_approve_bad_technical_output_or_invent_evidence():
    ctx = dict(
        caption="Dato confirmado.",
        facts=[dict(id="f", text="Dato confirmado.")],
        brand_direction="Natural",
        voice_rules="Claro",
        visual_direction="Simple",
        reference_judgments=[],
        technical=dict(status="failed"),
    )
    value = model_reply(ctx)
    assert validate_model(value, ctx)["criteria"][0]["verdict"] == "needs_changes"
    value["criteria"][0]["evidence"] = [
        dict(surface="fact", fact_id="absent", quote="Dato confirmado.")
    ]
    with pytest.raises(HTTPException, match="unknown_fact_quote"):
        validate_model(value, ctx)
    value = model_reply(ctx)
    value["criteria"][0]["evidence"] = [
        dict(surface="image", region=dict(x=0.9, y=0, width=0.2, height=0.5))
    ]
    with pytest.raises(ValueError):
        validate_model(value, ctx)
