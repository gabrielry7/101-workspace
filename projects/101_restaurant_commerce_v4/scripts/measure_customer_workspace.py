"""Reproducible local lab, not field INP or a real-device benchmark.

Run against a fresh demo database with --customers 10000. Auth is performed before
measurement. Each cold run has a fresh context, empty cache, 390x844 viewport,
4x CPU slowdown, 150ms network latency, 1.6Mbit/s down and 750Kbit/s up.
"""

import argparse
import gzip
import json
import platform
import statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8807")
parser.add_argument("--area", choices=["customers", "sales"], default="customers")
parser.add_argument("--out", default="/tmp/101-customer-evidence/performance.json")
parser.add_argument("--chromium", default="/usr/bin/chromium")
args = parser.parse_args()
if not args.url.startswith("http://127.0.0.1:"):
    parser.error("Only the explicit local demo is supported")
init = """window.lab={lcp:0,cls:0};new PerformanceObserver(l=>{for(const e of l.getEntries())window.lab.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.lab.cls+=e.value}).observe({type:'layout-shift',buffered:true});new MutationObserver(()=>{if(!window.lab.useful&&document.querySelector('tbody tr')){requestAnimationFrame(()=>{if(!window.lab.useful)window.lab.useful=performance.now()})}if(window.lab.click&&document.querySelector('.detail h2')&&!window.lab.detail)window.lab.detail=performance.now()-window.lab.click;if(window.lab.back&&!document.querySelector('.detail')&&!window.lab.restored)requestAnimationFrame(()=>window.lab.restored=performance.now()-window.lab.back)}).observe(document,{childList:true,subtree:true});document.addEventListener('click',e=>{if(e.target.closest('.customer-link')){window.lab.click=performance.now();requestAnimationFrame(()=>requestAnimationFrame(()=>window.lab.feedback=performance.now()-window.lab.click))}if(e.target.closest('[aria-label="Cerrar detalle"]'))window.lab.back=performance.now()},true);"""
if args.area == "sales":
    init = init.replace(".customer-link", ".sale-link").replace(
        "Cerrar detalle", "Cerrar pedido"
    )
result = {
    "area": args.area,
    "profile": {
        "viewport": [390, 844],
        "cpu_slowdown": 4,
        "latency_ms": 150,
        "download_bits_sec": 1600000,
        "upload_bits_sec": 750000,
        "cache": "empty new context per run",
        "auth": "pre-established, excluded",
        "finish": "first painted directory row; separately browser LCP",
        "machine": platform.platform(),
    },
    "runs": [],
}
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=args.chromium, headless=True, args=["--no-sandbox"]
    )
    result["browser"] = browser.version
    for i in range(3):
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
        )
        auth = context.request.post(
            args.url + "/api/staff/login",
            data={
                "username": "campaign.manager",
                "password": "synthetic campaign demonstration only",
            },
            headers={"X-101-Login": "1"},
        )
        assert auth.ok
        page = context.new_page()
        cdp = context.new_cdp_session(page)
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
        page.add_init_script(init)
        page.goto(args.url + "/workspace/" + args.area)
        page.locator("tbody tr").first.wait_for()
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(500)
        first = page.evaluate("window.lab")
        assert first["useful"] > 0
        result["dataset_label"] = page.locator(
            ".overview-stat strong"
            if args.area == "customers"
            else ".sales-summary strong"
        ).first.inner_text()
        page.locator(
            ".customer-link" if args.area == "customers" else ".sale-link"
        ).first.click()
        page.locator(".detail h2").wait_for()
        page.wait_for_timeout(50)
        page.get_by_label(
            "Cerrar detalle" if args.area == "customers" else "Cerrar pedido"
        ).click()
        page.locator(".detail").wait_for(state="detached")
        page.wait_for_timeout(50)
        result["runs"].append(page.evaluate("window.lab"))
        context.close()
    browser.close()
assets = (
    Path(__file__).resolve().parents[1]
    / "src/world_model/restaurant_commerce/web/workspace/assets"
)
result["bundle"] = {
    suffix: {
        "raw_bytes": sum(p.stat().st_size for p in assets.glob("*." + suffix)),
        "gzip_bytes": sum(
            len(gzip.compress(p.read_bytes(), compresslevel=5))
            for p in assets.glob("*." + suffix)
        ),
    }
    for suffix in ["js", "css", "woff2"]
}
result["median_ms"] = {
    key: round(statistics.median(r[key] for r in result["runs"]), 1)
    for key in ["useful", "lcp", "feedback", "detail", "restored"]
}
result["max_cls"] = max(r["cls"] for r in result["runs"])
Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
