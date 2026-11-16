"""Real scoped artifacts and human judgments; synthetic material, no providers."""

# ruff: noqa: F401,F811
import base64
import copy
import hashlib
import io
import json
import zipfile
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw
from sqlalchemy import select, func
from test_campaigns import env, factory, BUSINESS, OTHER
from test_social_production import social, ROOT, create, brief, photo, approval, assessment_payload
from world_model.restaurant_commerce.social_production import Revision, Approval, Asset, canonical
from world_model.restaurant_commerce.social_review_models import ReviewEvent, Comparison
from world_model.restaurant_commerce.social_reviews import ever_approved


def assess(q, pack, **changes):
    return q.client.post(
        ROOT + "/packs/" + pack["id"] + "/reviews",
        headers=q.headers,
        json=assessment_payload(pack, **changes),
    )


def alternatives(q):
    image = Image.new("RGB", (1400, 1500), "#d6cbb9")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 200, 650, 1100), fill="#845632")
    draw.ellipse((750, 400, 1300, 1000), fill="#bd9158")
    out = io.BytesIO()
    image.save(out, format="JPEG")
    asset = photo(q, data_base64=base64.b64encode(out.getvalue()).decode()).json()["id"]
    value = brief(asset)
    a = q.client.post(ROOT + "/packs", headers=q.headers, json=value).json()
    value.update(expected_revision=1, focal_x=0)
    b = q.client.put(ROOT + "/packs/" + a["id"], headers=q.headers, json=value).json()
    assert a["digest"] != b["digest"]
    return value, a, b


def present(q, a, b, **changes):
    payload = {
        "request_id": str(uuid4()),
        "a_revision": a["revision"],
        "b_revision": b["revision"],
        "a_digest": a["digest"],
        "b_digest": b["digest"],
        "criterion": "brand_fit",
    }
    payload.update(changes)
    return q.client.post(
        ROOT + "/packs/" + a["id"] + "/comparisons", headers=q.headers, json=payload
    ), payload


def test_reject_edit_review_approve_current_only_and_manifest(social):
    q = social
    value, pack = create(q)
    route = ROOT + "/packs/" + pack["id"]
    assert (
        q.client.post(
            route + "/approve",
            headers=q.headers,
            json={
                "digest": pack["digest"],
                "craft_reviewed": True,
                "brand_reviewed": True,
                "purpose_reviewed": True,
            },
        ).status_code
        == 409
    )
    rejected = assess(
        q,
        pack,
        outcome="rejected",
        reason="The crop hides the product",
        craft={"verdict": "needs_changes", "reason": "Product is not visible"},
    )
    assert rejected.status_code == 200, rejected.text
    assert q.client.get(route).json()["review_state"] == "rejected"
    assert q.client.get(route + "/export").status_code == 409
    assert q.client.get(ROOT + "/review-queue").json()["items"][0]["status"] == "rejected"
    value.update(
        expected_revision=1, handoff={"platform": "instagram", "account_label": "@fixture-only"}
    )
    revised = q.client.put(route, headers=q.headers, json=value).json()
    assert revised["review_state"] == "ready_for_review"
    assert assess(q, pack).status_code == 409
    assert approval(q, revised).status_code == 200
    blob = q.client.get(route + "/export")
    assert blob.status_code == 200, blob.text
    with zipfile.ZipFile(io.BytesIO(blob.content)) as z:
        manifest = json.loads(z.read("manifest.json"))
        assert set(z.namelist()) == set(manifest["files"]) | {"manifest.json"}
        for name, item in manifest["files"].items():
            data = z.read(name)
            assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
        assert manifest["approved_scope"]["destination"]["account_label"] == "@fixture-only"
        assert manifest["approved_scope"]["intended_action"] == "manual_export"
        assert manifest["source"]["fixture"]
        review = json.loads(z.read("review.json"))
        assert [e["kind"] for e in review["events"]] == ["assessment", "approval"]
        assert review["commercial"] == {"value": None, "reason": "not_measured"}
        approved = json.loads(z.read("approval.json"))
        assert approved["mode"] == "structured"
        assert approved["binding"]["image_sha256"] == hashlib.sha256(z.read("post.jpg")).hexdigest()
        assert (
            approved["binding"]["caption_sha256"]
            == hashlib.sha256(z.read("caption.txt")).hexdigest()
        )
    history = q.client.get(route + "/history").json()["revisions"]
    assert history[0]["historically_approved"] and not history[1]["historically_approved"]
    with q.factory() as s:
        rejected_row = s.scalar(
            select(ReviewEvent).where(ReviewEvent.revision_id == pack["id"] + ":1")
        )
        assert json.loads(rejected_row.document)["outcome"] == "rejected"


def test_later_review_invalidates_approval_and_is_immutable(social):
    q = social
    _, pack = create(q)
    route = ROOT + "/packs/" + pack["id"]
    assert approval(q, pack).status_code == 200
    value = assessment_payload(
        pack,
        outcome="changes_requested",
        purpose={"verdict": "uncertain", "reason": "Next step unclear"},
        reason="Please clarify the action",
    )
    first = q.client.post(route + "/reviews", headers=q.headers, json=value)
    assert first.status_code == 200
    assert (
        q.client.post(route + "/reviews", headers=q.headers, json=value).json()["id"]
        == first.json()["id"]
    )
    value["reason"] = "Attempt to replace historical reason"
    assert q.client.post(route + "/reviews", headers=q.headers, json=value).status_code == 409
    assert (
        q.client.get(route).json()["historically_approved"]
        and not q.client.get(route).json()["approved"]
    )
    assert q.client.get(route + "/export").status_code == 409
    assert (
        q.client.post(
            route + "/approve",
            headers=q.headers,
            json={"digest": pack["digest"], "review_id": first.json()["id"]},
        ).status_code
        == 409
    )
    ready = assess(q, pack)
    assert ready.status_code == 200
    payload = {"digest": pack["digest"], "review_id": ready.json()["id"]}
    for _ in range(2):
        assert q.client.post(route + "/approve", headers=q.headers, json=payload).status_code == 200
    records = q.client.get(route + "/reviews").json()["events"]
    assert [r["sequence"] for r in records] == [1, 2, 3, 4, 5]
    assert q.client.get(route + "/export").status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        {"reason": " "},
        {"craft": {"verdict": "needs_changes", "reason": ""}},
        {"purpose": {"verdict": "uncertain", "reason": "Not sure"}},
        {"commercial": {"value": 10}},
        {"score": 99},
    ],
)
def test_no_blank_reasons_unresolved_ready_or_unmeasured_success(social, change):
    _, pack = create(social)
    assert assess(social, pack, **change).status_code == 422


def test_tenant_permission_and_revoked_source(social):
    q = social
    value, a, b = alternatives(q)
    route = ROOT + "/packs/" + a["id"]
    assert q.client.get(route.replace(BUSINESS, OTHER) + "/reviews").status_code in (403, 404)
    assert q.client.get(ROOT.replace(BUSINESS, OTHER) + "/review-queue").status_code in (403, 404)
    assert q.client.post(route + "/reviews", json=assessment_payload(b)).status_code == 403
    result, _ = present(q, a, b)
    assert result.status_code == 200, result.text
    pair = result.json()
    assert (
        q.client.delete(ROOT + "/assets/" + value["asset_id"], headers=q.headers).status_code == 200
    )
    assert assess(q, b).status_code == 409
    assert (
        q.client.post(
            ROOT + "/comparisons/" + pair["id"] + "/vote",
            headers=q.headers,
            json={
                "request_id": str(uuid4()),
                "context_sha256": pair["context_sha256"],
                "choice": "tie",
                "reason": "Not enough difference",
            },
        ).status_code
        == 409
    )
    assert q.client.get(route).json()["review_state"] == "needs_input"


@pytest.mark.parametrize("choice", ["a", "b", "tie", "both_unacceptable", "insufficient_context"])
def test_all_pairwise_choices_bound_to_actual_versions_and_reviewer(social, choice):
    q = social
    _, a, b = alternatives(q)
    result, payload = present(q, a, b)
    assert result.status_code == 200, result.text
    pair = result.json()
    assert {pair["a"]["digest"], pair["b"]["digest"]} == {a["digest"], b["digest"]}
    again = q.client.post(
        ROOT + "/packs/" + a["id"] + "/comparisons", headers=q.headers, json=payload
    )
    assert again.json() == pair
    vote = {
        "request_id": str(uuid4()),
        "context_sha256": pair["context_sha256"],
        "choice": choice,
        "reason": "Evaluated this exact brief and pair",
        "tags": ["awkward_crop"],
    }
    route = ROOT + "/comparisons/" + pair["id"] + "/vote"
    bad = dict(vote, context_sha256="0" * 64)
    assert q.client.post(route, headers=q.headers, json=bad).status_code == 409
    saved = q.client.post(route, headers=q.headers, json=vote)
    assert saved.status_code == 200, saved.text
    assert q.client.post(route, headers=q.headers, json=vote).json() == saved.json()
    assert (
        saved.json()["vote"]["choice"] == choice
        and saved.json()["vote"]["reviewer_id"] == pair["reviewer_id"]
    )
    assert saved.json()["allowed_use"] == "private_workspace_review_only"
    vote.update(reason="Changed my mind")
    assert q.client.post(route, headers=q.headers, json=vote).status_code == 409
    assert not q.client.get(ROOT + "/packs/" + a["id"]).json()["approved"]
    assert q.client.get(ROOT + "/comparisons/" + pair["id"] + "/vote").status_code == 405
    assert q.client.post(
        route.replace(BUSINESS, OTHER), headers=q.headers, json=vote
    ).status_code in (403, 404)


def test_pair_rejects_different_context_same_outputs_and_wrong_digests(social):
    q = social
    value, a, b = alternatives(q)
    assert present(q, a, b, a_digest="0" * 64)[0].status_code == 409
    value.update(expected_revision=2, objective="Different purpose")
    c = q.client.put(ROOT + "/packs/" + a["id"], headers=q.headers, json=value).json()
    assert present(q, b, c)[0].json()["detail"] == "comparison_brief_mismatch"
    value.update(expected_revision=3)
    d = q.client.put(ROOT + "/packs/" + a["id"], headers=q.headers, json=value).json()
    assert present(q, c, d)[0].json()["detail"] == "distinct_comparison_required"


def test_corrupted_output_blocks_approval_and_export(social):
    q = social
    _, pack = create(q)
    assert approval(q, pack).status_code == 200
    with q.factory.begin() as s:
        r = s.get(Revision, pack["id"] + ":1")
        r.image = b"not-an-image"
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
    assert assess(q, pack).status_code == 409


def test_legacy_approval_retained_without_invented_review(social):
    q = social
    _, pack = create(q)
    with q.factory.begin() as s:
        rev = s.get(Revision, pack["id"] + ":1")
        doc = json.loads(rev.document)
        doc.pop("review_contract")
        doc["destination_account"] = None
        doc["brief"].pop("handoff")
        rev.document = canonical(doc)
        rev.digest = hashlib.sha256(
            (rev.document + hashlib.sha256(rev.image).hexdigest()).encode()
        ).hexdigest()
        s.add(
            Approval(
                revision_id=rev.id,
                actor_id="legacy-fixture",
                digest=rev.digest,
                approved_at="2026-01-01T00:00:00Z",
            )
        )
    route = ROOT + "/packs/" + pack["id"]
    assert q.client.get(route).json()["approved"]
    assert q.client.get(route + "/reviews").json()["legacy_approval"]
    output = q.client.get(route + "/export")
    assert output.status_code == 200, output.text
    with zipfile.ZipFile(io.BytesIO(output.content)) as z:
        assert json.loads(z.read("review.json"))["events"] == []
        assert json.loads(z.read("approval.json"))["mode"] == "legacy_checkbox"
    # A new structured objection also invalidates a legacy approval without changing its original row.
    p = q.client.get(route).json()
    assert (
        assess(
            q, p, outcome="changes_requested", reason="Historical crop needs correction"
        ).status_code
        == 200
    )
    assert q.client.get(route + "/export").status_code == 409
    with q.factory() as s:
        assert s.get(Approval, pack["id"] + ":1").actor_id == "legacy-fixture"


def test_queue_is_bounded_and_tenant_scoped(social):
    q = social
    value, first = create(q)
    for _ in range(21):
        value["request_id"] = str(uuid4())
        assert q.client.post(ROOT + "/packs", headers=q.headers, json=value).status_code == 200
    page = q.client.get(ROOT + "/review-queue").json()
    assert len(page["items"]) == 20 and page["next_cursor"]
    more = q.client.get(ROOT + "/review-queue", params={"cursor": page["next_cursor"]}).json()
    assert len(more["items"]) == 2 and more["next_cursor"] is None
    assert len({i["id"] for i in page["items"] + more["items"]}) == 22


def test_duplicate_review_and_approval_clicks_serialize(social):
    from concurrent.futures import ThreadPoolExecutor

    q = social
    _, pack = create(q)
    route = ROOT + "/packs/" + pack["id"]
    payload = assessment_payload(pack)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: q.client.post(route + "/reviews", headers=q.headers, json=payload),
                range(2),
            )
        )
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json()["id"] == results[1].json()["id"]
    decision = {"digest": pack["digest"], "review_id": results[0].json()["id"]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        approved = list(
            pool.map(
                lambda _: q.client.post(route + "/approve", headers=q.headers, json=decision),
                range(2),
            )
        )
    assert [r.status_code for r in approved] == [200, 200]
    assert [r["kind"] for r in q.client.get(route + "/reviews").json()["events"]] == [
        "assessment",
        "approval",
    ]


def test_manual_destination_change_is_a_new_unapproved_scope(social):
    q = social
    value, pack = create(q)
    assert approval(q, pack).status_code == 200
    route = ROOT + "/packs/" + pack["id"]
    value.update(
        expected_revision=1,
        handoff={"platform": "facebook", "account_label": "Different manual destination"},
    )
    next_pack = q.client.put(route, headers=q.headers, json=value).json()
    assert next_pack["digest"] != pack["digest"] and not next_pack["approved"]
    assert q.client.get(route + "/export").status_code == 409
    assert (
        q.client.post(
            route + "/approve", headers=q.headers, json={"digest": pack["digest"]}
        ).status_code
        == 409
    )


def test_comparison_reviewer_cannot_be_impersonated(social):
    from world_model.restaurant_commerce.campaign_demo import PASSWORD

    q = social
    _, a, b = alternatives(q)
    r, _ = present(q, a, b)
    pair = r.json()
    # Authenticate a different real staff account with access to the same business.
    from world_model.restaurant_commerce.staff import provision

    with q.factory.begin() as session:
        provision(
            session, "second.reviewer", PASSWORD, BUSINESS, "manager", actor="synthetic-fixture"
        )
    names = ["second.reviewer"]
    login = q.client.post(
        "/api/staff/login",
        headers={"X-101-Login": "1"},
        json={"username": names[0], "password": PASSWORD},
    )
    assert login.status_code == 200
    headers = {"X-101-CSRF": q.client.get("/api/staff/me").json()["csrf"]}
    vote = {
        "request_id": str(uuid4()),
        "context_sha256": pair["context_sha256"],
        "choice": "a",
        "reason": "Different actor cannot overwrite a choice",
    }
    assert (
        q.client.post(
            ROOT + "/comparisons/" + pair["id"] + "/vote", headers=headers, json=vote
        ).status_code
        == 403
    )
