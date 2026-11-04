"""Live-backend browser reproduction for ZAP's stored JSON and email CSP findings."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from security_fixtures import Fixtures
from sqlalchemy.orm import Session
from world_model.restaurant_commerce.models import OutboundMessage

PAYLOAD = '<img src=x onerror="window.__attack=1"><script>window.__attack=2</script>'


@pytest.fixture
def live():
    c = json.loads(Path(os.environ["COMMERCE_RECORD_CONFIG"]).read_text())
    f = Fixtures(c)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        context = browser.new_context()
        context.add_cookies(
            [
                {
                    "name": "commerce_staff",
                    "value": c["single_staff_headers"]["Cookie"].split("=", 1)[1],
                    "url": c["base_url"],
                    "httpOnly": True,
                    "sameSite": "Strict",
                }
            ]
        )
        external = []

        def route(r):
            if urlsplit(r.request.url).hostname not in {"127.0.0.1", "localhost"}:
                external.append(r.request.url)
                r.abort()
            else:
                r.continue_()

        context.route("**/*", route)
        page = context.new_page()
        try:
            yield f, page
        finally:
            context.close()
            browser.close()
            f.close()
            assert not external


def test_stored_json_values_are_text_in_real_growth_page(live):
    f, page = live
    root = f"/api/operator/restaurants/{f.business}"
    f.call("POST", root + "/rewards", {"name": PAYLOAD, "points_cost": 1, "discount_minor": 100})
    f.call(
        "POST",
        root + "/automations",
        {
            "name": PAYLOAD,
            "trigger_kind": "customer.winback",
            "purpose": "marketing",
            "template_text": PAYLOAD,
        },
    )
    ids, _ = f.prepare("POST", "/api/operator/outbox/{message_id}/handoff")
    with Session(f.engine) as s:
        s.get(OutboundMessage, ids["message_id"]).body = PAYLOAD
        s.commit()
    response = f.http.get(root + "/automations", headers=f.headers)
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert any(x["name"] == PAYLOAD and x["template_text"] == PAYLOAD for x in response.json())
    page.goto(f.config["base_url"] + "/growth?business_id=" + f.business)
    expect(page.locator("#rewards")).to_contain_text(PAYLOAD)
    expect(page.locator("#outbox")).to_contain_text(PAYLOAD)
    assert page.locator("#rewards img, #rewards script, #outbox img, #outbox script").count() == 0
    assert page.evaluate("window.__attack || 0") == 0


def test_campaign_preview_preserves_styles_and_blocks_unlisted_css(live):
    f, page = live
    body = f.draft()
    body["content"].update(title=PAYLOAD, body=PAYLOAD)
    campaign = f.call("POST", f.campaign_root, body)
    response = page.goto(f.config["base_url"] + f.campaign_root + "/" + campaign["id"] + "/email")
    policy = response.headers["content-security-policy"]
    assert "'unsafe-inline'" not in policy and "'unsafe-hashes'" not in policy
    assert "'nonce-" in policy and "style-src-attr 'none'" in policy
    assert "default-src 'none'" in policy
    expect(page.locator("h1")).to_have_text(PAYLOAD)
    assert page.locator("h1 img, h1 script").count() == 0
    assert (
        page.locator("body").evaluate("(e)=>getComputedStyle(e).backgroundColor")
        == "rgb(244, 239, 231)"
    )
    assert page.locator("h1").evaluate("(e)=>getComputedStyle(e).fontSize") == "34px"
    page.locator("h1").evaluate('(e)=>e.setAttribute("style","font-size:99px")')
    assert page.locator("h1").evaluate("(e)=>getComputedStyle(e).fontSize") != "99px"
    assert page.evaluate("window.__attack || 0") == 0
