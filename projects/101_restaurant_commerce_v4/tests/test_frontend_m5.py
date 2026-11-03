"""M5 against an actual loopback HTTP server; synthetic data, no provider traffic."""

import json
import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import func, select
from test_browser_security import browser as browser
from test_browser_security import playwright
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.models import Order, Reservation, RestaurantCommerceProfile
from world_model.restaurant_commerce.staff import provision

BID = "demo-restaurant-bogota"
ROOT = "/api/restaurants/" + BID
PASSWORD = "synthetic M5 browser passphrase"


@pytest.fixture
def live(tmp_path, browser):
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'live.db'}",
        seed=True,
        demo_mode=True,
        payment_recovery_enabled=False,
    )
    with app.state.session_factory() as session:
        provision(session, "m5.manager", PASSWORD, BID, "manager", actor="synthetic-test")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.02)
    assert server.started
    context = browser.new_context(
        base_url=url,
        viewport={"width": 390, "height": 844},
        timezone_id="America/Los_Angeles",
        reduced_motion="reduce",
    )
    errors = []
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        yield page, context, app, url, errors
    finally:
        context.close()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()
        assert not errors


def add(page):
    page.goto("/")
    page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    page.locator("#cName").fill("Synthetic M5")
    page.locator("#cPhone").fill("3005550101")
    playwright.expect(page.locator("#checkoutButton")).to_be_enabled()


def login(page):
    page.goto("/admin")
    page.locator("#staffUsername").fill("m5.manager")
    page.locator("#staffPassword").fill(PASSWORD)
    page.locator("#staffSignIn").click()
    playwright.expect(page.locator("#staffStatus")).to_contain_text("Sesión de")


def count(app, model=Order):
    with app.state.session_factory() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_complete_customer_staff_journey_and_reload(live):
    page, context, app, _, _ = live
    login(page)
    playwright.expect(page.locator("#publicMenuLink")).to_have_attribute(
        "href", "/?business_id=" + BID
    )
    page.locator("#loadSettings").click()
    playwright.expect(page.locator("#settingsFields")).to_be_enabled()
    page.locator("#scheduledPickup").check()
    page.locator("#opens").fill("00:00")
    page.locator("#closes").fill("23:59")
    page.locator("#settingsReason").fill("Synthetic full-day acceptance")
    page.get_by_role("button", name="Guardar horarios", exact=True).click()
    playwright.expect(page.locator("#settingsMessage")).to_contain_text("Horarios guardados")
    add(page)
    page.locator("#pickupSlot").select_option(index=1)
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    assert count(app) == 1
    page.reload()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    assert count(app) == 1
    page.goto("/admin")
    for label in ["Aceptar", "Preparar", "Marcar listo", "Entregar"]:
        page.get_by_role("button", name=label, exact=True).click()
    page.locator("#queueFilter").select_option("all")
    playwright.expect(page.locator("#orders")).to_contain_text("Entregado")
    page.locator("#loadDaily").click()
    playwright.expect(page.locator("#dailyResult")).to_contain_text("Neto liquidado: sin verificar")
    assert count(app) == 1


def test_two_tabs_lost_response_reload_one_order(live):
    page, context, app, _, _ = live
    add(page)
    other = context.new_page()
    add(other)
    seen = []

    def lost(route):
        response = route.fetch()
        assert response.status == 200
        seen.append(json.loads(route.request.post_data))
        route.abort("failed")

    page.route("**" + ROOT + "/orders", lost)
    page.locator("#checkoutButton").evaluate("(b)=>{b.click();b.click()}")
    playwright.expect(page.locator("#notice")).to_contain_text("No pudimos confirmar")
    assert count(app) == 1 and len(seen) == 1
    # A pause after commit must not invalidate recovery or clear the original key.
    with app.state.session_factory() as session:
        session.get(RestaurantCommerceProfile, BID).ordering_enabled = False
        session.commit()
    page.unroute("**" + ROOT + "/orders", lost)
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    # Tab two observes the persisted recovery key, rather than creating its own order.
    other.locator("#checkoutButton").click()
    playwright.expect(other.locator("#checkoutRecovery")).to_contain_text("Pedido #")
    page.reload()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pedido #")
    assert count(app) == 1
    saved = page.evaluate("JSON.stringify(localStorage)")
    assert "Synthetic M5" not in saved and "3005550101" not in saved


def test_offline_cart_and_no_automatic_submission(live):
    page, context, app, _, _ = live
    add(page)
    context.set_offline(True)
    playwright.expect(page.locator("#networkStatus")).to_contain_text("Sin conexión")
    page.locator("#checkoutButton").click()
    assert count(app) == 0
    context.set_offline(False)
    page.reload()
    playwright.expect(page.get_by_role("button", name="Quitar", exact=True)).to_be_visible()
    page.wait_for_timeout(400)
    assert count(app) == 0
    assert page.locator("#cName").input_value() == ""


def test_reservation_lost_response_reloaded_same_intent_and_timezone(live):
    page, context, app, _, _ = live
    when = (datetime.now(UTC) + timedelta(days=3)).strftime("%Y-%m-%d") + "T12:00"

    def fill():
        page.goto("/")
        page.get_by_role("button", name="Reservar", exact=True).click()
        page.locator("#rName").fill("Synthetic reservation")
        page.locator("#rPhone").fill("3005550102")
        page.locator("#rDate").fill(when)

    sent = []

    def lost(route):
        sent.append(json.loads(route.request.post_data))
        response = route.fetch()
        assert response.status == 200
        route.abort("failed")

    fill()
    page.route("**" + ROOT + "/reservations", lost)
    page.locator('[data-click="reserve"]').click()
    playwright.expect(page.locator("#notice")).to_contain_text("No pudimos confirmar")
    assert count(app, Reservation) == 1
    page.unroute("**" + ROOT + "/reservations", lost)
    with app.state.session_factory() as session:
        session.get(RestaurantCommerceProfile, BID).accepts_reservations = False
        session.commit()
    app.state.storefront_cache.invalidate(BID)
    fill()
    playwright.expect(page.locator("#reservationRecovery")).to_contain_text("solicitud anterior")
    with page.expect_request("**" + ROOT + "/reservations") as request:
        page.locator('[data-click="reserve"]').click()
    playwright.expect(page.locator("#notice")).to_contain_text("solicitada")
    assert request.value.post_data_json == sent[0]
    assert sent[0]["starts_at"].endswith("T17:00:00.000Z")
    assert count(app, Reservation) == 1


def test_unavailable_storage_and_locks_fail_before_checkout(live):
    page, context, app, _, _ = live
    context.add_init_script(
        "Storage.prototype.setItem=function(){throw new DOMException('Quota','QuotaExceededError')}"
    )
    add(page)
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("No se envió un pedido")
    assert count(app) == 0
    context.add_init_script("Object.defineProperty(navigator,'locks',{value:undefined})")
    add(page)
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("navegador actualizado")
    assert count(app) == 0


def test_poll_singleflight_hidden_offline_and_bounded_response(live):
    page, context, app, _, _ = live
    page.goto("/")
    page.locator("#menu article").first.wait_for()
    result = page.evaluate("""async()=>{
      let calls=0,running=0,max=0;
      const poll=CommerceUI.poll(async()=>{calls++;running++;
      max=Math.max(max,running);await new Promise(r=>setTimeout(r,80));running--;},
      {interval:40});
      poll.refresh();poll.refresh();poll.refresh();
      await new Promise(r=>setTimeout(r,230));
      Object.defineProperty(document,'hidden',{configurable:true,value:true});
      await new Promise(r=>setTimeout(r,100));const hidden=calls;
      await new Promise(r=>setTimeout(r,150));const unchanged=calls===hidden;
      Object.defineProperty(document,'hidden',{configurable:true,value:false});
      window.dispatchEvent(new Event('online'));await new Promise(r=>setTimeout(r,100));
      poll.stop();return {max,unchanged,resumed:calls>hidden};
    }""")
    assert result == {"max": 1, "unchanged": True, "resumed": True}
    held = []
    page.route("**/test-delayed-body", lambda route: held.append(route))
    result = page.evaluate(
        """async()=>{const start=performance.now();
      try{await CommerceUI.request('/test-delayed-body',{timeout:100});return false;}
      catch(e){return performance.now()-start<1500;}}"""
    )
    assert result
    for route in held:
        route.abort()
    assert count(app) == 0


def test_layout_accessibility_and_slow_network(live):
    page, context, app, url, _ = live
    artifacts = Path(os.environ.get("COMMERCE_M5_ARTIFACTS", "/tmp/commerce-m5-browser"))
    artifacts.mkdir(parents=True, exist_ok=True)
    axe = Path(
        os.environ.get(
            "COMMERCE_AXE_PATH",
            str(Path(__file__).resolve().parents[1] / "node_modules/axe-core/axe.min.js"),
        )
    )
    assert axe.exists(), "Set COMMERCE_AXE_PATH to a local axe-core distribution"
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 6})
    cdp.send(
        "Network.emulateNetworkConditions",
        {"offline": False, "latency": 800, "downloadThroughput": 50000, "uploadThroughput": 12500},
    )
    page.add_init_script(
        """window.m5metrics={lcp:0,cls:0};
      new PerformanceObserver(l=>{for(const e of l.getEntries())m5metrics.lcp=e.startTime})
      .observe({type:'largest-contentful-paint',buffered:true});
      new PerformanceObserver(l=>{for(const e of l.getEntries())
      if(!e.hadRecentInput)m5metrics.cls+=e.value})
      .observe({type:'layout-shift',buffered:true});"""
    )
    page.goto("/")
    page.locator("#menu article").first.wait_for(timeout=30000)
    page.locator("#bootNotice").wait_for(state="hidden", timeout=30000)
    page.wait_for_timeout(500)
    metrics = page.evaluate(
        '({...m5metrics,loadedAt:performance.now(),bytes:performance.getEntriesByType("resource").reduce((n,r)=>n+r.transferSize,0),resources:performance.getEntriesByType("resource").length})'
    )
    (artifacts / "slow-network.json").write_text(json.dumps(metrics, indent=2))
    assert metrics["lcp"] > 0 and metrics["lcp"] < 15000
    assert metrics["cls"] < 0.1
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    cdp.send(
        "Network.emulateNetworkConditions",
        {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1},
    )
    for width in [320, 390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.evaluate(axe.read_text())
        result = page.evaluate(
            "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
        )
        (artifacts / f"customer-{width}-axe.json").write_text(json.dumps(result))
        assert not result["violations"]
        page.screenshot(path=str(artifacts / f"customer-{width}.png"), full_page=True)
    login(page)
    page.locator("#loadSettings").click()
    playwright.expect(page.locator("#settingsFields")).to_be_enabled()
    page.set_viewport_size({"width": 320, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.evaluate(axe.read_text())
    result = page.evaluate(
        "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
    )
    (artifacts / "staff-320-axe.json").write_text(json.dumps(result))
    assert not result["violations"]
    page.screenshot(path=str(artifacts / "staff-320.png"), full_page=True)


def test_missing_javascript_keeps_checkout_disabled(live, browser):
    page, context, app, url, _ = live
    page.route("**/assets/index.js*", lambda r: r.abort())
    page.goto("/")
    playwright.expect(page.locator("#bootNotice")).to_be_visible()
    playwright.expect(page.locator("#checkoutButton")).to_be_disabled()
    with browser.new_context(java_script_enabled=False) as nojs:
        p = nojs.new_page()
        p.goto(url)
        playwright.expect(p.locator("noscript")).to_be_visible()
        playwright.expect(p.locator("#checkoutButton")).to_be_disabled()
    assert count(app) == 0


def test_five_percent_read_loss_and_unknown_staff_action(live):
    page, context, app, url, _ = live
    add(page)
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    login(page)
    # One of exactly twenty genuine API reads loses its response; no write retries.
    attempts = []

    def loss(route):
        response = route.fetch()
        attempts.append(response.status)
        if len(attempts) == 7:
            route.abort("failed")
        else:
            route.fulfill(response=response)

    page.route("**" + ROOT + "/pickup-slots", loss)
    results = page.evaluate(
        """async path=>{let ok=0,failed=0;for(let i=0;i<20;i++){
      try{const r=await CommerceUI.request(path);if(r.ok)ok++;else failed++;}
      catch(e){failed++;}}return {ok,failed};}""",
        ROOT + "/pickup-slots",
    )
    assert results == {"ok": 19, "failed": 1} and attempts == [200] * 20
    # A failed queue read must not look fresh because another resource succeeds.
    page.route("**/api/operator/restaurants/*/orders?*", lambda r: r.abort("failed"))
    page.get_by_role("button", name="Actualizar", exact=True).click()
    playwright.expect(page.locator("#staffActionStatus")).to_contain_text("desactualizados")
    playwright.expect(page.locator("#networkStatus")).to_contain_text("sin confirmar")
    page.unroute("**/api/operator/restaurants/*/orders?*")
    page.get_by_role("button", name="Actualizar", exact=True).click()
    playwright.expect(page.locator("#networkStatus")).to_contain_text("Servidor accesible")
    mutations = []

    def uncertain(route):
        if route.request.method != "PATCH":
            return route.continue_()
        mutations.append(route.request.post_data_json)
        response = route.fetch()
        assert response.status == 200
        route.abort("failed")

    page.route("**/api/operator/orders/*", uncertain)
    page.get_by_role("button", name="Aceptar", exact=True).click()
    playwright.expect(page.locator("#staffActionStatus")).to_contain_text("No repetimos la acción")
    playwright.expect(page.get_by_role("button", name="Preparar", exact=True)).to_be_visible()
    page.wait_for_timeout(300)
    assert len(mutations) == 1 and mutations[0]["expected_version"] >= 1
    with app.state.session_factory() as session:
        assert session.scalar(select(Order)).status == "accepted"
    assert count(app) == 1


def test_keyboard_dialog_and_two_hundred_percent_zoom(live):
    page, context, app, _, _ = live
    page.set_viewport_size({"width": 768, "height": 1024})
    page.goto("/")
    page.locator("#menu article").first.wait_for()
    page.keyboard.press("Tab")
    playwright.expect(page.get_by_role("link", name="Ir al menú", exact=True)).to_be_focused()
    page.keyboard.press("Enter")
    button = page.locator("#menu article").filter(has_text="Smash 101").get_by_role("button")
    button.focus()
    page.keyboard.press("Enter")
    playwright.expect(page.locator("#itemDialog")).to_be_visible()
    page.keyboard.press("Escape")
    playwright.expect(page.locator("#itemDialog")).not_to_be_visible()
    playwright.expect(button).to_be_focused()
    # Chromium CSS zoom gives reproducible 200% content enlargement; exact OS/browser
    # zoom and physical assistive technology still require device qualification.
    page.evaluate("document.documentElement.style.zoom='2'")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert count(app) == 0


def test_server_price_change_requires_confirmation_and_discount_breakdown(live):
    from world_model.restaurant_commerce.models import MenuItem, Promotion

    page, context, app, _, _ = live
    with app.state.session_factory() as session:
        session.add(
            Promotion(
                business_id=BID,
                code="M5PUBLIC",
                name="Synthetic discount",
                value=1000,
                discount_type="fixed",
            )
        )
        session.commit()
    add(page)
    page.get_by_text("Agregar nota o código promocional", exact=True).click()
    page.locator("#promoCode").fill("M5PUBLIC")
    playwright.expect(page.locator("#cartTotal")).to_contain_text("10.900")
    playwright.expect(page.locator("#foodTotal")).to_contain_text("11.900")
    playwright.expect(page.locator("#discountTotal")).to_contain_text("1.000")
    with app.state.session_factory() as session:
        item = session.scalar(select(MenuItem).where(MenuItem.name == "Papas de la casa"))
        item.base_price_minor = 12900
        session.commit()
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("cotización venció o cambió")
    assert count(app) == 0
    playwright.expect(page.locator("#cartTotal")).to_contain_text("11.900")
    playwright.expect(page.locator(".cart-row-price")).to_contain_text("12.900")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text("Pago confirmado")
    with app.state.session_factory() as session:
        assert session.scalar(select(Order)).total_minor == 11900
    assert count(app) == 1


def test_manual_refresh_queues_behind_session_restore(live):
    page, _, _, _, _ = live
    held = []
    orders = []

    def delay_first_reconciliation(route):
        if not held:
            response = route.fetch()
            assert response.status == 200
            held.append((route, response))
        else:
            route.continue_()

    page.route("**/payment-reconciliation", delay_first_reconciliation)
    page.on(
        "request",
        lambda request: (
            orders.append(request.url) if request.url.split("?")[0].endswith("/orders") else None
        ),
    )
    login(page)
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(20)
    assert held and len(orders) == 1
    page.get_by_role("button", name="Actualizar", exact=True).click()
    held[0][0].fulfill(response=held[0][1])
    # Must honor the click promptly, rather than waiting for the15s periodic poll.
    for _ in range(100):
        if len(orders) >= 2:
            break
        page.wait_for_timeout(20)
    assert len(orders) == 2
