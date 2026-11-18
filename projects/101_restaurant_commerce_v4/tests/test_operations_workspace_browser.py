"""Built native U04–U06 over HTTP; synthetic providers, no external writes."""

# ruff: noqa: F811 -- pytest fixture imports
import json
import os
import re
from pathlib import Path

import httpx
import pytest
import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright  # noqa: F401
from test_operations_workspace import BID, PASSWORD, ROOT, app_fixture
from test_wompi_financial import factory as factory  # noqa: F401
from test_wompi_financial_browser import live_finance as live_finance  # noqa: F401
from world_model.restaurant_commerce.models import Order

OUT = Path(os.environ.get("OPERATIONS_EVIDENCE", "/tmp/101-operations-browser"))


@pytest.fixture(autouse=True)
def forbid_real_provider_network(monkeypatch):
    # The reused fixture's "live" means local HTTP app, not live Wompi access.
    # prepared()/setup_order() use only httpx.MockTransport and synthetic keys.
    # Fail rather than ever falling through to an ordinary HTTP transport.
    def forbidden(*args, **kwargs):
        pytest.fail("Real provider HTTP is forbidden in workspace fixture checks")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    monkeypatch.setattr(customers, "app_for_demo", lambda db, url, count: app_fixture(db))
    OUT.mkdir(parents=True, exist_ok=True)
    yield from customers.site.__wrapped__(tmp_path, browser)


def signin(page, path, user="ops.manager"):
    page.goto(path)
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.evaluate("document.fonts.ready")


def confirm(page):
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(dialog).to_have_count(0)


def inspect(page, name):
    observations = {}
    for width in [1440, 390, 320]:
        page.set_viewport_size({"width": width, "height": 1000})
        page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
        measures = page.evaluate("""() => ({
          overflow:document.documentElement.scrollWidth-innerWidth,
          font:getComputedStyle(document.body).fontFamily,
          small:[...document.querySelectorAll(
            '.operations-page button, .operation-detail button,'+
            '.sales-views button, .daily-finance button')]
             .filter(b=>b.getBoundingClientRect().width &&
              b.getBoundingClientRect().height < 43).map(b=>b.textContent)})""")
        assert measures["overflow"] == 0
        assert "Inter" in measures["font"] and not measures["small"]
        observations[str(width)] = measures
    page.evaluate(
        (
            Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
        ).read_text()
    )
    violations = page.evaluate("""async () => (await axe.run(document.querySelector('main'),
      {runOnly:{type:'tag',values:['wcag2a','wcag2aa']}})).violations""")
    observations["a11y"] = violations
    (OUT / f"{name}.json").write_text(json.dumps(observations, indent=2))
    assert violations == []
    page.set_viewport_size({"width": 1440, "height": 1000})


def test_delivery_lost_response_manual_completion_and_cancellation(site):
    page, context, url, app, *_ = site
    ids = app.state.test_ids
    signin(page, f"/workspace/sales?business={BID}&view=deliveries&delivery={ids['delivery']}")
    detail = page.get_by_role("complementary", name="Detalle de entrega")
    playwright.expect(detail.get_by_role("heading", name=re.compile("Entrega #"))).to_be_visible()
    inspect(page, "delivery-before")
    calls = []

    def lost(route):
        calls.append(route.request.url)
        assert route.fetch().ok
        route.abort("failed")

    page.route("**/delivery/dispatch", lost)
    detail.get_by_role("button", name="Solicitar transportador", exact=True).click()
    confirm(page)
    playwright.expect(
        detail.get_by_role("button", name="Comprobar estado", exact=True)
    ).to_be_visible()
    playwright.expect(
        detail.get_by_role("button", name="Solicitar transportador", exact=True)
    ).to_be_disabled()
    detail.get_by_role("button", name="Comprobar estado", exact=True).click()
    playwright.expect(detail.get_by_role("button", name="Simular recogida")).to_be_enabled()
    assert len(calls) == 1 and app.state.test_courier.dispatches == 1
    page.unroute("**/delivery/dispatch", lost)
    for action in ["Simular recogida", "Simular entrega"]:
        detail.get_by_role("button", name=action, exact=True).click()
        confirm(page)
    playwright.expect(detail.locator(".badge")).to_have_text("Entregada")
    with app.state.session_factory() as session:
        assert session.get(Order, ids["delivery_order"]).status == "completed"
    assert not detail.locator('a[href*="/demo/delivery/"]').count()
    inspect(page, "delivery-after")


def test_settings_stock_conflict_unsaved_rows_and_readonly(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/settings?business={BID}")
    form = page.get_by_role("form", name="Disponibilidad del negocio")
    form.get_by_label("Hora de cierre", exact=True).fill("24:00")
    form.get_by_label("Motivo del cambio").fill("Synthetic midnight roundtrip")
    form.get_by_role("button", name="Guardar disponibilidad").click()
    playwright.expect(page.get_by_text("Disponibilidad guardada.", exact=False)).to_be_visible()
    playwright.expect(form.get_by_label("Hora de cierre", exact=True)).to_have_value("24:00")
    me = context.request.get("/api/staff/me").json()
    data = context.request.get(ROOT + "/settings").json()
    body = {
        **data["policy"],
        "expected_version": data["version"],
        "capacity": 12,
        "reason": "Synthetic concurrent edit",
    }
    assert context.request.put(ROOT + "/settings", data=body, headers={"X-101-CSRF": me["csrf"]}).ok
    form.get_by_label("Motivo del cambio").fill("Synthetic stale edit")
    form.get_by_role("button", name="Guardar disponibilidad").click()
    playwright.expect(form.locator("[role=status]")).to_contain_text(
        re.compile("cambi|changed|versi", re.I)
    )
    form.get_by_role("button", name="Descartar cambios y actualizar").click()
    playwright.expect(form.get_by_label("Pedidos por horario")).to_have_value("12")
    inspect(page, "settings")
    page.get_by_role("button", name="Existencias", exact=True).click()
    forms = page.locator(".stock-form")
    playwright.expect(forms.first).to_be_visible()
    first, second = forms.nth(0), forms.nth(1)
    second.locator('input[name="remaining"]').fill("17")
    first.locator('input[name="remaining"]').fill("0")
    first.locator('input[name="reason"]').fill("Synthetic sold out")
    first.get_by_role("button", name="Guardar existencias").click()
    playwright.expect(page.get_by_text("Existencias guardadas para", exact=False)).to_be_visible()
    playwright.expect(first.locator('input[name="remaining"]')).to_have_value("0")
    playwright.expect(second.locator('input[name="remaining"]')).to_have_value("17")
    inspect(page, "stock")
    context.request.post("/api/staff/logout", headers={"X-101-CSRF": me["csrf"]})
    signin(page, f"/workspace/settings?business={BID}", "ops.viewer")
    playwright.expect(
        page.get_by_text("Tu acceso permite consultar estos ajustes.", exact=False)
    ).to_be_visible()
    assert page.get_by_role("button", name="Guardar disponibilidad").count() == 0


def test_financial_lookup_resolve_refund_lost_response_and_allocation(site):
    page, context, url, app, *_ = site
    ids = app.state.test_ids
    path = f"/workspace/sales?business={BID}&view=reviews&review_order={ids['finance_order']}"
    signin(page, path)
    detail = page.get_by_role("complementary", name="Detalle financiero")
    playwright.expect(detail.get_by_role("heading", name="Acciones financieras")).to_be_visible()
    detail.get_by_label("Motivo de la acción financiera").fill("Synthetic payment verification")
    detail.get_by_role("button", name="Consultar pago con el proveedor", exact=True).click()
    confirm(page)
    evidence = detail.get_by_role("button", name=re.compile("Revisar evidencia")).first
    playwright.expect(evidence).to_be_visible()
    queries = app.state.test_finance.lookups
    detail.get_by_role("button", name="Actualizar historial", exact=True).click()
    playwright.expect(evidence).to_be_visible()
    assert queries == app.state.test_finance.lookups
    for _ in range(3):
        evidence.click()
        confirm(page)
        playwright.expect(
            detail.get_by_role("button", name="Actualizar historial", exact=True)
        ).to_be_enabled()
        data = context.request.get(
            f"/api/finance/restaurants/{BID}/orders/{ids['finance_order']}"
        ).json()
        if not any(r["status"] == "open" for r in data["reviews"]):
            break
    playwright.expect(
        detail.get_by_text("No hay revisiones abiertas para este pedido.")
    ).to_be_visible()
    inspect(page, "finance-lookup")
    calls = []

    def lost(route):
        calls.append(route.request.post_data_json)
        assert route.fetch().ok
        route.abort("failed")

    page.route("**/orders/*/refund", lost)
    detail.get_by_label("Motivo de la acción financiera").fill("Synthetic full refund")
    detail.get_by_role("button", name="Solicitar devolución completa", exact=True).click()
    confirm(page)
    detail.get_by_role("button", name="Comprobar historial", exact=True).click()
    playwright.expect(
        detail.get_by_text("Ya existe una solicitud de devolución", exact=False)
    ).to_be_visible()
    assert len(calls) == 1 and app.state.test_finance.effects == 1
    page.unroute("**/orders/*/refund", lost)
    inspect(page, "finance-refund")
    page.goto(
        f"/workspace/sales?business={BID}&view=reviews&review_order={ids['allocation_order']}"
    )
    form = page.get_by_role("form", name="Distribución de devolución native-confirmed-partial")
    playwright.expect(form).to_be_visible()
    form.get_by_label("Distribución para", exact=False).first.fill("1000")
    form.get_by_role("checkbox").check()
    form.get_by_role("button", name="Registrar distribución").click()
    playwright.expect(
        form.get_by_text("Distribución registrada. Este registro es inmutable.")
    ).to_be_visible()
    assert app.state.test_finance.effects == 1
    inspect(page, "finance-allocation")


def test_daily_currency_nulls_and_business_navigation(site):
    page, context, url, app, *_ = site
    from datetime import UTC, datetime

    from sqlalchemy import select
    from world_model.restaurant_commerce.models import Customer

    with app.state.session_factory() as session:
        customer = session.scalar(select(Customer).where(Customer.business_id == BID))
        for currency, total in [("COP", 10000), ("USD", 100)]:
            session.add(
                Order(
                    id="daily-" + currency,
                    public_code="DAILY-" + currency,
                    business_id=BID,
                    customer_id=customer.id,
                    status="completed",
                    payment_status="paid",
                    currency=currency,
                    subtotal_minor=total,
                    total_minor=total,
                    prep_minutes=15,
                    created_at=datetime(2026, 1, 5, 15, tzinfo=UTC),
                )
            )
        session.commit()
    signin(page, f"/workspace/reports?business={BID}&view=daily&day=2026-01-05")
    playwright.expect(
        page.get_by_text("Hay pedidos en distintas monedas.", exact=False)
    ).to_be_visible()
    assert page.locator(".daily-money").count() == 0
    page.get_by_label("Moneda del resumen").select_option("COP")
    playwright.expect(page.locator(".daily-money")).to_contain_text(re.compile(r"10[.,]000"))
    inspect(page, "daily-cop")
    page.get_by_label("Moneda del resumen").select_option("USD")
    playwright.expect(page.locator(".daily-money")).to_contain_text(re.compile(r"1[.,]00"))
    playwright.expect(page.locator(".daily-finance")).to_contain_text("sin verificar")
    inspect(page, "daily-usd")


def test_native_wompi_inspection_remains_evidence_not_confirmed_refund(live_finance, browser):
    url, order, calls = live_finance
    context = browser.new_context(base_url=url, viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    try:
        signin(
            page,
            f"/workspace/sales?business={BID}&view=reviews&review_order={order.id}",
            "refund.manager",
        )
        detail = page.get_by_role("complementary", name="Detalle financiero")
        playwright.expect(
            detail.get_by_role("button", name="Consultar devolución del proveedor", exact=True)
        ).to_be_visible()
        assert not detail.get_by_role(
            "button", name="Solicitar devolución completa", exact=True
        ).count()
        detail.get_by_label("Motivo de la acción financiera").fill("Synthetic source inspection")
        detail.get_by_label("ID de devolución del proveedor").fill("123")
        detail.get_by_role("button", name="Consultar devolución del proveedor", exact=True).click()
        confirm(page)
        playwright.expect(
            detail.get_by_text("Estado reportado de devolución: APPROVED.", exact=False).first
        ).to_be_visible()
        playwright.expect(
            detail.get_by_text("no confirma una devolución", exact=False).first
        ).to_be_visible()
        assert len(calls) == 2 and all(r.method == "GET" for r in calls)
        page.reload()
        playwright.expect(
            detail.get_by_text("no confirma una devolución", exact=False).first
        ).to_be_visible()
        assert len(calls) == 2
        inspect(page, "finance-inspection")
    finally:
        context.close()


def test_delivery_unknown_is_visible_after_reload_and_cannot_resubmit(site):
    page, context, url, app, *_ = site
    ids = app.state.test_ids
    app.state.test_courier.lose = True
    signin(page, f"/workspace/sales?business={BID}&view=deliveries&delivery={ids['delivery']}")
    detail = page.get_by_role("complementary", name="Detalle de entrega")
    detail.get_by_role("button", name="Solicitar transportador", exact=True).click()
    confirm(page)
    detail.get_by_role("button", name="Comprobar estado", exact=True).click()
    playwright.expect(
        detail.get_by_text("Hay una solicitud de transportador sin confirmar.", exact=False)
    ).to_be_visible()
    page.reload()
    playwright.expect(
        detail.get_by_text("Hay una solicitud de transportador sin confirmar.", exact=False)
    ).to_be_visible()
    assert not detail.get_by_role("button", name="Solicitar transportador", exact=True).count()
    assert not detail.get_by_role("button", name="Cancelar entrega", exact=True).count()
    assert app.state.test_courier.dispatches == 1
    inspect(page, "delivery-unknown")
