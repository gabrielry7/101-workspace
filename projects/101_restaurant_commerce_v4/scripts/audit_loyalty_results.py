"""Measure the explicit local synthetic Stage7 demo; no reward or provider writes."""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8831")
parser.add_argument("--out", required=True)
args = parser.parse_args()
url = urlsplit(args.url)
if (
    url.scheme != "http"
    or url.hostname != "127.0.0.1"
    or not url.port
    or url.username
    or url.password
    or url.path not in ("", "/")
    or url.query
    or url.fragment
):
    parser.error("Use the explicit loopback demonstration origin")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=False)
source = Path(__file__).resolve().parents[1]
measure = (source / "scripts/measure_loyalty_results.js").read_text()
axe = (source / "frontend/node_modules/axe-core/axe.min.js").read_text()
root = "/api/operator/restaurants/honorato-campaign-test/loyalty-config"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    context = browser.new_context(
        base_url=args.url, viewport={"width": 1440, "height": 1000}
    )
    assert context.request.post(
        "/api/staff/login",
        data={"username": "101", "password": "101"},
        headers={"X-101-Login": "1"},
    ).ok
    programs = context.request.get(root + "/experiments").json()
    target = next(
        e
        for e in programs
        if e["document"]["name"] == "Próximas visitas · medición en curso"
    )
    route = f"/workspace/customers?business=honorato-campaign-test&view=loyalty&loyaltyTab=results&loyaltyId={target['id']}"
    page = context.new_page()
    errors, external, screens = [], [], {}
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "request",
        lambda r: (
            external.append(r.url)
            if not r.url.startswith(args.url) and not r.url.startswith("data:")
            else None
        ),
    )
    page.goto(route)
    heading = page.get_by_role(
        "heading", name="Ganancia incremental por cliente asignado", exact=True
    )
    heading.wait_for()

    def capture(name):
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out / (name + ".png")), full_page=True)
        page.evaluate(axe)
        result = page.evaluate(
            measure,
            [
                ".loyalty-results h2",
                ".loyalty-comparison h4",
                ".loyalty-comparison dd",
                ".loyalty-confidence",
                ".loyalty-metrics strong",
                ".loyalty-section",
                ".loyalty-field",
                ".loyalty-table-wrap td",
                ".loyalty-table-wrap th",
            ],
        )
        result["violations"] = page.evaluate(
            "async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations"
        )
        assert not result["overflow"] and not result["violations"]
        screens[name] = result

    capture("provisional-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    capture("provisional-mobile")
    page.get_by_text("Qué revisar antes de interpretar", exact=False).click()
    capture("warnings-mobile")
    page.get_by_label("Vista de color", exact=True).select_option("white-gray")
    page.wait_for_function(
        "document.documentElement.dataset.workspacePairing==='white-gray'"
    )
    capture("white-gray-mobile")
    timings = []
    for _ in range(3):
        cold = browser.new_context(
            base_url=args.url, viewport={"width": 390, "height": 844}
        )
        cold.add_cookies(context.cookies())
        tab = cold.new_page()
        cdp = cold.new_cdp_session(tab)
        cdp.send("Network.enable")
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        cdp.send(
            "Network.emulateNetworkConditions",
            {
                "offline": False,
                "latency": 150,
                "downloadThroughput": 1600000 / 8,
                "uploadThroughput": 750000 / 8,
            },
        )
        started = time.perf_counter()
        tab.goto(route)
        tab.get_by_role(
            "heading", name="Ganancia incremental por cliente asignado", exact=True
        ).wait_for()
        tab.evaluate("document.fonts.ready")
        timings.append(round((time.perf_counter() - started) * 1000, 2))
        cold.close()
    result = {
        "screens": screens,
        "errors": errors,
        "external": external,
        "cold_content_ms": timings,
        "profile": "local Chromium;390x844;150ms latency;1.6Mbps down/750Kbps up;cache disabled;no CPU throttle;warm server;80synthetic workspace contacts/40assigned customers;current incomplete follow-up;not field data",
    }
    (out / "measurements.json").write_text(json.dumps(result, indent=2))
    assert not errors and not external
    print(
        "Screens",
        len(screens),
        "axe violations",
        sum(len(s["violations"]) for s in screens.values()),
        "cold content ms",
        timings,
    )
    context.close()
    browser.close()
