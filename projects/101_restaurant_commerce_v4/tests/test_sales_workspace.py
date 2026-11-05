"""Sales is a scoped projection of canonical orders and the existing mutation path."""

from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory  # noqa: F401
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import (
    BUSINESS,
    OTHER,
    PASSWORD,
    seed_campaign_demo,
)
from world_model.restaurant_commerce.customer_workspace_demo import seed
from world_model.restaurant_commerce.sales_workspace_demo import seed_sales
from world_model.restaurant_commerce.models import Order, Payment

ROOT = f"/api/operator/restaurants/{BUSINESS}/sales"


@pytest.fixture
def env(factory):
    app = create_app(
        engine=factory.kw["bind"], demo_mode=True, payment_recovery_enabled=False
    )
    with factory() as s:
        seed_campaign_demo(s)
        seed(s, 80)
        seed_sales(s)
    with TestClient(app) as client:
        login(client)
        yield SimpleNamespace(client=client, factory=factory, app=app)


def login(client, user="campaign.manager"):
    assert (
        client.post(
            "/api/staff/login",
            json={"username": user, "password": PASSWORD},
            headers={"X-101-Login": "1"},
        ).status_code
        == 200
    )


def patch(env, oid, status, version):
    return env.client.patch(
        "/api/operator/orders/" + oid,
        json={
            "status": status,
            "expected_version": version,
            "reason": "Synthetic operator confirmation",
        },
        headers={"X-101-CSRF": env.client.get("/api/staff/me").json()["csrf"]},
    )


def test_listing_scope_filters_and_assets(env):
    c = env.client
    d = c.get(ROOT).json()
    assert d["count"] == 25 and len(d["items"]) == 25 and d["review_count"] == 1
    assert d["counts"]["ready"] == 5
    all_rows = c.get(ROOT, params={"status": "all"}).json()
    second = c.get(ROOT, params={"status": "all", "offset": 25}).json()
    assert all_rows["count"] == 31 and len(second["items"]) == 6
    assert not {o["id"] for o in all_rows["items"]} & {o["id"] for o in second["items"]}
    assert c.get(ROOT, params={"q": "demo-201"}).json()["count"] == 1
    assert c.get(ROOT, params={"q": "%"}).json()["count"] == 0
    assert c.get(ROOT, params={"status": "ready"}).json()["count"] == 5
    assert c.get(ROOT, params={"status": "madeup"}).status_code == 422
    assert c.get(ROOT, params={"limit": 101}).status_code == 422
    assert c.get(ROOT.replace(BUSINESS, OTHER)).status_code == 403
    assert c.get(ROOT + "/workspace-foreign-sale").status_code == 404
    assert c.get("/workspace/sales").status_code == 200
    assert c.get(ROOT).headers["cache-control"] == "no-store"
    with TestClient(env.app) as anon:
        assert anon.get(ROOT).status_code == 401


def test_actions_match_existing_mutation_version_and_roles(env):
    oid = "workspace-sale-000"
    detail = env.client.get(ROOT + "/" + oid).json()
    assert detail["access_token"] is None
    assert next(a for a in detail["actions"] if a["status"] == "accepted")["allowed"]
    assert not next(a for a in detail["actions"] if a["status"] == "cancelled")[
        "allowed"
    ]
    old = detail["version"]
    for target in ["accepted", "preparing", "ready", "completed"]:
        d = env.client.get(ROOT + "/" + oid).json()
        response = patch(env, oid, target, d["version"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target
    assert patch(env, oid, "completed", old).status_code == 409
    login(env.client, "sales.viewer")
    assert env.client.get(ROOT).status_code == 200
    assert env.client.get(ROOT + "/" + oid).status_code == 200
    assert patch(env, "workspace-sale-001", "ready", 1).status_code == 403


def test_blocked_payment_review_delivery_and_cash(env):
    for oid, target in [
        ("workspace-sale-012", "accepted"),
        ("workspace-sale-020", "completed"),
    ]:
        d = env.client.get(ROOT + "/" + oid).json()
        action = next(a for a in d["actions"] if a["status"] == target)
        assert not action["allowed"] and action["reason"]
        assert patch(env, oid, target, d["version"]).status_code == 409
    d = env.client.get(ROOT + "/workspace-sale-004").json()
    assert "placed" not in [a["status"] for a in d["actions"]]
    oid = "workspace-sale-008"
    d = env.client.get(ROOT + "/" + oid).json()
    assert d["payment_status"] == "unpaid"
    assert (
        next(a for a in d["actions"] if a["status"] == "completed")["confirmation"]
        == "cash_received"
    )
    r = patch(env, oid, "completed", d["version"])
    assert r.status_code == 200, r.text
    d = env.client.get(ROOT + "/" + oid).json()
    assert d["payment_status"] == "paid" and d["money"][0]["scope"] == "cash"
    assert d["money"][0]["net_minor"] == d["total_minor"]


def test_refunds_snapshot_and_read_only_projection(env):
    # The customer fixture carries a partial historical snapshot and canonical refund.
    with env.factory() as s:
        p = s.get(Payment, "workspace-example-payment")
        oid = p.order_id
        before = s.get(Order, oid).customer_snapshot_json
        version = s.get(Order, oid).version
    d = env.client.get(ROOT + "/" + oid).json()
    assert d["money"] == [
        {
            "scope": "test",
            "currency": "COP",
            "captured_minor": 24900,
            "refunded_minor": 5000,
            "net_minor": 19900,
        }
    ]
    assert d["customer_name"] is None and d["customer_phone"] == ""
    assert d["identity_verified"] is False
    with env.factory() as s:
        assert s.get(Order, oid).customer_snapshot_json == before
        assert s.get(Order, oid).version == version
        s.get(Payment, "workspace-example-payment").status = "refunded"
        s.commit()
    d = env.client.get(ROOT + "/" + oid).json()
    assert d["money"][0]["refunded_minor"] == 24900 and d["money"][0]["net_minor"] == 0
    # Existing promotion discount is already in order total, not subtracted again.
    d = env.client.get(ROOT + "/workspace-sale-000").json()
    assert d["subtotal_minor"] == 24900 and d["discount_minor"] == 1000
    assert d["money"][0]["captured_minor"] == d["total_minor"] == 23900
