"""Temporary local-review shortcut reuses ordinary scoped sessions."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.workspace_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.models import StaffAccount


def test_demo_shortcut_session_scope_and_retirement(tmp_path):
    app = app_for_demo("sqlite:///" + str(tmp_path / "demo.db"))
    with TestClient(app) as c:
        headers = {"X-101-Login": "1"}
        assert (
            c.post(
                "/api/staff/login",
                json={"username": "101", "password": "wrong"},
                headers=headers,
            ).status_code
            == 401
        )
        assert (
            c.post(
                "/api/staff/login",
                json={"username": "101", "password": "101"},
                headers=headers,
            ).status_code
            == 200
        )
        me = c.get("/api/staff/me").json()
        assert me["username"] == "campaign.manager"
        assert [b["business_id"] for b in me["businesses"]] == [BUSINESS]
        assert (
            c.get(f"/api/operator/restaurants/{OTHER}/workspace/overview").status_code
            == 403
        )
        assert (
            c.post("/api/staff/logout", headers={"X-101-CSRF": me["csrf"]}).status_code
            == 200
        )
        assert c.get("/api/staff/me").status_code == 401
        del app.state.workspace_demo_login
        assert (
            c.post(
                "/api/staff/login",
                json={"username": "101", "password": "101"},
                headers=headers,
            ).status_code
            == 401
        )
    with app.state.session_factory() as s:
        assert (
            s.scalar(select(StaffAccount).where(StaffAccount.username == "101")) is None
        )


def test_ordinary_application_has_no_shortcut(tmp_path):
    app = create_app(
        database_url="sqlite:///" + str(tmp_path / "normal.db"),
        demo_mode=True,
        payment_recovery_enabled=False,
    )
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/staff/login",
                json={"username": "101", "password": "101"},
                headers={"X-101-Login": "1"},
            ).status_code
            == 401
        )
