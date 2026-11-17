"""Real audio/render/DB pipeline; the recognizer in software tests is explicitly fake."""

# ruff: noqa: F401,F811
import copy
import hashlib
import io
import json
import zipfile
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_social_jobs import jobs, process, queue
from test_social_production import BUSINESS, OTHER, ROOT, create, env, factory, social
from test_social_video import clips, ready, render, review_video, upload
from world_model.restaurant_commerce.social_speech import validate_result
from world_model.restaurant_commerce.social_speech_models import Transcript


class FakeSpeech:
    identity = {
        "model": "explicit_fake_recognizer",
        "worker_sha256": "fixture",
        "adapter": "fixture-v1",
    }
    calls = 0

    def authorize(self, business):
        return business == BUSINESS

    def transcribe(self, audio, duration):
        assert audio.startswith(b"fLaC") and duration == 3000
        self.calls += 1
        return {
            "transcript": {
                "words": [
                    {
                        "index": 0,
                        "start": 200,
                        "end": 500,
                        "text": "No",
                        "probability": 0.98,
                        "uncertain": False,
                    },
                    {
                        "index": 1,
                        "start": 550,
                        "end": 1000,
                        "text": "vendemos",
                        "probability": 0.94,
                        "uncertain": False,
                    },
                    {
                        "index": 2,
                        "start": 1100,
                        "end": 1800,
                        "text": "panes.",
                        "probability": 0.51,
                        "uncertain": True,
                    },
                ]
            },
            "raw": {"fixture": "not actual recognition"},
            "metrics": {"elapsed_seconds": 0.001},
        }


def spoken(q, files):
    q.client.app.state.social_transcriber = FakeSpeech()
    _, pack = create(q)
    response = q.client.post(
        ROOT + "/shoots",
        headers=q.headers,
        json={
            "request_id": str(uuid4()),
            "pack_id": pack["id"],
            "expected_revision": pack["revision"],
            "recipe": "spoken_answer",
        },
    )
    assert response.status_code == 200, response.text
    s = response.json()
    takes = [
        upload(q, s, slot, file).json()
        for slot, file in zip(("detail", "process", "finish"), files, strict=True)
    ]
    r = q.client.post(ROOT + f"/video/takes/{takes[1]['id']}/transcriptions", headers=q.headers)
    assert r.status_code == 200, r.text
    j = r.json()
    assert process(q, j)["state"] == "succeeded"
    t = q.client.get(ROOT + "/transcripts/" + j["id"]).json()
    tl = {
        "shoot_id": s["id"],
        "recipe": "spoken_answer",
        "speech": {"transcript_id": t["id"], "revision": 0, "reviewed": True},
        "clips": [
            {
                "shot_id": slot,
                "asset_id": take["id"],
                "source_in": 0,
                "source_out": 2000,
                "timeline_start": i * 2000,
            }
            for i, (slot, take) in enumerate(
                zip(("detail", "process", "finish"), takes, strict=True)
            )
        ],
    }
    return pack, s, takes, t, tl, j


def correction(t, **kw):
    return {
        "request_id": str(uuid4()),
        "expected_revision": t["revision"],
        "changes": [{"index": 2, "text": "pasteles."}],
        "reason": "Corrección tras escuchar el original; fixture",
        "meaning_confirmed": True,
        **kw,
    }


def test_spoken_word_correction_approval_manifest_and_preserved_cuts(queue, clips, tmp_path):
    q = queue
    p, shoot, takes, t, timeline, j = spoken(q, clips)
    assert t["machine"]["quality"] == "automatic_unverified" and t["words"][2]["uncertain"]
    # Same normalized source/runtime has one durable result, not another model call.
    assert (
        q.client.post(
            ROOT + f"/video/takes/{takes[1]['id']}/transcriptions", headers=q.headers
        ).json()["id"]
        == j["id"]
    )
    assert q.client.app.state.social_transcriber.calls == 1
    p, _ = render(q, p, timeline)
    assert review_video(q, p).status_code == 200
    path = ROOT + f"/packs/{p['id']}"
    assert q.client.get(path + "/export").status_code == 200
    payload = correction(t)
    route = ROOT + "/transcripts/" + t["id"] + "/corrections"
    # Owner-entered ranges must not allow rewriting recognizer-supplied word timing.
    protected = correction(t, changes=[{"index": 2, "text": "panes.", "start": 1100, "end": 1900}])
    rejected = q.client.post(route, json=protected, headers=q.headers)
    assert (
        rejected.status_code == 422
        and rejected.json()["detail"] == "automatic_word_times_protected"
    )
    assert "origin" not in t and "granularity" not in t  # Preserve legacy approval snapshots.
    response = q.client.post(route, json=payload, headers=q.headers)
    assert response.status_code == 200, response.text
    newer = response.json()
    assert newer["revision"] == 1 and newer["machine"] == t["machine"]
    assert newer["words"][2]["text"] == "pasteles." and newer["words"][0]["text"] == "No"
    assert q.client.post(route, json=payload, headers=q.headers).json()["revision"] == 1
    assert q.client.get(path).json()["stale"]
    assert q.client.get(path + "/export").status_code == 409
    timeline["speech"]["revision"] = 1
    fixed, job = render(q, p, timeline)
    assert fixed["document"]["brief"]["video"]["clips"] == p["document"]["brief"]["video"]["clips"]
    assert not fixed["approved"] and q.client.app.state.social_transcriber.calls == 1
    assert review_video(q, fixed).status_code == 200
    data = q.client.get(path + "/export")
    assert data.status_code == 200, data.text
    with zipfile.ZipFile(io.BytesIO(data.content)) as z:
        assert "pasteles." in z.read("subtitles.srt").decode()
        assert "panes." in z.read("transcript-machine.json").decode()
        assert z.read("subtitles.vtt").startswith(b"WEBVTT")
        speech_usage = json.loads(z.read("speech-production.json"))["attempts"][0]["usage"]
        assert speech_usage["model_calls"] == 1 and speech_usage["total_cost_microusd"] is None
        edl = json.loads(z.read("timeline.json"))
        assert edl["captions"][0]["start"] == 2200
        for name, item in json.loads(z.read("manifest.json"))["files"].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == item["sha256"]
        (tmp_path / "spoken.zip").write_bytes(data.content)
    # A stale correction must never overwrite another owner's revision.
    assert q.client.post(route, headers=q.headers, json=correction(t)).status_code == 409
    assert q.client.get(ROOT.replace(BUSINESS, OTHER) + "/transcripts/" + t["id"]).status_code in (
        403,
        404,
    )
    q.client.delete(ROOT + f"/assets/{takes[1]['id']}", headers=q.headers)
    assert q.client.get(ROOT + "/transcripts/" + t["id"]).status_code == 409
    with q.factory() as session:
        row = session.get(Transcript, t["id"])
        assert row.machine_json == "" and row.raw_json == ""
        from sqlalchemy import select
        from world_model.restaurant_commerce.social_production import Revision
        from world_model.restaurant_commerce.social_speech_models import TranscriptEdit

        for revision in session.scalars(select(Revision).where(Revision.pack_id == p["id"])):
            document = json.loads(revision.document)
            if document.get("speech_snapshot"):
                assert document["speech_snapshot"] == {"purged": True}
                assert json.loads(revision.report)["subtitles"] == {"purged": True}
        for job in session.scalars(select(jobs.Job).where(jobs.Job.pack_id == p["id"])):
            snapshot = json.loads(job.input_json).get("snapshot", {})
            if snapshot.get("speech_snapshot"):
                assert snapshot["speech_snapshot"] == {"purged": True}
        for edit in session.scalars(
            select(TranscriptEdit).where(TranscriptEdit.transcript_id == t["id"])
        ):
            assert json.loads(edit.document) == {}


def test_speech_needs_runtime_and_no_lost_negations(queue, clips):
    q = queue
    p, s, takes, t, timeline, _ = spoken(q, clips)
    timeline["clips"][1]["source_in"] = 500
    timeline["clips"][2]["timeline_start"] = 3500
    route = ROOT + f"/packs/{p['id']}/video"
    response = q.client.post(
        route,
        headers=q.headers,
        json={
            "request_id": str(uuid4()),
            "expected_revision": p["revision"],
            "timeline": timeline,
            "confirmed": True,
        },
    )
    assert (
        response.status_code == 422
        and response.json()["detail"] == "speech_trim_would_remove_words"
    )
    q.client.app.state.social_transcriber = None
    q.client.delete(ROOT + f"/assets/{takes[1]['id']}", headers=q.headers)
    replacement = upload(q, s, "process", clips[0]).json()
    r = q.client.post(ROOT + f"/video/takes/{replacement['id']}/transcriptions", headers=q.headers)
    assert r.status_code == 503 and r.json()["detail"] == "speech_runtime_unavailable"


def test_invalid_word_timing_and_renderer_text_are_blocked():
    from world_model.restaurant_commerce.social_subtitles import layout
    from world_model.restaurant_commerce.social_video_contracts import Segment

    word = {"index": 0, "start": 50, "end": 900, "text": "No", "probability": 0.7}
    with pytest.raises(HTTPException):
        validate_result({"words": [word]}, 300)
    with pytest.raises(ValueError):
        validate_result({"words": [{**word, "probability": float("nan")}]}, 1000)
    clip = Segment(
        shot_id="process", asset_id="test", source_in=0, source_out=1000, timeline_start=2000
    )
    with pytest.raises(HTTPException, match="subtitle_unsupported_character"):
        layout([{**word, "text": "{\\p1}m0"}], clip)
    with pytest.raises(HTTPException, match="subtitle_text_overflow"):
        layout([{**word, "text": "W" * 64}], clip)


def test_speech_checkpoint_recovery_runtime_change_and_authorization(queue, clips):
    q = queue
    p, shoot, takes, t, timeline, _ = spoken(q, clips)
    # Changing a runtime creates a distinct idempotent job. Its completed byte
    # checkpoint survives a killed worker; recovery doesn't call the recognizer twice.
    q.client.app.state.social_transcriber.identity = {"model": "explicit_second_fixture"}
    route = ROOT + f"/video/takes/{takes[1]['id']}/transcriptions"
    j = q.client.post(route, headers=q.headers).json()
    pair = jobs.claim(q.factory, job_id=j["id"])
    jobs.checkpoint(q.factory, q.client.app, *pair)
    with q.factory() as session:
        session.get(jobs.Job, j["id"]).lease_until = 0
        session.commit()
    replacement = jobs.claim(q.factory, job_id=j["id"])
    with pytest.raises(HTTPException, match="job_lease_lost"):
        jobs.complete(q.factory, q.client.app, *pair)
    jobs.checkpoint(q.factory, q.client.app, *replacement)
    jobs.complete(q.factory, q.client.app, *replacement)
    result = q.client.get(ROOT + "/jobs/" + j["id"]).json()
    assert result["attempts"][-1]["usage"]["checkpoint_reused"]
    assert q.client.app.state.social_transcriber.calls == 2
    q.client.app.state.social_transcriber.identity = {"model": "explicit_third_fixture"}
    next_job = q.client.post(route, headers=q.headers).json()
    q.client.app.state.social_transcriber.identity = {"model": "changed_after_enqueue"}
    pair = jobs.claim(q.factory, job_id=next_job["id"])
    if pair:
        with pytest.raises(HTTPException, match="speech_runtime_changed"):
            jobs.checkpoint(q.factory, q.client.app, *pair)
    else:
        assert (
            q.client.get(ROOT + "/jobs/" + next_job["id"]).json()["reason"]
            == "speech_runtime_changed"
        )
    q.client.app.state.social_transcriber.authorize = lambda _: False
    assert q.client.post(route, headers=q.headers).status_code == 403


def test_silent_answer_gets_targeted_rerecord_request(queue, clips, tmp_path):
    import subprocess

    q = queue
    q.client.app.state.social_transcriber = FakeSpeech()
    _, p = create(q)
    s = q.client.post(
        ROOT + "/shoots",
        headers=q.headers,
        json={
            "request_id": str(uuid4()),
            "pack_id": p["id"],
            "expected_revision": 1,
            "recipe": "spoken_answer",
        },
    ).json()
    quiet = tmp_path / "quiet.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(clips[0]),
            "-af",
            "volume=0",
            "-c:v",
            "copy",
            str(quiet),
        ],
        check=True,
        timeout=15,
        capture_output=True,
    )
    take = upload(q, s, "process", quiet).json()
    r = q.client.post(ROOT + f"/video/takes/{take['id']}/transcriptions", headers=q.headers)
    assert r.status_code == 200, r.text
    j = r.json()
    pair = jobs.claim(q.factory, job_id=j["id"])
    try:
        jobs.checkpoint(q.factory, q.client.app, *pair)
        pytest.fail("silent speech must not succeed")
    except HTTPException as e:
        assert e.detail == "speech_too_quiet_rerecord"
        jobs.failed(q.factory, *pair, e)
    result = q.client.get(ROOT + "/jobs/" + j["id"]).json()
    assert result["state"] == "needs_input" and result["reason"] == "speech_too_quiet_rerecord"
    assert q.client.app.state.social_transcriber.calls == 0


def test_subtitle_times_safe_regions_and_plain_exports():
    from world_model.restaurant_commerce.social_subtitles import ass, layout, text_exports
    from world_model.restaurant_commerce.social_video_contracts import Segment, Timeline

    clip = Segment(
        shot_id="process", asset_id="test", source_in=1000, source_out=3000, timeline_start=4000
    )
    plan = layout(
        [
            {"index": 0, "start": 1100, "end": 1500, "text": "Sí,"},
            {"index": 1, "start": 1600, "end": 2600, "text": "mañana."},
        ],
        clip,
    )
    assert plan["cues"][0]["start"] == 4100
    assert plan["cues"][0]["end"] == 5600
    assert plan["style"]["safe_bottom"] == 320 and plan["style"]["max_lines"] == 2
    assert "0:00:04.10,0:00:05.60" in ass(plan)
    assert "00:00:04,100 --> 00:00:05,600" in text_exports(plan)["subtitles.srt"]


def test_corrections_scope_expiry_and_deleted_derivatives(queue, clips):
    from datetime import timedelta

    from world_model.restaurant_commerce.models import StaffMembership, utcnow
    from world_model.restaurant_commerce.social_production import Asset, Revision

    q = queue
    p, s, takes, t, timeline, _ = spoken(q, clips)
    route = ROOT + "/transcripts/" + t["id"] + "/corrections"
    invalid = correction(t, changes=[{"index": 99, "text": "inexistente"}])
    assert q.client.post(route, json=invalid, headers=q.headers).status_code == 422
    assert q.client.get(ROOT.replace(BUSINESS, OTHER) + "/transcripts/" + t["id"]).status_code in {
        403,
        404,
    }
    with q.factory() as session:
        asset = session.get(Asset, takes[1]["id"])
        meta = json.loads(asset.metadata_json)
        meta["expires_at"] = (utcnow() - timedelta(seconds=2)).isoformat()
        asset.metadata_json = json.dumps(meta)
        session.commit()
    assert q.client.post(route, json=correction(t), headers=q.headers).status_code == 409
    jobs.purge_unavailable(q.factory)
    with q.factory() as session:
        row = session.get(Transcript, t["id"])
        assert row.machine_json == "" and row.raw_json == ""
