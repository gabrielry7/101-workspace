"""Marketing assertions retain scope/history; new exports require current versions."""

# ruff: noqa: F401,F811 -- imported pytest fixtures

import copy
import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
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
from world_model.restaurant_commerce.social_context import Context, ContextVersion, FactDependency
from world_model.restaurant_commerce.social_migrations import upgrade_social
from world_model.restaurant_commerce.social_production import Revision
from world_model.restaurant_commerce.social_reviews import ever_approved, effective_approval


def context_payload():
    now = datetime.now(UTC)
    return {
        "expected_revision": 0,
        "confirmed": True,
        "brief": {
            "offering": "Producto de prueba",
            "objective": "Explicar el precio",
            "buying_destination": "Consultar en el local",
            "constraints": "Sujeto a confirmación de disponibilidad",
            "locale": "es-CO",
            "capacity": None,
            "margin": None,
        },
        "facts": [
            {
                "id": "price",
                "label": "Precio",
                "kind": "money",
                "value": "12000",
                "currency": "COP",
                "unit": None,
                "source": "Operador de prueba",
                "effective_at": (now - timedelta(days=1)).isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
                "status": "confirmed",
            },
            {
                "id": "description",
                "label": "Descripción",
                "kind": "text",
                "value": "Producto de prueba.",
                "source": "Operador de prueba",
                "effective_at": (now - timedelta(days=1)).isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
                "status": "confirmed",
            },
        ],
    }


def save_context(env, value):
    result = env.client.put(ROOT + "/context", json=value, headers=env.headers)
    assert result.status_code == 200, result.text
    return result.json()


def linked_brief(env, context, fact_id="price"):
    fact = next(f for f in context["facts"] if f["id"] == fact_id)
    return brief(
        photo(env).json()["id"],
        objective=context["brief"]["objective"],
        context_version_id=context["id"],
        facts=[{k: fact[k] for k in ("id", "text", "source", "valid_until")}],
        caption_fact_ids=[fact_id],
        fact_refs=[
            {
                "context_version_id": context["id"],
                "fact_id": fact_id,
                "fact_revision": fact["revision"],
            }
        ],
    )


def test_changed_price_stale_recovery_preserves_history_and_unrelated_fact(social):
    payload = context_payload()
    context = save_context(social, payload)
    assert context["brief"]["capacity"] is None and context["brief"]["margin"] is None
    value = linked_brief(social, context)
    pack = social.client.post(ROOT + "/packs", json=value, headers=social.headers).json()
    assert approval(social, pack).status_code == 200
    old_image = social.client.get(ROOT + "/packs/" + pack["id"] + "/image").content
    with social.factory() as s:
        frozen = s.get(Revision, pack["id"] + ":1").document
        assert s.scalar(select(FactDependency)).fact_revision == 1
    payload["expected_revision"] = 1
    payload["facts"][0]["value"] = "15000"
    latest = save_context(social, payload)
    assert latest["facts"][0]["revision"] == 2
    assert latest["facts"][1]["revision"] == 1
    route = ROOT + "/packs/" + pack["id"]
    stale = social.client.get(route).json()
    assert stale["stale"] and not stale["approved"] and stale["historically_approved"]
    assert stale["document"]["caption"] == "Precio: 12000 COP."
    assert social.client.get(route + "/image").content == old_image
    assert social.client.get(route + "/export").status_code == 409
    assert approval(social, pack).status_code == 409
    assert (
        social.client.put(
            route, json={**value, "expected_revision": 1}, headers=social.headers
        ).status_code
        == 409
    )
    fact = latest["facts"][0]
    value.update(
        expected_revision=1,
        context_version_id=latest["id"],
        facts=[{k: fact[k] for k in ("id", "text", "source", "valid_until")}],
        fact_refs=[{"context_version_id": latest["id"], "fact_id": "price", "fact_revision": 2}],
    )
    corrected = social.client.put(route, json=value, headers=social.headers)
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["document"]["caption"] == "Precio: 15000 COP."
    assert not corrected.json()["approved"]
    assert approval(social, corrected.json()).status_code == 200
    assert social.client.get(route + "/export").status_code == 200
    with social.factory() as s:
        assert s.get(Revision, pack["id"] + ":1").document == frozen
        assert ever_approved(s, pack["id"] + ":1")
    history = social.client.get(ROOT + "/context/history").json()["versions"]
    assert history[0]["facts"][0]["value"] == "12000"


def test_context_validation_scope_and_optimistic_edit(social):
    payload = context_payload()
    context = save_context(social, payload)
    assert (
        social.client.put(ROOT + "/context", json=payload, headers=social.headers).status_code
        == 409
    )
    assert social.client.put(ROOT + "/context", json=payload).status_code == 403
    assert social.client.get(ROOT.replace(BUSINESS, OTHER) + "/context").status_code == 403
    assert social.client.get(ROOT + "/context?location_id=" + str(uuid4())).status_code == 503
    for changes in (
        {"value": "NaN"},
        {"currency": None},
        {"value": "-2"},
        {"value": "12.345"},
        {"value": "[price]"},
        {"effective_at": "2099-01-01T00:00:00Z"},
    ):
        invalid = copy.deepcopy(payload)
        invalid["expected_revision"] = 1
        invalid["facts"][0].update(changes)
        assert (
            social.client.put(ROOT + "/context", json=invalid, headers=social.headers).status_code
            == 422
        )
    forged = linked_brief(social, context)
    forged["facts"][0]["text"] = "Precio: 1 COP."
    assert (
        social.client.post(ROOT + "/packs", json=forged, headers=social.headers).status_code == 409
    )
    with social.factory.begin() as s:
        for member in s.scalars(
            select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
        ):
            member.role = "viewer"
    assert social.client.get(ROOT + "/context").status_code == 200
    assert (
        social.client.post(ROOT + "/packs", json=forged, headers=social.headers).status_code == 403
    )
    assert (
        social.client.put(
            ROOT + "/context", json={**payload, "expected_revision": 1}, headers=social.headers
        ).status_code
        == 403
    )


def test_expiry_withdrawal_and_legacy_backfill(social):
    payload = context_payload()
    context = save_context(social, payload)
    value = linked_brief(social, context)
    pack = social.client.post(ROOT + "/packs", json=value, headers=social.headers).json()
    payload["expected_revision"] = 1
    payload["facts"][0]["status"] = "withdrawn"
    save_context(social, payload)
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    legacy = social.client.post(
        ROOT + "/packs", json=brief(photo(social).json()["id"]), headers=social.headers
    ).json()
    assert approval(social, legacy).status_code == 200
    with social.factory() as s:
        frozen = s.get(Revision, legacy["id"] + ":1").document
        engine = s.get_bind()
    upgrade_social(engine)
    upgrade_social(engine)
    with social.factory() as s:
        assert s.get(Revision, legacy["id"] + ":1").document == frozen
        version = s.get(ContextVersion, "legacy:" + legacy["id"] + ":1")
        assert json.loads(version.document)["basis"] == "legacy_pack_assertion"
        assert ever_approved(s, legacy["id"] + ":1")
    assert social.client.get(ROOT + "/packs/" + legacy["id"] + "/export").status_code == 200


def test_clock_expiry_and_removed_id_cannot_resurrect_old_approval(social, monkeypatch):
    payload = context_payload()
    context = save_context(social, payload)
    value = linked_brief(social, context)
    pack = social.client.post(ROOT + "/packs", json=value, headers=social.headers).json()
    assert approval(social, pack).status_code == 200
    from world_model.restaurant_commerce import social_context, social_production

    later = datetime.now(UTC) + timedelta(days=1, minutes=1)
    with monkeypatch.context() as patch:
        patch.setattr(social_context, "utcnow", lambda: later)
        patch.setattr(social_production, "utcnow", lambda: later)
        assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
        assert social.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
        assert social.client.get(ROOT + "/packs/" + pack["id"] + "/image").status_code == 200
    payload["expected_revision"] = 1
    removed = payload["facts"].pop(0)
    save_context(social, payload)
    payload["expected_revision"] = 2
    payload["facts"].insert(0, removed)
    restored = save_context(social, payload)
    assert restored["facts"][0]["revision"] == 3
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]


def test_v1_database_additive_upgrade_preserves_digest_approval_and_original(social):
    from world_model.restaurant_commerce.social_migrations import schema_ready
    from world_model.restaurant_commerce.social_production import Asset

    value = brief(photo(social).json()["id"])
    pack = social.client.post(ROOT + "/packs", json=value, headers=social.headers).json()
    assert approval(social, pack).status_code == 200
    with social.factory() as s:
        engine = s.get_bind()
        original = s.get(Asset, value["asset_id"]).original
        frozen = s.get(Revision, pack["id"] + ":1").document
    for model in (FactDependency, ContextVersion, Context):
        model.__table__.drop(engine)
    assert not schema_ready(engine)
    assert social.client.get(ROOT).status_code == 503
    upgrade_social(engine)
    upgrade_social(engine)
    assert schema_ready(engine)
    assert social.client.get(ROOT + "/context").json()["revision"] == 0
    with social.factory() as s:
        assert s.get(Revision, pack["id"] + ":1").document == frozen
        assert s.get(Asset, value["asset_id"]).original == original
        assert effective_approval(s,s.get(Revision,pack["id"]+":1"),json.loads(frozen)).digest == pack["digest"]
        assert s.get(ContextVersion, "legacy:" + pack["id"] + ":1") is not None
    assert social.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 200
