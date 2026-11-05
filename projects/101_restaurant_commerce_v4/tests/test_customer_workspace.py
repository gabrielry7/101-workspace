"""Customer projections use canonical contacts/payments and stay tenant scoped."""

from types import SimpleNamespace
import pytest
from test_payment_durability_m3 import factory  # noqa: F401 - shared fixture
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import (
    BUSINESS,
    OTHER,
    PASSWORD,
    seed_campaign_demo,
)
from world_model.restaurant_commerce.customer_workspace_demo import seed
from world_model.restaurant_commerce.models import (
    Customer,
    Payment,
    StaffMembership,
    LoyaltyAccount,
)
from world_model.restaurant_commerce.customer_signup_models import CustomerMembership

ROOT = "/api/operator/restaurants/" + BUSINESS + "/customers"


@pytest.fixture
def env(factory):
    app = create_app(
        engine=factory.kw["bind"], demo_mode=True, payment_recovery_enabled=False
    )
    with factory() as s:
        seed_campaign_demo(s)
        seed(s, 80)
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/staff/login",
                json={"username": "campaign.manager", "password": PASSWORD},
                headers={"X-101-Login": "1"},
            ).status_code
            == 200
        )
        yield SimpleNamespace(client=client, factory=factory, app=app)


def test_paginated_search_filters_and_null_phone(env):
    first = env.client.get(ROOT).json()
    assert first["total"] == 80 and len(first["items"]) == 25
    second = env.client.get(ROOT, params={"offset": 25}).json()
    assert not ({r["id"] for r in first["items"]} & {r["id"] for r in second["items"]})
    rows = env.client.get(ROOT, params={"q": "lucía"}).json()
    assert rows["count"] == 4
    assert all("Lucía" in r["name"] for r in rows["items"])
    email = env.client.get(ROOT, params={"q": "cliente00005@"}).json()
    assert email["count"] == 1 and email["items"][0]["phone"] is None
    assert env.client.get(ROOT, params={"q": "%"}).json()["count"] == 0
    assert env.client.get(ROOT, params={"q": "_"}).json()["count"] == 0
    registered = env.client.get(
        ROOT, params={"kind": "registered", "limit": 100}
    ).json()
    assert registered["count"] == first["registered"] and all(
        c["registered"] for c in registered["items"]
    )
    assert env.client.get(ROOT, params={"limit": 101}).status_code == 422
    assert env.client.get(ROOT, params={"offset": -1}).status_code == 422
    assert env.client.get(ROOT, params={"kind": "bogus"}).status_code == 422


def test_scope_session_and_membership_revocation(env):
    assert env.client.get(ROOT.replace(BUSINESS, OTHER)).status_code == 403
    with env.factory() as s:
        foreign = s.scalar(select(Customer).where(Customer.business_id == OTHER)).id
    assert env.client.get(ROOT + "/" + foreign).status_code == 404
    assert env.client.get(ROOT + "/does-not-exist").status_code == 404
    with TestClient(env.app) as anon:
        assert anon.get(ROOT).status_code == 401
    with env.factory() as s:
        m = s.scalar(
            select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
        )
        s.delete(m)
        s.commit()
    assert env.client.get(ROOT).status_code == 403
    assert env.client.get(ROOT + "/workspace-demo-00001").status_code == 403


def test_partial_full_refund_read_only_and_test_separation(env):
    with env.factory() as s:
        before = (
            s.scalar(select(func.count()).select_from(CustomerMembership)),
            s.scalar(select(func.count()).select_from(LoyaltyAccount)),
        )
    data = env.client.get(ROOT + "/workspace-demo-00001").json()
    assert data["money"] == [
        {
            "scope": "test",
            "currency": "COP",
            "paid_orders": 1,
            "captured_minor": 24900,
            "refunded_minor": 5000,
            "net_minor": 19900,
        }
    ]
    assert data["orders"][0]["identity_verified"] is False
    assert data["membership"]["scope"] == "test" and data["permissions"] == []
    with env.factory() as s:
        assert before == (
            s.scalar(select(func.count()).select_from(CustomerMembership)),
            s.scalar(select(func.count()).select_from(LoyaltyAccount)),
        )
        p = s.get(Payment, "workspace-example-payment")
        p.status = "refunded"
        s.commit()
    assert (
        env.client.get(ROOT + "/workspace-demo-00001").json()["money"][0]["net_minor"]
        == 0
    )
    with env.factory() as s:
        p = s.get(Payment, "workspace-example-payment")
        p.provider = "wompi"
        s.commit()
    assert (
        env.client.get(ROOT + "/workspace-demo-00001").json()["money"][0]["scope"]
        == "provider"
    )


def test_permission_evidence_not_legacy_opt_in(env):
    with env.factory() as s:
        customer = s.scalar(
            select(Customer).where(
                Customer.business_id == BUSINESS,
                Customer.email == "persona2@example.test",
            )
        )
        customer.marketing_opt_in = True
        s.commit()
        cid = customer.id
    data = env.client.get(ROOT + "/" + cid).json()
    assert data["permissions"][0]["state"] == "withdrawn"
    assert data["permissions"][0]["scope"] == "test"
    assert "destination" not in data["permissions"][0]


def test_assets_html_and_api_cache_contract(env):
    import re

    page = env.client.get("/workspace/customers")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    assert "script-src 'self'" in page.headers["content-security-policy"]
    for url in re.findall(
        r'(?:src|href)="(/workspace-assets/assets/[^\"]+)"', page.text
    ):
        asset = env.client.get(url)
        assert asset.status_code == 200
        assert "immutable" in asset.headers["cache-control"]
    assert env.client.get("/workspace-assets/assets/../../api.py").status_code == 404
    assert env.client.get(ROOT).headers["cache-control"] == "no-store"
    assert "slug" in env.client.get("/api/staff/me").json()["businesses"][0]
