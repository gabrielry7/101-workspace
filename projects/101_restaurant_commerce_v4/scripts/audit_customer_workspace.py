from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import argparse

parser = argparse.ArgumentParser(
    description="Accessibility audit of the explicit local customer demo"
)
parser.add_argument("--url", default="http://127.0.0.1:8806")
parser.add_argument("--out", default="/tmp/101-customer-accessibility")
args = parser.parse_args()
if not args.url.startswith("http://127.0.0.1:"):
    parser.error("Only the local demonstration is supported")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    page = c.new_page()
    login = c.request.post(
        args.url + "/api/staff/login",
        data={
            "username": "campaign.manager",
            "password": "synthetic campaign demonstration only",
        },
        headers={"X-101-Login": "1"},
    )
    assert login.ok
    page.goto(args.url + "/workspace/customers")
    page.locator("tbody tr").first.wait_for()
    axe = (
        Path(__file__).resolve().parents[1]
        / "frontend/node_modules/axe-core/axe.min.js"
    ).read_text()
    results = {}
    for state in ["directory", "detail", "qr", "mobile"]:
        if state == "detail":
            page.locator(".customer-link").filter(
                has_text="Lucía Fernández"
            ).first.click()
            page.locator(".detail h2").wait_for()
        if state == "qr":
            page.get_by_label("Cerrar detalle").click()
            page.get_by_role("button", name="Invitar clientes").click()
            page.get_by_role("dialog").wait_for()
            page.wait_for_function(
                "() => { const img=document.querySelector('[role=dialog] img'); return img && img.complete && img.naturalWidth>0; }"
            )
        if state == "mobile":
            page.keyboard.press("Escape")
            page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate(axe)
        result = page.evaluate(
            "async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
        )
        results[state] = [
            {
                "id": v["id"],
                "impact": v["impact"],
                "nodes": [
                    {"target": n["target"], "summary": n["failureSummary"]}
                    for n in v["nodes"]
                ],
            }
            for v in result["violations"]
        ]
    (out / "axe.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    b.close()
    assert not any(results.values()), results
