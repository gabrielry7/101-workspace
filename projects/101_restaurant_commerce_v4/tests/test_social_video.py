"""Actual local media bytes; synthetic labelled clips, never customer footage."""

# ruff: noqa: F401,F811 -- shared pytest fixtures
import base64
import copy
import hashlib
import io
import json
import subprocess
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_social_jobs import queue, process, jobs
from test_social_production import social, env, factory, BUSINESS, OTHER, ROOT, create, approval
from world_model.restaurant_commerce.social_production import Asset, Pack, Revision
from world_model.restaurant_commerce.social_video_models import ClipMedia, VideoOutput


@pytest.fixture(scope="session")
def clips(tmp_path_factory):
    td = tmp_path_factory.mktemp("synthetic-video")
    files = []
    for i, color in enumerate(("red", "green", "blue")):
        out = td / f"fixture-{i}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=720x1280:r=24,drawbox=x=40:y=80:w=200:h=160:color=white:t=fill",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={440 + i * 110}:sample_rate=48000",
                "-t",
                "3",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(out),
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )
        files.append(out)
    return files


def shoot(q):
    _, pack = create(q)
    p = {"request_id": str(uuid4()), "pack_id": pack["id"], "expected_revision": pack["revision"]}
    r = q.client.post(ROOT + "/shoots", headers=q.headers, json=p)
    assert r.status_code == 200, r.text
    return pack, r.json()


def upload(q, s, shot, path, **changes):
    raw = path.read_bytes()
    payload = {
        "media_kind": "video",
        "shoot_id": s["id"],
        "shot_id": shot,
        "total": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rights_statement": "Synthetic licensed engineering clip, not real owner material",
        "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "permitted_use": "production",
        "fixture": True,
    }
    payload.update(changes)
    r = q.client.post(ROOT + "/uploads", headers=q.headers, json=payload)
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    for offset in range(0, len(raw), 262144):
        p = {
            "offset": offset,
            "data_base64": base64.b64encode(raw[offset : offset + 262144]).decode(),
        }
        r = q.client.put(ROOT + "/uploads/" + uid, headers=q.headers, json=p)
        assert r.status_code == 200, r.text
    return q.client.post(ROOT + "/uploads/" + uid + "/complete", headers=q.headers)


def ready(q, files):
    pack, s = shoot(q)
    takes = []
    for id, path in zip(("detail", "process", "finish"), files, strict=True):
        r = upload(q, s, id, path)
        assert r.status_code == 200, r.text
        takes.append(r.json())
    timeline = {
        "shoot_id": s["id"],
        "clips": [
            {
                "shot_id": id,
                "asset_id": t["id"],
                "source_in": 0,
                "source_out": 1500,
                "timeline_start": i * 1500,
            }
            for i, (id, t) in enumerate(zip(("detail", "process", "finish"), takes, strict=True))
        ],
    }
    return pack, s, takes, timeline


def render(q, pack, timeline):
    data = {
        "request_id": str(uuid4()),
        "expected_revision": pack["revision"],
        "timeline": timeline,
        "confirmed": True,
    }
    route = ROOT + "/packs/" + pack["id"] + "/video"
    r = q.client.post(route, headers=q.headers, json=data)
    assert r.status_code == 200, r.text
    job = r.json()
    assert q.client.post(route, headers=q.headers, json=data).json()["id"] == job["id"]
    assert process(q, job)["state"] == "succeeded"
    result = q.client.get(ROOT + "/packs/" + pack["id"]).json()
    return result, job


def review_video(q, p):
    criteria = {
        k: {"verdict": "acceptable", "reason": "Synthetic full temporal/audio engineering review"}
        for k in ("technical", "factual", "craft", "brand_fit", "purpose")
    }
    data = {
        "request_id": str(uuid4()),
        "digest": p["digest"],
        "outcome": "ready",
        "reason": "Complete fixture video reviewed for this test",
        **criteria,
    }
    route = ROOT + "/packs/" + p["id"]
    assert q.client.post(route + "/reviews", headers=q.headers, json=data).status_code == 409
    data["video_watched_and_listened"] = True
    r = q.client.post(route + "/reviews", headers=q.headers, json=data)
    assert r.status_code == 200, r.text
    return q.client.post(
        route + "/approve",
        headers=q.headers,
        json={"digest": p["digest"], "review_id": r.json()["id"]},
    )


def test_actual_montage_full_workflow_and_targeted_revision(queue, clips, tmp_path):
    q = queue
    pack, s, takes, timeline = ready(q, clips)
    p, j = render(q, pack, timeline)
    assert p["revision"] == 2 and not p["approved"]
    assert p["document"]["caption"] == pack["document"]["caption"]
    assert p["document"]["video_output"]["width"] == 1080
    assert abs(p["document"]["video_output"]["duration_ms"] - 4500) < 150
    assert review_video(q, p).status_code == 200
    route = ROOT + "/packs/" + p["id"]
    final = q.client.get(route + "/video/final")
    assert final.status_code == 200 and final.headers["content-type"] == "video/mp4"
    out = tmp_path / "final.mp4"
    out.write_bytes(final.content)
    pcm = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(out), "-map", "0:a:0", "-f", "s16le", "-"],
        check=True,
        capture_output=True,
        timeout=15,
    ).stdout
    assert any(pcm), "Natural source sound was lost"
    zdata = q.client.get(route + "/export")
    assert zdata.status_code == 200, zdata.text
    with zipfile.ZipFile(io.BytesIO(zdata.content)) as z:
        assert len([name for name in z.namelist() if name.startswith("originals/")]) == 3
        assert z.read("video.mp4") == final.content
        assert z.read("README.txt").decode().startswith("Paquete de vídeo")
        assert "Usa post.jpg" not in z.read("README.txt").decode()
        assert json.loads(z.read("timeline.json"))["clips"][1]["asset_id"] == takes[1]["id"]
        for name, m in json.loads(z.read("manifest.json"))["files"].items():
            assert (
                len(z.read(name)) == m["bytes"]
                and hashlib.sha256(z.read(name)).hexdigest() == m["sha256"]
            )
        assert (
            json.loads(z.read("approval.json"))["binding"]["video"]["files"]["video.mp4"]["sha256"]
            == hashlib.sha256(final.content).hexdigest()
        )
    # Replace only process shot, preserve the other selected ranges/crops/audio.
    new = upload(q, s, "process", clips[0])
    assert new.status_code == 200
    changed = copy.deepcopy(timeline)
    changed["clips"][1]["asset_id"] = new.json()["id"]
    newer, _ = render(q, p, changed)
    assert newer["revision"] == 3 and not newer["approved"]
    assert (
        newer["document"]["brief"]["video"]["clips"][0]
        == p["document"]["brief"]["video"]["clips"][0]
    )
    assert q.client.get(route + "/export").status_code == 409
    assert review_video(q, newer).status_code == 200


@pytest.mark.parametrize(
    "change,code",
    [
        ("missing", 422),
        ("gap", 422),
        ("range", 422),
        ("crop", 422),
        ("foreign", 404),
        ("other_shot", 409),
        ("reference", 409),
        ("expired", 409),
    ],
)
def test_invalid_timeline_is_rejected(queue, clips, change, code):
    q = queue
    pack, s, takes, t = ready(q, clips)
    if change == "missing":
        t["clips"].pop()
    elif change == "gap":
        t["clips"][1]["timeline_start"] = 1501
    elif change == "range":
        t["clips"][0]["source_out"] = 4000
        t["clips"][1]["timeline_start"] = 4000
        t["clips"][2]["timeline_start"] = 5500
    elif change == "crop":
        t["clips"][0]["focal_x"] = 1.2
    elif change == "foreign":
        t["clips"][0]["asset_id"] = "not-this-tenant"
    elif change == "other_shot":
        t["clips"][0]["asset_id"], t["clips"][1]["asset_id"] = (
            t["clips"][1]["asset_id"],
            t["clips"][0]["asset_id"],
        )
    else:
        with q.factory() as session:
            a = session.get(Asset, takes[0]["id"])
            m = json.loads(a.metadata_json)
            m.update(
                {"permitted_use": "reference_only"}
                if change == "reference"
                else {"expires_at": "2000-01-01T00:00:00Z"}
            )
            a.metadata_json = json.dumps(m)
            session.commit()
    r = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/video",
        headers=q.headers,
        json={"request_id": str(uuid4()), "expected_revision": 1, "timeline": t, "confirmed": True},
    )
    assert r.status_code == code, r.text


def test_revocation_purges_all_video_derivatives_and_blocks_history(queue, clips):
    q = queue
    pack, s, takes, t = ready(q, clips)
    p, j = render(q, pack, t)
    assert review_video(q, p).status_code == 200
    aid = takes[1]["id"]
    assert q.client.delete(ROOT + "/assets/" + aid, headers=q.headers).status_code == 200
    route = ROOT + "/packs/" + p["id"]
    for suffix in (
        "/export",
        "/video/preview",
        "/video/final",
        "/video/cover",
        "/revisions/2/image",
    ):
        assert q.client.get(route + suffix).status_code == 409
    assert q.client.get(ROOT + "/video/takes/" + aid + "/analysis").status_code == 409
    with q.factory() as session:
        row = session.get(VideoOutput, f"{p['id']}:2")
        assert row.final == row.preview == row.cover == b""
        assert session.get(ClipMedia, aid).analysis == b""
        assert session.get(jobs.Job, j["id"]).state == "needs_input"
    replacement = upload(q, s, "process", clips[0])
    assert replacement.status_code == 200, replacement.text
    changed = copy.deepcopy(t)
    changed["clips"][1]["asset_id"] = replacement.json()["id"]
    recovered, _ = render(q, p, changed)
    assert recovered["revision"] == 3 and not recovered["approved"]
    assert recovered["document"]["brief"]["video"]["clips"][0]["asset_id"] == takes[0]["id"]
    assert recovered["document"]["brief"]["video"]["clips"][2]["asset_id"] == takes[2]["id"]
    assert q.client.get(route + "/video/preview").status_code == 200


def test_bad_upload_has_specific_rerecord_request_and_no_fake_take(queue, clips, tmp_path):
    q = queue
    pack, s = shoot(q)
    bad = tmp_path / "bad.mov"
    bad.write_bytes(b"not a video")
    r = upload(q, s, "detail", bad)
    assert r.status_code == 422 and r.json()["detail"] == "video_decode_failed_rerecord"
    assert q.client.get(ROOT + "/shoots/" + s["id"]).json()["missing_shots"] == [
        "detail",
        "process",
        "finish",
    ]
    assert q.client.get(ROOT.replace(BUSINESS, OTHER) + "/shoots/" + s["id"]).status_code in (
        403,
        404,
    )


def test_video_checkpoint_lease_recovery_and_changed_approval(queue, clips):
    q = queue
    pack, s, takes, t = ready(q, clips)
    r = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/video",
        headers=q.headers,
        json={"request_id": str(uuid4()), "expected_revision": 1, "timeline": t, "confirmed": True},
    )
    jid = r.json()["id"]
    first = jobs.claim(q.factory, job_id=jid)
    jobs.checkpoint(q.factory, q.client.app, *first)
    with q.factory() as session:
        session.get(jobs.Job, jid).lease_until = 0
        session.commit()
    second = jobs.claim(q.factory, job_id=jid)
    with pytest.raises(HTTPException):
        jobs.complete(q.factory, q.client.app, *first)
    jobs.checkpoint(q.factory, q.client.app, *second)
    jobs.complete(q.factory, q.client.app, *second)
    p = q.client.get(ROOT + "/packs/" + pack["id"]).json()
    assert p["revision"] == 2
    job = q.client.get(ROOT + "/jobs/" + jid).json()
    assert job["attempts"][1]["usage"]["checkpoint_reused"]
    assert job["attempts"][1]["usage"]["model_calls"] == 0
    with pytest.raises(HTTPException):
        jobs.complete(q.factory, q.client.app, *second)


def test_portrait_rotation_hdr_and_silent_source_contract(clips, tmp_path):
    from world_model.restaurant_commerce.social_video_media import intake, encode
    from world_model.restaurant_commerce.social_video_contracts import Timeline

    # Ordinary source without audio stays usable; sound is not a mandatory speech test.
    silent = tmp_path / "silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(clips[0]),
            "-an",
            "-c:v",
            "copy",
            str(silent),
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )
    meta, analysis, poster = intake(silent.read_bytes())
    assert not meta["has_audio"] and meta["transcription"] == "separate_job_when_requested"
    assert analysis and poster
    # Phone rotation is applied to displayed geometry before orientation checks.
    rotated = tmp_path / "rotated.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-display_rotation",
            "90",
            "-i",
            str(clips[0]),
            "-c",
            "copy",
            str(rotated),
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )
    with pytest.raises(HTTPException, match="video_record_vertically"):
        intake(rotated.read_bytes())
    hdr = tmp_path / "hdr.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(clips[0]),
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            "-color_primaries",
            "bt2020",
            "-color_trc",
            "smpte2084",
            "-colorspace",
            "bt2020nc",
            "-x264-params",
            "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc",
            "-c:a",
            "copy",
            str(hdr),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    with pytest.raises(HTTPException, match="video_hdr_record_in_sdr"):
        intake(hdr.read_bytes())


def test_clip_expiry_and_corrupted_output_fail_closed(queue, clips):
    q = queue
    pack, s, takes, t = ready(q, clips)
    p, j = render(q, pack, t)
    assert review_video(q, p).status_code == 200
    route = ROOT + "/packs/" + p["id"]
    with q.factory() as session:
        v = session.get(VideoOutput, f"{p['id']}:2")
        v.final = b"corrupt"
        session.commit()
    assert q.client.get(route + "/video/final").status_code == 409
    assert q.client.get(route + "/export").status_code == 409
    with q.factory() as session:
        a = session.get(Asset, takes[0]["id"])
        m = json.loads(a.metadata_json)
        m["expires_at"] = "2000-01-01T00:00:00Z"
        a.metadata_json = json.dumps(m)
        session.get(ClipMedia, a.id).expires_at = 0
        session.commit()
    jobs.purge_unavailable(q.factory)
    with q.factory() as session:
        assert session.get(ClipMedia, takes[0]["id"]).analysis == b""
        assert session.get(VideoOutput, f"{p['id']}:2").final == b""
    assert q.client.get(route).json()["stale"]


def test_pre_video_queued_photo_snapshot_still_completes(queue):
    from test_social_jobs import submit

    q = queue
    j, _ = submit(q)
    # Replay the prior schema's stored optional-field representation.
    with q.factory() as session:
        row = session.get(jobs.Job, j["id"])
        payload = json.loads(row.input_json)
        payload["brief"].pop("video", None)
        payload["snapshot"]["brief"].pop("video", None)
        row.input_json = json.dumps(payload)
        session.commit()
    assert process(q, j)["state"] == "succeeded"


def test_variable_frame_rate_and_phone_rotation_normalize(clips, tmp_path):
    from world_model.restaurant_commerce.social_video_media import intake, encode, unpack, probe
    from world_model.restaurant_commerce.social_video_contracts import Timeline

    variable = tmp_path / "variable.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(clips[0]),
            "-vf",
            "setpts='if(lt(N,24),PTS,1.2*PTS)'",
            "-fps_mode",
            "vfr",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            "-c:a",
            "copy",
            str(variable),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    landscape = tmp_path / "landscape.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(clips[1]),
            "-vf",
            "transpose=clock",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            "-c:a",
            "copy",
            str(landscape),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    rotated = tmp_path / "phone.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-display_rotation",
            "90",
            "-i",
            str(landscape),
            "-c",
            "copy",
            str(rotated),
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )
    raws = [variable.read_bytes(), rotated.read_bytes(), clips[2].read_bytes()]
    metas = [intake(raw)[0] for raw in raws]
    assert metas[0]["fps_native"] != "24/1" and metas[1]["rotation"] in (90, 270)
    assert metas[1]["width"] == 720 and metas[1]["height"] == 1280
    timeline = Timeline.model_validate(
        {
            "shoot_id": "fixture",
            "clips": [
                {
                    "shot_id": shot,
                    "asset_id": "fixture-" + str(i),
                    "source_in": 500,
                    "source_out": 1500,
                    "timeline_start": i * 1000,
                }
                for i, shot in enumerate(("detail", "process", "finish"))
            ],
        }
    )
    data, report = encode(raws, timeline, metas)
    final = tmp_path / "normalized.mp4"
    final.write_bytes(unpack(data)["video.mp4"])
    result = probe(final, source=False)
    assert result["fps"] == 30 and result["width"] == 1080 and result["height"] == 1920
    assert abs(result["duration_ms"] - 3000) < 150 and report["technical"] == "passed"


def test_revoked_owner_cannot_finish_video_job(queue, clips):
    from world_model.restaurant_commerce.models import StaffMembership

    q = queue
    pack, s, takes, t = ready(q, clips)
    r = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/video",
        headers=q.headers,
        json={"request_id": str(uuid4()), "expected_revision": 1, "timeline": t, "confirmed": True},
    )
    assert r.status_code == 200, r.text
    jid = r.json()["id"]
    with q.factory() as session:
        job = session.get(jobs.Job, jid)
        session.delete(session.get(StaffMembership, (job.actor_id, BUSINESS)))
        session.commit()
    assert jobs.dispatch_one(q.factory, q.client.app)
    with q.factory() as session:
        assert session.get(jobs.Job, jid).reason == "job_authorization_revoked"
        assert session.get(Pack, pack["id"]).revision == 1
        assert session.get(VideoOutput, f"{pack['id']}:2") is None


def test_named_video_partial_upload_resume_duplicate_completion_and_photo_library(queue, clips):
    q = queue
    pack, s = shoot(q)
    raw = clips[0].read_bytes()
    r = q.client.post(
        ROOT + "/uploads",
        headers=q.headers,
        json={
            "media_kind": "video",
            "shoot_id": s["id"],
            "shot_id": "detail",
            "total": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "rights_statement": "Synthetic source for interrupted upload verification",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "permitted_use": "production",
            "fixture": True,
        },
    )
    assert r.status_code == 200, r.text
    route = ROOT + "/uploads/" + r.json()["id"]
    first = {"offset": 0, "data_base64": base64.b64encode(raw[:1000]).decode()}
    for _ in range(2):
        assert q.client.put(route, headers=q.headers, json=first).json()["received"] == 1000
    assert q.client.get(route).json()["received"] == 1000
    assert q.client.post(route + "/complete", headers=q.headers).status_code == 409
    assert q.client.get(route.replace(BUSINESS, OTHER)).status_code == 403
    for offset in range(1000, len(raw), 262144):
        assert (
            q.client.put(
                route,
                headers=q.headers,
                json={
                    "offset": offset,
                    "data_base64": base64.b64encode(raw[offset : offset + 262144]).decode(),
                },
            ).status_code
            == 200
        )
    result = q.client.post(route + "/complete", headers=q.headers)
    assert result.status_code == 200, result.text
    aid = result.json()["id"]
    assert q.client.post(route + "/complete", headers=q.headers).json()["id"] == aid
    assert not any(a["id"] == aid for a in q.client.get(ROOT + "/assets").json()["assets"])
    assert q.client.get(ROOT + "/video/takes/" + aid + "/analysis").status_code == 200


def test_focal_point_changes_actual_crop_pixels(tmp_path):
    from PIL import Image
    from world_model.restaurant_commerce.social_video_media import intake, encode, unpack
    from world_model.restaurant_commerce.social_video_contracts import Timeline

    wide = tmp_path / "portrait-wide.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=960x1280:r=30,drawbox=x=400:y=120:w=160:h=160:color=white:t=fill",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            str(wide),
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    raw = wide.read_bytes()
    meta = intake(raw)[0]
    centers = []
    for focal in (0, 1):
        timeline = Timeline.model_validate(
            {
                "shoot_id": "fixture",
                "clips": [
                    {
                        "shot_id": shot,
                        "asset_id": "fixture-" + str(i),
                        "source_in": 0,
                        "source_out": 1000,
                        "timeline_start": i * 1000,
                        "focal_x": focal,
                    }
                    for i, shot in enumerate(("detail", "process", "finish"))
                ],
            }
        )
        data, _ = encode([raw] * 3, timeline, [meta] * 3)
        im = Image.open(io.BytesIO(unpack(data)["cover.jpg"])).convert("RGB")
        xs = [x for y in range(150, 450) for x in range(im.width) if min(im.getpixel((x, y))) > 220]
        centers.append(sum(xs) / len(xs))
    # 960×1280 scales to1440×1920: 360px of horizontal crop travel.
    assert abs((centers[0] - centers[1]) - 360) < 3
