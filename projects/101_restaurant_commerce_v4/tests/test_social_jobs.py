"""Real queue state, concurrency and process-death recovery; no provider traffic."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import func, select
from test_social_context import context_payload, linked_brief, save_context
from test_social_production import (
    BUSINESS,
    OTHER,
    ROOT,
    approval,
    brief,
    env,
    factory,
    photo,
    social,
)
from world_model.restaurant_commerce import social_jobs as jobs
from world_model.restaurant_commerce.models import StaffMembership
from world_model.restaurant_commerce.social_production import Pack, Revision


@pytest.fixture
def queue(social):
    social.client.app.state.social_worker_paused = True
    return social


def submit(q, value=None, **changes):
    data = {"kind": "photo_render", "brief": value or brief(photo(q).json()["id"])}
    data.update(changes)
    r = q.client.post(ROOT + "/jobs", json=data, headers=q.headers)
    assert r.status_code == 200, r.text
    return r.json(), data


def state(q, j):
    return q.client.get(ROOT + "/jobs/" + j["id"]).json()


def process(q, j):
    pair = jobs.claim(q.factory, job_id=j["id"])
    assert pair
    jobs.checkpoint(q.factory, q.client.app, *pair)
    jobs.complete(q.factory, q.client.app, *pair)
    return state(q, j)


def test_queue_idempotence_inspection_render_approval_effort(queue):
    q = queue
    j, p = submit(q)
    assert q.client.post(ROOT + "/jobs", json=p, headers=q.headers).json()["id"] == j["id"]
    assert j["state"] == "queued" and j["cost"]["total_microusd"] is None
    assert q.client.get(ROOT).json()["packs"] == []
    result = process(q, j)
    assert result["state"] == "succeeded"
    assert len(result["attempts"]) == 1
    usage = result["attempts"][0]["usage"]
    assert usage["actual_provider_microusd"] == 0 and usage["total_cost_microusd"] is None
    assert usage["model"] is None and usage["prompt_version"] is None
    pack = q.client.get(ROOT + "/packs/" + result["pack_id"]).json()
    assert pack["document"]["caption"] == "Fotografía de prueba."
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
    assert approval(q, pack).status_code == 200
    exported = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert exported.status_code == 200
    import zipfile

    with zipfile.ZipFile(io.BytesIO(exported.content)) as package:
        activity = json.loads(package.read("production.json"))
        assert activity["result_revision"] == result["result_revision"]
        assert activity["attempt_count"] == 1
    # Repeating a completed request is a read, not another output or attempt.
    repeated = q.client.post(ROOT + "/jobs", json=p, headers=q.headers)
    assert repeated.status_code == 200 and repeated.json()["attempt_count"] == 1
    inspect, _ = submit(q, kind="inspect_asset", brief=None, asset_id=p["brief"]["asset_id"])
    inspected = process(q, inspect)
    assert inspected["media"]["source_dimensions"] == [1200, 1500]
    assert inspected["media"]["semantic_analysis"] == "not_run"
    pixels = q.client.get(ROOT + "/jobs/" + inspect["id"] + "/preview")
    assert max(Image.open(io.BytesIO(pixels.content)).size) == 640
    effort = {"request_id": "owner-timing", "role": "owner", "seconds": 75}
    url = ROOT + "/jobs/" + j["id"] + "/effort"
    assert q.client.post(url, json=effort, headers=q.headers).status_code == 200
    assert len(q.client.post(url, json=effort, headers=q.headers).json()["effort"]) == 1
    effort["seconds"] = 85
    assert q.client.post(url, json=effort, headers=q.headers).status_code == 409


def test_concurrent_claim_fencing_and_duplicate_completion(queue):
    q = queue
    j, _ = submit(q)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(lambda _: jobs.claim(q.factory, job_id=j["id"]), range(2)))
    pair = next(p for p in claimed if p)
    assert sum(p is not None for p in claimed) == 1
    jobs.checkpoint(q.factory, q.client.app, *pair)
    # Simulate lease expiry and takeover; old worker cannot commit its bytes.
    with q.factory() as s:
        s.get(jobs.Job, j["id"]).lease_until = 0
        s.commit()
    replacement = jobs.claim(q.factory, job_id=j["id"])
    with pytest.raises(HTTPException, match="job_lease_lost"):
        jobs.complete(q.factory, q.client.app, *pair)
    jobs.checkpoint(q.factory, q.client.app, *replacement)
    jobs.complete(q.factory, q.client.app, *replacement)
    result = state(q, j)
    assert [a["state"] for a in result["attempts"]] == ["interrupted", "succeeded"]
    assert result["attempts"][1]["usage"]["checkpoint_reused"]
    with pytest.raises(HTTPException):
        jobs.complete(q.factory, q.client.app, *replacement)
    with q.factory() as s:
        assert s.scalar(select(func.count()).select_from(Revision)) == 1


def test_actual_killed_worker_after_checkpoint_recovers(queue, tmp_path):
    q = queue
    j, _ = submit(q)
    with q.factory() as s:
        url = str(s.bind.url)
    ready = tmp_path / "checkpoint-ready"
    code = """
import sys,time
from pathlib import Path
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce import social_jobs as j
app=create_app(database_url=sys.argv[1],social_worker_enabled=False,payment_recovery_enabled=False)
f=app.state.session_factory
pair=j.claim(f,job_id=sys.argv[2])
j.checkpoint(f,app,*pair)
Path(sys.argv[3]).write_text('ready')
time.sleep(60)
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", code, url, j["id"], str(ready)],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    try:
        deadline = time.monotonic() + 15
        while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists()
        proc.kill()
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    with q.factory() as s:
        saved = s.get(jobs.Job, j["id"])
        assert saved.checkpoint and saved.result_bytes
        assert s.scalar(select(func.count()).select_from(Revision)) == 0
        saved.lease_until = 0
        s.commit()
    # New app instance represents restart; it does not regenerate checkpoint bytes.
    from world_model.restaurant_commerce.api import create_app

    restarted = create_app(
        database_url=url, social_worker_enabled=False, payment_recovery_enabled=False
    )
    pair = jobs.claim(restarted.state.session_factory, job_id=j["id"])

    def no_render(*_):
        raise AssertionError("checkpoint must be reused")

    jobs.checkpoint(restarted.state.session_factory, restarted, *pair, transform=no_render)
    jobs.complete(restarted.state.session_factory, restarted, *pair)
    r = state(q, j)
    assert r["state"] == "succeeded" and r["attempt_count"] == 2
    assert r["attempts"][0]["state"] == "interrupted"
    assert r["attempts"][0]["usage"]["output_bytes"] > 0
    assert r["attempts"][1]["usage"]["checkpoint_reused"]


def test_changed_facts_and_newer_revision_cannot_be_overwritten(queue):
    q = queue
    c = save_context(q, context_payload())
    j, _ = submit(q, linked_brief(q, c))
    pair = jobs.claim(q.factory, job_id=j["id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    p = context_payload()
    p["expected_revision"] = 1
    p["facts"][0]["value"] = "15000"
    save_context(q, p)
    with pytest.raises(HTTPException) as err:
        jobs.complete(q.factory, q.client.app, *pair)
    jobs.failed(q.factory, *pair, err.value)
    assert state(q, j)["state"] == "superseded"
    with q.factory() as s:
        assert s.scalar(select(func.count()).select_from(Revision)) == 0
    # Two revisions against the same base: only one can win.
    first, p = submit(q)
    done = process(q, first)
    b = p["brief"]
    b.update(expected_revision=1, focal_x=0.1)
    queued, _ = submit(q, b, pack_id=done["pack_id"])
    pair = jobs.claim(q.factory, job_id=queued["id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    b["focal_x"] = 0.9
    assert (
        q.client.put(ROOT + "/packs/" + done["pack_id"], json=b, headers=q.headers).status_code
        == 200
    )
    with pytest.raises(HTTPException) as err:
        jobs.complete(q.factory, q.client.app, *pair)
    jobs.failed(q.factory, *pair, err.value)
    assert state(q, queued)["state"] == "superseded"
    assert (
        q.client.get(ROOT + "/packs/" + done["pack_id"]).json()["document"]["brief"]["focal_x"]
        == 0.9
    )


@pytest.mark.parametrize("failure", ["delete", "expiry", "membership"])
def test_source_and_authorization_rechecked_at_completion(queue, failure):
    q = queue
    j, p = submit(q)
    pair = jobs.claim(q.factory, job_id=j["id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    if failure == "delete":
        assert (
            q.client.delete(
                ROOT + "/assets/" + p["brief"]["asset_id"], headers=q.headers
            ).status_code
            == 200
        )
    else:
        with q.factory() as s:
            if failure == "membership":
                s.get(
                    StaffMembership, (s.get(jobs.Job, j["id"]).actor_id, BUSINESS)
                ).role = "viewer"
            else:
                from world_model.restaurant_commerce.social_production import Asset, canonical

                a = s.get(Asset, p["brief"]["asset_id"])
                m = json.loads(a.metadata_json)
                m["expires_at"] = "2000-01-01T00:00:00+00:00"
                a.metadata_json = canonical(m)
            s.commit()
    with pytest.raises(HTTPException) as err:
        jobs.complete(q.factory, q.client.app, *pair)
    jobs.failed(q.factory, *pair, err.value)
    r = state(q, j)
    assert r["state"] == "needs_input"
    with q.factory() as s:
        assert not s.get(jobs.Job, j["id"]).result_bytes
        assert s.scalar(select(func.count()).select_from(Revision)) == 0


def test_failed_retry_is_bounded_and_preserves_cost_attempts(queue, monkeypatch):
    q = queue
    j, _ = submit(q)
    pair = jobs.claim(q.factory, job_id=j["id"])
    jobs.failed(q.factory, *pair, RuntimeError("private metadata must not leak"))
    assert "private" not in json.dumps(state(q, j))
    assert q.client.post(ROOT + "/jobs/" + j["id"] + "/retry", headers=q.headers).status_code == 200
    done = process(q, j)
    assert [a["state"] for a in done["attempts"]] == ["failed", "succeeded"]
    assert all(a["usage"]["total_cost_microusd"] is None for a in done["attempts"])
    assert q.client.post(ROOT + "/jobs/" + j["id"] + "/retry", headers=q.headers).status_code == 409


def test_permissions_limits_and_no_arbitrary_operations(queue):
    q = queue
    asset = photo(q).json()["id"]
    value = {"kind": "inspect_asset", "asset_id": asset}
    assert q.client.post(ROOT + "/jobs", json=value).status_code == 403
    assert q.client.post(
        ROOT.replace(BUSINESS, OTHER) + "/jobs", json=value, headers=q.headers
    ).status_code in (403, 404)
    for change in ({"kind": "shell"}, {"budget_microusd": 1}, {"command": "echo x"}):
        assert (
            q.client.post(ROOT + "/jobs", json={**value, **change}, headers=q.headers).status_code
            == 422
        )
    ref = photo(q, permitted_use="reference_only").json()["id"]
    assert (
        q.client.post(
            ROOT + "/jobs", json={**value, "asset_id": ref}, headers=q.headers
        ).status_code
        == 409
    )
    j, _ = submit(q, **value, brief=None)
    other = q.client.get(ROOT.replace(BUSINESS, OTHER) + "/jobs/" + j["id"])
    assert other.status_code in (403, 404)
    process(q, j)
    assert q.client.delete(ROOT + "/assets/" + asset, headers=q.headers).status_code == 200
    assert q.client.get(ROOT + "/jobs/" + j["id"] + "/preview").status_code == 409
    with q.factory() as s:
        assert s.get(jobs.Job, j["id"]).result_json is None


def test_completed_inspection_derivative_expiry_is_purged(queue):
    from world_model.restaurant_commerce.social_production import Asset, canonical

    q = queue
    asset = photo(q).json()["id"]
    j, _ = submit(q, kind="inspect_asset", brief=None, asset_id=asset)
    assert process(q, j)["state"] == "succeeded"
    with q.factory() as s:
        a = s.get(Asset, asset)
        meta = json.loads(a.metadata_json)
        meta["expires_at"] = "2000-01-01T00:00:00+00:00"
        a.metadata_json = canonical(meta)
        s.commit()
    assert q.client.get(ROOT + "/jobs/" + j["id"] + "/preview").status_code == 409
    jobs.purge_unavailable(q.factory)
    with q.factory() as s:
        saved = s.get(jobs.Job, j["id"])
        assert not saved.result_bytes and saved.result_json is None
    assert state(q, j)["state"] == "needs_input"


def test_retry_cap_and_derived_size_limit(queue):
    q = queue
    j, _ = submit(q)
    pair = jobs.claim(q.factory, job_id=j["id"])
    with pytest.raises(HTTPException) as e:
        jobs.checkpoint(
            q.factory, q.client.app, *pair, transform=lambda *_: (b"x" * (4 * 1024 * 1024 + 1), {})
        )
    assert e.value.detail == "derived_size_limit"
    jobs.failed(q.factory, *pair, RuntimeError("size"))
    for _ in range(jobs.MAX_ATTEMPTS - 1):
        assert (
            q.client.post(ROOT + "/jobs/" + j["id"] + "/retry", headers=q.headers).status_code
            == 200
        )
        pair = jobs.claim(q.factory, job_id=j["id"])
        jobs.failed(q.factory, *pair, RuntimeError("test"))
    assert state(q, j)["attempt_count"] == jobs.MAX_ATTEMPTS
    assert q.client.post(ROOT + "/jobs/" + j["id"] + "/retry", headers=q.headers).status_code == 409
