"""Capture and measure the real local Sales/Customers demonstration for visual review.

This does not mutate orders or call providers. Use a fresh sales_workspace_demo.
"""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8808")
parser.add_argument("--out", default="/tmp/101-sales-visual")
args = parser.parse_args()
if not args.url.startswith("http://127.0.0.1:"):
    parser.error("Only the explicit local demo is supported")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
axe = (
    Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
).read_text()
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    context = browser.new_context(viewport={"width": 1920, "height": 944})
    assert context.request.post(
        args.url + "/api/staff/login",
        data={
            "username": "campaign.manager",
            "password": "synthetic campaign demonstration only",
        },
        headers={"X-101-Login": "1"},
    ).ok
    page = context.new_page()
    results = {}
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def capture(name):
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out / (name + ".png")), full_page=True)
        page.evaluate(axe)
        results[name] = page.evaluate(
            """async()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,violations:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),roles:['.customer-link strong','.contact-cell > span','nav > a','.sale-link strong','.sale-detail h2'].map(s=>{let e=document.querySelector(s);if(!e)return null;let c=getComputedStyle(e),r=e.getBoundingClientRect();return {selector:s,font:c.fontSize,color:c.color,width:r.width,height:r.height}}).filter(Boolean)})"""
        )

    for area in ["customers", "sales"]:
        page.goto(args.url + "/workspace/" + area)
        page.locator("tbody tr").first.wait_for()
        for width in [1920, 390]:
            page.set_viewport_size(
                {"width": width, "height": 944 if width > 700 else 844}
            )
            capture(area + "-" + str(width))
    for width in [1440, 390]:
        page.set_viewport_size({"width": width, "height": 1000 if width > 700 else 844})
        page.goto(args.url + "/workspace/sales?order=workspace-sale-000")
        page.locator(".sale-detail h2").wait_for()
        capture("detail-" + str(width))
    page.goto(args.url + "/workspace/sales?order=workspace-sale-008")
    page.get_by_role("button", name="Confirmar cobro y entrega").click()
    page.get_by_role("dialog").wait_for()
    capture("cash-mobile")
    # Measure actual solid-background contrast for visible role samples, using axe's color utilities.
    page.keyboard.press("Escape")
    page.goto(args.url + "/workspace/customers")
    page.locator("tbody tr").first.wait_for()
    page.set_viewport_size({"width": 1920, "height": 944})
    page.evaluate(axe)
    results["solid_contrast"] = page.evaluate("""()=>{
      function rgb(v){return v.match(/[0-9.]+/g).map(Number)}
      function luminance(c){let a=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return .2126*a[0]+.7152*a[1]+.0722*a[2]}
      return ['.customer-link strong','.contact-cell > span','.contact-cell > small','.date-cell','.badge','.page-heading p'].map(s=>{
        let e=document.querySelector(s),c=getComputedStyle(e),fg=rgb(c.color),bg=null,node=e;
        while(node){let style=getComputedStyle(node),color=rgb(style.backgroundColor);if(style.backgroundImage!=='none')break;if(color.length===3||color[3]===1){bg=color;break}if(color[3]>0)break;node=node.parentElement}
        let ratio=null;if(bg&&(fg.length===3||fg[3]===1)){let a=luminance(fg),b=luminance(bg);ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}
        return {selector:s,ratio,font:c.fontSize,foreground:c.color,background:bg,method:'WCAG sRGB luminance; solid ancestor only'}
      })
    }""")
    results["errors"] = errors
    (out / "visual-measurements.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    assert not errors
    assert all(
        not v["violations"] and not v["overflow"]
        for v in results.values()
        if isinstance(v, dict)
    )
    browser.close()
