"""Source-timed owner captions work without an ASR runtime or fictitious confidence."""

# ruff: noqa: F401,F811
import copy
import io
import json
import zipfile
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from test_social_jobs import jobs, process, queue
from test_social_production import BUSINESS, OTHER, ROOT, env, factory, social
from test_social_video import clips, ready, render, review_video
from world_model.restaurant_commerce.social_speech_models import Transcript


def captions(**changes):
    return {
        "request_id": str(uuid4()),
        "confirmed": True,
        "segments": [
            {"index": 0, "start": 200, "end": 800, "text": "No vendemos"},
            {"index": 1, "start": 1000, "end": 1800, "text": "panes."},
        ],
        **changes,
    }


def setup(q, clips, *, only_answer=False):
    from test_social_production import create
    from test_social_video import upload

    _, p = create(q)
    response = q.client.post(
        ROOT + "/shoots",
        headers=q.headers,
        json={
            "request_id": str(uuid4()),
            "pack_id": p["id"],
            "expected_revision": p["revision"],
            "recipe": "spoken_answer",
        },
    )
    assert response.status_code == 200, response.text
    s = response.json()
    takes = []
    for shot, file in zip(("detail", "process", "finish"), clips, strict=True):
        if only_answer and shot != "process":
            takes.append(None)
            continue
        r = upload(q, s, shot, file)
        assert r.status_code == 200, r.text
        takes.append(r.json())
    tl = {
        "shoot_id": s["id"],
        "recipe": "spoken_answer",
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
            if take is not None
        ],
    }
    return p, s, takes, tl


def test_manual_captions_correct_times_export_and_withdrawal(queue, clips):
    q = queue
    p, s, takes, tl = setup(q, clips)
    q.client.app.state.social_transcriber = None
    capability = q.client.get(ROOT + "/speech/capability").json()
    assert capability["state"] == "blocked" and capability["manual_subtitles"] == "available"
    route = ROOT + f"/video/takes/{takes[1]['id']}/manual-subtitles"
    payload = captions()
    r = q.client.post(route, headers=q.headers, json=payload)
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["origin"] == "owner_supplied" and t["granularity"] == "segments"
    assert t["machine"]["runtime"] is None and all(w["probability"] is None for w in t["words"])
    assert q.client.post(route, headers=q.headers, json=payload).json()["id"] == t["id"]
    altered = copy.deepcopy(payload)
    altered["segments"][1]["text"] = "otro texto"
    assert q.client.post(route, headers=q.headers, json=altered).status_code == 409
    tl["speech"] = {"transcript_id": t["id"], "revision": 0, "reviewed": True}
    p, _ = render(q, p, tl)
    assert review_video(q, p).status_code == 200
    correction = {
        "request_id": str(uuid4()),
        "expected_revision": 0,
        "meaning_confirmed": True,
        "reason": "Corregí el texto y el tiempo al escuchar la toma.",
        "changes": [{"index": 1, "text": "pasteles.", "start": 1100, "end": 1900}],
    }
    r = q.client.post(
        ROOT + f"/transcripts/{t['id']}/corrections", headers=q.headers, json=correction
    )
    assert r.status_code == 200, r.text
    assert r.json()["words"][1]["start"] == 1100
    assert r.json()["machine"] == t["machine"]
    assert (
        q.client.post(
            ROOT + f"/transcripts/{t['id']}/corrections", headers=q.headers, json=correction
        ).json()["revision"]
        == 1
    )
    overlapping = {
        **correction,
        "request_id": str(uuid4()),
        "expected_revision": 1,
        "changes": [{"index": 1, "text": "pasteles.", "start": 700, "end": 1900}],
    }
    assert (
        q.client.post(
            ROOT + f"/transcripts/{t['id']}/corrections", headers=q.headers, json=overlapping
        ).status_code
        == 422
    )
    assert q.client.get(ROOT + f"/transcripts/{t['id']}").json()["revision"] == 1
    assert q.client.get(ROOT + f"/packs/{p['id']}/export").status_code == 409
    tl["speech"]["revision"] = 1
    fixed, _ = render(q, p, tl)
    assert fixed["document"]["brief"]["video"]["clips"] == p["document"]["brief"]["video"]["clips"]
    assert review_video(q, fixed).status_code == 200
    response = q.client.get(ROOT + f"/packs/{p['id']}/export")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert "transcript-machine.json" not in z.namelist()
        assert json.loads(z.read("transcript-original.json"))["origin"] == "owner_supplied"
        assert "pasteles." in z.read("subtitles.srt").decode()
        plan = json.loads(z.read("subtitle-plan.json"))
        assert (
            len(plan["cues"]) == 2
            and plan["cues"][1]["start"] == 3100
            and plan["cues"][1]["end"] == 3900
        )
        activity = json.loads(z.read("speech-production.json"))
        assert activity["kind"] == "subtitle_manual"
        usage = activity["attempts"][0]["usage"]
        assert usage["model_calls"] == 0 and usage["asr_dispatch_started"] is False
    q.client.delete(ROOT + f"/assets/{takes[1]['id']}", headers=q.headers)
    assert q.client.get(ROOT + f"/transcripts/{t['id']}").status_code == 409
    with q.factory() as session:
        assert session.get(Transcript, t["id"]).machine_json == ""


@pytest.mark.parametrize(
    "segments",
    [
        [{"index": 0, "start": 900, "end": 200, "text": "No"}],
        [
            {"index": 0, "start": 0, "end": 900, "text": "No"},
            {"index": 1, "start": 800, "end": 1500, "text": "sí"},
        ],
        [{"index": 0, "start": 0, "end": 4000, "text": "No"}],
        [{"index": 0, "start": 0, "end": 500, "text": "{\\p1}m0"}],
        [{"index": 0, "start": 0, "end": 500, "text": "No", "probability": 1}],
    ],
)
def test_bad_timing_or_injected_rendering_and_confidence_are_blocked(queue, clips, segments):
    q = queue
    _, _, takes, _ = setup(q, clips, only_answer=True)
    r = q.client.post(
        ROOT + f"/video/takes/{takes[1]['id']}/manual-subtitles",
        headers=q.headers,
        json=captions(segments=segments),
    )
    assert r.status_code == 422, r.text
    with q.factory() as session:
        assert not session.scalars(select(Transcript)).all()


def test_manual_captions_denied_tenant_and_review_required(queue, clips):
    q = queue
    _, _, takes, _ = setup(q, clips, only_answer=True)
    path = f"/video/takes/{takes[1]['id']}/manual-subtitles"
    assert (
        q.client.post(ROOT + path, headers=q.headers, json=captions(confirmed=False)).status_code
        == 422
    )
    assert q.client.post(
        ROOT.replace(BUSINESS, OTHER) + path, headers=q.headers, json=captions()
    ).status_code in (403, 404)


def test_manual_ranges_respect_renderer_bound_with_probe_tolerance():
    from world_model.restaurant_commerce.social_manual_speech import ranges

    ranges([{"start": 29800, "end": 30000}], 30100)
    with pytest.raises(HTTPException) as error:
        ranges([{"start": 29800, "end": 30080}], 30100)
    assert error.value.detail == "manual_caption_times_invalid"
