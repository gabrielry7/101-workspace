"""Closed manual learning loop; synthetic posts and manually entered fixture results."""

# ruff: noqa: F401,F811
import copy, io, json, zipfile
from datetime import datetime, UTC, timedelta
from uuid import uuid4
import pytest
from test_campaigns import env, factory, BUSINESS, OTHER
from test_social_production import social, ROOT, create, approval
from test_social_jobs import queue
from world_model.restaurant_commerce.social_production import Revision


def receipt(pack, **changes):
    p = {
        "request_id": str(uuid4()),
        "digest": pack["digest"],
        "platform": "instagram",
        "account": "fixture-only",
        "permalink": "https://www.instagram.com/p/fixture-" + str(uuid4()) + "/",
        "provider_post_id": "",
        "published_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "timezone": "UTC",
        "timestamp_precision": "second",
        "source_ref": "Synthetic software receipt; no real publication",
        "matches_approved": True,
        "reason": "Test author records a fixture publication",
    }
    p.update(changes)
    return p


def published(q):
    brief, pack = create(q)
    assert approval(q, pack).status_code == 200
    p = receipt(pack)
    r = q.client.post(ROOT + "/packs/" + pack["id"] + "/publications", headers=q.headers, json=p)
    assert r.status_code == 200, r.text
    return brief, pack, p, r.json()


def metric(pub, **changes):
    now = datetime.now(UTC)
    p = {
        "request_id": str(uuid4()),
        "metric": "qualified_inquiries",
        "availability": "measured",
        "value": 0,
        "definition": "Relevant buying inquiries counted manually",
        "window_kind": "lifetime_snapshot",
        "window_start": pub["published_at_utc"],
        "window_end": now.isoformat(),
        "observed_at": now.isoformat(),
        "source_ref": "Synthetic owner tally, no live analytics",
        "source_kind": "owner_report",
    }
    p.update(changes)
    return p


def observe(q, pub, p=None, **changes):
    return q.client.post(
        ROOT + "/publications/" + pub["id"] + "/observations",
        headers=q.headers,
        json=p or metric(pub, **changes),
    )


def get_report(q, pub):
    return q.client.get(ROOT + "/publications/" + pub["id"] + "/report").json()


def decision(q, pub, r, **changes):
    p = {
        "request_id": str(uuid4()),
        "evidence_digest": r["evidence_digest"],
        "evidence_ids": [
            o["id"] for o in r["observations"] if not o["stale"] and not o["request"]["test_data"]
        ],
        "action": "modify",
        "owner_reason": "Try a clearer answer; the reported result is observational",
        "next_question": "¿Cómo pedir este producto de prueba?",
    }
    p.update(changes)
    return q.client.post(
        ROOT + "/publications/" + pub["id"] + "/decisions", headers=q.headers, json=p
    )


def test_approved_manual_receipt_zero_unknown_and_export(social):
    q = social
    _, pack, p, pub = published(q)
    assert not pub["independently_verified"] and pub["verification"] == "fixture_owner_report"
    assert (
        q.client.post(
            ROOT + "/packs/" + pack["id"] + "/publications", headers=q.headers, json=p
        ).json()["id"]
        == pub["id"]
    )
    observation = observe(q, pub)
    assert observation.status_code == 200, observation.text
    r = get_report(q, pub)
    assert r["primary"]["value"] == 0 and r["primary"]["availability"] == "measured"
    assert r["confirmed_commerce_orders"]["value"] is None and r["causal_effect"]["value"] is None
    unknown = observe(
        q,
        pub,
        metric="reach",
        availability="unavailable",
        value=None,
        reason="No reach field supplied",
    )
    assert unknown.status_code == 200, unknown.text
    r = get_report(q, pub)
    assert len(r["observations"]) == 2
    saved = decision(q, pub, r)
    assert saved.status_code == 200, saved.text
    blob = q.client.get(ROOT + "/packs/" + pack["id"] + "/export")
    assert blob.status_code == 200, blob.text
    with zipfile.ZipFile(io.BytesIO(blob.content)) as z:
        assert json.loads(z.read("measurement.json"))["value"] == 0
        assert json.loads(z.read("results.json"))["primary"]["value"] == 0
        assert "results.json" in json.loads(z.read("manifest.json"))["files"]
    assert (
        q.client.get(ROOT + "/packs/" + pack["id"]).json()["publication"]["status"]
        == "manual_reported"
    )


def test_no_unapproved_wrong_digest_future_or_fake_verification(social):
    q = social
    _, pack = create(q)
    route = ROOT + "/packs/" + pack["id"] + "/publications"
    assert q.client.post(route, headers=q.headers, json=receipt(pack)).status_code == 409
    assert approval(q, pack).status_code == 200
    for change, code in [
        ({"digest": "0" * 64}, 409),
        (
            {
                "published_at": (datetime.now(UTC) + timedelta(days=1))
                .replace(microsecond=0)
                .isoformat()
            },
            409,
        ),
        ({"independently_verified": True}, 422),
        ({"permalink": "https://instagram.com.evil.invalid/p/no"}, 422),
        ({"timezone": "America/Bogota"}, 422),
    ]:
        assert (
            q.client.post(route, headers=q.headers, json=receipt(pack, **change)).status_code
            == code
        )


def test_duplicate_post_and_tenant_denial(social):
    q = social
    _, pack, p, pub = published(q)
    p["request_id"] = str(uuid4())
    assert (
        q.client.post(
            ROOT + "/packs/" + pack["id"] + "/publications", headers=q.headers, json=p
        ).status_code
        == 409
    )
    assert q.client.get(
        ROOT.replace(BUSINESS, OTHER) + "/publications/" + pub["id"] + "/report"
    ).status_code in (403, 404)
    assert (
        q.client.post(
            ROOT + "/publications/" + pub["id"] + "/observations", json=metric(pub)
        ).status_code
        == 403
    )


def test_metric_corrections_invalidate_decision_without_erasing_observation(social):
    from world_model.restaurant_commerce.social_results import learning_context
    from fastapi import HTTPException

    q = social
    _, pack, p, pub = published(q)
    first = observe(q, pub).json()
    r = get_report(q, pub)
    d = decision(q, pub, r).json()
    corrected = metric(pub, supersedes_id=first["id"], value=3, reason="Corrected a manual tally")
    second = observe(q, pub, corrected)
    assert second.status_code == 200, second.text
    assert observe(q, pub, corrected).json()["id"] == second.json()["id"]
    assert (
        observe(
            q, pub, metric(pub, supersedes_id=first["id"], value=4, reason="Stale correction")
        ).status_code
        == 409
    )
    r = get_report(q, pub)
    assert r["primary"]["value"] == 3 and r["decisions"][0]["stale"]
    assert len([e for e in r["history"] if e["kind"] == "metric"]) == 2
    with q.factory() as session:
        with pytest.raises(HTTPException, match="learning_evidence_changed"):
            learning_context(session, BUSINESS, d["id"])


def test_complete_learning_to_grounded_proposal_and_next_pack(queue):
    from test_social_proposals import setup, run, review
    from world_model.restaurant_commerce import social_jobs as jobs

    q = queue
    p, _ = setup(q)
    _, pack, _, pub = published(q)
    assert observe(q, pub).status_code == 200
    r = get_report(q, pub)
    d = decision(q, pub, r).json()
    p["learning_decision_id"] = d["id"]
    p["question"] = d["request"]["next_question"]
    proposal = run(q, p)
    assert "Consultas de compra: 0" in proposal["output"]["observation"]
    assert "learning:" + d["id"] in proposal["output"]["evidence_ids"]
    assert proposal["input"]["learning"]["id"] == d["id"]
    chosen = review(q, proposal)
    assert chosen.status_code == 200, chosen.text
    produced = q.client.post(
        ROOT + "/proposals/" + proposal["id"] + "/produce",
        headers=q.headers,
        json={"decision_id": chosen.json()["id"]},
    )
    assert produced.status_code == 200, produced.text
    assert jobs.dispatch_one(q.factory, q.client.app)
    next_pack = q.client.get(ROOT + "/packs/" + produced.json()["pack_id"]).json()
    assert next_pack["id"] != pack["id"]
    assert next_pack["document"]["learning_snapshot"]["id"] == d["id"]
    assert "Consultas de compra: 0" in next_pack["document"]["learning_snapshot"]["observation"]
    assert next_pack["document"]["caption"] == chosen.json()["text"]
    assert approval(q, next_pack).status_code == 200
    first = r["observations"][0]
    assert (
        observe(
            q, pub, metric(pub, supersedes_id=first["id"], value=2, reason="Corrected source")
        ).status_code
        == 200
    )
    assert q.client.get(ROOT + "/proposals/" + proposal["id"]).json()["stale"]
    assert q.client.get(ROOT + "/packs/" + next_pack["id"]).json()["stale"]
    assert q.client.get(ROOT + "/packs/" + next_pack["id"] + "/export").status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        {"value": None},
        {"availability": "unavailable", "value": 0},
        {"availability": "not_yet_collected", "value": None, "reason": ""},
        {"value": True},
        {"metric": "search_views", "search_specific": False},
        {"metric": "net_revenue_minor", "currency": None},
        {"metric": "views", "value": -1},
        {"source_kind": "provider_live_verified"},
        {"independently_verified": True},
        {
            "observed_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "window_end": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
    ],
)
def test_unsupported_or_inconsistent_metrics_are_not_success(social, change):
    q = social
    _, _, _, pub = published(q)
    assert observe(q, pub, metric(pub, **change)).status_code in (409, 422)


def test_test_events_and_mismatched_definitions_do_not_produce_a_winner(social):
    q = social
    _, _, _, pub = published(q)
    assert observe(q, pub, test_data=True, value=999).status_code == 200
    r = get_report(q, pub)
    assert r["primary"]["value"] is None
    assert decision(q, pub, r).status_code in (409, 422)
    assert observe(q, pub, definition="Definition one", value=2).status_code == 200
    assert observe(q, pub, definition="Different definition", value=8).status_code == 200
    r = get_report(q, pub)
    assert r["primary"]["value"] is None
    assert r["primary"]["reason"] == "incompatible_definitions_or_windows"
    assert r["suggested_action"] == "collect_evidence"


def test_correction_and_withdrawal_preserve_receipt_and_results(social):
    q = social
    _, pack, p, pub = published(q)
    assert observe(q, pub).status_code == 200
    correction = {
        **p,
        "request_id": str(uuid4()),
        "expected_revision": 1,
        "reason": "Corrected the source description",
        "source_ref": "Corrected fixture source",
    }
    path = ROOT + "/publications/" + pub["id"]
    changed = q.client.put(path, headers=q.headers, json=correction)
    assert changed.status_code == 200, changed.text
    assert changed.json()["revision"] == 2
    assert q.client.put(path, headers=q.headers, json=correction).status_code == 200
    stale = get_report(q, pub)
    assert stale["observations"][0]["stale"] and stale["primary"]["value"] is None
    versions = q.client.get(path + "/history").json()["versions"]
    assert len(versions) == 2 and versions[0]["source_ref"] == p["source_ref"]
    withdrawn = {
        **correction,
        "request_id": str(uuid4()),
        "expected_revision": 2,
        "status": "withdrawn",
        "reason": "This receipt was entered in error",
    }
    assert q.client.put(path, headers=q.headers, json=withdrawn).status_code == 200
    assert observe(q, pub).status_code == 409
    assert q.client.get(ROOT + "/packs/" + pack["id"]).json()["publication"]["post_id"] is None
    assert len(get_report(q, pub)["history"]) == 1


def test_time_precision_and_retrospective_plan_are_honest(social, monkeypatch):
    from world_model.restaurant_commerce import social_production as production

    q = social
    _, pack, p, pub = published(q)
    # A plan before entering a receipt is still retrospective if the real reported
    # publication precedes its recorded time; minute uncertainty never implies preregistration.
    plan = {
        "request_id": str(uuid4()),
        "digest": pack["digest"],
        "question": "Does a clearer explanation help?",
        "variant_difference": "Explain the next step",
        "primary_metric": "qualified_inquiries",
        "review_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "reason": "Single observational question",
    }
    response = q.client.post(
        ROOT + "/packs/" + pack["id"] + "/measurement-plan", headers=q.headers, json=plan
    )
    assert response.status_code == 200, response.text
    r = get_report(q, pub)
    assert r["plan"]["timing"] in {"retrospective", "uncertain_within_timestamp_precision"}
    assert r["comparison_type"] == "observational_not_randomized" and not r["review_due"]
    assert r["suggested_action"] == "inconclusive"
    # The existing clock also guards publication and observation futures.
    monkeypatch.setattr(production, "utcnow", lambda: datetime.now(UTC) - timedelta(days=1))
    assert observe(q, pub).status_code == 409


def test_report_keeps_missing_effort_cost_and_reconciled_orders_unknown(social):
    q = social
    _, _, _, pub = published(q)
    r = get_report(q, pub)
    assert (
        r["production"]["provider_microusd"] is None and r["production"]["total_microusd"] is None
    )
    assert r["production"]["reported_activity_effort_seconds"]["owner"] is None
    p = {
        "request_id": str(uuid4()),
        "role": "owner",
        "seconds": 0,
        "activity": "review",
        "source_ref": "Owner timed the activity",
        "reason": "No time spent in this activity",
    }
    path = ROOT + "/publications/" + pub["id"] + "/effort"
    assert q.client.post(path, headers=q.headers, json=p).status_code == 200
    assert q.client.post(path, headers=q.headers, json=p).status_code == 200
    r = get_report(q, pub)
    assert r["production"]["reported_activity_effort_seconds"]["owner"] == 0
    assert r["production"]["recorded_job_effort_seconds"]["owner"] is None
    assert observe(q, pub, metric="orders", value=4).status_code == 200
    assert get_report(q, pub)["confirmed_commerce_orders"]["value"] is None


def test_duplicate_observations_and_decisions_serialize(social):
    from concurrent.futures import ThreadPoolExecutor

    q = social
    _, _, _, pub = published(q)
    payload = metric(pub)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: observe(q, pub, payload), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(get_report(q, pub)["observations"]) == 1


def test_negative_reported_net_revenue_is_not_a_negative_count(social):
    q = social
    _, _, _, pub = published(q)
    response = observe(
        q,
        pub,
        metric="net_revenue_minor",
        value=-500,
        currency="COP",
        definition="Net of returns in this stated period",
    )
    assert response.status_code == 200, response.text
    r = get_report(q, pub)
    assert r["observations"][0]["request"]["value"] == -500
    assert r["confirmed_commerce_orders"]["value"] is None


def test_withdrawn_test_and_search_counts_do_not_become_qualified_purchases(social):
    q = social
    _, _, _, pub = published(q)
    assert (
        observe(
            q,
            pub,
            metric="search_views",
            value=12,
            search_specific=True,
            definition="Search-specific views explicitly exposed in a manually supplied report",
        ).status_code
        == 200
    )
    r = get_report(q, pub)
    assert r["primary"]["value"] is None and r["primary"]["metric"] == "qualified_inquiries"
    assert r["causal_effect"]["value"] is None


def test_source_revocation_blocks_reuse_but_does_not_erase_historical_measurement(social):
    q = social
    b, pack, p, pub = published(q)
    assert q.client.delete(ROOT + "/assets/" + b["asset_id"], headers=q.headers).status_code == 200
    assert observe(q, pub).status_code == 200
    r = get_report(q, pub)
    assert r["primary"]["value"] == 0
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/image").status_code == 409
    assert q.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409


def test_same_receipt_click_is_idempotent_and_native_post_ids_deduplicate(social):
    from concurrent.futures import ThreadPoolExecutor

    q = social
    _, pack = create(q)
    assert approval(q, pack).status_code == 200
    payload = receipt(pack, provider_post_id="fixture-native-identifier")
    path = ROOT + "/packs/" + pack["id"] + "/publications"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: q.client.post(path, headers=q.headers, json=payload), range(2))
        )
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json()["id"] == results[1].json()["id"]
    another = {
        **payload,
        "request_id": str(uuid4()),
        "permalink": "https://www.instagram.com/p/another-fixture-alias/",
    }
    assert q.client.post(path, headers=q.headers, json=another).status_code == 409
