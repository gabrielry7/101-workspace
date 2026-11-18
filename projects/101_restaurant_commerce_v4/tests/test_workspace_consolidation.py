"""Lossless HTML entry + native Sales boundaries, using isolated canonical records."""

# ruff: noqa: F811 -- pytest imports fixtures by name.

import json
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory  # noqa: F401
from test_sales_workspace import ROOT, env, login  # noqa: F401
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.errors import InvalidTransitionError
from world_model.restaurant_commerce.models import (
    Customer,
    Order,
    Reservation,
    StaffAccount,
    StaffMembership,
    StaffSession,
    utcnow,
)
from world_model.restaurant_commerce.service import RestaurantCommerceService
from world_model.restaurant_commerce.workspace_access import (
    LEGACY_PAGES,
    WORKSPACE_PAGES,
    safe_destination,
)


def seed_reservations(app):
    with app.state.session_factory() as s:
        customer = s.scalar(select(Customer).where(Customer.business_id == BUSINESS))
        for i in range(28):
            s.add(
                Reservation(
                    id=f"workspace-reservation-{i}",
                    public_code=f"RSV-{i:03}",
                    business_id=BUSINESS,
                    customer_id=customer.id,
                    customer_snapshot_json=json.dumps(
                        {"name": "Invitada de prueba", "phone": "+573005550100"}
                    ),
                    starts_at=utcnow() + timedelta(days=i + 1),
                    party_size=2,
                    status="requested",
                    notes="Reserva ficticia para verificar la interfaz.",
                )
            )
        s.commit()


def test_all_staff_html_uses_one_entry_without_changing_public_or_api_access(env):
    with TestClient(env.app) as c:
        for path in sorted(LEGACY_PAGES | WORKSPACE_PAGES):
            r = c.get(path, params={"business_id": BUSINESS}, follow_redirects=False)
            assert r.status_code == 307, (path, r.text)
            assert urlsplit(r.headers["location"]).path == "/workspace/login"
            target = parse_qs(urlsplit(r.headers["location"]).query)["next"][0]
            assert urlsplit(target).path == path
            assert r.headers["cache-control"] == "no-store"
            assert "base-uri 'none'" in r.headers["content-security-policy"]
        assert c.get("/workspace/login").status_code == 200
        assert c.get("/").status_code == 200
        assert c.get("/api/staff/me").status_code == 401
        assert c.get(ROOT).status_code == 401
        assert c.post("/api/staff/logout").status_code == 401
        assert c.get("/workspace/identity").status_code == 404
    # No old functionality is removed as a side effect of moving login.
    for path in LEGACY_PAGES:
        assert env.client.get(path, params={"business_id": BUSINESS}).status_code == 200


@pytest.mark.parametrize(
    "value",
    [
        "//evil.test/admin",
        "https://evil.test/admin",
        "/\\evil.test",
        "/connections/google/callback?code=secret",
        "/workspace/login?next=/admin",
        "/workspace/home?access_token=secret",
        "/admin?business_id=a&business_id=b",
        "/workspace/home#secret",
        "//[",
        "/admin?" + "&".join("q=x" for _ in range(65)),
    ],
)
def test_return_routes_reject_external_recursive_secret_and_ambiguous_state(value):
    assert safe_destination(value) == "/workspace/home"


def test_return_preserves_context_and_requires_explicit_multi_business_selection(env):
    c = env.client
    target = (
        "/workspace/sales?business="
        + BUSINESS
        + "&order=workspace-sale-000&status=ready&date_from=2026-11-01&date_to=2026-11-18"
    )
    result = c.get("/api/staff/entry", params={"next": target}).json()
    assert result["destination"] == target and not result["needs_business"]
    with env.factory() as s:
        account = s.scalar(select(StaffAccount).where(StaffAccount.username == "campaign.manager"))
        s.add(StaffMembership(account_id=account.id, business_id=OTHER, role="manager"))
        s.commit()
    result = c.get("/api/staff/entry", params={"next": "/admin"}).json()
    assert result["needs_business"] and result["destination"] is None
    assert c.get("/admin", follow_redirects=False).status_code == 307
    result = c.get("/api/staff/entry", params={"next": "/admin", "business": OTHER}).json()
    assert result["destination"] == "/admin?business_id=" + OTHER
    result = c.get("/api/staff/entry", params={"next": "/admin?business_id=foreign"}).json()
    assert result["denied"] and result["needs_business"]
    result = c.get("/api/staff/entry", params={"next": target, "business": OTHER}).json()
    assert "order=" not in result["destination"]
    assert "business=" + OTHER in result["destination"]


def test_revoked_session_redirects_html_and_returns_api_401(env):
    with env.factory() as s:
        for row in s.scalars(select(StaffSession)):
            row.revoked = True
        s.commit()
    assert env.client.get("/admin", follow_redirects=False).status_code == 307
    assert env.client.get("/workspace/sales", follow_redirects=False).status_code == 307
    assert env.client.get("/api/staff/entry").status_code == 401
    assert env.client.get(ROOT).status_code == 401


def test_name_and_payment_filters_match_displayed_snapshot_before_pagination(env):
    with env.factory() as s:
        row = s.get(Order, "workspace-sale-000")
        row.customer.name = "Current replacement identity"
        row.customer_snapshot_json = json.dumps(
            {"name": "Snapshot % customer", "phone": "+573005550100"}
        )
        payment = row.payment_status
        s.get(Order, "workspace-sale-001").customer_snapshot_json = json.dumps(
            {"phone": "+573005550100"}
        )
        s.commit()
    c = env.client
    result = c.get(
        ROOT, params={"status": "all", "q": "Snapshot %", "payment_status": payment}
    ).json()
    assert result["count"] == 1 and result["items"][0]["id"] == "workspace-sale-000"
    assert result["items"][0]["customer_name"] == "Snapshot % customer"
    current = c.get(ROOT, params={"status": "all", "q": "Current replacement identity"}).json()
    assert "workspace-sale-000" not in {r["id"] for r in current["items"]}
    assert "workspace-sale-001" not in {r["id"] for r in current["items"]}
    assert c.get(ROOT, params={"payment_status": "madeup"}).status_code == 422
    assert all(
        r["payment_status"] == "unpaid"
        for r in c.get(ROOT, params={"payment_status": "unpaid"}).json()["items"]
    )


def test_reservation_queue_version_conflicts_roles_scope_and_contact(env):
    seed_reservations(env.app)
    c = env.client
    root = ROOT.replace("/sales", "/sales-reservations")
    page = c.get(root).json()
    second = c.get(root, params={"offset": 25}).json()
    assert page["count"] == 28 and len(page["items"]) == 25 and len(second["items"]) == 3
    assert page["date_basis"] == "starts_at" and page["timezone"]
    rid = page["items"][0]["id"]
    patch = "/api/operator/reservations/" + rid
    csrf = {"X-101-CSRF": c.get("/api/staff/me").json()["csrf"]}
    before = c.get(root + "/" + rid).json()
    assert before["actions"] == ["cancelled", "confirmed"]
    assert (
        c.patch(
            patch, json={"status": "confirmed", "expected_version": before["version"]}
        ).status_code
        == 403
    )
    r = c.patch(
        patch, json={"status": "confirmed", "expected_version": before["version"]}, headers=csrf
    )
    assert r.status_code == 200 and r.json()["version"] == before["version"] + 1
    assert (
        c.patch(
            patch, json={"status": "confirmed", "expected_version": before["version"]}, headers=csrf
        ).status_code
        == 409
    )
    assert (
        c.patch(
            patch,
            json={"status": "cancelled", "expected_version": r.json()["version"]},
            headers=csrf,
        ).status_code
        == 200
    )
    assert c.get(root + "/" + rid).json()["actions"] == []
    assert c.get(root.replace(BUSINESS, OTHER)).status_code == 403
    message = c.get(patch + "/whatsapp")
    assert message.status_code == 200 and message.json()["url"].startswith(
        "https://wa.me/573005550100?"
    )
    assert (
        c.get(patch + "/whatsapp", params={"destination_phone": "wrong recipient"}).status_code
        == 422
    )
    login(c, "sales.viewer")
    csrf = {"X-101-CSRF": c.get("/api/staff/me").json()["csrf"]}
    assert c.get(root).status_code == 200
    assert (
        c.patch(
            patch, json={"status": "confirmed", "expected_version": before["version"]}, headers=csrf
        ).status_code
        == 403
    )
    assert c.get(patch + "/whatsapp").status_code == 403


def test_reservation_version_refreshes_existing_session_object(env):
    seed_reservations(env.app)
    with env.factory() as cached:
        row = cached.get(Reservation, "workspace-reservation-0")
        old = row.version
        with env.factory() as other:
            live = other.get(Reservation, row.id)
            live.status = "confirmed"
            other.commit()
        with pytest.raises(InvalidTransitionError):
            RestaurantCommerceService(cached).transition_reservation(
                row.id, "cancelled", expected_version=old
            )
    assert (
        env.client.get(
            ROOT.replace("/sales", "/sales-reservations") + "/workspace-reservation-0"
        ).json()["status"]
        == "confirmed"
    )
