"""Period drill-through, canonical money, tenant boundaries and home evidence."""

from test_sales_workspace import env, factory  # noqa: F401
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.workspace_demo import seed_workspace
from world_model.restaurant_commerce.models import Payment
from world_model.restaurant_commerce.workspace_period import period

ROOT = f"/api/operator/restaurants/{BUSINESS}"


def test_home_period_drillthrough_and_refunds(env):
    params = {"date_from": "2026-11-03", "date_to": "2026-11-03"}
    d = env.client.get(ROOT + "/workspace/overview", params=params).json()
    assert d["orders"] == 31 and d["new_customers"] == 4
    assert d["money"][0]["scope"] == "test"
    assert sum(m["refunds"] for m in d["money"]) == 5000
    assert all(m["net"] == m["captured"] - m["refunds"] for m in d["money"])
    assert "date_from=2026-11-03" in d["links"]["orders"]
    rows = env.client.get(ROOT + "/sales", params={**params, "status": "all"}).json()
    assert rows["count"] == d["orders"]
    customers = env.client.get(ROOT + "/customers", params=params).json()
    assert customers["count"] == d["new_customers"]
    assert d["activity"] and all(
        e["href"].startswith("/workspace/") for e in d["activity"]
    )
    empty = env.client.get(
        ROOT + "/workspace/overview",
        params={"date_from": "2020-01-01", "date_to": "2020-01-01"},
    ).json()
    assert empty["orders"] == 0 and empty["money"] == [] and empty["activity"] == []
    assert empty[
        "attention"
    ]  # current pending work is explicitly independent of period
    with env.factory() as s:
        s.get(Payment, "workspace-example-payment").status = "refunded"
        s.commit()
    after = env.client.get(ROOT + "/workspace/overview", params=params).json()
    assert sum(m["refunds"] for m in after["money"]) == 24900


def test_campaign_projection_dates_and_scope(env):
    with env.factory() as s:
        seed_workspace(s)
    root = ROOT + "/workspace/campaigns"
    d = env.client.get(root).json()
    assert d["count"] == 3
    assert {r["state"] for r in d["items"]} == {"draft", "approved", "scheduled"}
    assert all(r["subject"] and r["channel"] == "email" for r in d["items"])
    assert env.client.get(root, params={"state": "draft"}).json()["count"] == 1
    assert env.client.get(root, params={"q": "%"}).json()["count"] == 0
    assert (
        env.client.get(
            root, params={"date_from": "2020-01-01", "date_to": "2020-01-02"}
        ).json()["count"]
        == 0
    )
    assert env.client.get(root.replace(BUSINESS, OTHER)).status_code == 403
    assert (
        env.client.get(
            ROOT.replace(BUSINESS, OTHER) + "/workspace/overview"
        ).status_code
        == 403
    )
    for p in (
        {"date_from": "bad", "date_to": "2026-01-01"},
        {"date_from": "2026-11-05", "date_to": "2026-11-01"},
        {"date_from": "2020-01-01", "date_to": "2026-11-01"},
    ):
        assert env.client.get(root, params=p).status_code == 422
        assert env.client.get(ROOT + "/workspace/overview", params=p).status_code == 422
    for area in ("home", "campaigns", "analytics", "identity"):
        assert env.client.get("/workspace/" + area).status_code == 200


def test_bogota_boundaries_and_no_optional_filter():
    assert period() is None
    p = period("2026-11-03", "2026-11-03")
    assert p["start"].isoformat() == "2026-11-03T05:00:00+00:00"
    assert p["end"].isoformat() == "2026-11-04T05:00:00+00:00"
