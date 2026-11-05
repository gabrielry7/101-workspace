"""Installed-browser profit reads, exact evidence retries, roles and scoped navigation."""

import csv
import json
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import func, select
from test_browser_security import browser as browser  # noqa: PLC0414
from test_browser_security import playwright
from test_loyalty_analytics import analytics as analytics  # noqa: PLC0414
from test_loyalty_analytics import factory as factory  # noqa: PLC0414
from test_loyalty_analytics import write_cost

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.loyalty_measurement_models import (
    LoyaltyFinancialEvidence,
)
from world_model.restaurant_commerce.models import (
    LoyaltyLedgerEntry,
    RestaurantCommerceProfile,
    StaffAccount,
    StaffMembership,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.staff import provision

PASSWORD = "synthetic analytics passphrase only"
OTHER = "analytics-other-demo"
OUT = Path(
    os.environ.get(
        "LOYALTY_ANALYTICS_BROWSER_EVIDENCE", "/tmp/101-loyalty-analytics-browser"
    )
)
AXE = Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
MEASURE = Path(__file__).resolve().parents[1] / "scripts/measure_loyalty_results.js"


@pytest.fixture
def site(analytics, browser, request):
    data = analytics(n=getattr(request, "param", 4))
    app = create_app(
        engine=data["factory"].kw["bind"],
        loyalty_configuration_enabled=True,
        loyalty_analytics_enabled=True,
        demo_mode=True,
        payment_recovery_enabled=False,
    )
    with data["factory"]() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id=OTHER,
                slug="analytics-other-demo",
                display_name="Otro negocio ficticio",
            )
        )
        s.commit()
        for name, role in [
            ("analytics.manager", "manager"),
            ("analytics.viewer", "viewer"),
        ]:
            provision(s, name, PASSWORD, BID, role, actor="synthetic")
        user = s.scalar(
            select(StaffAccount).where(StaffAccount.username == "analytics.manager")
        )
        s.add(StaffMembership(account_id=user.id, business_id=OTHER, role="manager"))
        s.commit()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    origin = "http://127.0.0.1:" + str(sock.getsockname()[1])
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
        base_url=origin, viewport={"width": 1440, "height": 1000}
    )
    page = context.new_page()
    errors, external, csp = [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "request",
        lambda r: (
            external.append(r.url)
            if not r.url.startswith(origin) and not r.url.startswith("data:")
            else None
        ),
    )
    page.on(
        "console",
        lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        yield page, app, data
    finally:
        page.screenshot(
            path=str(OUT / (request.node.name + "-last.png")), full_page=True
        )
        (OUT / (request.node.name + "-last.json")).write_text(
            json.dumps(
                {
                    "url": page.url,
                    "text": page.locator("body").inner_text(),
                    "errors": errors,
                },
                indent=2,
            )
        )
        context.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not errors and not external and not csp


def login(page, data, user="analytics.manager"):
    page.goto(
        f"/workspace/customers?business={BID}&view=loyalty&loyaltyTab=results&loyaltyId={data['experiment_id']}"
    )
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role(
        "heading", name="Ganancia incremental por cliente asignado", exact=True
    ).wait_for()


def count(app, model):
    with app.state.session_factory() as s:
        return s.scalar(select(func.count()).select_from(model))


def capture(page, name):
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(OUT / (name + ".png")), full_page=True)
    page.evaluate(AXE.read_text())
    violations = page.evaluate(
        "async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations"
    )
    (OUT / (name + "-axe.json")).write_text(json.dumps(violations, indent=2))
    measurements = page.evaluate(
        MEASURE.read_text(),
        [
            ".loyalty-results h2",
            ".loyalty-comparison h4",
            ".loyalty-comparison dd",
            ".loyalty-confidence",
            ".loyalty-metrics strong",
            ".loyalty-section",
            ".loyalty-field",
            ".loyalty-table-wrap td",
            ".loyalty-table-wrap th",
        ],
    )
    (OUT / (name + "-measurements.json")).write_text(json.dumps(measurements, indent=2))
    assert violations == []
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytest.mark.parametrize("site", [30], indirect=True)
def test_complete_itt_interval_nonbuyers_csv_and_mobile(site):
    page, app, data = site
    before = count(app, LoyaltyLedgerEntry)
    login(page, data)
    page.get_by_text("Evaluación disponible", exact=True).wait_for()
    comparison = page.get_by_role(
        "region", name="Comparaciones con el control", exact=True
    )
    playwright.expect(comparison).to_contain_text("1.500,00 COP")
    playwright.expect(comparison).to_contain_text("Confianza conjunta 95%")
    playwright.expect(
        page.get_by_role("region", name="Resultados por grupo", exact=True)
    ).to_contain_text("30 / 15")
    capture(page, "complete-desktop")
    with page.expect_download() as download:
        page.get_by_role("link", name="Exportar CSV", exact=True).click()
    download.value.save_as(str(OUT / "complete-export.csv"))
    rows = list(csv.reader((OUT / "complete-export.csv").read_text().splitlines()))
    assert [r[2] for r in rows[3:]] == ["30", "30"]
    assert all(r[4] == "15" for r in rows[3:])
    for width in [390, 320, 768, 1920]:
        page.set_viewport_size({"width": width, "height": 844 if width < 768 else 1000})
        capture(page, "complete-" + str(width))
        assert (
            page.get_by_role("region", name="Resultados por grupo")
            .locator("th")
            .evaluate_all(
                "nodes=>nodes.every(n=>getComputedStyle(n).display==='table-cell')"
            )
        )
        bounds = page.locator(".loyalty-confidence").first.bounding_box()
        assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
    page.set_viewport_size({"width": 390, "height": 844})
    stable = comparison.inner_text()
    page.evaluate(
        "document.documentElement.style.setProperty('--wm-radius','4px');document.documentElement.style.setProperty('--wm-accent','#315d8b');document.documentElement.style.setProperty('--wm-label','16px')"
    )
    capture(page, "editable-roles-390")
    assert comparison.inner_text() == stable
    page.evaluate(
        "['--wm-radius','--wm-accent','--wm-label'].forEach(k=>document.documentElement.style.removeProperty(k))"
    )
    page.get_by_label("Vista de color", exact=True).select_option("gray-white")
    playwright.expect(page.locator("html")).to_have_attribute(
        "data-workspace-pairing", "gray-white"
    )
    capture(page, "gray-white-390")
    assert comparison.inner_text() == stable
    page.get_by_label("Vista de color", exact=True).select_option("original")
    samples = []
    for _ in range(3):
        page.get_by_role("link", name="Programas", exact=True).click()
        page.get_by_role("heading", name="Programas", exact=True).wait_for()
        started = time.perf_counter()
        page.get_by_role("link", name="Resultados", exact=True).click()
        page.get_by_role("heading", name="Elige una comparación", exact=True).wait_for()
        samples.append(round((time.perf_counter() - started) * 1000, 2))
    (OUT / "tab-return-timings.json").write_text(
        json.dumps(
            {
                "milliseconds": samples,
                "profile": "local Chromium,390x844,no network/CPU throttle;warm shell;60synthetic assigned customers;result picker ready,not report completed",
            },
            indent=2,
        )
    )
    assert count(app, LoyaltyLedgerEntry) == before


def test_financial_cost_lost_reply_retry_and_pending_dialog(site):
    page, app, data = site
    login(page, data)
    page.get_by_text("Costos de pedidos", exact=False).click()
    page.get_by_role("button", name="Registrar costos de ", exact=False).first.click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Costos variables (COP)", exact=True).fill("12345")
    dialog.get_by_label("Fuente de los costos", exact=True).fill(
        "synthetic revised invoice"
    )
    before = count(app, LoyaltyFinancialEvidence)
    calls = []

    def lost(route):
        if route.request.method != "POST":
            return route.continue_()
        calls.append(json.loads(route.request.post_data))
        if len(calls) == 1:
            route.fetch()
            route.abort("failed")
        else:
            route.continue_()

    page.route("**/analytics/orders/*", lost)
    dialog.get_by_role("button", name="Guardar evidencia", exact=True).evaluate(
        "b=>{b.click();b.click()}"
    )
    dialog.get_by_text("No recibimos la confirmación.", exact=False).wait_for()
    page.keyboard.press("Escape")
    playwright.expect(dialog).to_be_visible()
    assert len(calls) == 1
    capture(page, "uncertain-cost-dialog")
    dialog.get_by_role(
        "button", name="Verificar solicitud pendiente", exact=True
    ).click()
    playwright.expect(dialog).not_to_be_visible()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert count(app, LoyaltyFinancialEvidence) == before + 1
    page.get_by_text("Recompensas, exposición y costos", exact=True).click()
    page.get_by_role("button", name="Registrar costo de Control", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Costo operativo total del grupo (COP)", exact=True).fill("800")
    dialog.get_by_label("Fuente de los costos", exact=True).fill(
        "synthetic operating invoice"
    )
    dialog.get_by_role("button", name="Guardar evidencia", exact=True).click()
    playwright.expect(dialog).not_to_be_visible()
    assert count(app, LoyaltyFinancialEvidence) == before + 2


def test_stale_cost_requires_explicit_reload_and_phone_history(site):
    page, _app, data = site
    login(page, data)
    page.get_by_text("Costos de pedidos", exact=False).click()
    button = page.get_by_role("button", name="Registrar costos de ", exact=False).first
    code = button.inner_text().replace("Registrar costos de ", "")
    button.click()
    dialog = page.get_by_role("dialog")
    field = dialog.get_by_label("Costos variables (COP)", exact=True)
    field.fill("1111")
    with data["factory"]() as s:
        from world_model.restaurant_commerce.models import Order

        oid = s.scalar(select(Order.id).where(Order.public_code == code))
        write_cost(s, oid, variable=2222)
    dialog.get_by_role("button", name="Guardar evidencia", exact=True).click()
    dialog.get_by_text("La versión cambió.", exact=False).wait_for()
    assert field.input_value() == "1111"
    dialog.get_by_role("button", name="Recargar registros", exact=True).click()
    playwright.expect(
        dialog.get_by_label("Costos variables (COP)", exact=True)
    ).to_have_value("2222")
    playwright.expect(
        dialog.get_by_text("La versión cambió.", exact=False)
    ).not_to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    capture(page, "cost-history-mobile")
    box = dialog.bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390
    dialog.get_by_label("Costos variables (COP)", exact=True).fill("2223")
    dialog.get_by_role("button", name="Guardar evidencia", exact=True).click()
    playwright.expect(dialog).not_to_be_visible()


def test_viewer_readonly_failure_retry_and_missing_feature(site):
    page, _app, data = site
    login(page, data, "analytics.viewer")
    page.get_by_text("Costos de pedidos", exact=False).click()
    assert (
        page.get_by_role("button", name="Registrar costos de ", exact=False).count()
        == 0
    )
    path = f"**/experiments/{data['experiment_id']}/report"
    page.route(
        path,
        lambda route: route.fulfill(
            status=503, json={"detail": "synthetic unavailable"}
        ),
    )
    page.get_by_role("button", name="Actualizar informe", exact=True).click()
    page.get_by_role("heading", name="No se pudo cargar", exact=True).wait_for()
    capture(page, "read-retry")
    page.unroute(path)
    page.get_by_role("button", name="Reintentar", exact=True).click()
    page.get_by_role(
        "heading", name="Ganancia incremental por cliente asignado", exact=True
    ).wait_for()

    def feature_off(route):
        response = route.fetch()
        value = response.json()
        value["analytics_enabled"] = False
        route.fulfill(response=response, json=value)

    page.route("**/loyalty-config/capabilities", feature_off)
    page.reload()
    page.get_by_role(
        "heading", name="Resultados aún no habilitados", exact=True
    ).wait_for()


def test_business_switch_discards_late_report(site):
    page, _app, data = site
    login(page, data)
    held = []
    page.route(
        f"**/experiments/{data['experiment_id']}/report",
        lambda route: held.append((route, route.fetch())),
    )
    page.get_by_role("button", name="Actualizar informe", exact=True).click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(20)
    assert held
    page.get_by_label("Negocio", exact=True).select_option(OTHER)
    page.get_by_role("heading", name="Elige una comparación", exact=True).wait_for()
    held[0][0].fulfill(response=held[0][1])
    page.wait_for_timeout(100)
    assert "business=" + OTHER in page.url
    assert not page.get_by_role(
        "heading", name="Ganancia incremental por cliente asignado", exact=True
    ).count()


def test_structured_readout_is_reviewed_and_published_without_activation(site):
    page, app, data = site
    login(page, data)
    page.get_by_role("link", name="Experimentos", exact=True).click()
    page.get_by_role("button", name="Crear experimento", exact=True).click()
    page.get_by_label("Nombre del experimento", exact=True).fill(
        "Plan de próximas visitas"
    )
    page.get_by_label("Oferta de variante 2", exact=True).select_option(
        data["program_version"]
    )
    page.get_by_label("Plan de evaluación", exact=True).fill(
        "Comparar ganancias durante el seguimiento original y conservar a todos los clientes asignados."
    )
    page.get_by_label(
        "Definir evaluación estadística antes de asignar clientes", exact=True
    ).check()
    page.get_by_label("Mínimo previsto de clientes por grupo", exact=True).fill("30")
    page.get_by_label("Justificación del tamaño de muestra", exact=True).fill(
        "Diseño sintético para revisar el protocolo; no representa una recomendación comercial."
    )
    page.get_by_role("button", name="Guardar experimento", exact=True).click()
    page.get_by_role("button", name="Revisar y publicar", exact=True).click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_contain_text("mínimo 30 por grupo")
    playwright.expect(dialog).to_contain_text("Welch / Bonferroni")
    capture(page, "protocol-review")
    dialog.get_by_role("button", name="Publicar esta versión", exact=True).click()
    page.get_by_role("button", name="Pausar", exact=True).wait_for()
    with app.state.session_factory() as s:
        from world_model.restaurant_commerce.loyalty_assignment_models import (
            LoyaltyAssignment,
        )

        assert s.scalar(select(func.count()).select_from(LoyaltyAssignment)) == 8
    assert page.get_by_role("button", name="Activar", exact=True).count() == 0
