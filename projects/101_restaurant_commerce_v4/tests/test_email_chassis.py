"""Chassis edits retain campaign evidence and exact approval; no provider calls."""

# ruff: noqa: F401,F811
import copy

import pytest
from test_campaigns import ROOT, create, draft, env, factory
from world_model.restaurant_commerce import campaign_react_email as re

PROFILE = {
    "schema_version": "1",
    "coat": "neutral",
    "geometry": {"maxWidth": 560},
    "bones": {
        "shape": "soft",
        "surfaces": {"content": {"fill": "#ffffff", "padding": 24}, "controls": {"radius": 12}},
    },
    "typography": {
        "heading": {"fontSize": 24},
        "body": {"fontFamily": "Georgia", "color": "#123456"},
    },
}


def test_chassis_change_preserves_material_content_and_requires_new_approval(env):
    original = create(env, draft(env, email_design={"template_id": "protocol"}))
    path = ROOT + "/" + original["id"]
    assert (
        env.client.post(
            path + "/approve", json={"digest": original["digest"]}, headers=env.headers
        ).status_code
        == 200
    )
    result = env.client.post(
        path + "/design",
        json={
            "digest": original["digest"],
            "email_design": {"template_id": "protocol", "chassis": PROFILE},
        },
        headers=env.headers,
    )
    assert result.status_code == 200, result.text
    current = result.json()
    assert current["document"]["content"] == original["document"]["content"]
    for key in ("recipients", "brand", "promotion", "scheduled_at", "budget_microusd"):
        assert current["document"].get(key) == original["document"].get(key)
    assert current["digest"] != original["digest"] and not current["approved"]
    assert "#123456" in current["email"]["html"] and "font-size:24px" in current["email"]["html"]
    assert (
        env.client.post(
            path + "/approve", json={"digest": original["digest"]}, headers=env.headers
        ).status_code
        == 409
    )
    assert (
        env.client.post(
            path + "/approve", json={"digest": current["digest"]}, headers=env.headers
        ).status_code
        == 200
    )
    for family in ("classic", "barebone", "matte", "arcane", "studio"):
        comparison = env.client.get(path + "/email-content", params={"template_id": family})
        assert comparison.status_code == 200, comparison.text
        assert "#123456" in comparison.json()["html"]
        assert comparison.json()["campaign_digest"] == current["digest"]
    assert env.client.get(path).json()["approved"]


@pytest.mark.parametrize(
    "bad",
    [
        {"schema_version": "1", "css": "display:none"},
        {"schema_version": "1", "bones": {"surfaces": {"footer": {"opacity": 0}}}},
        {
            "schema_version": "1",
            "bones": {"surfaces": {"controls": {"fill": "url(javascript:alert(1))"}}},
        },
        {"schema_version": "1", "typography": {"heading": {"fontSize": 1000}}},
        {"schema_version": "1", "geometry": {"maxWidth": "560"}},
        {"schema_version": "1", "ordering_url": "https://evil.example.test"},
        {"schema_version": "1", "bones": {"surfaces": {"footer": {"padding": True}}}},
    ],
)
def test_untrusted_or_unsupported_chassis_cannot_save(env, bad):
    r = env.client.post(
        ROOT,
        json=draft(env, email_design={"template_id": "matte", "chassis": bad}),
        headers=env.headers,
    )
    assert r.status_code == 422, r.text


def test_approved_v1_artifact_still_renders_byte_identically(env):
    current = create(env, draft(env, email_design={"template_id": "arcane"}))
    old = copy.deepcopy(current["document"])
    old["email_design"]["template_version"] = "1"
    old["renderer"] = (
        "react-email-v1:1e159c4a6701fcb636875fe4a6256064ed0a346f395f7d2ea1bed9495f9ade51"
    )
    assert re.compatible(old)
    a = re.render(old, old["recipients"][0], "#order", "#unsubscribe")
    b = re.render(old, old["recipients"][0], "#order", "#unsubscribe")
    assert a == b and "#unsubscribe" in a["text"]
    assert "data-101-bone-role=" not in a["html"]
    assert re.runtime_manifest(1)["renderer_sha256"] == old["renderer"].split(":")[1]


def test_card_stage_and_padding_owner_are_real_catalogued_parts(env):
    profile = copy.deepcopy(PROFILE)
    profile["bones"]["surfaces"].update(
        card={"radius": 20, "fill": "#fffdfa"}, stage={"fill": "#fafafa"}
    )
    result = create(env, draft(env, email_design={"template_id": "matte", "chassis": profile}))
    assert (
        result["document"]["email_design"]["chassis"]["bones"]["surfaces"]["card"]["radius"] == 20
    )
    assert 'data-101-bone-role="card"' in result["email"]["html"]
    assert "border-radius:20px" in result["email"]["html"]
    catalogue = env.client.get(ROOT + "/email-templates").json()["chassis"]
    assert catalogue["shared_bones"] == "101-bones-v1"
    parts = catalogue["recipes"]["matte"]["parts"]
    assert next(p for p in parts if p["role"] == "content-inset")["selector"].endswith(
        "> tbody > tr > td"
    )
