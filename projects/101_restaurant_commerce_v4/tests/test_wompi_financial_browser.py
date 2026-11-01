"""Real browser and HTTP backend; only Wompi provider responses are controlled."""

import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import expect
from staff_helpers import PASSWORD
from test_browser_security import browser as browser
from test_wompi_financial import factory as factory
from test_wompi_financial import prepared
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.models import RestaurantCommerceProfile
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.staff import provision


@pytest.fixture
def live_finance(factory):
    adapter, tx, refund, order, calls = prepared(factory)
    with factory() as session:
        engine = session.get_bind()
        provision(session, "refund.manager", PASSWORD, BID, "manager", actor="test-fixture")
        session.add(
            RestaurantCommerceProfile(business_id="other", slug="other", display_name="Other")
        )
        session.commit()
    app = create_app(engine=engine, wompi_sandbox=adapter.payments, payment_recovery_enabled=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            assert server.started
            yield f"http://127.0.0.1:{port}", order, calls
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()


def test_staff_browser_refund_gate_inspection_reload_and_scope(live_finance, browser):
    base, order, calls = live_finance
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(base + "/admin")
        page.locator("#staffUsername").fill("refund.manager")
        page.locator("#staffPassword").fill(PASSWORD)
        page.locator("#staffSignIn").click()
        expect(page.locator("#staffLogout")).to_be_visible()
        page.locator("#business").fill(BID)
        page.locator("#financeOrder").fill(order.id)
        expect(page.locator("#financeRefundButton")).to_be_disabled()
        page.locator('[data-click="financeHistory"]').click()
        expect(page.locator("#financeAvailability")).to_contain_text("contrato del proveedor")
        expect(page.locator("#financeInspectButton")).to_be_enabled()
        page.locator("#financeReason").fill("Inspect reported refund")
        page.locator("#financeRefundReference").fill("123")
        page.locator("#financeInspectButton").click()
        expect(page.locator("#financeResult")).to_contain_text("Requiere investigación")
        expect(page.locator("#financeResult")).to_contain_text("APPROVED (no confirma devolución")
        expect(page.locator("#financeResult")).to_contain_text(
            "no identifica el reembolso como Sandbox"
        )
        assert len(calls) == 2 and all(r.method == "GET" for r in calls)
        page.reload()
        page.locator("#business").fill(BID)
        page.locator("#financeOrder").fill(order.id)
        page.locator('[data-click="financeHistory"]').click()
        expect(page.locator("#financeResult")).to_contain_text("Requiere investigación")
        expect(page.locator("#financeRefundButton")).to_be_disabled()
        page.locator("#business").fill("other")
        expect(page.locator("#financeInspectButton")).to_be_disabled()
        expect(page.locator("#financeRefundButton")).to_be_disabled()
        expect(page.locator("#financeResult")).not_to_contain_text("APPROVED")
        page.locator('[data-click="financeHistory"]').click()
        expect(page.locator("#financeResult")).not_to_contain_text("APPROVED")
        assert len(calls) == 2 and not errors
    except Exception:
        print(
            "Financial panel:",
            page.locator("#financeResult").inner_text(),
            "Browser errors:",
            errors,
        )
        context.tracing.stop(path="/tmp/wompi-financial-browser-failure.zip")
        raise
    finally:
        context.close()
