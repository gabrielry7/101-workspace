"""Explicit named test staff; HTTP login remains the only credential issuer."""

from sqlalchemy import select

from world_model.restaurant_commerce.models import StaffAccount
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID
from world_model.restaurant_commerce.staff import provision

PASSWORD = "synthetic staff passphrase only"


def staff_headers(
    client,
    *,
    role="manager",
    platform_admin=False,
    business_id=DEMO_BUSINESS_ID,
    name="test.manager",
):
    existing = client.get("/api/staff/me")
    if existing.status_code == 200 and existing.json()["username"] == name:
        return {
            "X-101-CSRF": existing.json()["csrf"],
            "Cookie": "commerce_staff=" + client.cookies["commerce_staff"],
        }
    with client.app.state.session_factory() as session:
        if not session.scalar(
            select(StaffAccount).where(StaffAccount.username == name)
        ):
            provision(
                session,
                name,
                PASSWORD,
                business_id,
                role,
                actor="test-fixture",
                platform_admin=platform_admin,
            )
    response = client.post(
        "/api/staff/login",
        json={"username": name, "password": PASSWORD},
        headers={"X-101-Login": "1"},
    )
    assert response.status_code == 200, response.text
    me = client.get("/api/staff/me")
    assert me.status_code == 200, me.text
    return {
        "X-101-CSRF": me.json()["csrf"],
        "Cookie": "commerce_staff=" + client.cookies["commerce_staff"],
    }
