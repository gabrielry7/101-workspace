"""Guided choices preserve facts, scope, historical approval and explicit unknowns."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import copy

import pytest
from sqlalchemy import select
from test_social_context import context_payload, linked_brief, save_context
from test_social_production import BUSINESS, OTHER, ROOT, approval, env, factory, social
from world_model.restaurant_commerce.models import StaffMembership


def payload():
    return {
        "expected_revision": 0,
        "confirmed": True,
        "answers": {
            "goal": {"choice": "orders", "detail": ""},
            "channels": [
                {"choice": "whatsapp", "detail": "Número pendiente"},
                {"choice": "other", "detail": "Solicitudes en nuestra feria"},
            ],
            "feature": {"choice": "product", "detail": "Producto sintético de prueba"},
            "materials": ["photos", "other"],
            "material_detail": "Catálogo de prueba",
            "conditions": [{"choice": "advance", "detail": ""}],
            "lead_time": {"choice": "depends", "detail": "Según el producto"},
            "locale": "es-CO",
        },
    }


def test_roundtrip_custom_unknown_and_fact_preservation(social):
    c = save_context(social, context_payload())
    pack = social.client.post(
        ROOT + "/packs", json=linked_brief(social, c), headers=social.headers
    ).json()
    assert approval(social, pack).status_code == 200
    p = payload()
    p["expected_revision"] = 1
    r = social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers)
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["facts"] == c["facts"]
    assert saved["brief"]["margin"] is None
    assert saved["onboarding"] == p["answers"]
    assert "Solicitudes en nuestra feria" in saved["brief"]["buying_destination"]
    assert "depende del producto" in saved["brief"]["constraints"]
    assert social.client.get(ROOT + "/packs/" + pack["id"]).json()["stale"]
    assert social.client.get(ROOT + "/packs/" + pack["id"] + "/export").status_code == 409
    assert (
        social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers).status_code
        == 409
    )
    p["expected_revision"] = 2
    p["answers"].update(
        goal={"choice": "unknown"},
        channels=[{"choice": "later"}],
        feature={"choice": "help"},
        materials=["none"],
        material_detail="",
        conditions=[],
        lead_time=None,
        locale=None,
    )
    r = social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers)
    assert r.status_code == 200, r.text
    current = r.json()
    for key in ["objective", "offering", "buying_destination", "locale"]:
        assert current["brief"][key] is None
    assert current["facts"] == c["facts"]
    history = social.client.get(ROOT + "/context/history").json()["versions"]
    assert len(history) == 3
    assert history[1]["onboarding"]["channels"][1]["detail"] == "Solicitudes en nuestra feria"
    # The ordinary fact editor must retain guided choices when the brief is unchanged.
    manual = context_payload()
    manual.update(expected_revision=3, brief=current["brief"])
    result = save_context(social, manual)
    assert result["onboarding"] == current["onboarding"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(confirmed=False),
        lambda p: p["answers"]["goal"].update(choice="invented"),
        lambda p: p["answers"].update(channels=[{"choice": "other", "detail": "   "}]),
        lambda p: p["answers"].update(channels=[{"choice": "later"}, {"choice": "store"}]),
        lambda p: p["answers"].update(materials=["none", "photos"]),
        lambda p: p["answers"].update(materials=["photos", "photos"]),
        lambda p: p["answers"].update(conditions=[]),  # orphan lead time
        lambda p: p["answers"].update(feature={"choice": "product", "detail": ""}),
        lambda p: p.update(location_id="not-a-uuid"),
        lambda p: p["answers"].update(search_volume=1000),
    ],
)
def test_invalid_or_unconfirmed_answers_do_not_write(social, mutate):
    p = payload()
    mutate(p)
    assert (
        social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers).status_code
        == 422
    )
    assert social.client.get(ROOT + "/context").json()["revision"] == 0


def test_onboarding_permissions_and_no_automatic_facts(social):
    p = payload()
    assert social.client.put(ROOT + "/context/onboarding", json=p).status_code == 403
    foreign = ROOT.replace(BUSINESS, OTHER)
    assert social.client.put(
        foreign + "/context/onboarding", json=p, headers=social.headers
    ).status_code in (403, 404)
    response = social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers)
    assert response.status_code == 200, response.text
    assert response.json()["facts"] == []
    with social.factory() as session:
        member = session.scalar(
            select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
        )
        member.role = "viewer"
        session.commit()
    p["expected_revision"] = 1
    assert (
        social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers).status_code
        == 403
    )


def test_existing_expired_facts_stay_expired_and_branch_scope_is_validated(social, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from world_model.restaurant_commerce import social_context

    c = save_context(social, context_payload())
    clock = datetime.now(UTC) + timedelta(days=2)
    monkeypatch.setattr(social_context, "utcnow", lambda: clock.replace(tzinfo=None))
    p = payload()
    p["expected_revision"] = 1
    r = social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers)
    assert r.status_code == 200, r.text
    expired = r.json()["facts"][0]
    assert expired["current_status"] == "expired"
    assert expired["verified_at"] == c["facts"][0]["verified_at"]
    assert expired["revision"] == c["facts"][0]["revision"]
    p["location_id"] = str(uuid4())
    assert (
        social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers).status_code
        == 503
    )
    social.client.app.state.social_location_belongs_to_business = lambda business, location: False
    assert (
        social.client.put(ROOT + "/context/onboarding", json=p, headers=social.headers).status_code
        == 404
    )
