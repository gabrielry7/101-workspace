"""U04–U06 read/mutation boundaries using canonical services and fake transports."""

# ruff: noqa: F811 -- imported pytest fixtures
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from staff_helpers import PASSWORD, staff_headers
from test_delivery_v3 import delivery_order, pay_accept
from test_financial_resolution_m3b import Controlled
from test_growth_v2 import pay_and_complete
from test_loyalty_execution import configured as configured  # noqa: F401
from test_loyalty_execution import refund as partial_refund
from test_loyalty_execution import service as execution_service
from test_payment_durability_m3 import factory as factory  # noqa: F401
from test_payment_durability_m3 import request as order_request
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo
from world_model.restaurant_commerce.deliveries import SimulatedDeliveryProvider
from world_model.restaurant_commerce.errors import IdempotencyConflictError
from world_model.restaurant_commerce.models import (
    Customer,
    Delivery,
    MenuItem,
    Order,
    PaymentReconciliation,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService as Service
from world_model.restaurant_commerce.staff import provision

ROOT = f"/api/operator/restaurants/{BID}"


class Courier(SimulatedDeliveryProvider):
    def __init__(self):
        super().__init__()
        self.dispatches = 0
        self.cancels = 0
        self.lose = False
        self.lose_cancel = False

    def create_delivery(self, **kwargs):
        self.dispatches += 1
        value = super().create_delivery(**kwargs)
        if self.lose:
            raise TimeoutError("synthetic accepted delivery; response unavailable")
        return value

    def cancel_delivery(self, **kwargs):
        self.cancels += 1
        time.sleep(0.02)
        result = super().cancel_delivery(**kwargs)
        if self.lose_cancel:
            raise TimeoutError("synthetic accepted cancellation; reply unavailable")
        return result


class Finance(Controlled):
    def __init__(self):
        super().__init__()
        self.lookups = 0

    def lookup_payment(self, **kwargs):
        self.lookups += 1
        return super().lookup_payment(**kwargs)


def initialize(app):
    provider = app.state.test_finance
    courier = app.state.test_courier
    with app.state.session_factory() as s:
        seed_campaign_demo(s)
        for name, role in [
            ("ops.manager", "manager"),
            ("ops.viewer", "viewer"),
            ("ops.finance", "finance"),
        ]:
            provision(s, name, PASSWORD, BID, role, actor="synthetic-u04-u06-fixture")
        service = Service(
            s,
            payment_providers={"simulated": provider},
            financial_providers={"simulated": provider},
            delivery_providers={"simulated_delivery": courier},
        )
        _, delivery = delivery_order(service, idem="native-delivery-1")
        pay_accept(service, delivery)
        service.transition_order(delivery.id, "preparing")
        service.transition_order(delivery.id, "ready")
        payment = service.create_order(
            BID, order_request(service).model_copy(update={"idempotency_key": "native-finance-1"})
        )
        review = PaymentReconciliation(
            order_id=payment.id,
            business_id=BID,
            reason="contradictory_payment_notification",
            status="open",
            evidence_json='{"fixture":true}',
        )
        s.add(review)
        s.commit()
        body = order_request(service).model_copy(deep=True)
        c = Customer(business_id=BID, name="Synthetic verified customer", phone="+573005550777")
        s.add(c)
        s.commit()
        body.customer.phone = c.phone
        body.idempotency_key = "native-allocation-1"
        verified = Service(
            s,
            payment_providers={"simulated": provider},
            financial_providers={"simulated": provider},
            verified_customer_id=c.id,
        )
        allocation = verified.create_order(BID, body)
        pay_and_complete(verified, allocation)
        partial_refund(verified, allocation, 1000, reference="native-confirmed-partial")
        return {
            "delivery": s.scalar(select(Delivery.id).where(Delivery.order_id == delivery.id)),
            "delivery_order": delivery.id,
            "finance_order": payment.id,
            "allocation_order": allocation.id,
            "review": review.id,
            "item": body.items[0].menu_item_id,
        }


def app_fixture(database_url):
    provider, courier = Finance(), Courier()
    app = create_app(
        database_url=database_url,
        seed=True,
        demo_mode=True,
        payment_providers={"simulated": provider},
        financial_providers={"simulated": provider},
        delivery_providers={"simulated_delivery": courier},
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
    )
    app.state.test_finance = provider
    app.state.test_courier = courier
    app.state.test_ids = initialize(app)
    return app


@pytest.fixture
def env(factory):
    provider, courier = Finance(), Courier()
    app = create_app(
        engine=factory.kw["bind"],
        demo_mode=True,
        payment_providers={"simulated": provider},
        financial_providers={"simulated": provider},
        delivery_providers={"simulated_delivery": courier},
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
    )
    app.state.test_finance = provider
    app.state.test_courier = courier
    ids = initialize(app)
    with TestClient(app) as c:
        headers = staff_headers(c, name="ops.manager", business_id=BID)
        yield SimpleNamespace(
            client=c,
            headers=headers,
            ids=ids,
            app=app,
            provider=provider,
            courier=courier,
            factory=factory,
        )


def test_native_read_models_scope_pagination_and_readonly_provider_behavior(env):
    c = env.client
    d = c.get(ROOT + "/sales-deliveries").json()
    assert d["count"] == 1 and d["items"][0]["id"] == env.ids["delivery"]
    assert "dispatch" in d["items"][0]["actions"]
    assert c.get(ROOT + "/financial-orders").json()["count"] == 1
    before = (env.provider.calls, env.provider.lookups, env.courier.dispatches)
    detail = c.get(ROOT + "/financial-orders/" + env.ids["finance_order"])
    assert detail.status_code == 200 and detail.json()["allocation"]["blocker"]
    assert (
        c.get(f"/api/finance/restaurants/{BID}/orders/" + env.ids["finance_order"]).status_code
        == 200
    )
    assert before == (env.provider.calls, env.provider.lookups, env.courier.dispatches)
    for path in ["/sales-deliveries", "/financial-orders", "/settings"]:
        assert c.get(ROOT.replace(BID, "other-campaign-test") + path).status_code == 403
    assert c.get(ROOT + "/sales-deliveries/missing").status_code == 404
    with TestClient(env.app) as anon:
        for path in ["/sales-deliveries", "/financial-orders", "/daily-finance?day=2026-01-05"]:
            assert anon.get(ROOT + path).status_code == 401
    # Bounded reads stay independent of the newest order page and expose all rows.
    with env.factory() as s:
        row = s.get(Delivery, env.ids["delivery"])
        row.created_at = datetime(2020, 1, 1, tzinfo=UTC)
        s.commit()
    assert (
        c.get(ROOT + "/sales-deliveries", params={"limit": 1}).json()["items"][0]["id"]
        == env.ids["delivery"]
    )
    assert c.get(ROOT + "/sales-deliveries", params={"status": "wrong"}).status_code == 422


def test_delivery_versions_payment_hold_cancellation_and_no_duplicate_call(env):
    c = env.client
    root = ROOT + "/sales-deliveries/" + env.ids["delivery"]
    path = "/api/operator/orders/" + env.ids["delivery_order"] + "/delivery/"
    d = c.get(root).json()
    body = {"expected_version": d["version"], "expected_order_version": d["order_version"]}
    with env.factory() as s:
        s.add(
            PaymentReconciliation(
                order_id=env.ids["delivery_order"],
                business_id=BID,
                reason="native-fixture-hold",
                evidence_json="{}",
            )
        )
        s.commit()
    assert "dispatch" not in c.get(root).json()["actions"]
    assert c.post(path + "dispatch", json=body, headers=env.headers).status_code == 409
    assert env.courier.dispatches == 0
    with env.factory() as s:
        r = s.scalar(
            select(PaymentReconciliation).where(
                PaymentReconciliation.order_id == env.ids["delivery_order"]
            )
        )
        r.status = "resolved"
        s.commit()
    response = c.post(path + "dispatch", json=body, headers=env.headers)
    assert response.status_code == 200, response.text
    assert env.courier.dispatches == 1
    assert c.post(path + "dispatch", json=body, headers=env.headers).status_code == 409
    d = c.get(root).json()
    versions = {"expected_version": d["version"], "expected_order_version": d["order_version"]}
    assert (
        c.post(path + "cancel", json=versions, headers=env.headers).json()["status"] == "cancelled"
    )
    assert c.post(path + "cancel", headers=env.headers).json()["status"] == "cancelled"
    assert env.courier.cancels == 1
    with env.factory() as s:
        assert s.get(Order, env.ids["delivery_order"]).status == "ready"


def test_parallel_delivery_cancels_call_qualified_simulator_once(env):
    with env.factory() as s:
        Service(s, delivery_providers={"simulated_delivery": env.courier}).dispatch_delivery(
            env.ids["delivery_order"]
        )

    def cancel(_):
        with env.factory() as s:
            try:
                return (
                    Service(s, delivery_providers={"simulated_delivery": env.courier})
                    .cancel_delivery(env.ids["delivery_order"])
                    .status
                )
            except IdempotencyConflictError:
                return "in_progress"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(cancel, range(2)))
    assert "cancelled" in results and set(results) <= {"cancelled", "in_progress"}
    assert env.courier.cancels == 1


def test_delivery_manual_status_role_and_ready_guard(env):
    c = env.client
    d = c.post(
        "/api/operator/orders/" + env.ids["delivery_order"] + "/delivery/dispatch",
        headers=env.headers,
    ).json()
    url = "/api/operator/deliveries/" + d["id"] + "/status"
    for target in ["picked_up", "delivered"]:
        current = c.get(ROOT + "/sales-deliveries/" + d["id"]).json()
        r = c.patch(
            url,
            json={
                "status": target,
                "expected_version": current["version"],
                "expected_order_version": current["order_version"],
            },
            headers=env.headers,
        )
        assert r.status_code == 200, r.text
    with env.factory() as s:
        assert s.get(Order, env.ids["delivery_order"]).status == "completed"
    viewer = staff_headers(c, name="ops.viewer", role="viewer", business_id=BID)
    assert c.get(ROOT + "/sales-deliveries").status_code == 200
    assert c.patch(url, json={"status": "cancelled"}, headers=viewer).status_code == 403


def test_financial_allocation_is_source_bound_immutable_and_role_checked(env):
    c = env.client
    url = ROOT + "/financial-orders/" + env.ids["allocation_order"]
    m = c.get(url).json()
    assert m["refunds"][0]["amount_minor"] == 1000 and m["refunds"][0]["currency"] == "COP"
    assert m["allocation"]["basis"] == "baseline" and m["allocation"]["blocker"] is None
    assert all(line["remaining_minor"] is None for line in m["allocation"]["lines"])
    refund = m["refunds"][0]
    line = m["allocation"]["lines"][0]["id"]
    target = f"/api/finance/restaurants/{BID}/loyalty-refunds/{refund['id']}/allocation"
    payload = {"lines": {line: 1000}, "delivery_fee_minor": 0}
    assert c.post(target, json=payload).status_code == 403
    assert (
        c.post(
            target,
            json={"lines": {"foreign-line": 1000}, "delivery_fee_minor": 0},
            headers=env.headers,
        ).status_code
        == 422
    )
    assert c.post(target, json=payload, headers=env.headers).status_code == 200
    assert c.post(target, json=payload, headers=env.headers).status_code == 200
    assert c.get(url).json()["allocation"]["allocations"][0]["document"] == payload
    changed = {"lines": {line: 900}, "delivery_fee_minor": 100}
    assert c.post(target, json=changed, headers=env.headers).status_code == 422
    viewer = staff_headers(c, name="ops.viewer", role="viewer", business_id=BID)
    assert (
        c.get(url).status_code == 200
        and c.post(target, json=payload, headers=viewer).status_code == 403
    )


def test_settings_role_conflicts_and_midnight_roundtrip(env):
    c = env.client
    before = c.get(ROOT + "/settings").json()
    body = {
        **before["policy"],
        "expected_version": before["version"],
        "opens": 0,
        "closes": 1440,
        "scheduled": True,
        "reason": "Synthetic all-day pickup",
    }
    saved = c.put(ROOT + "/settings", json=body, headers=env.headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["policy"]["closes"] == 1440
    assert c.put(ROOT + "/settings", json=body, headers=env.headers).status_code == 409
    item = next(i for i in saved.json()["items"] if i["id"] == env.ids["item"])
    payload = {
        "remaining": 0,
        "sold_out": True,
        "reason": "Synthetic empty stock",
        "expected_version": item["version"],
    }
    assert (
        c.put(ROOT + "/stock/" + item["id"], json=payload, headers=env.headers).status_code == 200
    )
    assert (
        c.put(ROOT + "/stock/" + item["id"], json=payload, headers=env.headers).status_code == 409
    )
    with env.factory() as s:
        assert s.get(MenuItem, item["id"]).sold_out
    viewer = staff_headers(c, name="ops.viewer", role="viewer", business_id=BID)
    assert c.put(ROOT + "/settings", json=body, headers=viewer).status_code == 403


def test_daily_finance_currency_and_unknown_settlement(env):
    with env.factory() as s:
        customer = s.scalar(select(Customer).where(Customer.business_id == BID))
        for currency, total in [("COP", 10000), ("USD", 100)]:
            s.add(
                Order(
                    id="daily-" + currency,
                    public_code="DAILY-" + currency,
                    business_id=BID,
                    customer_id=customer.id,
                    status="completed",
                    payment_status="paid",
                    currency=currency,
                    subtotal_minor=total,
                    total_minor=total,
                    prep_minutes=15,
                    created_at=datetime(2026, 1, 5, 15, tzinfo=UTC),
                )
            )
        s.commit()
    c = env.client
    path = ROOT + "/daily-finance?day=2026-01-05"
    d = c.get(path).json()
    assert d["currencies"] == ["COP", "USD"] and d["currency"] is None
    for currency, total in [("COP", 10000), ("USD", 100)]:
        d = c.get(path + "&currency=" + currency).json()
        assert d["orders"] == 1 and d["gross_minor"] == total and d["known_balance_minor"] == total
        assert d["provider_fees_minor"] is None and d["settled_net_minor"] is None
        assert d["basis"] == "order_creation_day_current_local_payment_state"


def test_courier_unknown_survives_new_request_without_repeating_external_effect(env):
    c = env.client
    path = "/api/operator/orders/" + env.ids["delivery_order"] + "/delivery/"
    env.courier.lose = True
    assert c.post(path + "dispatch", headers=env.headers).status_code == 503
    for _ in range(2):
        d = c.get(ROOT + "/sales-deliveries/" + env.ids["delivery"]).json()
        assert d["dispatch_pending"] and not d["actions"] and d["status"] == "quoted"
        assert c.post(path + "dispatch", headers=env.headers).status_code == 409
        assert c.post(path + "cancel", headers=env.headers).status_code == 409
    assert env.courier.dispatches == 1
    env.courier.lose = False
    with env.factory() as s:
        service = Service(s, delivery_providers={"simulated_delivery": env.courier})
        _, order = delivery_order(service, idem="native-cancel-unknown")
        pay_accept(service, order)
        d = service.dispatch_delivery(order.id)
    env.courier.lose_cancel = True
    path = "/api/operator/orders/" + order.id + "/delivery/"
    assert c.post(path + "cancel", headers=env.headers).status_code == 503
    assert c.post(path + "cancel", headers=env.headers).status_code == 409
    result = c.get(ROOT + "/sales-deliveries/" + d.id).json()
    assert result["cancellation_requested"] and result["status"] == "courier_assigned"
    assert "cancel" not in result["actions"] and env.courier.cancels == 1


def test_allocation_projection_uses_verified_execution_snapshot(configured):
    from world_model.restaurant_commerce.finance_workspace import allocation_context

    factory, version, customer = configured
    with factory() as session:
        service = execution_service(session, version, customer)
        body = order_request(service)
        order = service.create_order(BID, body)
        pay_and_complete(service, order)
        current = session.get(Order, order.id)
        before = allocation_context(session, current)
        assert before["basis"] == "execution" and before["blocker"] is None
        assert before["lines"][0]["remaining_minor"] > 0
        line = before["lines"][0]["id"]
        partial_refund(
            service,
            order,
            1000,
            reference="native-execution-partial",
            allocation={"lines": {line: 1000}, "delivery_fee_minor": 0},
        )
        after = allocation_context(session, current)
        assert after["lines"][0]["remaining_minor"] == before["lines"][0]["remaining_minor"] - 1000
        assert len(after["allocations"]) == 1
