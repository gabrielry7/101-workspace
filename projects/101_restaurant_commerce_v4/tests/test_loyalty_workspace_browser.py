"""Real built UI and HTTP: publication, failures, scoped state and exact economics."""

import json
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import func, select
from test_browser_security import (
    browser as browser,  # noqa: PLC0414 - pytest fixture re-export
)
from test_browser_security import playwright

from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_models import (
    LoyaltyStrategy,
    LoyaltyStrategyVersion,
)
from world_model.restaurant_commerce.loyalty_schemas import StrategyEdit
from world_model.restaurant_commerce.loyalty_workspace_demo import app_for_demo
from world_model.restaurant_commerce.models import (
    LoyaltyLedgerEntry,
    StaffAccount,
    StaffMembership,
)
from world_model.restaurant_commerce.staff import provision

OUT = Path(os.environ.get("LOYALTY_BROWSER_EVIDENCE", "/tmp/101-loyalty-browser"))


@pytest.fixture
def site(tmp_path, browser):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = "http://127.0.0.1:" + str(sock.getsockname()[1])
    app = app_for_demo("sqlite:///" + str(tmp_path / "loyalty.db"), url)
    with app.state.session_factory() as s:
        provision(s, "loyalty.viewer", PASSWORD, BUSINESS, "viewer", actor="synthetic")
        provision(s, "loyalty.multi", PASSWORD, BUSINESS, "manager", actor="synthetic")
        user = s.scalar(
            select(StaffAccount).where(StaffAccount.username == "loyalty.multi")
        )
        s.add(StaffMembership(account_id=user.id, business_id=OTHER, role="manager"))
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
        yield page, app, errors
    finally:
        context.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not errors and not external and not csp


def login(page, user="campaign.manager"):
    page.goto("/workspace/customers?view=loyalty")
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Programas", exact=True).wait_for()
    playwright.expect(
        page.get_by_role("link", name="Puntos para la próxima visita", exact=False)
    ).to_be_visible()


def tally(app, model):
    with app.state.session_factory() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_create_lost_reply_retry_and_reviewed_publication(site):
    page, app, _ = site
    login(page)
    before = tally(app, LoyaltyLedgerEntry)
    calls = []
    lost = [False]

    def intercept(route):
        if route.request.method != "POST":
            return route.continue_()
        calls.append(json.loads(route.request.post_data))
        if not lost[0]:
            lost[0] = True
            route.fetch()
            route.abort("failed")
        else:
            route.continue_()

    page.route("**/loyalty-config/programs", intercept)
    page.get_by_role("button", name="Crear programa", exact=True).click()
    page.get_by_label("Nombre", exact=True).fill("Puntos revisados")
    page.get_by_label("Por cada compra de (COP)", exact=True).fill("2500")
    page.get_by_label("Canjear puntos por un descuento fijo", exact=True).check()
    page.get_by_label("Valor del descuento (COP)", exact=True).fill("2000")
    page.get_by_label("Elegir clientes específicos", exact=True).check()
    page.get_by_label("Buscar participantes").fill("Mateo")
    page.get_by_label("Mateo Restrepo", exact=True).check()
    page.get_by_text("Productos incluidos y excluidos", exact=True).click()
    page.locator(".loyalty-products>div").first.get_by_label(
        "Excluir", exact=True
    ).check()
    # Enter submits while the last money field remains focused.
    page.get_by_label("Presupuesto total (COP)", exact=True).fill("900000")
    page.get_by_label("Presupuesto total (COP)", exact=True).press("Enter")
    page.get_by_text("No recibimos la confirmación.", exact=False).wait_for()
    page.get_by_role("button", name="Reintentar guardado", exact=True).click()
    page.get_by_role("button", name="Revisar y publicar", exact=True).wait_for()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert calls[0]["document"]["earning"]["spend_minor_per_point"] == 2500
    assert calls[0]["document"]["campaign_budget_minor"] == 900000
    assert tally(app, LoyaltyStrategy) == 2
    page.get_by_role("button", name="Revisar y publicar", exact=True).click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_contain_text("Mateo Restrepo")
    page.screenshot(path=str(OUT / "publication-review.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    box = dialog.bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390
    assert box["y"] >= 0 and box["y"] + box["height"] <= 844
    page.keyboard.press("Tab")
    assert dialog.evaluate("node=>node.contains(document.activeElement)")
    page.screenshot(path=str(OUT / "publication-review-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    versions = tally(app, LoyaltyStrategyVersion)
    dialog.get_by_role("button", name="Publicar esta versión", exact=True).evaluate(
        "(b)=>{b.click();b.click()}"
    )
    page.get_by_role("button", name="Pausar", exact=True).wait_for()
    assert tally(app, LoyaltyStrategyVersion) == versions + 1
    page.get_by_role("button", name="Pausar", exact=True).click()
    page.get_by_text("La pausa se conserva", exact=False).wait_for()
    page.get_by_role("button", name="Editar propuesta", exact=True).click()
    page.get_by_label("Nombre", exact=True).fill("Puntos revisados segunda propuesta")
    page.get_by_role("button", name="Guardar borrador", exact=True).click()
    page.get_by_role("button", name="Revisar y publicar", exact=True).click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Publicar esta versión", exact=True
    ).click()
    page.get_by_text("La pausa se conserva", exact=False).wait_for()
    page.get_by_role("button", name="Versión 1", exact=False).click()
    playwright.expect(
        page.get_by_role("heading", name="Puntos revisados", exact=True)
    ).to_be_visible()
    assert tally(app, LoyaltyLedgerEntry) == before


def test_experiment_allocations_control_and_version_reference(site):
    page, _app, _ = site
    login(page)
    page.get_by_role("link", name="Experimentos", exact=True).click()
    page.get_by_role("button", name="Crear experimento", exact=True).click()
    page.get_by_label("Nombre del experimento").fill("Comparación de visitas")
    page.get_by_label("Oferta de variante 2", exact=True).select_option(
        label="Puntos para la próxima visita · versión 1"
    )
    page.get_by_label("Plan de evaluación").fill(
        "Comparar la ganancia por cliente asignado durante sesenta días completos."
    )
    page.get_by_label("Distribución 1 (%)", exact=True).fill("70")
    page.get_by_label("Distribución 2 (%)", exact=True).fill("20")
    page.get_by_role("button", name="Guardar experimento", exact=True).click()
    playwright.expect(page.get_by_role("alert")).to_contain_text("sumar 100")
    page.get_by_label("Distribución 2 (%)", exact=True).fill("30")
    page.get_by_role("button", name="Guardar experimento", exact=True).click()
    page.get_by_role("button", name="Revisar y publicar", exact=True).click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_contain_text(
        "Puntos para la próxima visita · versión 1"
    )
    dialog.get_by_role("button", name="Publicar esta versión", exact=True).click()
    page.get_by_role("heading", name="Participación registrada", exact=True).wait_for()
    playwright.expect(page.locator(".loyalty-definition")).to_contain_text("0")
    assert page.get_by_role("button", name="Activar", exact=True).count() == 0


def test_exact_simulation_stale_result_and_no_reward_writes(site):
    page, app, _ = site
    login(page)
    before = tally(app, LoyaltyLedgerEntry)
    page.get_by_role("link", name="Calculadora", exact=True).click()
    page.get_by_role("button", name="Calcular escenario", exact=True).click()
    page.get_by_role("heading", name="Resultado bajo estos supuestos").wait_for()
    playwright.expect(page.locator(".loyalty-results")).to_contain_text(
        "−$ 600.000 COP"
    )
    page.get_by_label("Compra promedio (COP)", exact=True).fill("9007199254740991")
    playwright.expect(
        page.get_by_text("Modificaste los supuestos.", exact=False)
    ).to_be_visible()
    with page.expect_response(
        lambda r: (
            r.url.endswith("/loyalty-config/simulator") and r.request.method == "POST"
        )
    ) as observed:
        page.get_by_role("button", name="Calcular escenario", exact=True).click()
    response = observed.value.json()
    value = int(
        response["projection"]["estimated_incremental_contribution_profit_minor"]
    )
    expected = (
        ("−" if value < 0 else "") + "$ " + f"{abs(value):,}".replace(",", ".") + " COP"
    )
    playwright.expect(page.locator(".loyalty-results")).to_contain_text(expected)
    assert abs(value) > 2**53 - 1
    assert tally(app, LoyaltyLedgerEntry) == before
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(OUT / "calculator-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")


def test_conflict_reload_and_late_mutation_cannot_switch_business(site):
    page, app, _ = site
    login(page, "loyalty.multi")
    page.get_by_role("link", name="Puntos para la próxima visita", exact=False).click()
    page.get_by_role("button", name="Editar propuesta", exact=True).click()
    page.get_by_label("Nombre", exact=True).fill("Mi propuesta local")
    with app.state.session_factory() as s:
        config = LoyaltyConfigurationService(s, "concurrent-operator")
        resource = config.list("programs", BUSINESS)[0]
        config.edit(
            "programs",
            BUSINESS,
            resource["id"],
            StrategyEdit(
                expected_revision=resource["revision"],
                document={**resource["document"], "name": "Cambio de otra persona"},
            ),
        )
    page.get_by_role("button", name="Guardar borrador", exact=True).click()
    playwright.expect(page.get_by_role("alert")).to_contain_text("La versión cambió")
    playwright.expect(page.get_by_label("Nombre", exact=True)).to_have_value(
        "Mi propuesta local"
    )
    page.get_by_role("button", name="Recargar versión guardada", exact=True).click()
    playwright.expect(page.get_by_label("Nombre", exact=True)).to_have_value(
        "Cambio de otra persona"
    )
    held = []

    def hold_save(route):
        if route.request.method == "PUT":
            held.append((route, route.fetch()))
        else:
            route.continue_()

    page.route("**/loyalty-config/programs/*", hold_save)
    page.get_by_label("Nombre", exact=True).fill("Respuesta tardía de otro negocio")
    page.get_by_role("button", name="Guardar borrador", exact=True).click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(20)
    assert held
    page.get_by_label("Negocio", exact=True).select_option(OTHER)
    page.get_by_role("button", name="Crear programa", exact=True).wait_for()
    held[0][0].fulfill(response=held[0][1])
    page.wait_for_timeout(150)
    assert "business=" + OTHER in page.url
    assert "Respuesta tardía" not in page.locator("main").inner_text()
    assert not page.get_by_label("Nombre", exact=True).count()
    page.screenshot(path=str(OUT / "empty-business.png"), full_page=True)


def test_viewer_missing_feature_and_retry_states(site):
    page, _app, _ = site
    login(page, "loyalty.viewer")
    assert page.get_by_role("button", name="Crear programa", exact=True).count() == 0
    page.get_by_role("link", name="Puntos para la próxima visita", exact=False).click()
    assert page.get_by_role("button", name="Editar propuesta", exact=True).count() == 0
    page.get_by_role("button", name="Volver a programas", exact=True).click()
    page.route(
        "**/loyalty-config/programs",
        lambda route: route.fulfill(
            status=503, json={"detail": "synthetic unavailable"}
        ),
    )
    page.reload()
    page.get_by_role("heading", name="No se pudo cargar").wait_for()
    page.screenshot(path=str(OUT / "read-retry.png"), full_page=True)
    page.unroute("**/loyalty-config/programs")
    page.get_by_role("button", name="Reintentar", exact=True).click()
    page.get_by_role(
        "link", name="Puntos para la próxima visita", exact=False
    ).wait_for()
    page.route(
        "**/loyalty-config/capabilities",
        lambda route: route.fulfill(status=404, json={"detail": "feature off"}),
    )
    page.reload()
    page.get_by_role("heading", name="Fidelización aún no está habilitada").wait_for()
    assert page.get_by_role("button", name="Crear programa", exact=True).count() == 0


def test_expired_session_cannot_save_or_replay_draft(site):
    page, app, _ = site
    login(page)
    before = tally(app, LoyaltyStrategy)
    page.get_by_role("button", name="Crear programa", exact=True).click()
    page.get_by_label("Nombre", exact=True).fill("No guardar con sesión terminada")
    identity = page.request.get("/api/staff/me").json()
    assert (
        page.request.post(
            "/api/staff/logout", headers={"X-101-CSRF": identity["csrf"]}
        ).status
        == 200
    )
    page.get_by_role("button", name="Guardar borrador", exact=True).click()
    page.get_by_label("Usuario", exact=True).wait_for()
    assert tally(app, LoyaltyStrategy) == before


def test_mobile_financial_columns_and_no_hidden_view_reads(site):
    page, app, _ = site
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    login(page)
    assert not any("/loyalty-config/overview" in u for u in requests)
    assert not any("/loyalty-config/experiments" in u for u in requests)
    page.get_by_role("link", name="Saldos y costos", exact=True).click()
    page.get_by_role("heading", name="Movimientos recientes").wait_for()
    before = tally(app, LoyaltyLedgerEntry)
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        assert page.locator(".loyalty-table-wrap th").evaluate_all(
            "nodes=>nodes.every(n=>getComputedStyle(n).display==='table-cell')"
        )
    assert tally(app, LoyaltyLedgerEntry) == before
