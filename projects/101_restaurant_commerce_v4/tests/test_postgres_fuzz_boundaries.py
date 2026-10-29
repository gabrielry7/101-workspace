from staff_helpers import staff_headers
"""Minimized regressions discovered with live PostgreSQL and generated requests."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from world_model.restaurant_commerce.api import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'fuzz.db'}",
        seed=True,
        webhook_secrets={"simulated": "test-hook", "simulated_delivery": "test-hook"},
    )
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "field", ["menu_item_id", "modifier_option", "name", "idempotency_key"]
)
def test_nul_rejected_before_database(client, field):
    item = {"menu_item_id": "unknown", "quantity": 1, "modifiers": []}
    body = {
        "customer": {"name": "Synthetic", "phone": "3005550000"},
        "items": [item],
        "idempotency_key": "synthetic",
    }
    if field == "menu_item_id":
        item["menu_item_id"] = "a\x00b"
    elif field == "modifier_option":
        item["modifiers"] = [{"group_id": "g", "option_ids": ["a\x00b"]}]
    elif field == "name":
        body["customer"]["name"] = "a\x00b"
    else:
        body[field] = "a\x00b"
    assert (
        client.post(
            "/api/restaurants/demo-restaurant-bogota/orders", json=body
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "field", ["points_cost", "discount_minor", "minimum_order_minor"]
)
def test_storage_integer_overflow_is_validation_error(client, field):
    body = {
        "name": "Synthetic reward",
        "points_cost": 1,
        "discount_minor": 1,
        field: 2**63,
    }
    r = client.post(
        "/api/operator/restaurants/demo-restaurant-bogota/rewards",
        json=body,
        headers=staff_headers(client),
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "kind,provider,body",
    [
        (
            "payments",
            "simulated",
            {
                "event_id": "bad",
                "provider_reference": "sim_test",
                "status": "paid",
                "amount_minor": float("nan"),
                "currency": "COP",
            },
        ),
        (
            "payments",
            "simulated",
            {
                "event_id": "\ud800",
                "provider_reference": "sim_test",
                "status": "paid",
                "amount_minor": 0,
                "currency": "COP",
            },
        ),
        (
            "deliveries",
            "simulated_delivery",
            {
                "event_id": "\ud800",
                "provider_delivery_reference": "test",
                "status": "delivered",
            },
        ),
    ],
)
def test_signed_webhook_invalid_input_serializes_safely(client, kind, provider, body):
    raw = json.dumps(body).encode()
    signature = hmac.new(b"test-hook", raw, hashlib.sha256).hexdigest()
    r = client.post(
        "/api/webhooks/" + kind + "/" + provider,
        content=raw,
        headers={
            "X-101-Webhook-Signature": signature,
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 422 and "input" not in r.json()["detail"][0]


def test_domain_validation_matches_documented_error_schema(client):
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/api/restaurants/{business_id}/orders"]["post"]["responses"][
        "422"
    ]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")

    ready = spec["paths"]["/ready"]["get"]["responses"]["503"]["content"][
        "application/json"
    ]["schema"]
    assert ready["type"] == "object"
    assert ready["additionalProperties"] == {"type": "string"}
