"""Native connections/signup and entry preservation; fixtures never use live providers."""

# ruff: noqa: F811 -- fixture aliases
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce import connections as c
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import (
    BUSINESS,
    CLOCK,
    OTHER,
    PASSWORD,
    seed_campaign_demo,
)
from world_model.restaurant_commerce.connection_google import FakeGoogleBusinessAdapter
from world_model.restaurant_commerce.customer_signup_delivery import FakePhoneVerifier
from world_model.restaurant_commerce.models import (
    RestaurantCommerceProfile,
    StaffAccount,
    StaffMembership,
)
from world_model.restaurant_commerce.staff import provision

ROOT = "/api/operator/restaurants/" + BUSINESS


class FakeInstagram:
    mode = "test"
    provider = "instagram"
    automatic_sync = False
    local_disconnect_only = True

    def authorize_url(self, state, verifier):
        return "/connections/instagram/callback?" + urlencode(
            {"state": state, "code": "fixture-only"}
        )

    def exchange(self, code, verifier, now):
        return {
            "access_token": "fixture-only",
            "user_id": "123",
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        }

    def discover(self, tokens):
        return [{"key": "123", "name": "fixture_business"}]

    def refresh(self, tokens, now):
        return tokens

    def snapshot(self, tokens, selected, now):
        return {
            "coverage": {"posts": 2, "requests": 3, "maximum_requests": 7, "has_more": True},
            "posts": [
                {
                    "id": str(i),
                    "caption": "Historical fixture",
                    "format": "IMAGE",
                    "published_at_native": "2026-11-02",
                    "published_at_utc": None,
                    "timestamp_precision": "day",
                    "metrics": {
                        "likes": {
                            "value": 0 if i == 0 else None,
                            "reason": None if i == 0 else "permission_or_field_unavailable",
                        },
                        "comments": {"value": None, "reason": "permission_or_field_unavailable"},
                    },
                }
                for i in range(2)
            ],
            "errors": {"insights": "unavailable"},
        }


@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def fail(*a, **kw):
        pytest.fail("Live HTTP forbidden in completion qualification")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fail)


def app_for_completion(database_url, origin, *, engine=None, worker=False):
    google = c.ConnectionRuntime(
        FakeGoogleBusinessAdapter(), Fernet.generate_key(), clock=lambda: CLOCK, worker=worker
    )
    instagram = c.ConnectionRuntime(
        FakeInstagram(), Fernet.generate_key(), clock=lambda: CLOCK, worker=worker
    )
    signup = {
        "mode": "test",
        "public_origin": origin,
        "adapters": {
            "phone": FakePhoneVerifier(),
            "email": FakePhoneVerifier("synthetic-email-only"),
        },
        "allowed_regions": ["CO", "US", "MX", "ES"],
    }
    app = create_app(
        database_url=database_url,
        engine=engine,
        demo_mode=True,
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
        social_worker_enabled=False,
        connections_runtime=google,
        instagram_runtime=instagram,
        signup_options=signup,
    )
    with app.state.session_factory() as s:
        seed_campaign_demo(s)
        provision(s, "completion.viewer", PASSWORD, BUSINESS, "viewer", actor="fixture")
    return app


@pytest.fixture
def env(factory):
    app = app_for_completion(None, "http://127.0.0.1:8803", engine=factory.kw["bind"])
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/staff/login",
                headers={"X-101-Login": "1"},
                json={"username": "campaign.manager", "password": PASSWORD},
            ).status_code
            == 200
        )
        yield SimpleNamespace(
            app=app,
            client=client,
            factory=factory,
            headers={"X-101-CSRF": client.get("/api/staff/me").json()["csrf"]},
        )


def test_retired_bookmarks_keep_business_and_supported_context(env):
    cases = [
        ("/admin", "/workspace/sales", {"order": "preserved-order"}),
        ("/delivery", "/workspace/sales", {"view": "deliveries"}),
        ("/growth", "/workspace/customers", {"view": "promotions"}),
        (
            "/campaigns",
            "/workspace/campaigns",
            {"campaign": "preserved-campaign", "channel": "sms"},
        ),
        ("/whatsapp", "/workspace/connections", {"provider": "whatsapp"}),
        ("/sms", "/workspace/connections", {"provider": "sms"}),
        ("/connections", "/workspace/connections", {"provider": "instagram"}),
        ("/customers/signup", "/workspace/customers", {"view": "signup"}),
        (
            "/whatsapp",
            "/workspace/campaigns",
            {"view": "inbox", "conversation": "preserved-conversation", "channel": "whatsapp"},
        ),
        ("/growth", "/workspace/campaigns", {"view": "outbox"}),
        ("/growth", "/workspace/reports", {"view": "growth"}),
    ]
    for old, target, query in cases:
        r = env.client.get(old, params={"business_id": BUSINESS, **query}, follow_redirects=False)
        assert r.status_code == 307 and r.headers["cache-control"] == "no-store"
        dest = urlsplit(r.headers["location"])
        assert dest.path == target
        assert parse_qs(dest.query) == {
            "business": [BUSINESS],
            **{k: [v] for k, v in query.items()},
        }
        assert env.client.get(r.headers["location"]).status_code == 200
        assert "staffUsername" not in env.client.get(r.headers["location"]).text
        with TestClient(env.app) as anonymous:
            assert (
                urlsplit(anonymous.get(old, follow_redirects=False).headers["location"]).path
                == "/workspace/login"
            )


def test_missing_foreign_duplicate_public_entries_and_slug_payment_context(env):
    for path in [
        "/",
        "/?business_id=",
        "/?business_id=unknown",
        "/?business_id=" + BUSINESS + "&business_id=" + OTHER,
    ]:
        r = env.client.get(path)
        assert r.status_code in {400, 404} and "Abre el enlace" in r.text
        assert "index.js" not in r.text
    with env.factory() as s:
        slug = s.get(RestaurantCommerceProfile, BUSINESS).slug
    r = env.client.get("/r/" + slug + "?id=payment-return&context=retained", follow_redirects=False)
    assert parse_qs(urlsplit(r.headers["location"]).query) == {
        "id": ["payment-return"],
        "context": ["retained"],
        "business_id": [BUSINESS],
    }
    assert env.client.get(r.headers["location"]).status_code == 200
    assert env.client.get("/r/" + slug + "?business_id=" + OTHER).status_code == 400
    with TestClient(env.app) as anonymous:
        assert anonymous.get("/join/" + BUSINESS).status_code == 200
        assert anonymous.get("/?business_id=" + BUSINESS).status_code == 200
        assert anonymous.get("/api/operator/restaurants/" + BUSINESS + "/signup").status_code == 401
        assert anonymous.post("/api/campaign-hooks/missing", json={}).status_code != 307
        assert anonymous.get("/api/orders/unknown").status_code in {401, 403, 404}


def test_completion_returns_bound_business_for_both_providers_and_denial(env):
    for provider, path in [("google", "/connections/google"), ("instagram", "/social/instagram")]:
        state = parse_qs(
            urlsplit(
                env.client.post(ROOT + path + "/authorize", headers=env.headers).json()["url"]
            ).query
        )["state"][0]
        r = env.client.post(
            "/connections/" + provider + "/complete",
            headers=env.headers,
            json={"state": state, "error": "access_denied"},
        )
        assert r.json() == {"completed": True, "business_id": BUSINESS}
        assert (
            env.client.post(
                "/connections/" + provider + "/complete",
                headers=env.headers,
                json={"state": state, "error": "access_denied"},
            ).status_code
            == 400
        )
    with env.factory() as s:
        actor = s.scalar(select(StaffAccount).where(StaffAccount.username == "campaign.manager"))
        s.add(StaffMembership(account_id=actor.id, business_id=OTHER, role="manager"))
        s.commit()
    r = env.client.get("/api/staff/entry", params={"next": "/connections"}).json()
    assert r["needs_business"]
    r = env.client.get(
        "/api/staff/entry", params={"next": "/connections", "business": OTHER}
    ).json()
    assert (
        r["destination"].startswith("/workspace/connections?")
        and "business=" + OTHER in r["destination"]
    )


@pytest.mark.parametrize("environment", ["development", "internal", "production"])
def test_developer_schema_policy_without_changing_public_api(env, environment):
    app = create_app(
        engine=env.factory.kw["bind"],
        environment=environment,
        demo_mode=False,
        auto_init_schema=False,
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
        social_worker_enabled=False,
        public_access_secret="fixture-public-access-secret-only-0123456789",
    )
    with TestClient(app) as client:
        for path in ["/docs", "/redoc", "/openapi.json"]:
            response = client.get(path, follow_redirects=False)
            assert response.status_code == (
                404 if environment == "production" else 200 if path == "/openapi.json" else 307
            )
        assert client.get("/api/browser-policy").status_code == 200


def test_cached_connection_times_are_explicit_utc(env):
    from test_connections import connected

    d = connected(
        SimpleNamespace(
            client=env.client,
            runtime=env.app.state.connections,
            factory=env.factory,
            headers=env.headers,
        )
    )
    assert d["last_success"].endswith("+00:00")
    assert d["cache_expires_at"].endswith("+00:00")
