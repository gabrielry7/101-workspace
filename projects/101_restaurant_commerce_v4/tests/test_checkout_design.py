"""Real API + existing staff/service boundary. Synthetic businesses, never live payments."""

import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, inspect
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.checkout_design import (
    CONTRACT,
    CheckoutDesign,
    upgrade_checkout_design,
)
from world_model.restaurant_commerce.models import RestaurantCommerceProfile, Order
from staff_helpers import staff_headers

B = "demo-restaurant-bogota"
ROOT = f"/api/operator/restaurants/{B}/checkout-design"
PUBLIC = f"/api/restaurants/{B}/checkout-design"


@pytest.fixture
def env(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'design.db'}", seed=True)
    with TestClient(app) as c:
        headers = staff_headers(c)
        yield app, c, headers


def save(c, headers, profile=None, version=0):
    return c.put(
        ROOT,
        headers=headers,
        json={
            "expected_revision": version,
            "profile": copy.deepcopy(profile or CONTRACT["presets"]["neutral"]),
        },
    )


def test_round_trip_revision_public_projection_restart_and_prices(env):
    app, c, headers = env
    cart_url = f"/api/restaurants/{B}/storefront"
    original = c.get(cart_url).json()
    assert c.get(PUBLIC).json()["profile"] == CONTRACT["presets"]["source"]
    r = save(c, headers)
    assert r.status_code == 200, r.text
    assert r.json()["revision"] == 1
    assert c.get(cart_url).json() == original
    assert set(c.get(PUBLIC).json()) == {"business_id", "revision", "profile"}
    assert save(c, headers).status_code == 409
    assert save(c, headers, CONTRACT["presets"]["warm"], 1).json()["revision"] == 2
    with app.state.session_factory() as s:
        assert s.get(CheckoutDesign, B).revision == 2
        assert list(s.scalars(select(Order))) == []
    # New app and process-local caches read the stored design, not a preview selection.
    restarted = create_app(database_url=str(app.state.engine.url), seed=False)
    with TestClient(restarted) as other:
        assert other.get(PUBLIC).json()["revision"] == 2
        assert other.get(PUBLIC).json()["profile"] == CONTRACT["presets"]["warm"]


def test_no_credentials_viewer_revocation_csrf_and_cross_business(env):
    app, c, headers = env
    assert (
        c.put(
            ROOT, json={"expected_revision": 0, "profile": CONTRACT["presets"]["neutral"]}
        ).status_code
        == 403
    )
    assert save(c, {**headers, "Origin": "https://other.test"}).status_code == 403
    with app.state.session_factory() as s:
        s.add(RestaurantCommerceProfile(business_id="other", slug="other", display_name="Other"))
        s.commit()
    assert c.get(ROOT.replace(B, "other")).status_code == 403
    assert (
        c.put(
            ROOT.replace(B, "other"),
            headers=headers,
            json={"expected_revision": 0, "profile": CONTRACT["presets"]["neutral"]},
        ).status_code
        == 403
    )
    viewer = staff_headers(c, role="viewer", name="design.viewer")
    assert c.get(ROOT).status_code == 200
    assert save(c, viewer).status_code == 403
    c.post("/api/staff/logout", headers=viewer)
    assert c.get(ROOT).status_code == 401
    assert c.get(PUBLIC).status_code == 200
    assert c.get(PUBLIC.replace(B, "unknown")).status_code == 404


@pytest.mark.parametrize(
    "patch",
    [
        {"colors": {"accent": "url(https://evil.test)"}},
        {"colors": {"price": "#ffffff"}},
        {"geometry": {"formWidth": 999999}},
        {"geometry": {"gap": True}},
        {"typography": {"bodyFont": "evil;font-size:0"}},
        {"typography": {"bodySize": 2}},
        {"bones": {"surfaces": {"panel": {"opacity": 0}}}},
        {"bones": {"surfaces": {"product": {"fill": "#ffffff"}}}},
        {"checkout_url": "https://evil.test"},
        {"business_id": "other"},
        {"schema_version": "2"},
    ],
)
def test_invalid_design_cannot_change_behavior_or_saved_profile(env, patch):
    app, c, headers = env
    profile = copy.deepcopy(CONTRACT["presets"]["neutral"])
    profile.update(patch)
    assert save(c, headers, profile).status_code == 422
    assert c.get(PUBLIC).json()["revision"] == 0


def test_missing_schema_is_explicit_and_offline_upgrade_is_additive(env):
    app, c, headers = env
    with app.state.engine.begin() as conn:
        CheckoutDesign.__table__.drop(conn)
    tables = set(inspect(app.state.engine).get_table_names())
    assert c.get(PUBLIC).status_code == 200
    assert c.get(ROOT).json()["available"] is False
    assert save(c, headers).status_code == 503
    upgrade_checkout_design(app.state.engine)
    upgrade_checkout_design(app.state.engine)
    assert set(inspect(app.state.engine).get_table_names()) == tables | {
        CheckoutDesign.__tablename__
    }
    assert save(c, headers).status_code == 200


def test_preview_requires_staff_and_scopes_frame_policy(env):
    app, c, headers = env
    preview = f"/?business_id={B}&checkout_preview=1"
    assert c.get(preview).headers["x-frame-options"] == "SAMEORIGIN"
    assert c.get(f"/?business_id={B}").headers["x-frame-options"] == "DENY"
    assert c.get(preview + "&checkout_preview=1").status_code == 400
    c.post("/api/staff/logout", headers=headers)
    assert c.get(preview).status_code == 401
    assert c.get(f"/?business_id={B}").status_code == 200
    assert c.get("/workspace/website").status_code in {200, 307}
    for name in [
        "checkout-chassis.js",
        "checkout-chassis.css",
        "checkout-anatomy.js",
        "checkout-contract.js",
        "checkout-bones.js",
        "checkout-types.js",
    ]:
        assert c.get("/assets/" + name).status_code == 200


def test_postgres_additive_round_trip_and_conflict_when_explicitly_enabled():
    import os

    url = os.environ.get("COMMERCE_PAYMENT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL required")
    app = create_app(database_url=url, seed=True)
    with TestClient(app) as c:
        headers = staff_headers(c, name="design.pg.manager")
        with app.state.engine.begin() as conn:
            CheckoutDesign.__table__.drop(conn)
        before = set(inspect(app.state.engine).get_table_names())
        upgrade_checkout_design(app.state.engine)
        assert set(inspect(app.state.engine).get_table_names()) == before | {
            CheckoutDesign.__tablename__
        }
        r = save(c, headers)
        assert r.status_code == 200, r.text
        assert save(c, headers).status_code == 409
        assert save(c, headers, CONTRACT["presets"]["warm"], 1).json()["revision"] == 2
        assert c.get(PUBLIC).json()["profile"] == CONTRACT["presets"]["warm"]
