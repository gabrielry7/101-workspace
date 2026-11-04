"""101-033: first checkout attribution is stable across retries."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from test_campaigns import approved, dispatch, env, factory, report
from world_model.restaurant_commerce import campaigns as c
from world_model.restaurant_commerce.campaign_demo import BUSINESS, CLOCK
from world_model.restaurant_commerce.models import Order, Payment


@pytest.mark.parametrize("cookie_change", ["absent", "replaced", "expired"])
def test_attributed_checkout_retry_uses_original_attribution(env, cookie_change):
    preview = approved(env)
    dispatch(env)
    job = next(j for j in report(env, preview)["deliveries"] if j["state"] == "accepted")
    assert env.client.get(job["tracking_url"], follow_redirects=False).status_code == 303
    root = "/api/restaurants/" + BUSINESS
    item = env.client.get(root + "/storefront").json()["menus"][0]["categories"][0]["items"][0]
    body = {"customer": {"phone": "+573005550100", "name": "Synthetic"},
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "payment_provider": "simulated", "idempotency_key": "audit-cookie-replay",
            "recovery_secret": "a" * 64}
    first = env.client.post(root + "/orders", json=body)
    assert first.status_code == 200, first.text
    cookie = "campaign_visit_" + c.digest(BUSINESS)[:16]
    if cookie_change == "expired":
        env.options["clock"] = lambda: CLOCK + timedelta(days=90)
    else:
        env.client.cookies.delete(cookie)
        if cookie_change == "replaced":
            env.client.cookies.set(cookie, "another-invalid-visit")
    replay = env.client.post(root + "/orders", json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    with env.factory() as session:
        order = session.get(Order, first.json()["id"])
        assert order.source_channel != "web" and order.external_source_ref
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        assert session.scalar(select(func.count()).select_from(Payment)) == 1
    changed = dict(body, items=[{"menu_item_id": item["id"], "quantity": 2}])
    assert env.client.post(root + "/orders", json=changed).status_code == 409
    changed = dict(body, recovery_secret="b" * 64)
    assert env.client.post(root + "/orders", json=changed).status_code == 409
