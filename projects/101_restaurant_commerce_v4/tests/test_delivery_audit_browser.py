"""101-033: active deliveries cannot depend on the newest pickup-order page."""

from uuid import uuid4

from staff_helpers import staff_headers
from test_browser_security import browser, cart, playwright, site

ROOT = "/api/restaurants/demo-restaurant-bogota"
OP = "/api/operator/restaurants/demo-restaurant-bogota"


def test_old_delivery_remains_dispatchable_after_newer_pickups(site):
    page, client, _, _, errors, external = site
    headers = staff_headers(client)
    quote = client.post(ROOT + "/delivery/quote", json={"destination": {
        "address_line": "Synthetic address", "city": "Bogotá", "latitude": 4.6697,
        "longitude": -74.0549}})
    assert quote.status_code == 200, quote.text
    body = {"customer": {"name": "Synthetic", "phone": "3005550101"}, "items": cart(client),
            "idempotency_key": uuid4().hex, "fulfillment_type": "delivery",
            "delivery_quote_id": quote.json()["id"]}
    result = client.post(ROOT + "/orders", json=body)
    assert result.status_code == 200, result.text
    order = result.json()
    assert client.post("/api/payments/simulated/" + order["payments"][0]["provider_reference"] + "/complete").status_code == 200
    assert client.patch("/api/operator/orders/" + order["id"], json={"status": "accepted"}, headers=headers).status_code == 200
    for _ in range(51):
        newer = client.post(ROOT + "/orders", json={
            "customer": body["customer"], "items": body["items"], "idempotency_key": uuid4().hex})
        assert newer.status_code == 200, newer.text
    latest = client.get(OP + "/orders").json()
    assert len(latest) == 50 and order["id"] not in {o["id"] for o in latest}
    assert order["id"] in {d["order_id"] for d in client.get(OP + "/deliveries").json()}
    page.goto("https://commerce.test/delivery")
    button = page.get_by_role("button", name="Despachar courier", exact=True)
    playwright.expect(button).to_be_visible(timeout=3000)
    button.click()
    playwright.expect(page.locator("#rows")).to_contain_text("courier_assigned")
    assert not errors and not external
