"""Real session, role, tenant, revocation, CSRF and audit acceptance."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from staff_helpers import PASSWORD, staff_headers
from test_payment_durability_m3 import factory as shared_factory
from test_payment_durability_m3 import request as order_request

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import database_ready, init_schema
from world_model.restaurant_commerce.migrations import STAFF_TABLES, upgrade_staff
from world_model.restaurant_commerce.models import (
    Base,
    Order,
    RestaurantCommerceProfile,
    StaffAccount,
    StaffAudit,
    StaffMembership,
    StaffSession,
    utcnow,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService

factory = shared_factory


@pytest.fixture
def client(factory):
    with factory() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id="other", slug="other", display_name="Other"
            )
        )
        s.commit()
        engine = s.get_bind()
    from test_financial_resolution_m3b import Controlled

    provider = Controlled()
    provider.unknown = True
    with TestClient(
        create_app(
            engine=engine,
            payment_recovery_enabled=False,
            financial_providers={"simulated": provider},
        )
    ) as c:
        yield c


def test_legacy_tokens_fail_closed_and_named_staff_isolated(client):
    root = "/api/operator/restaurants/"
    for headers in (
        {"X-101-Operator-Token": "dev-operator"},
        {"X-101-Financial-Token": "valid"},
        {},
    ):
        assert client.get(root + BID + "/orders", headers=headers).status_code == 401
    headers = staff_headers(client)
    assert client.get(root + BID + "/orders", headers=headers).status_code == 200
    for tail in (
        "orders",
        "deliveries",
        "reservations",
        "rewards",
        "promotions",
        "automations",
        "outbox",
        "analytics",
        "payment-reconciliation",
    ):
        assert client.get(root + "other/" + tail, headers=headers).status_code == 403
    for url in ("/api/operator/payments/recover", "/api/operator/events/drain"):
        assert client.post(url, headers=headers).status_code == 403
    assert client.get("/api/operator/metrics", headers=headers).status_code == 403


def test_csrf_origin_cookie_and_logout(client):
    staff_headers(client)
    assert client.get("/api/staff/me").headers["cache-control"] == "no-store"
    raw = client.cookies["commerce_staff"]
    cookie = client.post(
        "/api/staff/login",
        json={"username": "test.manager", "password": PASSWORD},
        headers={"X-101-Login": "1"},
    ).headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert (
        client.get(
            "/api/staff/me", headers={"Cookie": "commerce_staff=" + raw}
        ).status_code
        == 401
    )
    me = client.get("/api/staff/me").json()
    assert client.post("/api/staff/logout").status_code == 403
    assert (
        client.post(
            "/api/staff/logout",
            headers={"X-101-CSRF": me["csrf"], "Origin": "https://evil.test"},
        ).status_code
        == 403
    )
    assert (
        client.post("/api/staff/logout", headers={"X-101-CSRF": me["csrf"]}).status_code
        == 200
    )
    assert client.get("/api/staff/me").status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "idle",
        "revoked",
        "disabled",
        "password_version",
        "membership_removed",
        "role_changed",
    ],
)
def test_live_authority_changes_take_effect(client, change):
    headers = staff_headers(client)
    with client.app.state.session_factory() as s:
        a = s.scalar(select(StaffAccount))
        row = s.scalar(select(StaffSession))
        if change == "expired":
            row.expires_at = utcnow() - timedelta(seconds=1)
        if change == "idle":
            row.last_seen_at = utcnow() - timedelta(minutes=31)
        if change == "revoked":
            row.revoked = True
        if change == "disabled":
            a.active = False
        if change == "password_version":
            a.auth_version += 1
        if change == "membership_removed":
            s.delete(s.get(StaffMembership, (a.id, BID)))
        if change == "role_changed":
            s.get(StaffMembership, (a.id, BID)).role = "viewer"
        s.commit()
    response = client.post(
        "/api/operator/restaurants/" + BID + "/winback/plan",
        json={"limit": 1},
        headers=headers,
    )
    assert response.status_code == (
        403 if change in ("membership_removed", "role_changed") else 401
    )


def test_roles_and_bare_order_ids_audit(client):
    with client.app.state.session_factory() as s:
        svc = RestaurantCommerceService(s)
        order = svc.create_order(BID, order_request(svc))
        other = svc.create_order(BID, order_request(svc, key="other-order"))
        s.get(Order, other.id).business_id = "other"
        s.commit()
    viewer = staff_headers(client, role="viewer", name="test.viewer")
    assert (
        client.patch(
            "/api/operator/orders/" + order.id,
            json={"status": "accepted"},
            headers=viewer,
        ).status_code
        == 403
    )
    manager = staff_headers(client)
    for url in (
        "/api/operator/orders/" + other.id,
        "/api/operator/orders/" + other.id + "/access/revoke",
        "/api/operator/orders/" + other.id + "/delivery/dispatch",
        "/api/operator/orders/" + other.id + "/delivery/cancel",
    ):
        method = client.patch if url.endswith(other.id) else client.post
        assert (
            method(url, json={"status": "accepted"}, headers=manager).status_code == 403
        )
    response = client.post(
        "/api/operator/orders/" + order.id + "/access/revoke", headers=manager
    )
    assert response.status_code == 200, response.text
    with client.app.state.session_factory() as s:
        a = s.scalar(
            select(StaffAccount).where(StaffAccount.username == "test.manager")
        )
        audit = s.scalars(
            select(StaffAudit).where(StaffAudit.action == "revoke_order_access.commit")
        ).all()
        assert (
            len(audit) == 3
        )  # order/access event, outbox lease, and publish completion commits
        assert all(
            row.actor_id == a.id and row.business_id == BID and row.resource == order.id
            for row in audit
        )


def test_login_throttled_and_no_account_oracle(client, monkeypatch):
    from types import SimpleNamespace
    from world_model.restaurant_commerce import staff

    # This contract is per aligned minute. Keep requests in that window instead
    # of making the assertion depend on the wall clock during password hashing.
    clock = [1800000000.0]
    monkeypatch.setattr(staff, "time", SimpleNamespace(time=lambda: clock[0]))
    for i in range(5):
        r = client.post(
            "/api/staff/login",
            json={"username": "unknown.user", "password": PASSWORD},
            headers={"X-101-Login": "1"},
        )
        assert (
            r.status_code == 401 and r.json()["detail"] == "Invalid staff credentials"
        )
    assert (
        client.post(
            "/api/staff/login",
            json={"username": "unknown.user", "password": PASSWORD},
            headers={"X-101-Login": "1"},
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/api/staff/login", json={"username": "unknown.user", "password": PASSWORD}
        ).status_code
        == 403
    )
    clock[0] += 60
    assert client.post(
        "/api/staff/login",
        json={"username": "unknown.user", "password": PASSWORD},
        headers={"X-101-Login": "1"},
    ).status_code == 401  # A new aligned minute has a new bounded allowance.


def test_populated_upgrade_preserves_orders_and_never_creates_staff(factory):
    with factory() as s:
        svc = RestaurantCommerceService(s)
        order = svc.create_order(BID, order_request(svc))
        engine = s.get_bind()
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in STAFF_TABLES:
                table.drop(connection)
    assert not database_ready(engine)
    with pytest.raises(RuntimeError):
        init_schema(engine)
    upgrade_staff(engine)
    upgrade_staff(engine)
    assert database_ready(engine)
    with factory() as s:
        assert s.get(Order, order.id)
        assert s.scalar(select(StaffAccount)) is None


def test_malformed_csrf_and_invalid_username_do_not_alias(client):
    from fastapi import HTTPException
    from starlette.requests import Request

    from world_model.restaurant_commerce.staff import csrf_check

    with pytest.raises(HTTPException) as exc:
        csrf_check(
            Request(
                {
                    "type": "http",
                    "method": "POST",
                    "scheme": "http",
                    "path": "/",
                    "server": ("testserver", 80),
                    "headers": [(b"x-101-csrf", b"\xe9")],
                }
            ),
            type("Row", (), {"csrf": "ascii"})(),
        )
    assert exc.value.status_code == 403
    staff_headers(client, name="invalid-username")
    client.cookies.clear()
    r = client.post(
        "/api/staff/login",
        json={"username": "!!!", "password": PASSWORD},
        headers={"X-101-Login": "1"},
    )
    assert r.status_code == 401


def test_concurrent_logout_all_never_loses_revocation_version(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from world_model.restaurant_commerce import staff

    headers = staff_headers(client)
    original = staff.authenticate
    barrier = Barrier(2)

    def overlapping(*args):
        result = original(*args)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(staff, "authenticate", overlapping)
    with ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/api/staff/logout-all", headers=headers),
                range(2),
            )
        )
    assert [r.status_code for r in responses] == [200, 200]
    with client.app.state.session_factory() as s:
        assert s.scalar(select(StaffAccount)).auth_version == 3
    monkeypatch.setattr(staff, "authenticate", original)
    assert client.get("/api/staff/me", headers=headers).status_code == 401


def test_production_session_cookie_is_host_bound_secure(factory):
    from staff_helpers import PASSWORD

    from world_model.restaurant_commerce.staff import provision

    with factory() as s:
        engine = s.get_bind()
        provision(s, "secure.staff", PASSWORD, BID, "viewer", actor="test")
    app = create_app(
        engine=engine,
        environment="production",
        public_access_secret="s" * 32,
        payment_recovery_enabled=False,
    )
    with TestClient(app, base_url="https://testserver") as c:
        response = c.post(
            "/api/staff/login",
            json={"username": "secure.staff", "password": PASSWORD},
            headers={"X-101-Login": "1"},
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert (
            "__Host-commerce_staff=" in cookie
            and "Secure" in cookie
            and "HttpOnly" in cookie
            and "Domain=" not in cookie
        )
        assert c.get("/api/staff/me").status_code == 200


def test_platform_role_requires_explicit_grant(client):
    headers = staff_headers(client, platform_admin=True)
    assert client.get("/api/operator/metrics", headers=headers).status_code == 200
    assert (
        client.get(
            "/api/operator/restaurants/other/orders", headers=headers
        ).status_code
        == 403
    )


def test_foreign_delivery_reservation_and_message_ids_denied(client):
    from datetime import UTC, datetime

    from test_hardening_v4 import delivery_order

    from world_model.restaurant_commerce.models import OutboundMessage, Reservation
    from world_model.restaurant_commerce.schemas import CreateReservationRequest

    with client.app.state.session_factory() as s:
        svc = RestaurantCommerceService(s)
        _, order = delivery_order(svc, idem="scope-delivery")
        from world_model.restaurant_commerce.models import Delivery

        delivery_id = s.scalar(select(Delivery.id).where(Delivery.order_id == order.id))
        s.get(Order, order.id).business_id = "other"
        reservation = svc.create_reservation(
            BID,
            CreateReservationRequest.model_validate(
                {
                    "customer": {"name": "Synthetic", "phone": "3005550777"},
                    "party_size": 2,
                    "starts_at": (datetime.now(UTC) + timedelta(days=1))
                    .replace(hour=17, minute=0, second=0, microsecond=0)
                    .isoformat(),
                }
            ),
        )
        s.get(Reservation, reservation.id).business_id = "other"
        msg = OutboundMessage(
            business_id="other",
            customer_id=s.get(Order, order.id).customer_id,
            channel="whatsapp",
            purpose="marketing",
            message_kind="winback",
            destination="3005550777",
            body="Synthetic",
            scheduled_at=utcnow(),
            dedupe_key="scope-message",
        )
        s.add(msg)
        s.commit()
        mid = msg.id
    headers = staff_headers(client)
    cases = [
        (
            "PATCH",
            f"/api/operator/deliveries/{delivery_id}/status",
            {"status": "cancelled"},
        ),
        (
            "PATCH",
            f"/api/operator/reservations/{reservation.id}",
            {"status": "cancelled"},
        ),
        ("GET", f"/api/operator/reservations/{reservation.id}/whatsapp", None),
        ("GET", f"/api/operator/orders/{order.id}/whatsapp", None),
        ("POST", f"/api/operator/outbox/{mid}/handoff", {}),
        ("PATCH", f"/api/operator/outbox/{mid}/sent", {}),
    ]
    for method, url, body in cases:
        assert (
            client.request(method, url, json=body, headers=headers).status_code == 403
        )


def test_rejected_mutation_has_authorization_but_no_commit_audit(client):
    with client.app.state.session_factory() as s:
        svc = RestaurantCommerceService(s)
        order = svc.create_order(BID, order_request(svc))
    headers = staff_headers(client)
    r = client.patch(
        "/api/operator/orders/" + order.id,
        json={"status": "completed"},
        headers=headers,
    )
    assert r.status_code == 409
    with client.app.state.session_factory() as s:
        rows = s.scalars(
            select(StaffAudit).where(StaffAudit.resource == order.id)
        ).all()
        assert [r.action for r in rows] == ["operator_order_status.authorized"]
        assert s.get(Order, order.id).status == "awaiting_payment"


@pytest.mark.parametrize("role", ["viewer", "operator", "finance", "manager"])
def test_financial_and_fulfillment_roles_are_distinct(client, role):
    with client.app.state.session_factory() as s:
        svc = RestaurantCommerceService(s)
        order = svc.create_order(BID, order_request(svc))
    headers = staff_headers(client, role=role)
    root = "/api/finance/restaurants/" + BID + "/orders/" + order.id
    assert client.get(root, headers=headers).status_code == 200
    r = client.post(
        root + "/lookup",
        json={"idempotency_key": "role-lookup", "reason": "Verify"},
        headers=headers,
    )
    assert r.status_code == (200 if role in ("finance", "manager") else 403)
    r = client.post(
        "/api/operator/orders/" + order.id + "/access/revoke", headers=headers
    )
    assert r.status_code == (200 if role in ("operator", "manager") else 403)


def test_partial_staff_schema_rejected_without_repair(factory):
    from sqlalchemy import text

    with factory() as s:
        engine = s.get_bind()
    with engine.begin() as c:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in STAFF_TABLES:
                table.drop(c)
        c.execute(
            text("CREATE TABLE restaurant_staff_accounts (id VARCHAR(36) PRIMARY KEY)")
        )
    with pytest.raises(RuntimeError, match="Incomplete staff schema"):
        upgrade_staff(engine)
    assert not database_ready(engine)
