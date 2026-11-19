"""Real HTTP/Chromium owner lifecycle, without contacting a real provider."""

import json
import os
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from cryptography.fernet import Fernet
from test_browser_security import browser, playwright
from world_model.restaurant_commerce.connections_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import PASSWORD


@pytest.fixture
def live(tmp_path, browser):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = "http://127.0.0.1:" + str(sock.getsockname()[1])
    app = app_for_demo("sqlite:///" + str(tmp_path / "connections.db"), Fernet.generate_key())
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started
    context = browser.new_context(base_url=url, viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    external = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(url) else None)
    try:
        yield page, context, url, errors, external
    finally:
        context.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def signin(page):
    page.goto("/connections")
    page.get_by_label("Usuario", exact=True).fill("campaign.manager")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    playwright.expect(page.locator(".connection-state")).to_have_text("Sin conexión")


def confirm(page):
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(dialog).to_have_count(0)


def test_connect_select_sync_disconnect_and_reconnect(live):
    page, context, url, errors, external = live
    out = Path(
        os.environ.get("CONNECTIONS_BROWSER_EVIDENCE", "/tmp/101-connections-evidence/browser")
    )
    out.mkdir(parents=True, exist_ok=True)
    signin(page)
    page.get_by_role("button", name="Conectar Google", exact=True).click()
    page.locator("#deny").click()
    playwright.expect(page.locator(".connection-state")).to_have_text("Autorización cancelada")
    page.get_by_role("button", name="Volver a conectar Google", exact=True).click()
    page.locator("#allow").click()
    select = page.get_by_label("Recurso del negocio", exact=True)
    playwright.expect(select.locator("option")).to_have_count(3, timeout=20000)
    select.select_option(index=1)
    page.get_by_role("button", name="Confirmar recurso", exact=True).click()
    confirm(page)
    playwright.expect(page.locator(".connection-state")).to_have_text("Conectado", timeout=20000)
    playwright.expect(page.locator(".connection-snapshot")).to_contain_text(
        "No describe una experiencia real"
    )
    from test_workspace_completion_browser import capture
    capture(page,'google-synced')
    page.reload()
    playwright.expect(page.locator(".connection-table tbody tr")).to_have_count(3)
    page.get_by_role("button", name="Actualizar datos", exact=True).click()
    playwright.expect(page.get_by_role("status").filter(has_text="Espera")).to_have_count(1)
    page.get_by_role("button", name="Desconectar Google", exact=True).click()
    confirm(page)
    playwright.expect(page.locator(".connection-state")).to_have_text("Sin conexión", timeout=20000)
    assert not page.locator(".connection-snapshot").count()
    page.get_by_role("button", name="Conectar Google", exact=True).click()
    page.locator("#allow").click()
    playwright.expect(select.locator("option")).to_have_count(3, timeout=20000)
    select.select_option(index=2)
    page.get_by_role("button", name="Confirmar recurso", exact=True).click()
    confirm(page)
    playwright.expect(
        page.get_by_role("heading", name="Segunda ubicación ficticia", exact=True)
    ).to_be_visible(timeout=20000)
    page.get_by_role("button", name="Cerrar sesión", exact=True).click()
    playwright.expect(page.get_by_label("Usuario", exact=True)).to_be_visible()
    assert errors == [] and external == []


def test_cross_site_google_return_preserves_strict_staff_cookie(live):
    from html import escape
    from urllib.parse import urlencode, parse_qs, urlsplit

    page, context, url, errors, external = live
    signin(page)
    me = context.request.get("/api/staff/me").json()
    grant = context.request.post(
        "/api/operator/restaurants/honorato-campaign-test/connections/google/authorize",
        headers={"X-101-CSRF": me["csrf"]},
    ).json()
    state = parse_qs(urlsplit(grant["url"]).query)["state"][0]
    callback = (
        url
        + "/connections/google/callback?"
        + urlencode({"state": state, "code": "synthetic-owner-grant"})
    )
    context.route(
        "https://google.example.test/**",
        lambda route: route.fulfill(
            content_type="text/html",
            body='<a id="return" href="' + escape(callback) + '">Return</a>',
        ),
    )
    callbacks = []
    page.on(
        "request",
        lambda r: (
            callbacks.append(r.all_headers()) if "/connections/google/callback?" in r.url else None
        ),
    )
    page.goto("https://google.example.test/consent")
    page.locator("#return").click()
    playwright.expect(
        page.get_by_label("Recurso del negocio", exact=True).locator("option")
    ).to_have_count(3, timeout=20000)
    assert callbacks and "commerce_staff=" not in callbacks[0].get("cookie", "")
    assert (
        "business=honorato-campaign-test" in page.url
        and "code=" not in page.url
        and "state=" not in page.url
    )
    assert errors == [] and external == ["https://google.example.test/consent"]
