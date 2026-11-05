"""Capture, accessibility/geometry measurements and bounded local Stage6 timings.

Use the explicit synthetic loyalty fixture. No provider or reward writes.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8816")
parser.add_argument("--out", required=True)
args = parser.parse_args()
parsed = urlsplit(args.url)
if (
    parsed.scheme != "http"
    or parsed.hostname != "127.0.0.1"
    or not parsed.port
    or parsed.username
    or parsed.password
    or parsed.path not in ("", "/")
    or parsed.query
    or parsed.fragment
):
    parser.error("Only the explicit loopback demonstration is supported")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
axe = (
    Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
).read_text()
results = {}
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, base_url=args.url
    )
    assert context.request.post(
        "/api/staff/login",
        data={
            "username": "campaign.manager",
            "password": "synthetic campaign demonstration only",
        },
        headers={"X-101-Login": "1"},
    ).ok
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))

    def capture(name):
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out / (name + ".png")), full_page=True)
        page.evaluate(axe)
        results[name] = (
            page.evaluate(r"""async()=>{const rgba=s=>{const m=s.match(/^rgba?\(([^)]+)\)$/);if(!m)return null;const a=m[1].split(',').map(Number);return [a[0],a[1],a[2],a.length===4?a[3]:1]};const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3]));const lum=c=>{const v=c.map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2]};const contrast=e=>{let layers=[];for(let p=e;p;p=p.parentElement){const c=getComputedStyle(p);if(c.backgroundImage!=='none'||Number(c.opacity)!==1)return null;let v=rgba(c.backgroundColor);if(!v)return null;layers.push(v)}let bg=[255,255,255];layers.reverse().forEach(c=>bg=blend(c,bg));const fg=rgba(getComputedStyle(e).color);if(!fg)return null;const a=lum(blend(fg,bg)),b=lum(bg);return Number(((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(3))};return ({width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,
          violations:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),
          roles:['.loyalty-page h1','.loyalty-field','.loyalty-table-wrap td','.loyalty-table-wrap th','.loyalty-metrics strong','.loyalty-section','.loyalty-tabs a'].map(s=>{let e=document.querySelector(s);if(!e)return null;let c=getComputedStyle(e),r=e.getBoundingClientRect();return {selector:s,font:c.fontSize,color:c.color,background:c.backgroundColor,radius:c.borderRadius,width:r.width,height:r.height,solid_contrast:contrast(e)}}).filter(Boolean)})}""")
        )

    page.goto("/workspace/customers?view=loyalty")
    page.get_by_role("button", name="Crear programa", exact=True).wait_for()
    capture("programs-desktop")
    page.get_by_role("link", name="Puntos para la próxima visita", exact=False).click()
    page.get_by_role("button", name="Editar propuesta", exact=True).wait_for()
    capture("program-detail-desktop")
    page.get_by_role("button", name="Editar propuesta", exact=True).click()
    page.get_by_label("Nombre", exact=True).wait_for()
    capture("program-editor-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    capture("program-editor-mobile")
    # Demonstrate independently editable roles without changing facts or actions.
    before = page.get_by_label("Nombre", exact=True).input_value()
    page.evaluate(
        "document.documentElement.style.setProperty('--wm-radius','4px');document.documentElement.style.setProperty('--wm-accent','#315d8b');document.documentElement.style.setProperty('--wm-label','16px')"
    )
    capture("editable-roles-mobile")
    assert page.get_by_label("Nombre", exact=True).input_value() == before
    page.evaluate(
        "['--wm-radius','--wm-accent','--wm-label'].forEach(k=>document.documentElement.style.removeProperty(k))"
    )
    page.get_by_role("button", name="Volver", exact=True).click()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("link", name="Experimentos", exact=True).click()
    page.get_by_role("button", name="Crear experimento", exact=True).wait_for()
    capture("experiments-desktop")
    page.get_by_role(
        "link", name="Próxima visita · comparación inicial", exact=False
    ).click()
    page.get_by_role("heading", name="Participación registrada", exact=True).wait_for()
    capture("experiment-detail-desktop")
    page.get_by_role("link", name="Calculadora", exact=True).click()
    page.get_by_role("button", name="Calcular escenario", exact=True).click()
    page.get_by_role("heading", name="Resultado bajo estos supuestos").wait_for()
    capture("calculator-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    capture("calculator-mobile")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("link", name="Saldos y costos", exact=True).click()
    page.get_by_role("heading", name="Movimientos recientes", exact=True).wait_for()
    capture("exposure-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    capture("exposure-mobile")
    # Financial tables keep every fact column; horizontal scroll stays internal.
    assert page.locator(".loyalty-table-wrap th").evaluate_all(
        "nodes=>nodes.every(n=>getComputedStyle(n).display==='table-cell')"
    )
    for width in [320, 768, 1920]:
        page.set_viewport_size({"width": width, "height": 900})
        capture("exposure-" + str(width))
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
        start = time.perf_counter()
        tab.goto("/workspace/customers?view=loyalty")
        tab.get_by_role("button", name="Crear programa", exact=True).wait_for()
        useful = round((time.perf_counter() - start) * 1000, 2)
        start = time.perf_counter()
        tab.get_by_role("button", name="Crear programa", exact=True).click()
        tab.get_by_label("Nombre", exact=True).wait_for()
        feedback = round((time.perf_counter() - start) * 1000, 2)
        timings.append({"useful_content_ms": useful, "open_form_ms": feedback})
        cold.close()
    (out / "measurements.json").write_text(
        json.dumps(
            {
                "screens": results,
                "errors": errors,
                "timings": timings,
                "profile": "local Chromium;390x844;150ms RTT;1.6Mbps down/750Kbps up;cache disabled;80synthetic customers,1program,1experiment,1wallet;no CPU throttle;not field data",
            },
            indent=2,
        )
    )
    print(
        "Screens",
        len(results),
        "violations",
        sum(len(v["violations"]) for v in results.values()),
        "errors",
        errors,
        "timings",
        timings,
    )
    context.close()
    browser.close()
