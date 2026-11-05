"""Local browser lab for new shared workspace views; no field-performance claim."""

import argparse
import json
import platform
import statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--url", default="http://127.0.0.1:8809")
p.add_argument("--out", default="/tmp/101-home-evidence/performance.json")
a = p.parse_args()
if not a.url.startswith("http://127.0.0.1:"):
    p.error("Local demo only")
result = {
    "machine": platform.platform(),
    "profile": {
        "viewport": [390, 844],
        "cpu_slowdown": 4,
        "latency_ms": 150,
        "download_bits_sec": 1600000,
        "upload_bits_sec": 750000,
        "cache": "new browser context per run, cache disabled",
        "auth": "pre-established, excluded",
        "finish": "next paint after useful record/fixture content exists; separate browser LCP",
        "dataset": "80 fictitious customers,31 orders,3 campaigns; analytics is generated example data",
    },
    "areas": {},
}
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/usr/bin/chromium", args=["--no-sandbox"]
    )
    result["browser"] = browser.version
    auth = browser.new_context()
    response = auth.request.post(
        a.url + "/api/staff/login",
        data={
            "username": "campaign.manager",
            "password": "synthetic campaign demonstration only",
        },
        headers={"X-101-Login": "1"},
    )
    assert response.ok, f"Demo login failed: {response.status}"
    auth_cookies = auth.cookies()
    auth.close()
    for area, selector in [
        ("home", ".attention-row"),
        ("campaigns", ".campaign-row"),
        ("analytics", ".traffic-chart rect"),
    ]:
        runs = []
        for i in range(3):
            c = browser.new_context(
                viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
            )
            c.add_cookies(auth_cookies)
            page = c.new_page()
            cdp = c.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            cdp.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": 150,
                    "downloadThroughput": 200000,
                    "uploadThroughput": 93750,
                    "connectionType": "cellular4g",
                },
            )
            page.add_init_script(
                "window.lab={lcp:0,cls:0};new PerformanceObserver(l=>{for(const e of l.getEntries())window.lab.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.lab.cls+=e.value}).observe({type:'layout-shift',buffered:true});new MutationObserver(()=>{if(!window.lab.useful&&document.querySelector("
                + json.dumps(selector)
                + ")){requestAnimationFrame(()=>{if(!window.lab.useful)window.lab.useful=performance.now()})}}).observe(document,{childList:true,subtree:true});"
            )
            page.goto(a.url + "/workspace/" + area)
            page.locator(selector).first.wait_for()
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            if area == "analytics":
                page.locator(".analytics-metrics button").nth(1).evaluate(
                    "e=>{window.lab.start=performance.now();e.click()}"
                )
                page.wait_for_function(
                    "document.querySelector('.chart-panel h2').textContent.includes('Páginas vistas')"
                )
                page.evaluate(
                    "window.lab.metric_switch=performance.now()-window.lab.start"
                )
            runs.append(page.evaluate("window.lab"))
            c.close()
        result["areas"][area] = {
            "runs": runs,
            "median_useful_ms": round(statistics.median(r["useful"] for r in runs), 1),
            "median_lcp_ms": round(statistics.median(r["lcp"] for r in runs), 1),
            "max_cls": max(r["cls"] for r in runs),
        }
    browser.close()
Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
