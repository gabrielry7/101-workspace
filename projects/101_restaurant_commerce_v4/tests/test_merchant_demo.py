"""A merchant rehearsal must use real services while prohibiting external effects."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_models import Campaign, CampaignSettings
from world_model.restaurant_commerce.catalog_connection import Import, import_catalog
from world_model.restaurant_commerce.merchant_demo import app_for_demo
from world_model.restaurant_commerce.models import Customer, Order, RestaurantCommerceProfile

B = "b47585db-9441-4f59-9797-76e338529010"
R = "/api/operator/restaurants/" + B
SOURCE = json.loads((Path(__file__).parent / "fixtures/honorato-test-catalog.json").read_text())


@pytest.fixture
def ready(tmp_path):
    url = "sqlite:///" + str(tmp_path / "merchant.db")
    base = create_app(database_url=url, seed=True, demo_mode=True, social_worker_enabled=False)
    with base.state.session_factory() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id=B,
                slug="merchant-rehearsal",
                display_name="Honorato",
                payment_provider="simulated",
                cash_at_pickup_enabled=False,
                default_prep_minutes=0,
            )
        )
        s.flush()
        import_catalog(s, B, Import(expected_revision=0, catalog=SOURCE))
        s.commit()
    from world_model.restaurant_commerce.loyalty_assignment_migrations import (
        upgrade_loyalty_assignment,
    )
    from world_model.restaurant_commerce.loyalty_execution_migrations import (
        upgrade_loyalty_execution,
    )
    from world_model.restaurant_commerce.loyalty_measurement_migrations import (
        upgrade_loyalty_measurement,
    )
    from world_model.restaurant_commerce.loyalty_migrations import upgrade_loyalty_configuration

    for upgrade in [
        upgrade_loyalty_configuration,
        upgrade_loyalty_execution,
        upgrade_loyalty_assignment,
        upgrade_loyalty_measurement,
    ]:
        upgrade(base.state.engine)
    return url


def compose(url):
    return app_for_demo(
        url,
        business=B,
        name="Honorato",
        username="honorato.demo",
        store_url="http://localhost:4335/studio/compositions/mixed/C/",
    )


def login(c):
    r = c.post(
        "/api/staff/login",
        headers={"X-101-Login": "1"},
        json={"username": "101", "password": "101"},
    )
    assert r.status_code == 200, r.text
    me = c.get("/api/staff/me").json()
    assert [v["business_id"] for v in me["businesses"]] == [B]
    return {"X-101-CSRF": me["csrf"]}


def test_one_merchant_context_and_honest_capabilities(ready, monkeypatch):
    # Even accidentally enabled provider environment cannot start real connections.
    monkeypatch.setenv("COMMERCE_GOOGLE_CONNECTION_ENABLED", "1")
    monkeypatch.setenv("COMMERCE_INSTAGRAM_CONNECTION_ENABLED", "1")
    app = compose(ready)
    with TestClient(app) as c:
        assert c.get(R + "/workspace/context").status_code == 401
        login(c)
        ctx = c.get(R + "/workspace/context").json()
        assert ctx["no_money"] and ctx["mode"] == "demo" and ctx["external_actions"] is False
        assert ctx["catalog_count"] == 27 and ctx["web_analytics"] == "unconfigured"
        assert len(ctx["modules"]) == 6 and len(ctx["activation_gates"]) == 6
        assert c.get("/api/browser-policy").json()["offline_demo"] is True
        assert (
            c.get(R.replace(B, "demo-restaurant-bogota") + "/workspace/context").status_code == 403
        )
        assert c.get(R + "/workspace/overview").status_code == 200


def test_catalog_price_edit_requote_conflict_and_order_snapshots(ready):
    app = compose(ready)
    with TestClient(app) as c:
        h = login(c)
        catalog = c.get(R + "/workspace/catalog").json()
        item = catalog["items"][0]
        with app.state.session_factory() as s:
            prior = [
                (o.id, o.total_minor)
                for o in s.scalars(select(Order).where(Order.business_id == B))
            ]
        r = c.put(
            R + "/workspace/catalog/" + item["id"],
            headers=h,
            json={"expected_revision": catalog["revision"], "price_minor": 35700},
        )
        assert r.status_code == 200, r.text
        assert r.json()["current_price_confirmed"] is False
        assert (
            c.put(
                R + "/workspace/catalog/" + item["id"],
                headers=h,
                json={"expected_revision": catalog["revision"], "price_minor": 1},
            ).status_code
            == 409
        )
        quote = c.post(
            "/api/restaurants/" + B + "/orders/quote",
            json={"items": [{"menu_item_id": item["id"], "quantity": 2}]},
        ).json()
        assert quote["total_minor"] == 71400
        with app.state.session_factory() as s:
            assert [
                (o.id, o.total_minor)
                for o in s.scalars(select(Order).where(Order.business_id == B))
            ] == prior
        assert (
            c.put(
                R + "/workspace/catalog/" + item["id"],
                headers=h,
                json={"expected_revision": catalog["revision"] + 1, "price_minor": True},
            ).status_code
            == 422
        )
        assert (
            c.put(
                R + "/workspace/catalog/foreign",
                headers=h,
                json={"expected_revision": catalog["revision"] + 1, "price_minor": 1},
            ).status_code
            == 404
        )
        assert (
            c.put(
                R + "/workspace/catalog/" + item["id"],
                json={"expected_revision": catalog["revision"] + 1, "price_minor": 1},
            ).status_code
            == 403
        )


def test_campaign_approval_dispatch_receipt_is_local_and_test_scoped(ready, monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda *a, **k: pytest.fail("External HTTP forbidden"),
    )
    app = compose(ready)
    with TestClient(app) as c:
        h = login(c)
        with app.state.session_factory() as s:
            campaign = s.scalar(select(Campaign).where(Campaign.business_id == B))
            identifier = campaign.id
        preview = c.get(R + "/campaigns/" + identifier).json()
        digest = preview["digest"]
        for action in ["approve", "schedule"]:
            r = c.post(
                R + "/campaigns/" + identifier + "/" + action, headers=h, json={"digest": digest}
            )
            assert r.status_code == 200, r.text
        r = c.post(R + "/campaigns/simulate/dispatch", headers=h)
        assert r.status_code == 200, r.text
        receipts = c.post(R + "/campaigns/" + identifier + "/simulate-receipt", headers=h)
        assert receipts.status_code == 200, receipts.text
        report = c.get(R + "/campaigns/" + identifier + "/report?scope=test").json()
        assert report["scope"] == "test"
        assert report["delivery_cost_microusd"] == 0
        adapter = app.state.campaign_options["integrations"][B + "-email"]["adapter"]
        assert len(adapter.messages) == 2  # Third contact has no simulated permission.
        from world_model.restaurant_commerce.campaign_models import CampaignJob
        from world_model.restaurant_commerce.catalog_connection import stable_id

        with app.state.session_factory() as session:
            job = session.scalar(
                select(CampaignJob).where(
                    CampaignJob.business_id == B, CampaignJob.state == "delivered"
                )
            )
            token = job.tracking_token
            customer = session.get(Customer, job.customer_id)
            phone = customer.phone
        visit = c.get("/campaign-link/" + token, follow_redirects=False)
        assert (
            visit.status_code == 303 and "studio/compositions/mixed/C/" in visit.headers["location"]
        )
        order = c.post(
            "/api/restaurants/" + B + "/orders",
            json={
                "customer": {"name": "Pedido de prueba atribuido", "phone": phone},
                "items": [{"menu_item_id": stable_id(B, "product", "campo"), "quantity": 1}],
                "idempotency_key": "demo-campaign-order",
            },
        )
        assert order.status_code == 200, order.text
        paid = c.post(
            "/api/payments/simulated/"
            + order.json()["payments"][0]["provider_reference"]
            + "/complete?business_id="
            + B
        )
        assert paid.status_code == 200
        assert (
            c.get(R + "/campaigns/" + identifier + "/report?scope=test").json()["paid_orders"] == 1
        )
        assert c.get(R + "/campaigns/" + identifier + "/report?scope=live").json()["orders"] == []


def test_restarting_preserves_operator_price_draft_and_existing_customers(ready):
    app = compose(ready)
    with app.state.session_factory() as s:
        # Snapshot the durable demo rows; startup cannot append new examples.
        def counts():
            return tuple(
                s.scalar(select(func.count()).select_from(m)) for m in [Customer, Order, Campaign]
            )

        before = counts()
        settings = s.get(CampaignSettings, B)
        settings.paused = True
        s.commit()
    restarted = compose(ready)
    with restarted.state.session_factory() as s:
        after = tuple(
            s.scalar(select(func.count()).select_from(m)) for m in [Customer, Order, Campaign]
        )
        assert before == after and s.get(CampaignSettings, B).paused


@pytest.mark.parametrize(
    "kwargs",
    [
        {"environment": "production"},
        {"demo_mode": False},
        {"financial_providers": {"real": object()}},
        {"event_sink": object()},
        {"connections_runtime": object()},
        {"social_generator": object()},
        {"social_transcriber": object()},
        {"signup_options": {"adapters": {"email": type("Real", (), {"network": True})()}}},
        {
            "campaign_options": {
                "integrations": {
                    "real": {
                        "scope": "live",
                        "adapter": type("Real", (), {"capabilities": {"network": True}})(),
                    }
                }
            }
        },
    ],
)
def test_offline_mode_rejects_network_or_production_adapters(kwargs):
    with pytest.raises(RuntimeError, match="demo|Offline"):
        create_app(offline_demo=True, **kwargs)


def register_customer(c, channel, destination):
    root = "/api/customer/signup/" + B
    h = {"X-101-Signup": "1", "Origin": "http://localhost:8831"}
    r = c.post(
        root + "/start",
        headers=h,
        json={"channel": channel, "destination": destination, "source": "website"},
    )
    assert r.status_code == 200, r.text
    challenge = r.json()
    r = c.post(
        root + "/verify",
        headers=h,
        json={"challenge_id": challenge["challenge_id"], "code": challenge["demo_code"]},
    )
    assert r.status_code == 200, r.text
    return c.get(root).json()["account"]


def test_phone_registration_binds_checkout_with_csrf_and_keeps_anonymous_recovery(ready):
    from world_model.restaurant_commerce.catalog_connection import stable_id
    from world_model.restaurant_commerce.customer_signup_models import CustomerMembership

    app = compose(ready)
    with TestClient(app) as c:
        account = register_customer(c, "phone", "+573005551234")
        assert account["member"] and account["login_method"] == "phone"
        data = {
            "customer": {"name": "Cliente registrado de prueba", "phone": account["identifier"]},
            "items": [{"menu_item_id": stable_id(B, "product", "campo"), "quantity": 1}],
            "idempotency_key": "registered-customer-order",
            "recovery_secret": "a" * 64,
        }
        assert c.post("/api/restaurants/" + B + "/orders", json=data).status_code == 403
        h = {"X-101-Customer-CSRF": account["csrf"]}
        r = c.post("/api/restaurants/" + B + "/orders", headers=h, json=data)
        assert r.status_code == 200, r.text
        with app.state.session_factory() as s:
            order = s.get(Order, r.json()["id"])
            member = s.scalar(
                select(CustomerMembership).where(
                    CustomerMembership.business_id == B,
                    CustomerMembership.customer_id == order.customer_id,
                )
            )
            assert (
                member is not None and json.loads(order.customer_snapshot_json)["identity_verified"]
            )
        c.cookies.delete("commerce_customer")
        recovered = c.post(
            "/api/restaurants/" + B + "/orders/recover",
            json={
                "idempotency_key": data["idempotency_key"],
                "recovery_secret": data["recovery_secret"],
            },
        )
        assert recovered.status_code == 200 and recovered.json()["id"] == r.json()["id"]


def test_email_signup_never_claims_an_unverified_phone(ready):
    from world_model.restaurant_commerce.catalog_connection import stable_id

    app = compose(ready)
    with TestClient(app) as c:
        register_customer(c, "email", "registered@example.test")
        r = c.post(
            "/api/restaurants/" + B + "/orders",
            json={
                "customer": {"name": "Correo de prueba", "phone": "+573005558888"},
                "items": [{"menu_item_id": stable_id(B, "product", "campo"), "quantity": 1}],
                "idempotency_key": "email-is-not-phone-proof",
            },
        )
        assert r.status_code == 200, r.text
        with app.state.session_factory() as s:
            assert (
                json.loads(s.get(Order, r.json()["id"]).customer_snapshot_json)["identity_verified"]
                is False
            )


def test_sample_content_is_fixture_only_unapproved_and_replay_does_not_duplicate(ready):
    import io

    from PIL import Image
    from world_model.restaurant_commerce.merchant_demo import prepare_social_example
    from world_model.restaurant_commerce.social_production import Approval, Asset, Pack

    app = compose(ready)
    data = io.BytesIO()
    # A multi-chunk original beyond the direct base64 endpoint limit.
    Image.effect_noise((1600, 2000), 100).convert("RGB").save(data, format="PNG")
    assert len(data.getvalue()) > 700_000
    prepare_social_example(
        app, B, data.getvalue(), source="Synthetic image for software verification"
    )
    prepare_social_example(
        app, B, data.getvalue(), source="Synthetic image for software verification"
    )
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Asset).where(Asset.business_id == B)) == 1
        assert s.scalar(select(func.count()).select_from(Pack).where(Pack.business_id == B)) == 1
        assert s.scalar(select(func.count()).select_from(Approval)) == 0
        asset = s.scalar(select(Asset).where(Asset.business_id == B))
        assert json.loads(asset.metadata_json)["fixture"] is True
    with TestClient(app) as c:
        login(c)
        overview = c.get(R + "/workspace/overview").json()
        entry = next(p for p in overview["attention"] if p["kind"] == "social")
        assert "/workspace/social?" in entry["href"] and "pack=" in entry["href"]
        assert c.get(entry["href"], follow_redirects=False).status_code == 200


def test_postgres_catalog_price_cas_and_isolation():
    import os

    from staff_helpers import staff_headers

    url = os.environ.get("COMMERCE_PAYMENT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL required")
    app = create_app(
        database_url=url, seed=True, demo_mode=True, offline_demo=True, social_worker_enabled=False
    )
    with app.state.session_factory() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id=B,
                slug="merchant-pg",
                display_name="Merchant PG",
                payment_provider="simulated",
            )
        )
        s.flush()
        import_catalog(s, B, Import(expected_revision=0, catalog=SOURCE))
        s.commit()
    with TestClient(app) as c:
        h = staff_headers(c, business_id=B, name="merchant.pg")
        cat = c.get(R + "/workspace/catalog").json()
        item = cat["items"][0]
        payload = {"expected_revision": cat["revision"], "price_minor": 35700}
        result = c.put(R + "/workspace/catalog/" + item["id"], headers=h, json=payload)
        assert result.status_code == 200 and result.json()["revision"] == 2
        assert (
            c.put(R + "/workspace/catalog/" + item["id"], headers=h, json=payload).status_code
            == 409
        )
        assert (
            c.get(R.replace(B, "demo-restaurant-bogota") + "/workspace/catalog").status_code == 403
        )


def test_blocked_sample_render_retries_the_original_asset_without_hiding_failure(
    ready, monkeypatch
):
    import io

    from fastapi import HTTPException
    from PIL import Image
    from world_model.restaurant_commerce import social_production as production
    from world_model.restaurant_commerce.merchant_demo import prepare_social_example

    app = compose(ready)
    data = io.BytesIO()
    Image.new("RGB", (1600, 2000), (95, 70, 40)).save(data, format="JPEG")
    original = production.render

    def blocked(*a, **kw):
        raise HTTPException(422, "controlled_renderer_failure")

    monkeypatch.setattr(production, "render", blocked)
    with pytest.raises(RuntimeError, match="Demo content preparation blocked"):
        prepare_social_example(app, B, data.getvalue(), source="Synthetic software fixture")
    with app.state.session_factory() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(production.Asset)
                .where(production.Asset.business_id == B)
            )
            == 1
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(production.Pack)
                .where(production.Pack.business_id == B)
            )
            == 0
        )
    monkeypatch.setattr(production, "render", original)
    prepare_social_example(app, B, data.getvalue(), source="Synthetic software fixture")
    with app.state.session_factory() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(production.Asset)
                .where(production.Asset.business_id == B)
            )
            == 1
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(production.Pack)
                .where(production.Pack.business_id == B)
            )
            == 1
        )
