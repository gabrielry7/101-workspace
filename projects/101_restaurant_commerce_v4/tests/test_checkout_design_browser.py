"""The real public checkout and native editor over real API responses; offline synthetic orders."""

import json
import os
from pathlib import Path
import pytest
from test_browser_security import browser as browser, playwright, site as site

B = "demo-restaurant-bogota"
ROOT = f"/api/restaurants/{B}"
OUT = Path(os.environ.get("CHECKOUT_EVIDENCE", "/tmp/checkout-design-evidence"))

OUT.mkdir(parents=True, exist_ok=True)

def capture(page, name):
    OUT.mkdir(parents=True, exist_ok=True)
    page.evaluate("document.activeElement?.blur();window.scrollTo(0,0)")
    page.screenshot(path=str(OUT / (name + ".png")), full_page=True)
    if page.locator("#cart").count():
        from PIL import Image

        box = page.locator("#cart").bounding_box()
        Image.open(OUT / (name + ".png")).crop(
            (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])
        ).save(OUT / (name + "-cart.png"))


@pytest.mark.parametrize("width", [1440, 390])
def test_editor_coat_measure_export_import_and_actual_checkout(site, width):
    page, c, overrides, requests, errors, external = site
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"https://commerce.test/workspace/website?business={B}")
    page.get_by_role("heading", name="Checkout", exact=True).wait_for()
    frame = page.frame_locator('iframe[title="Vista previa del checkout"]')
    frame.locator("body[data-checkout-ready=true]").wait_for()
    page.get_by_label("Punto de partida").select_option("neutral")
    playwright.expect(frame.locator("#cart")).to_have_css("background-color", "rgb(255, 255, 255)")
    page.get_by_text("Piezas del chasis", exact=True).click()
    page.get_by_label("Esquinas (px)", exact=True).fill("3")
    playwright.expect(frame.locator("#cart")).to_have_css("border-radius", "3px")
    page.get_by_role("button", name="Medir piezas visibles", exact=True).click()
    playwright.expect(page.locator(".checkout-measurements")).to_contain_text(
        "piezas visibles medidas"
    )
    with page.expect_download() as download:
        page.get_by_role("button", name="Exportar diseño", exact=True).click()
    exported = json.loads(Path(download.value.path()).read_text())
    assert exported["profile"]["bones"]["surfaces"]["panel"]["radius"] == 3
    assert exported["measurements"]["boxes"]
    (OUT / f"measurements-editor-{width}.json").write_text(
        json.dumps(exported["measurements"], indent=2)
    )
    # Invalid import leaves the selected appearance intact.
    page.locator("input[type=file]").set_input_files(
        {
            "name": "bad.json",
            "mimeType": "application/json",
            "buffer": b'{"schema_version":"1","layout":"sidebar","checkout_url":"https://evil.test"}',
        }
    )
    playwright.expect(page.get_by_role("alert")).to_contain_text("No se importó")
    playwright.expect(frame.locator("#cart")).to_have_css("border-radius", "3px")
    page.locator("input[type=file]").set_input_files(
        {
            "name": "good.json",
            "mimeType": "application/json",
            "buffer": json.dumps(exported).encode(),
        }
    )
    page.get_by_role("button", name="Aplicar al checkout", exact=True).click()
    playwright.expect(
        page.get_by_text("Diseño aplicado al checkout. Los pedidos conservan sus datos.")
    ).to_be_visible()
    assert c.get(ROOT + "/checkout-design").json()["revision"] == 1
    capture(page, f"editor-{width}")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    # The embedded preview cannot place an order, even through its real button.
    frame.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    frame.locator("#cName").fill("Cliente de prueba")
    frame.locator("#cPhone").fill("3005550101")
    frame.locator("#checkoutButton").click()
    playwright.expect(frame.locator("#notice")).to_contain_text("Vista previa")
    assert not [r for r in requests if r[0] == "POST" and r[1] == ROOT + "/orders"]
    assert (
        frame.locator("body").evaluate('(e)=>localStorage.getItem("101.checkout.v1:' + B + '")')
        is None
    )
    assert (
        frame.locator("body").evaluate('(e)=>localStorage.getItem("101.cart.v1:' + B + '")') is None
    )
    # Normal customer entry loads the saved profile, preserves quotes and completes one synthetic order.
    page.goto(f"https://commerce.test/?business_id={B}")
    playwright.expect(page.locator("#cart")).to_have_css("border-radius", "3px")
    page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    page.locator("#cName").fill("Cliente de prueba")
    page.locator("#cPhone").fill("3005550101")
    playwright.expect(page.locator("#quoteState")).to_contain_text("Precio verificado")
    assert "11.900" in page.locator("#cartTotal").inner_text()
    capture(page, f"neutral-{width}")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("recibido")
    orders = [r for r in requests if r[0] == "POST" and r[1] == ROOT + "/orders"]
    assert len(orders) == 1
    assert not errors and not external


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_source_neutral_warm_layout_and_brand_scoping(site, width):
    page, c, overrides, requests, errors, external = site
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"https://commerce.test/?business_id={B}")
    page.locator("body[data-checkout-ready=true]").wait_for()
    page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    page.locator("#cName").fill("Cliente de prueba")
    page.locator("#cPhone").fill("3005550101")
    playwright.expect(page.locator("#quoteState")).to_contain_text("Precio verificado")
    before = page.locator("#cartTotal").inner_text()
    menu_before = page.locator("#menu").inner_text()
    menu_font = page.locator("#menu h3").first.evaluate("e=>getComputedStyle(e).fontFamily")
    assert "Inter" not in menu_font
    for coat in ["source", "neutral", "warm"]:
        page.evaluate(
            "async name=>{const m=await import('/assets/checkout-chassis.js');m.applyCheckoutProfile(document.body,m.preset(name));}",
            coat,
        )
        capture(page, f"{coat}-{width}")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        assert page.locator("#cartTotal").inner_text() == before
        assert page.locator("#menu").inner_text() == menu_before
        assert page.locator("#menu h3").first.evaluate("e=>getComputedStyle(e).fontFamily") == menu_font
        assert page.locator("#cName").input_value() == "Cliente de prueba"
    page.evaluate(
        "async()=>{const m=await import('/assets/checkout-chassis.js');const p=m.preset('neutral');p.layout='stacked';m.applyCheckoutProfile(document.body,p);}"
    )
    if width > 900:
        assert page.locator("#cart").bounding_box()["y"] > page.locator("#menu").bounding_box()["y"]
    assert not errors and not external


def test_style_change_keeps_locked_fields_retry_identity_and_reload_recovery(site):
    page, c, overrides, requests, errors, external = site
    page.goto(f"https://commerce.test/?business_id={B}")
    page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    page.locator("#cName").fill("Cliente de prueba")
    page.locator("#cPhone").fill("3005550101")
    playwright.expect(page.locator("#quoteState")).to_contain_text("Precio verificado")
    pending = []
    page.route("**" + ROOT + "/orders", lambda r: pending.append(r))
    page.locator("#checkoutButton").evaluate("(e)=>{e.click();e.click()}")
    for _ in range(80):
        if pending:
            break
        page.wait_for_timeout(50)
    assert len(pending) == 1
    first = json.loads(pending[0].request.post_data)
    playwright.expect(page.locator("#cName")).to_be_disabled()
    page.evaluate(
        "async()=>{const m=await import('/assets/checkout-chassis.js');m.applyCheckoutProfile(document.body,m.preset('warm'));}"
    )
    playwright.expect(page.locator("#cName")).to_be_disabled()
    committed = c.post(ROOT + "/orders", json=first)
    assert committed.status_code == 200, committed.text
    pending[0].abort("failed")
    playwright.expect(page.locator("#checkoutButton")).to_be_enabled()
    page.locator("#checkoutButton").click()
    for _ in range(80):
        if len(pending) == 2:
            break
        page.wait_for_timeout(50)
    assert len(pending) == 2
    assert json.loads(pending[1].request.post_data) == first
    repeated = c.post(ROOT + "/orders", json=first)
    assert repeated.json()["id"] == committed.json()["id"]
    pending[1].fulfill(status=200, json=repeated.json())
    playwright.expect(page.locator("#notice")).to_contain_text("recibido")
    page.reload()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    capture(page, "confirmed-recovery")
    assert not errors and not external


def test_shared_visible_measurements_distinguish_contrast_failure_and_unknown(site):
    page, c, overrides, requests, errors, external = site
    library = Path(__file__).resolve().parents[3] / "packages/101-checkout-chassis/vendor"
    def instrumentation(route):
        name=route.request.url.rsplit('/',1)[-1]
        assert name in {'measure.js','content-bounds.js'}
        route.fulfill(body=(library/name).read_text(),content_type='text/javascript')
    page.route('**/check-instrument/*',instrumentation)
    page.goto(f"https://commerce.test/?business_id={B}")
    page.locator("body[data-checkout-ready=true]").wait_for()
    page.locator("#cName").scroll_into_view_if_needed()
    result = page.evaluate(
        """async()=>{const m=await import('/assets/checkout-chassis.js');const inspect=await import('/check-instrument/measure.js');m.applyCheckoutProfile(document.body,m.preset('neutral'));return inspect.measureDesign(document.body,m.CHECKOUT_ANATOMY);}"""
    )
    assert result["contrast"] and not [v for v in result["contrast"] if v["status"] == "fail"]
    bad = page.evaluate(
        """async()=>{const m=await import('/assets/checkout-chassis.js');const inspect=await import('/check-instrument/measure.js');const p=m.preset('neutral');p.colors.ink='#ffffff';p.colors.canvas='#ffffff';m.applyCheckoutProfile(document.body,p);return inspect.measureDesign(document.body,m.CHECKOUT_ANATOMY);}"""
    )
    assert any(v["status"] == "fail" for v in bad["contrast"])
    unknown = page.evaluate(
        """async()=>{const m=await import('/assets/checkout-chassis.js');const inspect=await import('/check-instrument/measure.js');m.applyCheckoutProfile(document.body,m.preset('neutral'));document.querySelector('#cart').style.opacity='0.5';return inspect.measureDesign(document.body,m.CHECKOUT_ANATOMY);}"""
    )
    assert any(v["status"] == "unknown" for v in unknown["contrast"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "contrast-success-failure-unknown.json").write_text(
        json.dumps({"neutral": result, "failure": bad, "unknown": unknown}, indent=2)
    )
    assert not errors and not external
