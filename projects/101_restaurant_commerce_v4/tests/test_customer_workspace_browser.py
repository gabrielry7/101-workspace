"""Production-built workspace over HTTP: real API, QR/signup and navigation."""

import json
import re
import os
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from test_browser_security import browser, playwright  # noqa: F401 - shared browser fixture
from world_model.restaurant_commerce.customer_workspace_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD
from world_model.restaurant_commerce.models import StaffMembership, StaffAccount
from sqlalchemy import select
from world_model.restaurant_commerce.staff import provision

OUT = Path(
    os.environ.get("CUSTOMER_BROWSER_EVIDENCE", "/tmp/101-customer-evidence/browser")
)


@pytest.fixture
def site(tmp_path, browser):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = "http://127.0.0.1:" + str(sock.getsockname()[1])
    app = app_for_demo("sqlite:///" + str(tmp_path / "customers.db"), url, 80)
    with app.state.session_factory() as s:
        provision(
            s, "multi.owner", PASSWORD, BUSINESS, "manager", actor="synthetic-fixture"
        )
        account = s.scalar(
            select(StaffAccount).where(StaffAccount.username == "multi.owner")
        )
        s.add(StaffMembership(account_id=account.id, business_id=OTHER, role="manager"))
        s.commit()
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, daemon=True
    )
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started
    context = browser.new_context(
        base_url=url, viewport={"width": 1440, "height": 1000}
    )
    page = context.new_page()
    errors = []
    external = []
    csp = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "request",
        lambda r: (
            external.append(r.url)
            if not r.url.startswith(url) and not r.url.startswith("data:")
            else None
        ),
    )
    page.on(
        "console",
        lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        yield page, context, url, app, errors, external, csp
    finally:
        context.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert errors == [] and external == [] and csp == []


def login(page, user="campaign.manager"):
    page.goto("/workspace/customers")
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    playwright.expect(page.locator("tbody tr")).to_have_count(25)
    page.evaluate("document.fonts.ready")


def test_directory_detail_back_deep_link_and_qr(site):
    page, context, url, app, *_ = site
    login(page)
    assert page.locator("#business").count() == 0
    page.screenshot(path=str(OUT / "customers-desktop.png"), full_page=True)
    scroll = page.get_by_test_id("customer-list")
    scroll.evaluate("(e)=>e.scrollTop=600")
    link = page.locator(".customer-link").filter(has_text="Daniel Martínez").first
    link.scroll_into_view_if_needed()
    before = scroll.evaluate("(e)=>e.scrollTop")
    link.click()
    playwright.expect(page.locator(".detail h2")).to_have_text("Daniel Martínez")
    page.go_back()
    playwright.expect(page.locator(".detail")).to_have_count(0)
    assert abs(scroll.evaluate("(e)=>e.scrollTop") - before) < 2
    assert page.evaluate('document.activeElement.classList.contains("customer-link")')
    search = page.get_by_label("Buscar clientes")
    search.fill("Mateo")
    playwright.expect(page.locator("tbody tr")).to_have_count(4)
    page.locator(".customer-link").filter(has_text="Mateo Restrepo").first.click()
    playwright.expect(page.locator(".money")).to_contain_text(
        re.compile(r"\$\s*19\.900")
    )
    playwright.expect(page.locator(".money")).to_contain_text(
        re.compile(r"\$\s*5\.000")
    )
    page.screenshot(path=str(OUT / "customer-detail-desktop.png"), full_page=True)
    deep = page.url
    page.reload()
    playwright.expect(page.locator(".money")).to_contain_text(
        re.compile(r"\$\s*19\.900")
    )
    page.get_by_label("Cerrar detalle").click()
    playwright.expect(search).to_have_value("Mateo")
    page.get_by_role("button", name="Invitar clientes").click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_be_visible()
    page.wait_for_function(
        "() => {const img=document.querySelector('[role=dialog] img'); return img && img.complete && img.naturalWidth>100;}"
    )
    page.screenshot(path=str(OUT / "signup-qr-desktop.png"), full_page=True)
    with page.expect_download() as download:
        dialog.get_by_role("link", name="Descargar PNG").click()
    download.value.save_as(OUT / "signup.png")
    assert (OUT / "signup.png").read_bytes().startswith(b"\x89PNG")
    with page.expect_download() as download:
        dialog.get_by_role("link", name="SVG", exact=False).click()
    download.value.save_as(OUT / "signup.svg")
    signup = dialog.get_by_label("Enlace de registro").input_value()
    page.keyboard.press("Escape")
    playwright.expect(dialog).to_have_count(0)
    page.goto(signup)
    page.locator("#chooseEmail").click()
    page.locator("#email").fill("new-person@example.test")
    page.locator("#sendCode").click()
    playwright.expect(page.locator("#demoCode")).to_contain_text("Código de prueba")
    code = re.search(r"\b\d{6}\b", page.locator("#demoCode").inner_text()).group()
    page.locator("#code").fill(code)
    page.locator("#verifyCode").click()
    playwright.expect(page.locator("#welcome")).to_have_text("Ya eres parte.")
    page.goto("/workspace/customers?q=new-person")
    playwright.expect(page.locator("tbody tr")).to_have_count(1)
    playwright.expect(page.locator("tbody")).to_contain_text("Verificado")
    (OUT / "journey.json").write_text(
        json.dumps(
            {
                "deep_link": deep,
                "back_scroll_preserved": True,
                "qr_downloads": ["PNG", "SVG"],
                "email_signup_in_canonical_directory": True,
                "real_messages": 0,
            },
            indent=2,
        )
    )


def test_mobile_keyboard_empty_error_and_focus(site):
    page, *_ = site
    page.set_viewport_size({"width": 390, "height": 844})
    login(page)
    page.screenshot(path=str(OUT / "customers-mobile.png"), full_page=True)
    page.get_by_label("Abrir navegación").click()
    playwright.expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    playwright.expect(page.get_by_role("dialog")).to_have_count(0)
    search = page.get_by_label("Buscar clientes")
    search.fill("not-present-anywhere")
    playwright.expect(
        page.get_by_role("heading", name="Nadie por aquí con ese nombre")
    ).to_be_visible()
    page.screenshot(path=str(OUT / "empty-mobile.png"), full_page=True)
    page.get_by_role("button", name="Limpiar búsqueda", exact=True).last.click()
    playwright.expect(page.locator("tbody tr")).to_have_count(25)
    page.locator(".customer-link").first.focus()
    page.keyboard.press("Enter")
    playwright.expect(page.locator(".detail h2")).to_be_focused()
    assert page.get_by_test_id("customer-list").is_hidden()
    page.screenshot(path=str(OUT / "customer-detail-mobile.png"), full_page=True)
    page.get_by_role("button", name="Directorio", exact=True).click()
    page.get_by_role("button", name="Invitar clientes").click()
    page.screenshot(path=str(OUT / "signup-qr-mobile.png"), full_page=True)
    page.keyboard.press("Escape")
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.route(
        "**/api/operator/restaurants/*/customers?*",
        lambda route: route.fulfill(status=503, json={"detail": "synthetic outage"}),
    )
    page.reload()
    playwright.expect(
        page.get_by_role("heading", name="No se pudo cargar")
    ).to_be_visible()
    page.screenshot(path=str(OUT / "error-desktop.png"), full_page=True)
    page.unroute("**/api/operator/restaurants/*/customers?*")
    page.get_by_role("button", name="Reintentar").click()
    playwright.expect(page.locator("tbody tr")).to_have_count(25)


def test_business_switch_stale_response_and_legacy_context(site):
    page, context, url, app, *_ = site
    login(page, "multi.owner")
    select = page.get_by_label("Negocio", exact=True)
    select.select_option(OTHER)
    playwright.expect(page.locator("tbody tr")).to_have_count(7)
    assert "Lucía Fernández" not in page.locator("tbody").inner_text()
    select.select_option(BUSINESS)
    playwright.expect(page.locator("tbody tr")).to_have_count(25)
    held = []
    old_data = context.request.get(
        url + "/api/operator/restaurants/" + BUSINESS + "/customers?q=Lucía"
    ).json()
    page.route("**/customers?q=Luc*", lambda route: held.append(route))
    page.get_by_label("Buscar clientes").fill("Lucía")
    page.wait_for_timeout(300)  # Let the debounced request remain pending.
    assert held
    select.select_option(OTHER)
    playwright.expect(page.locator("tbody tr")).to_have_count(7)
    playwright.expect(page.get_by_label("Buscar clientes")).to_have_value("")
    held[0].fulfill(status=200, json=old_data)
    page.wait_for_timeout(50)
    assert "Lucía Fernández" not in page.locator("tbody").inner_text()
    page.get_by_role("link", name="Ventas", exact=False).click()
    playwright.expect(page.locator("#business")).to_have_value(OTHER)
    page.goto("/workspace/customers?business=not-authorized")
    playwright.expect(
        page.get_by_role("heading", name="Este negocio no está disponible")
    ).to_be_visible()
