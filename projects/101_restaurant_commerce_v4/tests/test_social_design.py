"""N06 actual image layers, source-bound text, constraints, versions and export."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import copy
import hashlib
import io
import json
import zipfile

import pytest
from fastapi import HTTPException
from PIL import Image
from test_social_context import context_payload, linked_brief, save_context
from test_social_jobs import process, queue, submit
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
from world_model.restaurant_commerce import social_design as design
from world_model.restaurant_commerce.social_production import Brief, render


def scene_payload(layout="photo_first", headline="description", price="price"):
    value = copy.deepcopy(design.presets()[layout])
    if layout != "photo_only":
        value["layers"] = [
            {**layer, "fact_id": headline if layer["id"] == "headline" else price}
            for layer in value["layers"]
            if layer["id"] != "detail"
        ]
    return value


def setup(q, layout="photo_first"):
    ctx = save_context(q, context_payload())
    asset = photo(q).json()["id"]
    payload = brief(
        asset,
        context_version_id=ctx["id"],
        objective=ctx["brief"]["objective"],
        facts=[{k: f[k] for k in ["id", "text", "source", "valid_until"]} for f in ctx["facts"]],
        caption_fact_ids=["description", "price"],
        fact_refs=[
            {"fact_id": f["id"], "context_version_id": ctx["id"], "fact_revision": f["revision"]}
            for f in ctx["facts"]
        ],
        design=scene_payload(layout),
    )
    return ctx, payload


@pytest.mark.parametrize("layout", ["photo_first", "information", "photo_only"])
def test_real_render_source_layers_approval_and_reproducible_export(queue, layout):
    q = queue
    ctx, payload = setup(q, layout)
    job, _ = submit(q, payload)
    finished = process(q, job)
    pack = q.client.get(ROOT + "/packs/" + finished["pack_id"]).json()
    scene = pack["document"]["design"]
    assert scene["layout"] == layout and pack["review"]["technical"] == "passed"
    assert scene["layers"][1]["source_sha256"] == pack["document"]["asset_sha256"]
    if layout != "photo_only":
        assert scene["layers"][-1]["text"] == "Precio: 12000 COP."
        assert scene["fonts"][0]["sha256"] == design.FONT_HASH
        pixels = q.client.get(ROOT + "/packs/" + pack["id"] + "/image").content
        title = scene["layers"][2]
        crop = Image.open(io.BytesIO(pixels)).crop(
            (title["x"], title["y"], title["x"] + title["width"], title["y"] + title["height"])
        )
        assert sum(max(pixel) < 100 for pixel in crop.get_flattened_data()) > 1000
    assert approval(q, pack).status_code == 200
    exported = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as z:
        document = json.loads(z.read("editable.json"))
        actual = z.read("post.jpg")
        assert Image.open(io.BytesIO(actual)).size == (1080, 1350)
        assert json.loads(z.read("design.json")) == scene
        assert not any(name.endswith((".ttf", ".woff2", ".otf")) for name in z.namelist())
        assert "OPEN FONT LICENSE" in z.read("INTER-LICENSE.txt").decode().upper()
        assert design.draw_scene(z.read("original"), scene) == actual
        assert hashlib.sha256(z.read("original")).hexdigest() == document["asset_sha256"]


def test_price_correction_preserves_photo_geometry_and_historical_image(queue):
    q = queue
    ctx, payload = setup(q)
    j, _ = submit(q, payload)
    finished = process(q, j)
    route = ROOT + "/packs/" + finished["pack_id"]
    old = q.client.get(route).json()
    assert approval(q, old).status_code == 200
    before = q.client.get(route + "/image").content
    replacement = context_payload()
    replacement["expected_revision"] = ctx["revision"]
    replacement["facts"][0]["value"] = "15000"
    current = save_context(q, replacement)
    assert q.client.get(route).json()["stale"]
    assert q.client.get(route + "/export").status_code == 409
    updated = copy.deepcopy(payload)
    updated.update(
        expected_revision=1, context_version_id=current["id"], revision_reason="factual_correction"
    )
    updated["facts"] = [
        {k: f[k] for k in ["id", "text", "source", "valid_until"]} for f in current["facts"]
    ]
    updated["fact_refs"] = [
        {"fact_id": f["id"], "context_version_id": current["id"], "fact_revision": f["revision"]}
        for f in current["facts"]
    ]
    j, _ = submit(q, updated, pack_id=old["id"])
    process(q, j)
    after = q.client.get(route).json()
    assert after["revision"] == 2 and not after["approved"] and not after["stale"]
    a, b = old["document"]["design"], after["document"]["design"]
    assert a["layers"][1] == b["layers"][1] and a["styles"] == b["styles"]
    for x, y in zip(a["layers"][2:], b["layers"][2:], strict=True):
        assert all(x[k] == y[k] for k in ("x", "y", "width", "height", "size", "tracking", "align"))
    assert b["layers"][-1]["text"] == "Precio: 15000 COP."
    assert "text.price" in after["document"]["changes"]
    new = q.client.get(route + "/image").content
    assert new != before
    assert (
        Image.open(io.BytesIO(new)).crop((0, 0, 1080, 840)).tobytes()
        == Image.open(io.BytesIO(before)).crop((0, 0, 1080, 840)).tobytes()
    )
    assert q.client.get(route + "/revisions/1/image").content == before
    history = q.client.get(route + "/history").json()["revisions"]
    assert [h["revision"] for h in history] == [2, 1]
    assert history[1]["historically_approved"] and not history[1]["current"]
    assert approval(q, old).status_code == 409
    assert approval(q, after).status_code == 200
    assert q.client.get(route.replace(BUSINESS, OTHER) + "/history").status_code in (403, 404)
    assert q.client.get(route.replace(BUSINESS, OTHER) + "/revisions/1/image").status_code in (
        403,
        404,
    )
    q.client.delete(ROOT + "/assets/" + payload["asset_id"], headers=q.headers)
    assert q.client.get(route + "/revisions/1/image").status_code == 409


@pytest.mark.parametrize(
    "change,code",
    [
        ("overflow", "text_overflow"),
        ("glyph", "unsupported_character"),
        ("safe", "safe_region"),
        ("overlap", "overlap"),
        ("contrast", "contrast"),
        ("foreign_fact", "unresolved_fact"),
    ],
)
def test_bad_scene_is_rejected_before_queue_or_approval(queue, change, code):
    q = queue
    _, p = setup(q)
    if change == "overflow":
        p["facts"][1]["text"] = "Palabra " * 70
    if change == "glyph":
        p["facts"][1]["text"] = "Producto 🧁"
    if change in ("glyph", "overflow"):
        # A standalone owner assertion exercises rendering. Context-linked tampering
        # is rejected earlier by the existing source validator.
        p["fact_refs"] = []
        p["context_version_id"] = None
    if change == "safe":
        p["design"]["layers"][0]["x"] = 0
    if change == "overlap":
        p["design"]["layers"][0]["y"] = 700
    if change == "contrast":
        p["design"]["styles"].update(foreground="#eeeeee", background="#ffffff")
    if change == "foreign_fact":
        p["design"]["layers"][0]["fact_id"] = "unresolved"
    r = q.client.post(ROOT + "/jobs", headers=q.headers, json={"kind": "photo_render", "brief": p})
    assert r.status_code == 422, r.text
    assert code in r.json()["detail"]
    assert q.client.get(ROOT + "/jobs").json()["jobs"] == []


def test_no_arbitrary_text_fonts_or_code_and_low_resolution(queue, monkeypatch, tmp_path):
    q = queue
    _, p = setup(q)
    for change in ("text", "font", "code"):
        bad = copy.deepcopy(p)
        if change == "text":
            bad["design"]["layers"][1]["text"] = "Precio: 15000 COP."
        if change == "font":
            bad["design"]["styles"]["font_id"] = "../../private.ttf"
        if change == "code":
            bad["design"]["command"] = "arbitrary-code"
        assert (
            q.client.post(
                ROOT + "/jobs", headers=q.headers, json={"kind": "photo_render", "brief": bad}
            ).status_code
            == 422
        )
    out = io.BytesIO()
    Image.new("RGB", (500, 500), "#999999").save(out, format="PNG")
    with pytest.raises(HTTPException, match="source_resolution"):
        render(out.getvalue(), Brief.model_validate(p))
    monkeypatch.setattr(design, "FONT_PATH", tmp_path / "missing.ttf")
    with pytest.raises(HTTPException, match="font_missing_or_changed"):
        design.font_record()
    assert q.client.get(ROOT + "/design/options").status_code == 422


def test_long_spanish_unicode_tracking_and_photo_replacement(queue):
    q = queue
    _, p = setup(q, "information")
    p["facts"][1]["text"] = "¿Preparación por encargo? Información útil."
    p["fact_refs"] = []
    p["context_version_id"] = None
    p["design"]["layers"][0].update(size=52, tracking=2)
    j, _ = submit(q, p)
    result = process(q, j)
    first = q.client.get(ROOT + "/packs/" + result["pack_id"]).json()
    assert first["review"]["technical"] == "passed"
    # Explicit owner replacement keeps layer geometry while changing the source reference.
    p["asset_id"] = photo(q).json()["id"]
    p["expected_revision"] = 1
    j, _ = submit(q, p, pack_id=first["id"])
    process(q, j)
    second = q.client.get(ROOT + "/packs/" + first["id"]).json()
    assert second["document"]["design"]["layers"][1]["asset_id"] == p["asset_id"]
    assert second["document"]["design"]["layers"][2:] == first["document"]["design"]["layers"][2:]


def test_reviewed_proposal_caption_survives_owner_photo_replacement(queue):
    from test_social_proposals import review, run
    from test_social_proposals import setup as proposal_setup
    from world_model.restaurant_commerce import social_jobs as jobs

    q = queue
    p, _ = proposal_setup(q)
    proposal = run(q, p)
    decision = review(q, proposal).json()
    produced = q.client.post(
        ROOT + "/proposals/" + proposal["id"] + "/produce",
        json={"decision_id": decision["id"]},
        headers=q.headers,
    )
    assert produced.status_code == 200, produced.text
    assert jobs.dispatch_one(q.factory, q.client.app)
    route = ROOT + "/packs/" + produced.json()["pack_id"]
    before = q.client.get(route).json()
    replacement = copy.deepcopy(before["document"]["brief"])
    replacement.update(asset_id=photo(q).json()["id"], expected_revision=1, design=scene_payload())
    j, _ = submit(q, replacement, pack_id=before["id"])
    process(q, j)
    after = q.client.get(route).json()
    assert after["document"]["caption"] == before["document"]["caption"]
    assert after["document"]["proposal_snapshot"]["owner_replaced_photo"]
    assert after["document"]["proposal_snapshot"]["proposed_asset_id"] == p["asset_id"]
    assert not after["approved"] and approval(q, after).status_code == 200


def test_transparent_owned_png_uses_chosen_background_without_black_matte(queue):
    import base64

    from PIL import ImageDraw

    q = queue
    _, p = setup(q)
    original = Image.new("RGBA", (1200, 1500), (0, 0, 0, 0))
    ImageDraw.Draw(original).rectangle((400, 400, 800, 1000), fill=(130, 55, 30, 255))
    out = io.BytesIO()
    original.save(out, format="PNG")
    uploaded = q.client.post(
        ROOT + "/assets",
        headers=q.headers,
        json={
            "data_base64": base64.b64encode(out.getvalue()).decode(),
            "rights_statement": "Synthetic transparent PNG owned by the test author",
            "expires_at": p["facts"][0]["valid_until"],
            "permitted_use": "production",
            "fixture": True,
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    p["asset_id"] = uploaded.json()["id"]
    j, _ = submit(q, p)
    process(q, j)
    pack = q.client.get(ROOT + "/packs/" + j["pack_id"]).json()
    actual = Image.open(io.BytesIO(q.client.get(ROOT + "/packs/" + pack["id"] + "/image").content))
    assert (
        max(abs(a - b) for a, b in zip(actual.getpixel((10, 10)), (245, 241, 233), strict=True)) < 4
    )
    assert (
        max(abs(a - b) for a, b in zip(actual.getpixel((540, 430)), (130, 55, 30), strict=True)) < 4
    )
