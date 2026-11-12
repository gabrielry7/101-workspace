"""Curated references/questions are scoped context, not facts or measured demand."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import copy
import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
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
from world_model.restaurant_commerce.models import StaffMembership
from world_model.restaurant_commerce.social_creative import CreativeBoard, CreativeVersion
from world_model.restaurant_commerce.social_migrations import schema_ready, upgrade_social
from world_model.restaurant_commerce.social_production import Revision


def board_payload():
    now = datetime.now(UTC)
    common = {
        "source": "Controlled test observation",
        "observed_at": (now - timedelta(days=1)).isoformat(),
        "valid_until": (now + timedelta(days=5)).isoformat(),
        "status": "active",
    }
    return {
        "expected_revision": 0,
        "visual_direction": "Fotografía natural",
        "voice_rules": "Hablar claro, sin superlativos.",
        "references": [
            {
                "id": "writing",
                "title": "Texto directo",
                "kind": "writing",
                "judgment": "positive",
                "purpose": "own_brand",
                "reason": "Explica el siguiente paso sin exagerar.",
                "permission": "Texto sintético escrito por el autor de la prueba",
                "excerpt": "Pregunta por las opciones disponibles.",
                **common,
            }
        ],
        "questions": [
            {
                "id": "order",
                "text": "¿Cuánto cuesta?",
                "source_kind": "customer_question",
                "intent": "how_to_buy",
                "answer_fact_ids": ["price"],
                "next_action": "Consultar en el local",
                **common,
            }
        ],
        "change_kind": "reference_review",
        "change_reason": "Initial controlled examples",
        "confirmed": True,
    }


def save_board(e, payload):
    response = e.client.put(ROOT + "/creative", json=payload, headers=e.headers)
    assert response.status_code == 200, response.text
    return response.json()


def setup_pack(e):
    facts = context_payload()
    context = save_context(e, facts)
    payload = board_payload()
    board = save_board(e, payload)
    value = linked_brief(e, context)
    value.update(
        creative_version_id=board["id"],
        reference_ids=["writing"],
        question_id="order",
        question="¿Cuánto cuesta?",
        question_source="customer_question",
        question_evidence=payload["questions"][0]["source"],
    )
    response = e.client.post(ROOT + "/packs", json=value, headers=e.headers)
    assert response.status_code == 200, response.text
    return facts, context, payload, board, value, response.json()


def test_reuse_snapshot_price_correction_never_updates_brand(social):
    facts, context, payload, board, value, pack = setup_pack(social)
    snap = pack["document"]["creative_snapshot"]
    assert snap["voice_rules"] == payload["voice_rules"]
    assert snap["references"][0]["judgment"] == "positive"
    assert snap["question"]["source_kind"] == "customer_question"
    assert snap["question"]["answer_fact_ids"] == ["price"]
    assert snap["search_volume"] is None and snap["demand_reason"] == "not_measured"
    assert approval(social, pack).status_code == 200
    frozen = pack["document"]
    facts["expected_revision"] = 1
    facts["facts"][0]["value"] = "16000"
    latest = save_context(social, facts)
    assert social.client.get(ROOT + "/creative").json() == {**board}
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    f = latest["facts"][0]
    value.update(
        expected_revision=1,
        revision_reason="factual_correction",
        context_version_id=latest["id"],
        facts=[{k: f[k] for k in ("id", "text", "source", "valid_until")}],
        fact_refs=[{"context_version_id": latest["id"], "fact_id": "price", "fact_revision": 2}],
    )
    revised = social.client.put(ROOT + "/packs/" + pack["id"], json=value, headers=social.headers)
    assert revised.status_code == 200, revised.text
    assert revised.json()["document"]["creative_snapshot"] == snap
    assert social.client.get(ROOT + "/creative").json() == board
    # One-off strategy/style editing stays in the pack, not persistent brand memory.
    value.update(
        expected_revision=2,
        revision_reason="strategy",
        brand_direction="Encuadre distinto para este post",
    )
    assert (
        social.client.put(
            ROOT + "/packs/" + pack["id"], json=value, headers=social.headers
        ).status_code
        == 200
    )
    assert social.client.get(ROOT + "/creative").json() == board
    with social.factory() as s:
        assert json.loads(s.get(Revision, pack["id"] + ":1").document) == frozen
    assert len(social.client.get(ROOT + "/creative/history").json()["versions"]) == 1


@pytest.mark.parametrize("change", ["voice", "reference", "question", "withdraw", "expire"])
def test_changed_selected_context_invalidates_approval_but_retains_metadata(
    social, change, monkeypatch
):
    facts, context, payload, board, value, pack = setup_pack(social)
    assert approval(social, pack).status_code == 200
    if change == "expire":
        from world_model.restaurant_commerce import social_production

        monkeypatch.setattr(
            social_production, "utcnow", lambda: datetime.now(UTC) + timedelta(days=6)
        )
    else:
        payload["expected_revision"] = 1
        if change == "voice":
            payload["voice_rules"] = "Más breve."
        if change == "reference":
            payload["references"][0]["judgment"] = "negative"
        if change == "question":
            payload["questions"][0]["source_kind"] = "hypothesis"
        if change == "withdraw":
            payload["references"][0]["status"] = "withdrawn"
        save_board(social, payload)
    route = ROOT + "/packs/" + pack["id"]
    assert social.client.get(route).json()["stale"]
    assert social.client.get(route + "/export").status_code == 409
    assert approval(social, pack).status_code == 409


def test_reference_only_media_and_scope_permissions(social):
    facts, context, payload, board, value, pack = setup_pack(social)
    reference = photo(social, permitted_use="reference_only").json()["id"]
    payload["expected_revision"] = 1
    payload["references"][0]["asset_id"] = reference
    latest = save_board(social, payload)
    value.update(request_id=str(uuid4()), creative_version_id=latest["id"], asset_id=reference)
    assert (
        social.client.post(ROOT + "/packs", json=value, headers=social.headers).status_code == 409
    )
    value["asset_id"] = photo(social).json()["id"]
    rendered = social.client.post(ROOT + "/packs", json=value, headers=social.headers)
    assert rendered.status_code == 200, rendered.text
    assert (
        social.client.delete(ROOT + "/assets/" + reference, headers=social.headers).status_code
        == 200
    )
    assert social.client.get(ROOT + "/packs/" + rendered.json()["id"]).json()["stale"]
    assert social.client.get(ROOT.replace(BUSINESS, OTHER) + "/creative").status_code == 403
    assert social.client.put(ROOT + "/creative", json=payload).status_code == 403
    assert social.client.get(ROOT + "/creative?location_id=" + str(uuid4())).status_code == 503
    with social.factory.begin() as s:
        for member in s.scalars(
            select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
        ):
            member.role = "viewer"
    assert social.client.get(ROOT + "/creative").status_code == 200
    assert (
        social.client.put(ROOT + "/creative", json=payload, headers=social.headers).status_code
        == 403
    )


def test_hypotheses_cannot_acquire_metrics_or_unresolved_answers(social):
    context = save_context(social, context_payload())
    payload = board_payload()
    payload["questions"][0]["source_kind"] = "hypothesis"
    for extra in ("search_volume", "rank", "views"):
        wrong = copy.deepcopy(payload)
        wrong["questions"][0][extra] = 100
        assert (
            social.client.put(ROOT + "/creative", json=wrong, headers=social.headers).status_code
            == 422
        )
    wrong = copy.deepcopy(payload)
    wrong["questions"][0]["answer_fact_ids"] = ["not_in_business"]
    assert (
        social.client.put(ROOT + "/creative", json=wrong, headers=social.headers).status_code == 422
    )
    wrong = copy.deepcopy(payload)
    wrong["references"][0]["url"] = "javascript:alert(1)"
    assert (
        social.client.put(ROOT + "/creative", json=wrong, headers=social.headers).status_code == 422
    )
    board = save_board(social, payload)
    assert board["search_volume"] is None
    assert (
        social.client.put(ROOT + "/creative", json=payload, headers=social.headers).status_code
        == 409
    )
    value = linked_brief(social, context)
    value.update(
        creative_version_id=board["id"],
        question_id="order",
        question="¿Cuánto cuesta?",
        question_source="customer_question",
        question_evidence=payload["questions"][0]["source"],
    )
    assert (
        social.client.post(ROOT + "/packs", json=value, headers=social.headers).status_code == 409
    )
    value["question_source"] = "hypothesis"
    value["fact_refs"] = []
    assert (
        social.client.post(ROOT + "/packs", json=value, headers=social.headers).status_code == 409
    )


def test_unselected_changes_and_retired_reference_never_revive_old_approval(social):
    facts, context, payload, board, value, pack = setup_pack(social)
    assert approval(social, pack).status_code == 200
    payload["expected_revision"] = 1
    payload["references"].append(
        {
            **payload["references"][0],
            "id": "another",
            "judgment": "borderline",
            "purpose": "remote_comparable",
        }
    )
    save_board(social, payload)
    assert not social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    payload["expected_revision"] = 2
    old = payload["references"].pop(0)
    save_board(social, payload)
    payload["expected_revision"] = 3
    payload["references"].insert(0, old)
    board = save_board(social, payload)
    assert board["references"][0]["revision"] == 3
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]


def test_additive_upgrade_preserves_existing_facts_and_approvals(social):
    context = save_context(social, context_payload())
    value = linked_brief(social, context)
    pack = social.client.post(ROOT + "/packs", json=value, headers=social.headers).json()
    assert approval(social, pack).status_code == 200
    with social.factory() as s:
        engine = s.get_bind()
    for model in (CreativeVersion, CreativeBoard):
        model.__table__.drop(engine)
    assert not schema_ready(engine)
    assert social.client.get(ROOT + "/creative").status_code == 503
    upgrade_social(engine)
    upgrade_social(engine)
    assert social.client.get(ROOT + "/creative").json()["revision"] == 0
    assert social.client.get(ROOT + "/context").json() == context
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["approved"]


def test_scoped_reference_and_question_versions_cannot_leak(social):
    location = str(uuid4())
    social.client.app.state.social_location_belongs_to_business = lambda business, loc: (
        business == BUSINESS and loc == location
    )
    value = board_payload()
    value["location_id"] = location
    value["questions"] = []
    response = social.client.put(ROOT + "/creative", json=value, headers=social.headers)
    assert response.status_code == 200, response.text
    board = response.json()
    assert social.client.get(ROOT + "/creative").json()["references"] == []
    pack = brief(
        photo(social).json()["id"], creative_version_id=board["id"], reference_ids=["writing"]
    )
    assert social.client.post(ROOT + "/packs", json=pack, headers=social.headers).status_code == 404
    pack["location_id"] = location
    assert social.client.post(ROOT + "/packs", json=pack, headers=social.headers).status_code == 200
    assert social.client.get(ROOT + "/creative?location_id=" + str(uuid4())).status_code == 404


def test_restoring_voice_rules_does_not_revive_old_approval(social):
    facts, context, payload, board, value, pack = setup_pack(social)
    assert approval(social, pack).status_code == 200
    initial = payload["voice_rules"]
    payload["expected_revision"] = 1
    payload["voice_rules"] = "Otra dirección."
    save_board(social, payload)
    payload["expected_revision"] = 2
    payload["voice_rules"] = initial
    latest = save_board(social, payload)
    assert latest["style_revision"] == 3
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
