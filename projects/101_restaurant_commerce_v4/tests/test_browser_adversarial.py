from staff_helpers import staff_headers
"""Delay/reorder/drop responses in a real browser, with all traffic intercepted."""

import json

from test_browser_security import (
    browser as browser,  # noqa: PLC0414 - pytest fixture re-export
)
from test_browser_security import playwright
from test_browser_security import (
    site as site,  # noqa: PLC0414 - pytest fixture re-export
)

ROOT = "/api/restaurants/demo-restaurant-bogota"


def add_item(page):
    page.goto("https://commerce.test/")
    page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
    page.get_by_role("button", name="Quitar", exact=True).wait_for()


def hold(page, url):
    routes = []
    page.route("**" + url, lambda route: routes.append(route))
    return routes


def pump(page, routes, n=1):
    for _ in range(50):
        if len(routes) >= n:
            return
        page.wait_for_timeout(20)
    assert len(routes) >= n


def test_late_food_quote_cannot_resurrect_empty_cart(site):
    page, _, _, _, errors, external = site
    pending = hold(page, ROOT + "/orders/quote")
    add_item(page)
    pump(page, pending)
    page.get_by_role("button", name="Quitar", exact=True).click()
    pending[0].fulfill(json={"total_minor": 99999, "subtotal_minor": 99999})
    page.wait_for_timeout(150)
    assert "999" not in page.locator("#cartTotal").inner_text()
    assert not errors and not external


def test_old_delivery_quote_cannot_authorize_new_address(site):
    page, client, _, requests, errors, external = site
    pending = hold(page, ROOT + "/delivery/quote")
    add_item(page)
    page.locator("#deliveryBtn").click()
    page.locator("#dAddress").fill("Address A")
    page.locator("#dLat").fill("4.6697")
    page.locator("#dLng").fill("-74.0549")
    page.get_by_role("button", name="Cotizar domicilio", exact=True).click()
    pump(page, pending)
    page.locator("#dAddress").fill("Address B")
    # Persist a genuine quote: accepting the stale response would now create
    # a real synthetic delivery order to A, not merely submit an invalid ID.
    quoted = client.post(
        ROOT + "/delivery/quote", json=json.loads(pending[0].request.post_data)
    )
    assert quoted.status_code == 200, quoted.text
    pending[0].fulfill(json=quoted.json())
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("Cotiza el domicilio")
    assert not any(
        method == "POST" and path == ROOT + "/orders" for method, path, _ in requests
    )
    assert not errors and not external


def test_duplicate_click_and_lost_response_reuse_original_intent(site):
    page, client, _, _, errors, external = site
    pending = hold(page, ROOT + "/orders")
    add_item(page)
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    # Native clicks exercise synchronous handler re-entry without Playwright's disabled-button wait.
    page.locator("#checkoutButton").evaluate("(el)=>{el.click();el.click()}")
    pump(page, pending)
    page.wait_for_timeout(100)
    assert len(pending) == 1
    first = json.loads(pending[0].request.post_data)
    # Server commits; network loses the response. Retry must recover the same order.
    response = client.post(ROOT + "/orders", json=first)
    assert response.status_code == 200
    pending[0].abort("failed")
    playwright.expect(page.locator("#checkoutButton")).to_be_enabled()
    page.locator("#checkoutButton").click()
    pump(page, pending, 2)
    second = json.loads(pending[1].request.post_data)
    assert first == second
    replay = client.post(ROOT + "/orders", json=second)
    assert replay.status_code == 200 and replay.json()["id"] == response.json()["id"]
    pending[1].fulfill(status=200, json=replay.json())
    playwright.expect(page.locator("#notice")).to_contain_text("recibido")
    assert not errors and not external


def test_reservation_duplicate_click_uses_one_request_and_retries_same_key(site):
    from datetime import UTC, datetime, timedelta

    page, _, _, _, errors, external = site
    pending = hold(page, ROOT + "/reservations")
    page.goto("https://commerce.test/")
    page.get_by_role("button", name="Reservar", exact=True).click()
    page.locator("#rName").fill("Synthetic")
    page.locator("#rPhone").fill("3005550101")
    page.locator("#rDate").fill(
        (datetime.now(UTC) + timedelta(days=3))
        .replace(hour=12, minute=0, second=0, microsecond=0)
        .strftime("%Y-%m-%dT%H:%M")
    )
    button = page.locator('[data-click="reserve"]')
    button.evaluate("(el)=>{el.click();el.click()}")
    pump(page, pending)
    page.wait_for_timeout(100)
    assert len(pending) == 1
    first = json.loads(pending[0].request.post_data)
    assert first["idempotency_key"]
    pending[0].abort("failed")
    playwright.expect(button).to_be_enabled()
    button.click()
    pump(page, pending, 2)
    assert json.loads(pending[1].request.post_data) == first
    pending[1].fulfill(status=200, json={"public_code": "SYNTHETIC", "party_size": 2})
    playwright.expect(page.locator("#notice")).to_contain_text("SYNTHETIC")
    assert not errors and not external


def test_policy_timeout_loads_ui_and_late_policy_cannot_reopen_navigation(site):
    page, _, _, _, errors, external = site
    pending = hold(page, "/api/browser-policy")
    page.goto("https://commerce.test/")
    page.locator("#menu article").first.wait_for(timeout=6000)
    assert (
        page.evaluate("CommerceUI.safeURL('https://unexpected.test/pay', 'checkout')")
        is None
    )
    pending[0].fulfill(
        json={
            "demo_mode": False,
            "checkout_origins": ["https://unexpected.test"],
            "tracking_origins": [],
        }
    )
    page.wait_for_timeout(100)
    assert (
        page.evaluate("CommerceUI.safeURL('https://unexpected.test/pay', 'checkout')")
        is None
    )
    assert not errors and not external


def test_reordered_food_quotes_keep_latest_result(site):
    page, _, _, _, errors, external = site
    pending = hold(page, ROOT + "/orders/quote")
    add_item(page)
    pump(page, pending)
    page.locator("#promoCode").fill("NEW")
    pump(page, pending, 2)
    pending[1].fulfill(json={"total_minor": 1000, "subtotal_minor": 1000})
    page.wait_for_timeout(50)
    latest = page.locator("#cartTotal").inner_text()
    pending[0].fulfill(json={"total_minor": 99999, "subtotal_minor": 99999})
    page.wait_for_timeout(100)
    assert page.locator("#cartTotal").inner_text() == latest
    assert not errors and not external


def test_checkout_without_uuid_or_browser_storage(site):
    page, _, _, _, errors, external = site
    page.add_init_script("""Object.defineProperty(crypto,'randomUUID',{value:undefined});
      for(const name of ['localStorage','sessionStorage'])Object.defineProperty(window,name,{get(){throw new DOMException('denied','SecurityError')}});""")
    add_item(page)
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("recibido")
    assert not errors and not external


def test_staff_business_change_discards_old_response_and_actions(site):
    from test_browser_security import order

    page, client, _, _, errors, external = site
    original = order(client)
    assert (
        client.post(
            "/api/payments/simulated/"
            + original["payments"][0]["provider_reference"]
            + "/complete"
        ).status_code
        == 200
    )
    url = "/api/operator/restaurants/demo-restaurant-bogota/orders"
    old = client.get(url, headers=staff_headers(client)).json()
    pending = hold(page, url)
    page.goto("https://commerce.test/admin")
    pump(page, pending)
    page.locator("#business").fill("other-business")
    pending[0].fulfill(json=old)
    page.wait_for_timeout(150)
    assert original["public_code"] not in page.locator("#orders").inner_text()
    assert page.get_by_role("button", name="accepted", exact=True).count() == 0
    assert not errors and not external


def test_payment_completion_rejection_does_not_create_second_order(site):
    page, _, _, requests, errors, external = site
    completed = []

    def complete(route):
        completed.append(route.request.url)
        if len(completed) == 1:
            route.fulfill(status=422, json={"detail": "Synthetic completion rejection"})
        else:
            route.fallback()

    page.route("**/api/payments/simulated/*/complete", complete)
    add_item(page)
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text(
        "Synthetic completion rejection"
    )
    playwright.expect(page.locator("#cName")).to_be_disabled()
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("recibido")
    orders = [
        json.loads(body)
        for method, url, body in requests
        if method == "POST" and url == ROOT + "/orders"
    ]
    assert len(orders) == 2 and orders[0] == orders[1]
    assert completed[0] == completed[1]
    assert not errors and not external


def test_reload_recovers_original_order_without_persisting_contact(site):
    page, client, _, requests, errors, external = site
    pending = hold(page, ROOT + "/orders")
    add_item(page)
    page.locator("#cName").fill("Recovery private name")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#cEmail").fill("private@example.test")
    page.locator("#checkoutButton").click()
    pump(page, pending)
    payload = json.loads(pending[0].request.post_data)
    committed = client.post(ROOT + "/orders", json=payload)
    assert committed.status_code == 200, committed.text
    original = committed.json()
    pending[0].abort("failed")
    playwright.expect(page.locator("#notice")).to_contain_text("Reintenta")
    stored = page.evaluate(
        "localStorage.getItem('101.checkout.v1:demo-restaurant-bogota')"
    )
    assert "Recovery private name" not in stored
    assert "3005550101" not in stored and "private@example.test" not in stored
    assert set(json.loads(stored)) == {
        "version",
        "business_id",
        "idempotency_key",
        "recovery_secret",
        "created_at",
    }
    page.reload()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        original["public_code"]
    )
    playwright.expect(page.locator("#cName")).to_have_value("")
    # Page-level interception catches any accidental new order POST after reload.
    page.wait_for_timeout(100)
    assert len(pending) == 1
    staff = client.get(
        ROOT.replace("/api/restaurants", "/api/operator/restaurants") + "/orders",
        headers=staff_headers(client),
    ).json()
    assert len(staff) == 1 and staff[0]["id"] == original["id"]
    assert any(
        method == "POST" and url == ROOT + "/orders/recover"
        for method, url, _ in requests
    )
    assert not errors and not external


def test_unknown_recovery_response_never_submits_new_order(site):
    page, _, _, requests, errors, external = site
    record = {
        "version": 1,
        "business_id": "demo-restaurant-bogota",
        "idempotency_key": "a" * 32,
        "recovery_secret": "b" * 64,
    }
    page.add_init_script(
        "localStorage.setItem('101.checkout.v1:demo-restaurant-bogota',JSON.stringify({..."
        + json.dumps(record)
        + ",created_at:Date.now()}))"
    )
    page.route(
        "**" + ROOT + "/orders/recover",
        lambda route: route.fulfill(status=503, json={"detail": "Unavailable"}),
    )
    page.goto("https://commerce.test/")
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "No hemos enviado otro pedido"
    )
    playwright.expect(page.locator("#cName")).to_be_disabled()
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "No hemos enviado otro pedido"
    )
    assert not any(
        method == "POST" and url == ROOT + "/orders" for method, url, _ in requests
    )
    assert (
        json.loads(
            page.evaluate(
                "localStorage.getItem('101.checkout.v1:demo-restaurant-bogota')"
            )
        )["idempotency_key"]
        == "a" * 32
    )
    assert not errors and not external


def test_recovery_not_found_reuses_original_reference(site):
    page, _, _, _, errors, external = site
    record = {
        "version": 1,
        "business_id": "demo-restaurant-bogota",
        "idempotency_key": "c" * 32,
        "recovery_secret": "d" * 64,
    }
    page.add_init_script(
        "localStorage.setItem('101.checkout.v1:demo-restaurant-bogota',JSON.stringify({..."
        + json.dumps(record)
        + ",created_at:Date.now()}))"
    )
    page.route(
        "**" + ROOT + "/orders/recover",
        lambda route: route.fulfill(status=404, json={"detail": "Not found"}),
    )
    pending = hold(page, ROOT + "/orders")
    add_item(page)
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    pump(page, pending)
    payload = json.loads(pending[0].request.post_data)
    assert payload["idempotency_key"] == record["idempotency_key"]
    assert payload["recovery_secret"] == record["recovery_secret"]
    pending[0].abort("failed")
    assert not errors and not external


def test_expired_recovery_does_not_silently_start_over(site):
    page, _, _, requests, errors, external = site
    page.add_init_script("""localStorage.setItem('101.checkout.v1:demo-restaurant-bogota',JSON.stringify({
      version:1,business_id:'demo-restaurant-bogota',idempotency_key:'e'.repeat(32),
      recovery_secret:'f'.repeat(64),created_at:Date.now()-86400001}));""")
    page.goto("https://commerce.test/")
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "Contacta al restaurante"
    )
    playwright.expect(page.locator("#checkoutButton")).to_be_disabled()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Iniciar una compra diferente", exact=True).click()
    playwright.expect(page.locator("#checkoutButton")).to_be_disabled()
    assert page.evaluate(
        "localStorage.getItem('101.checkout.v1:demo-restaurant-bogota')"
    )
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Iniciar una compra diferente", exact=True).click()
    playwright.expect(page.locator("#checkoutButton")).to_be_enabled()
    assert (
        page.evaluate("localStorage.getItem('101.checkout.v1:demo-restaurant-bogota')")
        is None
    )
    assert not any(
        method == "POST" and url == ROOT + "/orders" for method, url, _ in requests
    )
    assert not errors and not external


def test_recovery_review_never_claims_payment_success_or_offers_payment(site):
    page, _, _, requests, errors, external = site
    page.add_init_script("""localStorage.setItem('101.checkout.v1:demo-restaurant-bogota',JSON.stringify({
      version:1,business_id:'demo-restaurant-bogota',idempotency_key:'a'.repeat(32),
      recovery_secret:'b'.repeat(64),created_at:Date.now()}));""")
    page.route(
        "**" + ROOT + "/orders/recover",
        lambda route: route.fulfill(
            json={
                "id": "synthetic-review",
                "business_id": "demo-restaurant-bogota",
                "public_code": "REVIEW",
                "total_minor": 11900,
                "status": "cancelled",
                "payment_status": "paid",
                "checkout_state": "ready",
                "reconciliation_required": True,
                "payments": [
                    {"provider": "simulated", "provider_reference": "sim_review"}
                ],
            }
        ),
    )
    page.goto("https://commerce.test/")
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "El restaurante debe revisar este pago"
    )
    assert "Pago confirmado" not in page.locator("#checkoutRecovery").inner_text()
    assert (
        page.get_by_role("button", name="Continuar con el pago", exact=True).count()
        == 0
    )
    assert page.get_by_role("button", name="Hacer otro pedido", exact=True).count() == 0
    assert not any(
        method == "POST" and url.endswith("/complete") for method, url, _ in requests
    )
    assert not errors and not external


def test_missing_secure_randomness_prevents_unsafe_checkout(site):
    page, _, _, requests, errors, external = site
    page.add_init_script(
        "Object.defineProperty(crypto,'getRandomValues',{value:undefined});"
    )
    add_item(page)
    page.locator("#cName").fill("Synthetic")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#notice")).to_contain_text("referencia segura")
    assert not any(
        method == "POST" and url == ROOT + "/orders" for method, url, _ in requests
    )
    assert not errors and not external


def test_exact_retry_of_cancelled_paid_order_never_pays_or_claims_success(site):
    page, client, _, requests, errors, external = site
    pending = hold(page, ROOT + "/orders")
    add_item(page)
    page.locator("#cName").fill("Synthetic late payment")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    pump(page, pending)
    payload = json.loads(pending[0].request.post_data)
    created = client.post(ROOT + "/orders", json=payload)
    assert created.status_code == 200, created.text
    original = created.json()
    cancelled = client.patch(
        "/api/operator/orders/" + original["id"],
        json={"status": "cancelled"},
        headers=staff_headers(client),
    )
    assert cancelled.status_code == 200, cancelled.text
    paid = client.post(
        "/api/payments/simulated/"
        + original["payments"][0]["provider_reference"]
        + "/complete"
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["reconciliation_required"] is True
    pending[0].abort("failed")
    playwright.expect(page.locator("#notice")).to_contain_text("Reintenta")
    page.locator("#checkoutButton").click()
    pump(page, pending, 2)
    assert json.loads(pending[1].request.post_data) == payload
    replay = client.post(ROOT + "/orders", json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == original["id"]
    pending[1].fulfill(json=replay.json())
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "El restaurante debe revisar este pago"
    )
    assert "recibido" not in page.locator("#notice").inner_text()
    assert "Pago demo aprobado" not in page.locator("#notice").inner_text()
    assert not any(
        method == "POST" and url.endswith("/complete") for method, url, _ in requests
    )
    assert (
        page.get_by_role("button", name="Continuar con el pago", exact=True).count()
        == 0
    )
    assert not errors and not external


def test_cancellation_during_payment_completion_has_no_success_notice(site):
    page, client, _, _, errors, external = site
    observed = []

    def late_payment(route):
        orders = client.get(
            "/api/operator/restaurants/demo-restaurant-bogota/orders",
            headers=staff_headers(client),
        ).json()
        assert len(orders) == 1
        current = orders[0]
        cancelled = client.patch(
            "/api/operator/orders/" + current["id"],
            json={"status": "cancelled"},
            headers=staff_headers(client),
        )
        assert cancelled.status_code == 200, cancelled.text
        paid = client.post(
            "/api/payments/simulated/"
            + current["payments"][0]["provider_reference"]
            + "/complete"
        )
        assert paid.status_code == 200, paid.text
        assert paid.json()["reconciliation_required"] is True
        observed.append(paid.json()["id"])
        route.fulfill(json=paid.json())

    page.route("**/api/payments/simulated/*/complete", late_payment)
    add_item(page)
    page.locator("#cName").fill("Synthetic concurrent cancellation")
    page.locator("#cPhone").fill("3005550101")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "El restaurante debe revisar este pago"
    )
    assert len(observed) == 1
    assert "recibido" not in page.locator("#notice").inner_text()
    assert "Pago demo aprobado" not in page.locator("#notice").inner_text()
    assert not errors and not external


def test_wompi_return_without_storage_blocks_accidental_new_purchase(site):
    page, _, _, requests, errors, external = site
    page.goto('https://commerce.test/?id=synthetic-return&status=APPROVED')
    playwright.expect(page.locator('#checkoutRecovery')).to_contain_text('no vuelvas a pagar')
    playwright.expect(page.locator('#checkoutButton')).to_be_disabled()
    assert not any(method == 'POST' and url == ROOT + '/orders' for method, url, _ in requests)
    assert 'Pago confirmado' not in page.locator('#checkoutRecovery').inner_text()
    assert not errors and not external


def test_new_purchase_clears_previous_wompi_return_hint(site):
    page, _, _, requests, errors, external = site
    page.add_init_script("""localStorage.setItem('101.checkout.v1:demo-restaurant-bogota',JSON.stringify({
      version:1,business_id:'demo-restaurant-bogota',idempotency_key:'a'.repeat(32),
      recovery_secret:'b'.repeat(64),created_at:Date.now()}));""")
    recovery_bodies = []
    def recovered(route):
        recovery_bodies.append(json.loads(route.request.post_data))
        route.fulfill(json={'id':'first-order','business_id':'demo-restaurant-bogota',
                            'public_code':'FIRST','total_minor':11900,'status':'placed',
                            'payment_status':'paid','checkout_state':'ready',
                            'reconciliation_required':False,'payments':[{'provider':'wompi_sandbox'}]})
    page.route('**' + ROOT + '/orders/recover', recovered)
    page.goto('https://commerce.test/?id=old-transaction')
    playwright.expect(page.locator('#checkoutRecovery')).to_contain_text('Pago confirmado')
    assert recovery_bodies[0]['wompi_transaction_id'] == 'old-transaction'
    page.get_by_role('button', name='Hacer otro pedido', exact=True).click()
    assert 'id=' not in page.url
    playwright.expect(page.locator('#checkoutButton')).to_be_enabled()
    assert 'Volviste del pago' not in page.locator('#checkoutRecovery').inner_text()
    assert not errors and not external
