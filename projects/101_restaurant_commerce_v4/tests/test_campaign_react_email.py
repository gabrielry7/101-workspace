"""Actual React Email bundle -> Python -> saved revision -> simulated delivery."""

# ruff: noqa: F401,F811
import copy
import json
import subprocess
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from test_campaigns import BUSINESS, OTHER, ROOT, approved, create, draft, env, factory
from world_model.restaurant_commerce import campaign_react_email as re
from world_model.restaurant_commerce import campaigns as c
from world_model.restaurant_commerce.campaign_demo import CLOCK
from world_model.restaurant_commerce.campaign_models import CampaignJob, CampaignRevision


def styled(env, template="matte", **changes):
    return draft(env, email_design={"template_id": template, **changes})


def test_six_real_renderers_preserve_copy_personalization_and_links(env):
    for template in ["classic", "barebone", "matte", "protocol", "arcane", "studio"]:
        value = styled(
            env,
            template,
            image_url="https://merchant.example.test/product.png",
            image_alt="El producto real",
        )
        value["content"].update(
            title="Una nota específica",
            body="¿Qué tal? <script>alert(1)</script>\n\nSin afirmaciones inventadas.",
        )
        r = env.client.post(ROOT, json=value, headers=env.headers)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["document"]["email_design"]["template_id"] == template
        assert p["document"]["renderer"].startswith("react-email-v2:")
        email = p["email"]
        assert "<script>" not in email["html"] and "&lt;script&gt;" in email["html"]
        assert (
            "Sin afirmaciones inventadas." in email["text"]
            and "Una nota específica" in email["text"]
        )
        assert (
            "Dejar de recibir promociones" in email["html"]
            and "#preview-unsubscribe" in email["text"]
        )
        assert "https://merchant.example.test/product.png" in email["html"]
        assert "SKIN15" not in email["text"] and "Black Friday" not in email["text"]
        assert "<table" in email["html"]


def test_alternate_preview_is_read_only_and_saved_template_requires_approval(env):
    p = create(env, styled(env))
    assert (
        env.client.post(
            ROOT + "/" + p["id"] + "/approve", json={"digest": p["digest"]}, headers=env.headers
        ).status_code
        == 200
    )
    with env.factory() as s:
        before = s.scalar(select(func.count()).select_from(CampaignRevision))
    originals = []
    for template in ["barebone", "protocol", "arcane", "studio"]:
        r = env.client.get(
            ROOT + "/" + p["id"] + "/email-content", params={"template_id": template}
        )
        assert r.status_code == 200, r.text
        assert r.json()["saved"] is False and r.json()["campaign_digest"] == p["digest"]
        originals.append(r.json()["html"])
    assert len(set(originals)) == 4
    current = env.client.get(ROOT + "/" + p["id"]).json()
    assert current["digest"] == p["digest"] and current["approved"]
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CampaignRevision)) == before
    changed = styled(env, "arcane")
    r = env.client.post(
        ROOT + "/" + p["id"] + "/design",
        json={"digest": p["digest"], "email_design": changed["email_design"]},
        headers=env.headers,
    )
    assert r.status_code == 200, r.text
    new = r.json()
    assert all(
        new["document"][k] == p["document"][k] for k in c.Draft.model_fields if k != "email_design"
    )
    assert (
        env.client.post(
            ROOT + "/" + p["id"] + "/design",
            json={"digest": p["digest"], "email_design": changed["email_design"]},
            headers=env.headers,
        ).status_code
        == 409
    )
    assert new["digest"] != p["digest"] and not new["approved"]
    assert (
        env.client.post(
            ROOT + "/" + p["id"] + "/approve", json={"digest": p["digest"]}, headers=env.headers
        ).status_code
        == 409
    )
    assert (
        env.client.post(
            ROOT + "/" + p["id"] + "/approve", json={"digest": new["digest"]}, headers=env.headers
        ).status_code
        == 200
    )
    assert (
        env.client.put(ROOT + "/" + p["id"], json=draft(env), headers=env.headers).json()[
            "document"
        ]["email_design"]["template_id"]
        == "arcane"
    )


def test_actual_react_html_reaches_existing_delivery_transport(env):
    approved(env, styled(env, "protocol"))
    c.dispatch(env.factory, env.options["integrations"], now=CLOCK)
    assert env.adapter.messages
    for message in env.adapter.messages.values():
        assert (
            "<table" in message.html
            and "background-color:rgb(19,19,19)" in message.html.replace(" ", "")
            or "#131313" in message.html
        )
        assert "/campaign-link/" in message.text and "/campaign-unsubscribe/" in message.text
        assert "Dejar de recibir promociones" in message.text


def test_local_render_failure_never_crosses_send_boundary_and_can_recover(env, monkeypatch):
    approved(env, styled(env))

    def timeout(*a, **kw):
        raise subprocess.TimeoutExpired("node", 12)

    with monkeypatch.context() as patch:
        patch.setattr(re.subprocess, "run", timeout)
        c.dispatch(env.factory, env.options["integrations"], now=CLOCK)
    assert not env.adapter.messages
    with env.factory() as s:
        jobs = s.scalars(select(CampaignJob).where(CampaignJob.state == "queued")).all()
        assert len(jobs) == 2 and all(j.attempts == 0 for j in jobs)
    c.dispatch(env.factory, env.options["integrations"], now=CLOCK)
    assert env.adapter.messages


def test_missing_node_keeps_legacy_path_and_rejects_new_design_atomically(env, monkeypatch):
    approved(env)
    monkeypatch.setenv("CAMPAIGN_EMAIL_NODE", "/missing/101-node")
    c.dispatch(env.factory, env.options["integrations"], now=CLOCK)
    assert env.adapter.messages
    with env.factory() as s:
        before = s.scalar(select(func.count()).select_from(CampaignRevision))
    r = env.client.post(ROOT, json=styled(env), headers=env.headers)
    assert r.status_code == 503, r.text
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CampaignRevision)) == before


@pytest.mark.parametrize(
    "design",
    [
        {"template_id": "unknown"},
        {"template_id": "matte", "image_url": "javascript:alert(1)", "image_alt": "x"},
        {"template_id": "matte", "image_url": "https://a.test/x.png", "image_alt": ""},
        {"template_id": "matte", "image_url": "https://a.test/x.svg", "image_alt": "x"},
        {"template_id": "matte", "image_url": "https://u:p@a.test/x.png", "image_alt": "x"},
        {"template_id": "matte", "shell": "arbitrary"},
    ],
)
def test_bad_design_is_rejected(env, design):
    r = env.client.post(ROOT, json=draft(env, email_design=design), headers=env.headers)
    assert r.status_code == 422, r.text


def test_preview_nonce_allows_trusted_head_styles_and_scopes_tenants(env):
    p = create(env, styled(env))
    path = ROOT + "/" + p["id"] + "/email"
    r = env.client.get(path)
    assert r.status_code == 200, r.text
    assert "style-src-attr 'none'" in r.headers["content-security-policy"]
    assert "<style nonce=" in r.text and "unsafe-inline" not in r.headers["content-security-policy"]
    assert env.client.get(path.replace(BUSINESS, OTHER)).status_code in (403, 404)
    assert env.client.get(path, params={"template_id": "invalid"}).status_code == 422


def test_bundle_version_change_blocks_instead_of_switching_design(env, monkeypatch):
    approved(env, styled(env))
    with env.factory() as session:
        affected = set(session.scalars(select(CampaignJob.id).where(CampaignJob.state == "queued")))
    monkeypatch.setattr(re, "renderer_version", lambda *a: "react-email-v2:changed")
    c.dispatch(env.factory, env.options["integrations"], now=CLOCK)
    assert not env.adapter.messages
    with env.factory() as s:
        assert all(
            j.state == "skipped" and j.reason == "renderer_revision_changed"
            for j in s.scalars(select(CampaignJob).where(CampaignJob.id.in_(affected)))
        )


def test_saved_campaign_remains_editable_when_renderer_fails_without_approval(env, monkeypatch):
    p = create(env, styled(env))
    route = ROOT + "/" + p["id"]

    def fail(*a, **kw):
        raise subprocess.TimeoutExpired("node", 12)

    with monkeypatch.context() as patch:
        patch.setattr(re.subprocess, "run", fail)
        blocked = env.client.get(route)
        assert (
            blocked.status_code == 200 and blocked.json()["render_error"] == "email_render_failed"
        )
        assert (
            env.client.post(
                route + "/approve", headers=env.headers, json={"digest": p["digest"]}
            ).status_code
            == 503
        )
        assert not env.client.get(route).json()["approved"]
        restored = env.client.post(
            route + "/design",
            headers=env.headers,
            json={"digest": p["digest"], "email_design": {"template_id": "legacy"}},
        )
        assert restored.status_code == 200 and restored.json()["render_error"] is None
        assert not restored.json()["approved"]


def test_brand_accent_keeps_button_text_readable_in_actual_html(env):
    from world_model.restaurant_commerce.campaign_models import CampaignSettings

    with env.factory() as session:
        row = session.get(CampaignSettings, BUSINESS)
        config = json.loads(row.config_json)
        config["brand"]["accent"] = "#ffffff"
        row.config_json = json.dumps(config)
        session.commit()
    for template in ["barebone", "matte", "protocol", "arcane", "studio"]:
        p = create(env, styled(env, template))
        html = p["email"]["html"].lower()
        assert "background-color:#ffffff" in html and "color:#000000" in html


def test_missing_font_asset_blocks_current_bundle_instead_of_silent_substitution(
    tmp_path, monkeypatch
):
    import shutil

    from fastapi import HTTPException

    target = tmp_path / "runtime"
    shutil.copytree(re.RUNTIME, target)
    next((target / "fonts").glob("*.woff2")).unlink()
    monkeypatch.setattr(re, "RUNTIME", target)
    with pytest.raises(HTTPException) as error:
        re.runtime_manifest()
    assert error.value.status_code == 503


def test_packaged_fonts_are_served_locally_with_bounded_names(env):
    response = env.client.get("/assets/email-fonts/instrument-serif-latin-400-normal.woff2")
    assert response.status_code == 200
    assert response.content.startswith(b"wOF2")
    assert response.headers["content-type"] == "font/woff2"
    assert env.client.get("/assets/email-fonts/not-a-font.woff2").status_code == 404
    assert env.client.get("/assets/email-fonts/inter-LICENSE.txt").status_code == 404
