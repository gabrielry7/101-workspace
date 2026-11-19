"""Built shared workspace: native account intake, signup and public entry."""

# ruff: noqa: F811
import json
import os
import re
from pathlib import Path

import pytest
import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright  # noqa:F401
from test_workspace_completion import app_for_completion  # noqa:F401
from test_workspace_completion import no_provider_network as no_provider_network
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD

OUT = Path(os.environ.get("COMPLETION_EVIDENCE", "/tmp/101-completion-browser"))


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    monkeypatch.setattr(
        customers, "app_for_demo", lambda db, url, count: app_for_completion(db, url, worker=True)
    )
    OUT.mkdir(exist_ok=True, parents=True)
    yield from customers.site.__wrapped__(tmp_path, browser)


def signin(page, path, user="campaign.manager"):
    page.goto(path)
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_url(re.compile(r".*/workspace/(?!login).+"))


def confirm(page):
    d = page.get_by_role("dialog")
    d.get_by_role("checkbox").check()
    d.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(d).to_have_count(0)


def capture(page, name):
    measured = {}
    for width in [1440, 390, 320]:
        page.set_viewport_size({"width": width, "height": 1000})
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
        d = page.evaluate("""() => ({overflow:document.documentElement.scrollWidth-innerWidth,
          font:getComputedStyle(document.body).fontFamily,
          controls:[...document.querySelectorAll('.account-connections button,'+
          '.signup-tools button,.channel-tabs button')]
          .filter(b=>b.getBoundingClientRect().width)
          .map(b=>({text:b.textContent,height:b.getBoundingClientRect().height}))})""")
        assert d["overflow"] == 0 and "Inter" in d["font"]
        if page.locator(".signup-funnel table").count():
            assert (
                page.locator(".signup-funnel th")
                .nth(1)
                .evaluate("e=>e.getBoundingClientRect().width")
                > 0
            )
        if page.locator(".connection-table table").count():
            assert (
                page.locator(".connection-table th")
                .nth(1)
                .evaluate("e=>e.getBoundingClientRect().width")
                > 0
            )
        assert all(c["height"] >= 43 for c in d["controls"])
        measured[str(width)] = d
    page.evaluate(
        (
            Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
        ).read_text()
    )
    measured["a11y"] = page.evaluate("""async()=> (await axe.run(document.querySelector('main'),{
      runOnly:{type:'tag',values:['wcag2a','wcag2aa']}}))
      .violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))""")
    (OUT / (name + ".json")).write_text(json.dumps(measured, indent=2) + "\n")
    assert not measured["a11y"]
    page.set_viewport_size({"width": 1440, "height": 1000})


def test_instagram_native_select_partial_zero_unknown_and_disconnect(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/connections?business={BUSINESS}&provider=instagram")
    page.get_by_role("button", name="Conectar Instagram", exact=True).click()
    select = page.get_by_label("Recurso del negocio", exact=True)
    playwright.expect(select.locator("option")).to_have_count(2, timeout=20000)
    assert (
        "code=" not in page.url and "state=" not in page.url and "business=" + BUSINESS in page.url
    )
    select.select_option("123")
    page.get_by_role("button", name="Confirmar recurso", exact=True).click()
    confirm(page)
    playwright.expect(page.locator(".connection-state")).to_have_text(
        "Datos parciales", timeout=20000
    )
    playwright.expect(page.locator(".connection-snapshot")).to_contain_text("Me gusta: 0")
    playwright.expect(page.locator(".connection-snapshot")).to_contain_text(
        "Me gusta: No disponible"
    )
    capture(page, "instagram-partial")
    page.get_by_role("button", name="Desconectar Instagram", exact=True).click()
    confirm(page)
    playwright.expect(page.locator(".connection-state")).to_have_text("Sin conexión", timeout=20000)
    playwright.expect(page.locator(".connection-snapshot")).to_have_count(0)
    me = context.request.get("/api/staff/me").json()
    context.request.post("/api/staff/logout", headers={"X-101-CSRF": me["csrf"]})
    signin(page, f"/workspace/connections?business={BUSINESS}&provider=google", "completion.viewer")
    assert page.get_by_role("button", name="Conectar Google", exact=True).count() == 0
    capture(page, "google-readonly")


def test_native_signup_clipboard_qr_membership_and_funnel(site):
    page, context, url, app, *_ = site
    signin(page, f"/customers/signup?business_id={BUSINESS}")
    playwright.expect(
        page.get_by_role("heading", name="Registro de clientes", exact=True)
    ).to_be_visible()
    qr = page.get_by_alt_text(re.compile("^Código QR de registro"))
    playwright.expect(qr).to_be_visible()
    page.wait_for_function(
        """()=>{const q=document.querySelector('.qr-card img');
        return q?.complete&&q.naturalWidth>100}"""
    )
    page.evaluate(
        """Object.defineProperty(navigator,'clipboard',{configurable:true,
        value:{writeText:async()=>{throw Error('fixture denied')}}})"""
    )
    page.get_by_role("button", name="Copiar enlace", exact=True).click()
    playwright.expect(
        page.get_by_text("Seleccionamos el enlace para que puedas copiarlo.", exact=True)
    ).to_be_visible()
    field = page.get_by_label("Enlace de registro", exact=True)
    assert field.evaluate("e=>e.selectionEnd-e.selectionStart") == len(field.input_value())
    assert "source=website" in field.input_value()
    for name in ["Descargar PNG", "SVG"]:
        with page.expect_download() as d:
            page.get_by_role("link", name=name, exact=True).click()
        d.value.save_as(OUT / ("signup." + ("png" if name.endswith("PNG") else "svg")))
    root = "/api/operator/restaurants/" + BUSINESS + "/signup"
    data = context.request.get(root).json()
    assert "source=qr" in data["qr_url"]
    page.goto(data["qr_url"])
    page.locator("#chooseEmail").click()
    page.locator("#email").fill("native-join@example.test")
    page.locator("#sendCode").click()
    playwright.expect(page.locator("#demoCode")).to_contain_text("Código de prueba")
    code = re.search(r"\b\d{6}\b", page.locator("#demoCode").inner_text()).group()
    page.locator("#code").fill(code)
    page.locator("#verifyCode").click()
    playwright.expect(page.locator("#welcome")).to_have_text("Ya eres parte.")
    playwright.expect(page.locator("#welcome")).to_be_visible()
    member = context.request.get("/api/customer/signup/" + BUSINESS).json()["account"]
    assert member and member["member"] and member["identifier"] == "native-join@example.test"
    page.reload()
    playwright.expect(page.locator("#welcome")).to_have_text("Ya eres parte.")
    assert context.request.get("/api/customer/signup/" + BUSINESS).json()["account"] == member
    page.goto(f"/workspace/customers?business={BUSINESS}&view=signup")
    playwright.expect(page.locator(".signup-funnel")).to_contain_text("Nuevo registro")
    assert any(
        r["source"] == "qr" and r["stage"] == "membership_created" and r["count"] == 1
        for r in context.request.get(root).json()["funnel"]
    )
    capture(page, "signup-funnel")
    page.goto("/workspace/customers?business=" + OTHER + "&view=signup")
    playwright.expect(
        page.get_by_role("heading", name="Este negocio no está disponible", exact=True)
    ).to_be_visible()


def test_public_entry_owner_link_and_missing_business_are_clear(site):
    page, context, url, app, *_ = site
    r = page.goto("/?business_id=")
    assert r.status == 400
    playwright.expect(
        page.get_by_role("heading", name="No pudimos abrir este negocio", exact=True)
    ).to_be_visible()
    capture(page, "missing-public-business")
    page.goto("/?business_id=" + BUSINESS)
    owner = page.get_by_role("link", name="Acceso del restaurante", exact=True)
    playwright.expect(owner).to_have_attribute("href", "/workspace/sales?business=" + BUSINESS)
    owner.click()
    playwright.expect(page.get_by_role("button", name="Entrar", exact=True)).to_be_visible()
    page.get_by_label("Usuario", exact=True).fill("campaign.manager")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    playwright.expect(page.get_by_role("heading", name="Ventas", exact=True)).to_be_visible()
    assert "business=" + BUSINESS in page.url


def test_actual_legacy_admin_anchors_survive_login_and_direct_access(site):
    page, context, url, app, *_ = site
    signin(page, f"/admin?business_id={BUSINESS}#dailySection")
    playwright.expect(
        page.get_by_role("heading", name="Resumen diario", exact=True)
    ).to_be_visible()
    assert "business=" + BUSINESS in page.url and not page.url.endswith("#dailySection")
    for anchor, path, heading in [
        ("availability", "/workspace/settings", "Ajustes"),
        ("financialSection", "/workspace/sales", "Revisión de pagos"),
        ("orderQueue", "/workspace/sales", "Ventas"),
    ]:
        page.goto(f"/admin?business_id={BUSINESS}#" + anchor)
        page.wait_for_url(re.compile(re.escape(path) + r"\?"))
        assert not page.url.endswith("#" + anchor)
        playwright.expect(page.locator("main h1")).to_contain_text(heading)
