"""Real SQL/API pipeline with labeled observations, never live competitor data."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import copy
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_social_jobs import queue
from test_social_production import BUSINESS, OTHER, ROOT, approval, env, factory, photo, social
from test_social_proposals import create, review, run, setup
from world_model.restaurant_commerce import social_jobs as jobs
from world_model.restaurant_commerce.social_research import model_summary
from world_model.restaurant_commerce.social_research_contracts import ResearchInput
from world_model.restaurant_commerce.models import StaffMembership


def research_payload():
    observed = datetime.now(UTC) - timedelta(hours=1)
    source = dict(
        source="Synthetic reviewed observation, no account access",
        observed_at=observed.isoformat(),
        valid_until=(observed + timedelta(days=3)).isoformat(),
        status="active",
        permission="Test author owns these synthetic annotations",
        fixture=True,
    )
    posts = []
    for i, value in enumerate((10, 20, 30, 80)):
        posts.append(
            dict(
                id="post" + str(i),
                reference_id="writing",
                account_key="fixture-account",
                platform="instagram",
                format="photo",
                subject="Ordinary and unusual fixtures",
                observation="The visible count was recorded at 24 hours.",
                hypothesis="The explanation may have helped.",
                alternatives="Distribution is unknown.",
                adaptation="Answer the question using our own photograph.",
                timestamp_precision="second",
                timezone="UTC",
                published_at=(observed - timedelta(hours=24)).isoformat(),
                metrics=[
                    dict(
                        metric="likes",
                        definition="Visible like count",
                        value=value,
                        availability="measured",
                        window="24h",
                        observed_at=observed.isoformat(),
                        source_ref="Synthetic snapshot",
                    )
                ],
                **source,
            )
        )
    searches = [
        dict(
            id="search1",
            question_id="order",
            platform="instagram",
            locale="es-CO",
            geography="Owner supplied area",
            source_kind="customer_question",
            observation_context="Synthetic authorized customer question",
            observation="A customer asked about the price.",
            **source,
        )
    ]
    return dict(
        expected_revision=0,
        confirmed=True,
        reason="Controlled research fixtures",
        posts=posts,
        searches=searches,
    )


def saved(q, payload):
    r = q.client.put(ROOT + "/research", json=payload, headers=q.headers)
    assert r.status_code == 200, r.text
    return r.json()


def researched(q):
    p, _ = setup(q)
    payload = research_payload()
    board = saved(q, payload)
    p.update(
        question_id="order",
        question="¿Cuánto cuesta?",
        research_version_id=board["id"],
        research_post_ids=["post3"],
        research_search_ids=["search1"],
        search_plan_enabled=True,
    )
    return p, payload, board


def produced(q, p):
    proposal = run(q, p)
    decision = review(q, proposal)
    assert decision.status_code == 200, decision.text
    r = q.client.post(
        ROOT + "/proposals/" + proposal["id"] + "/produce",
        json={"decision_id": decision.json()["id"]},
        headers=q.headers,
    )
    assert r.status_code == 200, r.text
    assert jobs.dispatch_one(q.factory, q.client.app)
    pack = q.client.get(ROOT + "/packs/" + r.json()["pack_id"]).json()
    return proposal, pack


def test_research_to_search_answer_to_exact_approved_package(queue):
    q = queue
    p, payload, board = researched(q)
    comparison = board["analysis"]["posts"][-1]["comparisons"][0]
    assert (
        comparison["sample_size"],
        comparison["median"],
        comparison["range"],
        comparison["relative_to_median"],
    ) == (3, 20, [10, 30], 4)
    proposal, pack = produced(q, p)
    assert proposal["input"]["search_plan"]["search_volume"] is None
    assert "research:posts:post3" in json.dumps(proposal["output"])
    assert (
        pack["document"]["research_snapshot"]["posts"][0]["comparisons"][0]["relative_to_median"]
        == 4
    )
    assert approval(q, pack).status_code == 200
    out = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert out.status_code == 200, out.text
    with zipfile.ZipFile(io.BytesIO(out.content)) as z:
        assert json.loads(z.read("research.json"))["search_volume"] is None
        assert "caption_excerpt" not in z.read("research.json").decode()
    # Old version is retained, unrelated-account additions do not stale work.
    other = copy.deepcopy(payload["posts"][0])
    other.update(id="elsewhere", account_key="other-account")
    payload["posts"].append(other)
    payload["expected_revision"] = 1
    saved(q, payload)
    assert not q.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    # A correction to a baseline source invalidates even if the median stays 20.
    payload["posts"][0]["observation"] = "Corrected description of the baseline source."
    payload["expected_revision"] = 2
    saved(q, payload)
    current = q.client.get(ROOT + "/packs/" + pack["id"]).json()
    assert current["stale"] and any(r["scope"] == "research" for r in current["stale_reasons"])
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
    assert q.client.get(ROOT + "/proposals/" + proposal["id"]).json()["stale"]
    assert len(q.client.get(ROOT + "/research/history").json()["versions"]) == 3


@pytest.mark.parametrize(
    "case", ["zero", "sparse", "lifetime", "unknown", "definition", "format", "paid"]
)
def test_comparisons_keep_age_definitions_missing_and_zero_distinct(queue, case):
    q = queue
    setup(q)
    p = research_payload()
    if case == "zero":
        for row in p["posts"][:3]:
            row["metrics"][0]["value"] = 0
    elif case == "sparse":
        p["posts"] = p["posts"][-2:]
    elif case == "lifetime":
        p["posts"][-1]["metrics"][0]["window"] = "lifetime"
    elif case == "unknown":
        p["posts"][-1]["metrics"][0].update(
            value=None, availability="unavailable", reason="Not exposed"
        )
    elif case == "definition":
        p["posts"][0]["metrics"][0]["definition"] = "Other metric definition"
    elif case == "format":
        p["posts"][0]["format"] = "carousel"
    elif case == "paid":
        p["posts"][0].update(
            paid_support="paid_reported", distribution_evidence="Owner reported paid support"
        )
    c = saved(q, p)["analysis"]["posts"][-1]["comparisons"][0]
    assert c["relative_to_median"] is None
    if case == "zero":
        assert c["median"] == 0 and c["range"] == [0, 0]
    if case == "unknown":
        assert c["value"] is None and c["reason"] == "Not exposed"
    if case in {"definition", "format", "paid"}:
        assert c["sample_size"] == 2


@pytest.mark.parametrize(
    "change", ["minute", "age", "unknown", "volume", "private", "naive", "url"]
)
def test_rejects_invented_precision_private_metrics_and_search_volume(change):
    p = research_payload()
    r = p["posts"][0]
    if change == "minute":
        r.update(timestamp_precision="day", publication_day="2026-01-01")
    if change == "age":
        r["metrics"][0]["window"] = "7d"
    if change == "unknown":
        r["metrics"][0]["value"] = None
    if change == "volume":
        p["searches"][0]["search_volume"] = 100
    if change == "private":
        r["metrics"][0]["metric"] = "competitor_revenue"
    if change == "naive":
        r["published_at"] = "2026-01-01T12:00:00"
    if change == "url":
        r["source_url"] = "http://unsafe.test"
    with pytest.raises(ValueError):
        ResearchInput.model_validate(p)


def test_permissions_include_baseline_annotations_and_revocation(queue):
    q = queue
    p, payload, _ = researched(q)
    proposal = run(q, p)
    with pytest.raises(HTTPException, match="research_model_processing_not_authorized"):
        model_summary(proposal["input"]["research"])
    payload["expected_revision"] = 1
    payload["posts"][-1]["model_processing_allowed"] = True
    payload["searches"][0]["model_processing_allowed"] = True
    board = saved(q, payload)
    p.update(request_id=str(uuid4()), research_version_id=board["id"])
    proposal = run(q, p)
    with pytest.raises(HTTPException, match="research_baseline_model_processing_not_authorized"):
        model_summary(proposal["input"]["research"])
    assert q.client.put(ROOT + "/research", json=payload, headers=q.headers).status_code == 409
    assert q.client.get(ROOT.replace(BUSINESS, OTHER) + "/research").status_code == 403
    assert q.client.put(ROOT + "/research", json=payload).status_code == 403
    with q.factory() as s:
        member = (
            s.get(StaffMembership, (q.actor_id, BUSINESS))
            if hasattr(q, "actor_id")
            else s.query(StaffMembership).filter_by(business_id=BUSINESS).first()
        )
        member.role = "viewer"
        s.commit()
    payload["expected_revision"] = 2
    assert q.client.put(ROOT + "/research", json=payload, headers=q.headers).status_code == 403


@pytest.mark.parametrize("case", ["post_withdrawn", "search_withdrawn", "reference", "expiry"])
def test_selected_research_permissions_and_freshness_block_dependent_exports(
    queue, monkeypatch, case
):
    q = queue
    p, payload, board = researched(q)
    p["reference_ids"] = []  # The reference is used by research, not selected independently.
    if case == "expiry":
        for row in payload["posts"] + payload["searches"]:
            row["valid_until"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        payload["expected_revision"] = 1
        board = saved(q, payload)
        p["research_version_id"] = board["id"]
    _, pack = produced(q, p)
    assert approval(q, pack).status_code == 200
    if case == "expiry":
        from world_model.restaurant_commerce import social_reviews

        later = datetime.now(UTC) + timedelta(hours=2)
        monkeypatch.setattr(social_reviews, "current_time", lambda: later)
        # Imported users of the shared function retain its binding; its underlying
        # production clock is the common policy boundary.
        from world_model.restaurant_commerce import social_production

        monkeypatch.setattr(social_production, "utcnow", lambda: later)
    elif case == "reference":
        from test_social_creative import board_payload

        change = board_payload()
        change["expected_revision"] = 1
        change["references"][0]["permission"] = "Permission withdrawn by the test author"
        assert q.client.put(ROOT + "/creative", json=change, headers=q.headers).status_code == 200
    else:
        payload["expected_revision"] = 1
        payload["posts" if case == "post_withdrawn" else "searches"][-1]["status"] = "withdrawn"
        saved(q, payload)
    assert q.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
