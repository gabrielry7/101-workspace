"""Combined entry uses the existing session and both subsystem fixture owners."""

from fastapi.testclient import TestClient
from sqlalchemy import select, func
from world_model.restaurant_commerce.loyalty_workspace_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.campaign_models import Campaign
from world_model.restaurant_commerce.loyalty_models import LoyaltyStrategy
from world_model.restaurant_commerce.models import Order


def test_combined_login_capabilities_and_preserved_restart(tmp_path):
    db = "sqlite:///" + str(tmp_path / "combined.db")
    app = app_for_demo(db)

    def counts(app):
        with app.state.session_factory() as s:
            return [
                s.scalar(select(func.count()).select_from(m))
                for m in (Campaign, LoyaltyStrategy, Order)
            ]

    before = counts(app)
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/staff/login",
                json={"username": "101", "password": "101"},
                headers={"X-101-Login": "1"},
            ).status_code
            == 200
        )
        root = f"/api/operator/restaurants/{BUSINESS}"
        cap = c.get(root + "/loyalty-config/capabilities").json()
        assert cap["configuration_enabled"]
        assert (
            not cap["execution_enabled"]
            and not cap["assignment_enabled"]
            and not cap["analytics_enabled"]
        )
        assert c.get(root + "/workspace/campaigns").json()["count"] == 3
        assert c.get(root + "/sales", params={"status": "all"}).json()["count"] >= 31
        assert c.get(root + "/loyalty-config/programs").status_code == 200
        assert (
            c.get(
                root.replace(BUSINESS, OTHER) + "/loyalty-config/programs"
            ).status_code
            == 403
        )
        assert c.get(root + "/campaigns").json()["clock"].startswith("2026-11-03")
    with app.state.session_factory() as s:
        campaign = s.scalar(select(Campaign).where(Campaign.business_id == BUSINESS))
        changed_id = campaign.id
        campaign.state = "cancelled"
        s.commit()
    again = app_for_demo(db)
    assert counts(again) == before
    with again.state.session_factory() as s:
        assert s.get(Campaign, changed_id).state == "cancelled"
