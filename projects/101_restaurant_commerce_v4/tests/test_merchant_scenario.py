"""Canonical demo data agrees across screens and stays outside live reporting."""

from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select
from test_sales_workspace import login

from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.campaign_models import (
    CampaignOrderCredit,
    CampaignSettings,
)
from world_model.restaurant_commerce.merchant_scenario_demo import enrich, key
from world_model.restaurant_commerce.models import Customer, Order
from world_model.restaurant_commerce.monthly_report_pdf import render
from world_model.restaurant_commerce.monthly_reports import build, month_period
from world_model.restaurant_commerce.sales_metrics import money_totals
from world_model.restaurant_commerce.workspace_demo import app_for_demo

ANCHOR = datetime(2026, 11, 16, 5, 15, tzinfo=UTC)
ROOT = f"/api/operator/restaurants/{BUSINESS}"


@pytest.fixture
def app(tmp_path):
    return app_for_demo("sqlite:///" + str(tmp_path / "scenario.db"))


def test_additive_repeatable_scenario_and_source_totals(app):
    with app.state.session_factory() as s:
        old_orders = {
            o.id: (o.created_at, o.total_minor, o.status)
            for o in s.scalars(select(Order))
        }
        old_customers = {
            c.id: (c.created_at, c.name) for c in s.scalars(select(Customer))
        }
    result = enrich(app, as_of=ANCHOR)
    assert result["customers"] == 120 and result["orders"] == 411
    assert enrich(app, as_of=datetime(2027, 1, 2, tzinfo=UTC))["added"] is False
    with app.state.session_factory() as s:
        assert {
            i: (
                s.get(Order, i).created_at,
                s.get(Order, i).total_minor,
                s.get(Order, i).status,
            )
            for i in old_orders
        } == old_orders
        assert {
            i: (s.get(Customer, i).created_at, s.get(Customer, i).name)
            for i in old_customers
        } == old_customers
        for month in ["2026-10", "2026-09"]:
            doc = build(s, BUSINESS, month, "COP", now=ANCHOR, demo=True)
            row = doc["periods"][0]["sales"]
            expected = next(
                r
                for r in money_totals(
                    s, BUSINESS, month_period(month, "America/Bogota", ANCHOR)
                )
                if r["scope"] == "test"
            )
            assert row["net"] == expected["captured"] - expected["refunds"] > 0
            assert row["paid_orders"] == expected["paid_orders"] > 100
            assert row["refunds"] > 0
            assert doc["periods"][0]["website"]["status"] == "disconnected"
            pdf = PdfReader(BytesIO(render(doc)))
            assert len(pdf.pages) == 1
            assert "datos ficticios" in pdf.pages[0].extract_text()
            live = build(s, BUSINESS, month, "COP", now=ANCHOR)
            assert live["periods"][0]["sales"]["net"] is None
            assert live["campaigns"] == []
        # Every fictional conversion has a paid order in the same business.
        for credit in s.scalars(select(CampaignOrderCredit)):
            order = s.get(Order, credit.order_id)
            assert order.business_id == BUSINESS and credit.scope == "test"
            assert any(
                p.provider == "simulated" and p.status == "paid" for p in order.payments
            )
        recent = s.get(Order, key("order-410"))
        assert recent.created_at <= ANCHOR.replace(tzinfo=None)


@pytest.mark.parametrize("mode", ["production", "not_demo", "live_scope"])
def test_refuse_non_demo_before_writes(app, mode):
    if mode == "production":
        app.state.environment = "production"
    if mode == "not_demo":
        app.state.demo_mode = False
    if mode == "live_scope":
        with app.state.session_factory() as s:
            s.get(CampaignSettings, BUSINESS).scope = "live"
            s.commit()
    with pytest.raises(ValueError):
        enrich(app, as_of=ANCHOR)
    with app.state.session_factory() as s:
        assert s.get(Customer, key("customer-0")) is None


def test_http_report_opt_in_scope_and_drillthrough(app):
    enrich(app, as_of=ANCHOR)
    with TestClient(app) as client:
        login(client)
        params = {"date_from": "2026-11-10", "date_to": "2026-11-16"}
        home = client.get(ROOT + "/workspace/overview", params=params).json()
        sales = client.get(ROOT + "/sales", params={**params, "status": "all"}).json()
        customers = client.get(ROOT + "/customers", params=params).json()
        assert home["orders"] == sales["count"] > 0
        assert home["money"] == sales["money"]
        assert home["new_customers"] == customers["count"] > 0
        headers = {"X-101-CSRF": client.get("/api/staff/me").json()["csrf"]}

        def report():
            r = client.post(
                ROOT + "/reports",
                params={"month": "2026-10", "demo": "true"},
                headers=headers,
            )
            assert r.status_code == 200, r.text
            return r.json()

        assert report()["periods"][0]["sales"]["net"] is None
        app.state.monthly_report_demo_business = OTHER
        assert report()["demo"] is False
        app.state.monthly_report_demo_business = BUSINESS
        d = report()
        assert d["demo"] is True and d["periods"][0]["sales"]["net"] > 0
        assert client.get(ROOT + "/reports/" + d["id"] + "/pdf").status_code == 200
        assert (
            client.get(
                ROOT.replace(BUSINESS, OTHER) + "/reports/" + d["id"] + "/pdf"
            ).status_code
            == 403
        )
        app.state.demo_mode = False
        assert report()["demo"] is False
