"""Archived Honorato prices and user-confirmed units; isolated simulated commerce."""

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from staff_helpers import staff_headers
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.catalog_connection import (
    CatalogConnection,
    stable_id,
    upgrade_catalog_connection,
)
from world_model.restaurant_commerce.models import (
    MenuItem,
    Order,
    RestaurantCommerceProfile,
)

B = "b47585db-9441-4f59-9797-76e338529010"
ROOT = "/api/restaurants/" + B
IMPORT = "/api/operator/restaurants/" + B + "/catalog-connection"
SOURCE = json.loads((Path(__file__).parent / "fixtures/honorato-test-catalog.json").read_text())


@pytest.fixture
def env(tmp_path):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    app = create_app(database_url=url, seed=True, demo_mode=True)
    with app.state.session_factory() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id=B,
                slug="honorato-test",
                display_name="Honorato · tienda de prueba",
                payment_provider="simulated",
                cash_at_pickup_enabled=False,
                delivery_enabled=False,
                accepts_reservations=False,
                loyalty_enabled=False,
                marketing_automation_enabled=False,
                default_prep_minutes=0,
            )
        )
        s.commit()
    with TestClient(app) as c:
        headers = staff_headers(c, business_id=B, name="catalog.manager")
        yield app, c, headers, url


def put(c, headers, catalog=None):
    return c.put(
        IMPORT,
        headers=headers,
        json={"expected_revision": 0, "catalog": copy.deepcopy(catalog or SOURCE)},
    )


def payload(**extra):
    return {
        "customer": {"name": "Cliente de prueba", "phone": "3005550198"},
        "items": [
            {"menu_item_id": stable_id(B, "product", "campo"), "quantity": 2, "modifiers": []},
            {
                "menu_item_id": stable_id(B, "product", "pain-chocolat"),
                "quantity": 1,
                "modifiers": [],
            },
        ],
        "idempotency_key": "catalog-test-order",
        **extra,
    }


def test_all_27_source_prices_enter_canonical_catalog_and_quote(env):
    app, c, headers, url = env
    assert c.get(ROOT + "/storefront").json()["catalog_context"] is None
    r = put(c, headers)
    assert r.status_code == 200, r.text
    store = c.get(ROOT + "/storefront").json()
    items = [i for m in store["menus"] for category in m["categories"] for i in category["items"]]
    assert len(items) == 27
    assert {i["id"]: i["base_price_minor"] for i in items} == {
        stable_id(B, "product", p["ref"]): p["price_minor"] for p in SOURCE["products"]
    }
    assert store["catalog_context"]["current_price_confirmed"] is False
    assert c.get(ROOT + "/catalog-connection").json()["connected"] is True
    quote = c.post(ROOT + "/orders/quote", json={"items": payload()["items"]})
    assert quote.status_code == 200, quote.text
    assert quote.json()["total_minor"] == 55900
    assert len(quote.json()["items"]) == 2
    assert put(c, headers).status_code == 200
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(CatalogConnection)) == 1
        assert (
            len(
                list(
                    s.scalars(
                        select(MenuItem).where(
                            MenuItem.id.in_(
                                [stable_id(B, "product", p["ref"]) for p in SOURCE["products"]]
                            )
                        )
                    )
                )
            )
            == 27
        )


def test_simulated_order_scoped_payment_duplicate_and_restart(env):
    app, c, headers, url = env
    assert put(c, headers).status_code == 200
    first = c.post(ROOT + "/orders", json=payload())
    assert first.status_code == 200, first.text
    order = first.json()
    reference = order["payments"][0]["provider_reference"]
    assert c.post(ROOT + "/orders", json=payload()).json()["id"] == order["id"]
    assert (
        c.post("/api/payments/simulated/" + reference + "/complete?business_id=other").status_code
        == 404
    )
    paid = c.post("/api/payments/simulated/" + reference + "/complete?business_id=" + B)
    assert paid.status_code == 200, paid.text
    assert paid.json()["total_minor"] == 55900 and paid.json()["payment_status"] == "paid"
    assert paid.json()["business_id"] == B
    restarted = create_app(database_url=url, demo_mode=True)
    with TestClient(restarted) as other:
        assert other.get(ROOT + "/catalog-connection").json()["connected"] is True
    with restarted.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Order).where(Order.business_id == B)) == 1
        assert s.get(Order, order["id"]).payment_status == "paid"


def test_replay_preserves_operator_edits_and_rejects_changed_mapping(env):
    app, c, headers, url = env
    assert put(c, headers).status_code == 200
    with app.state.session_factory() as s:
        item = s.get(MenuItem, stable_id(B, "product", "campo"))
        item.base_price_minor = 21000
        item.sold_out = True
        s.commit()
    assert put(c, headers).status_code == 200
    with app.state.session_factory() as s:
        item = s.get(MenuItem, stable_id(B, "product", "campo"))
        assert item.base_price_minor == 21000 and item.sold_out
    changed = copy.deepcopy(SOURCE)
    changed["products"][0]["name"] = "Changed mapping"
    assert put(c, headers, changed).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "USD"},
        {"unit_multiplier": 1},
        {"current_price_confirmed": True},
        {"scope": "live"},
    ],
)
def test_uncertainty_and_simulation_cannot_be_upgraded_by_import(env, changes):
    app, c, headers, url = env
    value = copy.deepcopy(SOURCE)
    value.update(changes)
    assert put(c, headers, value).status_code == 422
    assert c.get(ROOT + "/catalog-connection").json()["connected"] is False


def test_mismatched_money_reference_duplicate_and_authority(env):
    app, c, headers, url = env
    bad = copy.deepcopy(SOURCE)
    bad["products"][0]["price_minor"] += 1
    assert put(c, headers, bad).status_code == 422
    bad = copy.deepcopy(SOURCE)
    bad["products"].append(bad["products"][0])
    assert put(c, headers, bad).status_code == 422
    assert c.put(IMPORT, json={"expected_revision": 0, "catalog": SOURCE}).status_code == 403
    viewer = staff_headers(c, business_id=B, role="viewer", name="catalog.viewer")
    assert put(c, viewer).status_code == 403
    assert (
        c.put(
            IMPORT.replace(B, "demo-restaurant-bogota"),
            headers=viewer,
            json={"expected_revision": 0, "catalog": SOURCE},
        ).status_code
        == 403
    )


def test_missing_schema_upgrade_and_live_profile_guard(env):
    app, c, headers, url = env
    with app.state.engine.begin() as conn:
        CatalogConnection.__table__.drop(conn)
    assert c.get(ROOT + "/catalog-connection").json()["connected"] is False
    assert put(c, headers).status_code == 503
    upgrade_catalog_connection(app.state.engine)
    upgrade_catalog_connection(app.state.engine)
    with app.state.session_factory() as s:
        s.get(RestaurantCommerceProfile, B).payment_provider = "wompi"
        s.commit()
    assert put(c, headers).status_code == 409
    with app.state.session_factory() as s:
        assert s.get(CatalogConnection, B) is None


def test_test_source_never_activates_real_payment_requests(env):
    app, c, headers, url = env
    assert put(c, headers).status_code == 200
    r = c.post(ROOT + "/orders", json=payload(payment_provider="wompi"))
    assert r.status_code == 422 and "simulados" in r.text
    with app.state.session_factory() as session:
        assert (
            session.scalar(select(func.count()).select_from(Order).where(Order.business_id == B))
            == 0
        )


def test_original_retry_reconciles_after_profile_change_but_new_writes_stop(env):
    app, c, headers, url = env
    assert put(c, headers).status_code == 200
    original = c.post(ROOT + "/orders", json=payload())
    assert original.status_code == 200, original.text
    with app.state.session_factory() as s:
        s.get(RestaurantCommerceProfile, B).payment_provider = "wompi"
        s.commit()
    retry = c.post(ROOT + "/orders", json=payload())
    assert retry.status_code == 200 and retry.json()["id"] == original.json()["id"]
    new = c.post(ROOT + "/orders", json=payload(idempotency_key="different-new-order"))
    assert new.status_code == 422 and "simulados" in new.text
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Order).where(Order.business_id == B)) == 1


def test_postgres_catalog_additive_import_quote_and_restart():
    import os

    from sqlalchemy import inspect

    url = os.environ.get("COMMERCE_PAYMENT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL required")
    app = create_app(database_url=url, seed=True, demo_mode=True)
    with app.state.session_factory() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id=B,
                slug="catalog-pg",
                display_name="Test catalog",
                payment_provider="simulated",
            )
        )
        s.commit()
    with app.state.engine.begin() as conn:
        CatalogConnection.__table__.drop(conn)
    before = set(inspect(app.state.engine).get_table_names())
    upgrade_catalog_connection(app.state.engine)
    upgrade_catalog_connection(app.state.engine)
    assert set(inspect(app.state.engine).get_table_names()) == before | {
        CatalogConnection.__tablename__
    }
    with TestClient(app) as c:
        headers = staff_headers(c, business_id=B, name="catalog.pg.manager")
        assert put(c, headers).status_code == 200
        assert put(c, headers).status_code == 200
        changed = copy.deepcopy(SOURCE)
        changed["products"][0]["name"] = "Changed mapping"
        assert put(c, headers, changed).status_code == 409
        assert (
            c.post(ROOT + "/orders/quote", json={"items": payload()["items"]}).json()["total_minor"]
            == 55900
        )
    with TestClient(create_app(database_url=url, demo_mode=True)) as c:
        assert c.get(ROOT + "/catalog-connection").json()["connected"] is True
