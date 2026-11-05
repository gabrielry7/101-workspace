"""Built UI, real HTTP and canonical state: operations, navigation and lost replies."""

import json
import os
from pathlib import Path
import pytest
import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright  # noqa: F401
from world_model.restaurant_commerce.sales_workspace_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS
from world_model.restaurant_commerce.models import Order

OUT = Path(os.environ.get("SALES_BROWSER_EVIDENCE", "/tmp/101-sales-evidence/browser"))


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    monkeypatch.setattr(
        customers, "app_for_demo", lambda db, url, _count: app_for_demo(db, url)
    )
    yield from customers.site.__wrapped__(tmp_path, browser)


def enter(page, user="campaign.manager"):
    customers.login(page, user)
    page.get_by_role("link", name="Ventas", exact=True).click()
    playwright.expect(page.locator(".sale-link")).to_have_count(25)


def open_order(page, code):
    page.get_by_label("Buscar pedido por código").fill(code)
    playwright.expect(page.locator(".sale-link")).to_have_count(1)
    playwright.expect(page.locator(".sale-link")).to_contain_text(code)
    page.locator(".sale-link").click()
    playwright.expect(page.locator(".sale-detail h2")).to_contain_text(code)


def test_operations_cash_cancel_and_context(site):
    page, _, _, app, *_ = site
    enter(page)
    OUT.mkdir(parents=True, exist_ok=True)
    open_order(page, "DEMO-201")
    for name, next_name in [
        ("Aceptar pedido", "Empezar preparación"),
        ("Empezar preparación", "Marcar listo"),
        ("Marcar listo", "Confirmar entrega"),
    ]:
        page.get_by_role("button", name=name, exact=True).click()
        playwright.expect(
            page.get_by_role("button", name=next_name, exact=True)
        ).to_be_visible()
        assert page.get_by_role("dialog").count() == 0
    page.get_by_role("button", name="Confirmar entrega", exact=True).click()
    playwright.expect(page.locator(".sale-detail .order-badges")).to_contain_text(
        "Entregado"
    )
    page.get_by_label("Cerrar pedido").click()
    page.get_by_role("button", name="Todos", exact=True).click()
    open_order(page, "DEMO-209")
    page.get_by_role("button", name="Confirmar cobro y entrega").click()
    dialog = page.get_by_role("dialog")
    playwright.expect(
        dialog.get_by_role("button", name="Confirmar", exact=True)
    ).to_be_disabled()
    page.screenshot(path=str(OUT / "cash-confirmation.png"), full_page=True)
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(page.locator(".sale-detail .order-badges")).to_contain_text(
        "Pagado"
    )
    playwright.expect(page.locator(".sale-detail .money")).to_contain_text("EFECTIVO")
    with app.state.session_factory() as s:
        assert s.get(Order, "workspace-sale-008").payment_status == "paid"
        assert s.get(Order, "workspace-sale-000").status == "completed"
    page.get_by_label("Cerrar pedido").click()
    open_order(page, "DEMO-205")
    page.get_by_role("button", name="Cancelar pedido", exact=True).click()
    playwright.expect(
        dialog.get_by_role("button", name="Confirmar", exact=True)
    ).to_be_disabled()
    dialog.get_by_label("Motivo de cancelación").fill(
        "Cancelación ficticia solicitada."
    )
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(page.locator(".sale-detail .order-badges")).to_contain_text(
        "Cancelado"
    )
    page.get_by_label("Cerrar pedido").click()
    playwright.expect(page.get_by_label("Buscar pedido por código")).to_have_value(
        "DEMO-205"
    )
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.get_by_label("Buscar clientes").fill("Mateo")
    playwright.expect(page.locator(".customer-link")).to_have_count(4)
    page.get_by_role("link", name="Ventas", exact=True).click()
    playwright.expect(page.get_by_label("Buscar pedido por código")).to_have_value(
        "DEMO-205"
    )
    page.get_by_role("link", name="Clientes", exact=True).click()
    playwright.expect(page.get_by_label("Buscar clientes")).to_have_value("Mateo")


def test_stale_version_lost_reply_and_no_blind_retry(site):
    page, context, url, app, *_ = site
    enter(page)
    open_order(page, "DEMO-201")
    with app.state.session_factory() as s:
        o = s.get(Order, "workspace-sale-000")
        o.version += 1
        s.commit()
    page.get_by_role("button", name="Aceptar pedido", exact=True).click()
    playwright.expect(page.get_by_role("status")).to_contain_text("El pedido cambió")
    with app.state.session_factory() as s:
        assert s.get(Order, "workspace-sale-000").status == "placed"
    calls = []

    def lost(route):
        if route.request.method != "PATCH":
            return route.continue_()
        calls.append(route.request.post_data_json)
        response = route.fetch()
        assert response.ok
        route.abort("failed")

    page.route("**/api/operator/orders/*", lost)
    page.get_by_role("button", name="Aceptar pedido", exact=True).click()
    playwright.expect(
        page.get_by_role("button", name="Comprobar estado")
    ).to_be_visible()
    assert len(calls) == 1
    assert page.get_by_role("button", name="Aceptar pedido", exact=True).count() == 0
    with app.state.session_factory() as s:
        assert s.get(Order, "workspace-sale-000").status == "accepted"
    page.get_by_role("button", name="Comprobar estado").click()
    playwright.expect(
        page.get_by_role("button", name="Empezar preparación")
    ).to_be_visible()
    assert len(calls) == 1
    page.screenshot(path=str(OUT / "reconciled-response.png"), full_page=True)


def test_readonly_layout_accessibility_and_editable_roles(site):
    page, context, url, app, *_ = site
    enter(page, "sales.viewer")
    open_order(page, "DEMO-201")
    playwright.expect(page.locator(".action-section")).to_contain_text(
        "Tu acceso permite consultar"
    )
    assert page.locator(".order-actions button").count() == 0
    page.get_by_label("Cerrar pedido").click()
    page.get_by_label("Limpiar búsqueda de pedidos").click()
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
    axe = (
        Path(__file__).resolve().parents[1]
        / "frontend/node_modules/axe-core/axe.min.js"
    ).read_text()
    measurements = {}
    violations = {}
    for width in [1920, 1440, 768, 390, 320]:
        page.set_viewport_size({"width": width, "height": 944 if width > 700 else 844})
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        if width < 700:
            playwright.expect(page.locator(".mobile-payment").first).to_be_visible()
        measurements[str(width)] = page.locator(".sale-link strong").first.evaluate(
            "(e)=>({font:getComputedStyle(e).fontSize,color:getComputedStyle(e).color,width:e.getBoundingClientRect().width})"
        )
        page.screenshot(path=str(OUT / f"sales-{width}.png"), full_page=True)
        page.evaluate(axe)
        violations[str(width)] = page.evaluate(
            "async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))"
        )
    page.set_viewport_size({"width": 1440, "height": 1000})
    before = context.request.get(
        url + f"/api/operator/restaurants/{BUSINESS}/sales"
    ).json()
    page.evaluate("document.documentElement.style.setProperty('--text-body','18px')")
    assert (
        page.locator("nav > a").first.evaluate("(e)=>getComputedStyle(e).fontSize")
        == "18px"
    )
    assert (
        context.request.get(url + f"/api/operator/restaurants/{BUSINESS}/sales").json()
        == before
    )
    page.evaluate("document.documentElement.style.removeProperty('--text-body')")
    (OUT / "measurements.json").write_text(json.dumps(measurements, indent=2))
    (OUT / "axe-sales.json").write_text(json.dumps(violations, indent=2))
    assert not any(violations.values()), violations


def test_pagination_back_scroll_deep_link_and_business_change(site):
    from world_model.restaurant_commerce.campaign_demo import OTHER

    page, context, url, app, *_ = site
    enter(page, "multi.owner")
    page.get_by_role("button", name="Todos", exact=True).click()
    page.get_by_label("Pedidos siguientes").click()
    playwright.expect(page.locator(".sale-link")).to_have_count(6)
    page.get_by_label("Pedidos anteriores").click()
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
    scroll = page.get_by_test_id("sales-list")
    scroll.evaluate("(e)=>e.scrollTop=600")
    link = page.locator(".sale-link").filter(has_text="DEMO-209")
    link.scroll_into_view_if_needed()
    before = scroll.evaluate("(e)=>e.scrollTop")
    link.click()
    playwright.expect(page.locator(".sale-detail h2")).to_contain_text("DEMO-209")
    page.go_back()
    playwright.expect(page.locator(".sale-detail")).to_have_count(0)
    assert abs(scroll.evaluate("(e)=>e.scrollTop") - before) < 2
    assert page.evaluate('document.activeElement.classList.contains("sale-link")')
    link.click()
    page.reload()
    playwright.expect(page.locator(".sale-detail h2")).to_contain_text("DEMO-209")
    page.locator("#business").select_option(OTHER)
    playwright.expect(page.locator(".sale-link")).to_have_count(1)
    assert "DEMO-" not in page.locator("tbody").inner_text()
    assert page.locator(".sale-detail").count() == 0
    page.locator(".sale-link").click()
    playwright.expect(page.locator(".sale-detail h2")).to_contain_text("OTHER-01")
    page.get_by_label("Cerrar pedido").click()
    page.locator("#business").select_option(BUSINESS)
    playwright.expect(page.locator(".sale-link")).to_have_count(25)
