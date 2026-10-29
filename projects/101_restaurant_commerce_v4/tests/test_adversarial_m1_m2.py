"""Offline attack regressions: all identities/providers/databases are synthetic."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_customer_safety_m2 import BUSINESS, ROOT, payload
from staff_helpers import staff_headers
from test_customer_safety_m2 import (
    env as env,  # noqa: PLC0414 - pytest fixture re-export
)

from world_model.restaurant_commerce.models import (
    IdempotencyRecord,
    Order,
    OutboundMessage,
)


@pytest.mark.parametrize("field", ["name", "phone", "notes", "idempotency_key"])
def test_unpaired_unicode_surrogates_rejected_without_writes(env, field):
    app, client, items, _, _ = env
    body = payload(items)
    if field in {"name", "phone"}:
        body["customer"][field] += "\ud800"
    else:
        body[field] = "bad\ud800"
    response = client.post(
        ROOT + "/orders",
        content=json.dumps(body),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422, response.text
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 0
        assert s.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0


@pytest.mark.parametrize(
    "phone", ["3001234567١", "3001234567²", "3001234567abc", "3001234567;999"]
)
def test_ambiguous_phone_cannot_authorize_different_browser_recipient(env, phone):
    _, client, items, _, _ = env
    body = payload(items)
    body["customer"]["phone"] = phone
    response = client.post(ROOT + "/orders", json=body)
    assert response.status_code == 422, response.text


def test_failed_validation_does_not_permanently_poison_replay_key(env):
    app, client, items, _, _ = env
    body = payload(items)
    body["items"][0]["menu_item_id"] = "missing-item"
    first = client.post(ROOT + "/orders", json=body)
    second = client.post(ROOT + "/orders", json=body)
    assert first.status_code == second.status_code == 404
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0


def test_simultaneous_exact_and_conflicting_replays(env):
    app, client, items, _, _ = env
    body = payload(items)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(
            pool.map(lambda _: client.post(ROOT + "/orders", json=body), range(6))
        )
    assert all(r.status_code in {200, 409} for r in results), [
        (r.status_code, r.text) for r in results
    ]
    successful = [r.json() for r in results if r.status_code == 200]
    assert successful and len({o["id"] for o in successful}) == 1
    changed = payload(items)
    changed["customer"]["name"] = "Different attacker"
    assert client.post(ROOT + "/orders", json=changed).status_code == 409
    assert client.post(ROOT + "/orders", json=body).json()["id"] == successful[0]["id"]
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1


@pytest.mark.parametrize("purpose", ["unknown", "", "MARKETING"])
def test_unrecognized_message_purpose_fails_closed(env, purpose):
    app, client, _, _, victim = env
    with app.state.session_factory() as s:
        message = OutboundMessage(
            business_id=BUSINESS,
            customer_id=victim,
            channel="whatsapp",
            purpose=purpose,
            message_kind="winback",
            destination="3001234567",
            body="Synthetic",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
            dedupe_key="unknown-purpose",
        )
        s.add(message)
        s.commit()
        mid = message.id
    assert (
        client.post(
            "/api/operator/outbox/" + mid + "/handoff", headers=staff_headers(client)
        ).status_code
        == 422
    )


def test_reservation_exact_replay_does_not_duplicate(env):
    _, client, _, _, _ = env
    body = {
        "customer": {"name": "Synthetic", "phone": "3001234567"},
        "starts_at": (datetime.now(UTC) + timedelta(days=3))
        .replace(hour=12, minute=0, second=0, microsecond=0)
        .isoformat(),
        "party_size": 2,
        "idempotency_key": "race-reservation",
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(lambda _: client.post(ROOT + "/reservations", json=body), range(4))
        )
    assert all(r.status_code in {200, 409} for r in responses)
    ids = {r.json()["id"] for r in responses if r.status_code == 200}
    assert len(ids) == 1


def test_nonfinite_coordinate_errors_are_serializable(env):
    _, client, _, _, _ = env
    response = client.post(
        ROOT + "/delivery/quote",
        content='{"destination":{"address_line":"Synthetic street","latitude":NaN,"longitude":-74}}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422 and "NaN" not in response.text


def test_failed_no_key_order_rolls_back_guest_profile(env):
    from world_model.restaurant_commerce.models import Customer

    app, client, items, _, _ = env
    body = payload(items)
    body.pop("idempotency_key")
    body["customer"]["phone"] = "3000000123"
    body["items"][0]["menu_item_id"] = "missing"
    assert client.post(ROOT + "/orders", json=body).status_code == 404
    with app.state.session_factory() as s:
        assert s.scalar(select(Customer).where(Customer.phone == "3000000123")) is None


def test_formatted_ascii_phone_is_canonical_and_unicode_name_remains_valid(env):
    _, client, items, _, _ = env
    body = payload(items)
    body["customer"].update(phone="+57 (300) 123-4567", name="María 李 👩🏽‍🍳")
    response = client.post(ROOT + "/orders", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["customer_phone"] == "+573001234567"
    assert response.json()["customer_name"] == "María 李 👩🏽‍🍳"


def test_every_operator_route_rejects_missing_and_wrong_credentials(env):
    import re

    app, client, _, _, _ = env
    checked = 0
    for route in app.routes:
        if not getattr(route, "path", "").startswith("/api/operator/"):
            continue
        url = re.sub(r"\{[^}]+\}", "synthetic", route.path)
        for method in route.methods - {"HEAD", "OPTIONS"}:
            for headers in [{}, {"X-101-Operator-Token": "wrong-synthetic-token"}]:
                response = client.request(method, url, json={}, headers=headers)
                assert response.status_code == 401, (method, url, response.status_code)
            checked += 1
    assert checked >= 20


def test_capability_cannot_cross_orders_or_be_extended_by_editing_expiry(env):
    _, client, items, _, _ = env
    first = client.post(ROOT + "/orders", json=payload(items)).json()
    second = client.post(
        ROOT + "/orders", json=payload(items, idempotency_key="second-order")
    ).json()
    prefix, expiry, signature = first["access_token"].split(".")
    forged = [
        first["access_token"],
        f"{prefix}.{int(expiry) + 864000}.{signature}",
        "v2." + "9" * 100 + ".x",
        "..",
        "a" * 1000,
        "v2.99999999999." + "0" * 64,
    ]
    for token in forged:
        response = client.get(
            "/api/orders/" + second["id"], headers={"X-101-Order-Token": token}
        )
        assert response.status_code == 401 and "Guest supplied" not in response.text
        assert response.headers["cache-control"] == "no-store"
    assert (
        client.get(
            "/api/orders/" + second["id"],
            headers={"X-101-Order-Token": second["access_token"]},
        ).status_code
        == 200
    )
