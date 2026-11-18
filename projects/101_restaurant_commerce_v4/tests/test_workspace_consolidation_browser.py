"""Real built shared entry and reservation workflows; no external actions."""

# ruff: noqa: F811 -- pytest imports fixtures by name.

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright  # noqa: F401
from test_workspace_consolidation import seed_reservations
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD
from world_model.restaurant_commerce.models import Reservation
from world_model.restaurant_commerce.sales_workspace_demo import app_for_demo

OUT = Path(os.environ.get("CONSOLIDATION_EVIDENCE", "/tmp/101-consolidation-browser"))


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    def app(db, url, _count):
        value = app_for_demo(db, url)
        seed_reservations(value)
        return value

    monkeypatch.setattr(customers, "app_for_demo", app)
    yield from customers.site.__wrapped__(tmp_path, browser)


def signin(page, user="campaign.manager"):
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()


def test_bookmark_login_reservation_revision_and_lost_reply(site):
    page, context, url, app, *_ = site
    OUT.mkdir(parents=True, exist_ok=True)
    page.goto(
        f"/workspace/sales?business={BUSINESS}&view=reservations&reservation=workspace-reservation-0"
    )
    playwright.expect(page).to_have_url(re.compile("/workspace/login\\?"))
    page.screenshot(path=str(OUT / "shared-login.png"), full_page=True)
    signin(page)
    playwright.expect(page.get_by_role("heading", name="Reserva #RSV-000")).to_be_visible()
    page.get_by_role("button", name="Confirmar reserva", exact=True).click()
    playwright.expect(page.locator(".sale-detail .badge")).to_have_text("Confirmada")
    playwright.expect(
        page.get_by_role("button", name="Registrar llegada", exact=True)
    ).to_be_visible()
    with app.state.session_factory() as s:
        assert s.get(Reservation, "workspace-reservation-0").version == 2
        r = s.get(Reservation, "workspace-reservation-0")
        r.version += 1
        s.commit()
    page.get_by_role("button", name="Registrar llegada", exact=True).click()
    playwright.expect(page.locator(".sale-detail p[role=status]")).to_contain_text(
        "La reserva cambió"
    )
    calls = []

    def lost(route):
        calls.append(route.request.post_data_json)
        response = route.fetch()
        assert response.ok
        route.abort("failed")

    page.route("**/api/operator/reservations/*", lost)
    page.get_by_role("button", name="Registrar llegada", exact=True).click()
    playwright.expect(
        page.get_by_role("button", name="Comprobar estado", exact=True)
    ).to_be_visible()
    assert len(calls) == 1
    page.get_by_role("button", name="Comprobar estado", exact=True).click()
    playwright.expect(page.locator(".sale-detail .badge")).to_have_text("En el local")
    assert len(calls) == 1
    page.unroute("**/api/operator/reservations/*", lost)
    page.get_by_role("button", name="Cerrar reserva").click()
    playwright.expect(page.locator(".reservation-row")).to_have_count(25)
    measures = {}
    for width in [1440, 390, 320]:
        page.set_viewport_size({"width": width, "height": 900})
        page.screenshot(path=str(OUT / f"reservations-{width}.png"), full_page=True)
        measures[str(width)] = (
            page.evaluate("""() => ({overflow:document.documentElement.scrollWidth-innerWidth,
          font:getComputedStyle(document.body).fontFamily,
          smallButtons:[...document.querySelectorAll(
            '.reservation-workspace button, .sales-views button')]
          .filter(b=>b.getBoundingClientRect().width && b.getBoundingClientRect().height<43)
          .map(b=>b.textContent)})""")
        )
        assert measures[str(width)]["overflow"] == 0
        assert not measures[str(width)]["smallButtons"]
    (OUT / "measurements.json").write_text(json.dumps(measures, indent=2))
    page.evaluate(
        (
            Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
        ).read_text()
    )
    violations = page.evaluate("""async () => (await axe.run('.reservation-workspace', {
      runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21aa']}
    })).violations.map(v => ({id:v.id, targets:v.nodes.map(n=>n.target)}))""")
    (OUT / "accessibility.json").write_text(json.dumps(violations, indent=2))
    assert not violations
    page.locator(".reservation-row").filter(has_text="RSV-001").click()
    page.get_by_role("button", name="Cancelar reserva", exact=True).click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog.get_by_role("button", name="Confirmar", exact=True)).to_be_disabled()
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(page.locator(".sale-detail .badge")).to_have_text("Cancelada")
    page.screenshot(path=str(OUT / "reservation-phone-detail.png"), full_page=True)


def test_business_selection_legacy_access_and_cross_tab_logout(site):
    page, context, url, app, *_ = site
    page.goto("/admin")
    signin(page, "multi.owner")
    playwright.expect(
        page.get_by_role("heading", name="Elige tu negocio", exact=True)
    ).to_be_visible()
    assert "/workspace/login" in page.url
    # Select from the authorized options, never whichever membership sorts first.
    page.locator(".entry-businesses button").first.click()
    playwright.expect(page).to_have_url(re.compile("/admin\\?business_id="))
    legacy_business = parse_qs(urlsplit(page.url).query)["business_id"][0]
    assert legacy_business in {BUSINESS, OTHER}
    page.goto(f"/workspace/sales?business={BUSINESS}")
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
    other = context.new_page()
    other.goto(f"/workspace/sales?business={BUSINESS}")
    playwright.expect(other.locator(".sale-link")).to_have_count(25)
    page.get_by_role("button", name="Cerrar sesión", exact=True).click()
    playwright.expect(other.get_by_label("Usuario", exact=True)).to_be_visible()
    assert other.locator(".sale-link").count() == 0
    other.close()
    signin(page, "multi.owner")
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
    isolated = context.browser.new_context(base_url=url)
    try:
        assert (
            isolated.request.post(
                "/api/staff/login",
                data={"username": "multi.owner", "password": PASSWORD},
                headers={"X-101-Login": "1"},
            ).status
            == 200
        )
        assert isolated.request.get("/api/staff/me").status == 200
        page.get_by_label("Opciones de sesión", exact=True).click()
        page.get_by_role("button", name="Cerrar todas mis sesiones", exact=True).click()
        playwright.expect(page.get_by_label("Usuario", exact=True)).to_be_visible()
        assert isolated.request.get("/api/staff/me").status == 401
    finally:
        isolated.close()


def test_native_payment_filter_name_search_and_manual_contact(site):
    page, context, url, app, *_ = site
    page.goto(f"/workspace/sales?business={BUSINESS}")
    signin(page)
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
    with page.expect_response(
        lambda r: "/sales?" in r.url and "payment_status=unpaid" in r.url and r.status == 200
    ) as response:
        page.get_by_label("Estado del pago", exact=True).select_option("unpaid")
    expected = response.value.json()["items"]
    playwright.expect(page.locator(".sale-link")).to_have_count(len(expected))
    assert all(
        "Sin pagar" in text
        for text in page.locator(".sales-table tbody td:last-child").all_text_contents()
    )
    page.get_by_label("Estado del pago", exact=True).select_option("paid")
    with page.expect_response(
        lambda r: "/sales?" in r.url and "q=Santiago" in r.url and r.status == 200
    ):
        page.get_by_label("Buscar pedido por código o cliente", exact=True).fill("Santiago Mora")
    playwright.expect(page.locator(".sale-link").first).to_contain_text("Santiago Mora")
    page.locator(".sale-link").first.click()
    page.get_by_role("button", name="Preparar mensaje de WhatsApp", exact=True).click()
    handoff = page.get_by_role("link", name="Abrir WhatsApp", exact=True)
    playwright.expect(handoff).to_be_visible()
    assert handoff.get_attribute("href").startswith("https://wa.me/")
    # Preparing the handoff never navigates/sends or creates a provider request.
    assert page.url.startswith(url + "/workspace/sales")
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / "order-contact-desktop.png"), full_page=True)
