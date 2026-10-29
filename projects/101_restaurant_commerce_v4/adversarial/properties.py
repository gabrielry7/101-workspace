"""Bounded live HTTP property sequences; no test double replaces the application.

Run: python adversarial/properties.py --config RUN/config.json --output RUN/properties
The config is task-local and contains only synthetic credentials. Every example
uses fresh resource identifiers, so shrinking does not reuse consumed state.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.metadata
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest
from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st

RUN = None
COUNTS = Counter()
SEED = 101027
BOUNDED = settings(
    max_examples=30,
    deadline=None,
    database=None,
    phases=(Phase.explicit, Phase.generate, Phase.shrink),
)


def cfg():
    global RUN
    if RUN is None:
        RUN = json.loads(Path(os.environ["COMMERCE_PROPERTY_CONFIG"]).read_text())
        host = urlsplit(RUN["base_url"]).hostname
        assert host in {"127.0.0.1", "localhost", "::1"}, (
            "Only disposable loopback targets are allowed"
        )
    return RUN


def http(method, path, *, operator=False, headers=None, **kwargs):
    merged = dict(headers or {})
    if operator:
        merged["X-101-Operator-Token"] = cfg()["operator_token"]
    started = time.monotonic()
    response = httpx.request(
        method,
        cfg()["base_url"].rstrip("/") + path,
        headers=merged,
        timeout=15,
        trust_env=False,
        **kwargs,
    )
    COUNTS["http_requests"] += 1
    COUNTS["http_status_" + str(response.status_code)] += 1
    with (Path(os.environ["COMMERCE_PROPERTY_OUTPUT"]) / "requests.jsonl").open(
        "a"
    ) as stream:
        stream.write(
            json.dumps(
                {
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "elapsed_ms": round(1000 * (time.monotonic() - started), 3),
                    "operator_authorized": operator,
                }
            )
            + "\n"
        )
    return response


def business(index=0):
    return cfg().get("business_ids", ["demo-restaurant-bogota"])[index]


def setup_order(quantity=1, whatsapp=False, marketing=False):
    bid = business()
    store = http("GET", f"/api/restaurants/{bid}/storefront")
    assert store.status_code == 200, store.text
    store = store.json()
    item = next(
        i
        for m in store["menus"]
        for c in m["categories"]
        for i in c["items"]
        if i["available"] and not i["modifier_groups"]
    )
    identity = uuid4().hex
    body = {
        "customer": {
            "name": "Property " + identity,
            "phone": "3" + str(int(identity[:10], 16)).zfill(12)[-9:],
            "whatsapp_opt_in": whatsapp,
            "marketing_opt_in": marketing,
        },
        "items": [{"menu_item_id": item["id"], "quantity": quantity, "modifiers": []}],
        "payment_provider": store["payment_provider"],
        "idempotency_key": "prop-" + identity,
    }
    quote = http(
        "POST", f"/api/restaurants/{bid}/orders/quote", json={"items": body["items"]}
    )
    assert quote.status_code == 200, quote.text
    response = http("POST", f"/api/restaurants/{bid}/orders", json=body)
    assert response.status_code == 200, response.text
    order = response.json()
    assert (
        order["total_minor"]
        == quote.json()["total_minor"]
        == item["base_price_minor"] * quantity
    )
    COUNTS["created_orders"] += 1
    return bid, body, order


def read_order(order):
    response = http(
        "GET",
        "/api/orders/" + order["id"],
        headers={"X-101-Order-Token": order["access_token"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def webhook(order, status="paid", *, valid=True, amount=None):
    payment = order["payments"][0]
    provider = payment["provider"]
    secret = cfg().get("webhook_secrets", {}).get(provider, cfg().get("webhook_secret"))
    assert secret, "Configured signed webhook test credentials are required"
    body = {
        "event_id": "prop-event-" + uuid4().hex,
        "provider_reference": payment["provider_reference"],
        "status": status,
        "amount_minor": payment["amount_minor"] if amount is None else amount,
        "currency": payment["currency"],
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    signature = (
        hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest() if valid else "wrong"
    )
    return http(
        "POST",
        "/api/webhooks/payments/" + provider,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-101-Webhook-Signature": signature,
        },
    )


@seed(SEED)
@BOUNDED
@given(
    actions=st.lists(
        st.sampled_from(
            [
                "quote",
                "retry",
                "conflict",
                "wrong_token",
                "bad_webhook",
                "pay",
                "advance",
            ]
        ),
        min_size=3,
        max_size=10,
    ),
    quantity=st.integers(min_value=1, max_value=5),
)
def test_generated_order_actions_preserve_value_identity_and_authority(
    actions, quantity
):
    COUNTS["sequence_examples"] += 1
    bid, body, order = setup_order(quantity)
    expected_status = order["status"]
    expected_payment = order["payment_status"]
    next_status = {
        "placed": "accepted",
        "accepted": "preparing",
        "preparing": "ready",
        "ready": "completed",
    }
    for action in actions:
        COUNTS["transitions"] += 1
        COUNTS["action_" + action] += 1
        if action == "quote":
            result = http(
                "POST",
                f"/api/restaurants/{bid}/orders/quote",
                json={"items": body["items"]},
            )
            assert (
                result.status_code == 200
                and result.json()["total_minor"] == order["total_minor"]
            )
        elif action == "retry":
            result = http("POST", f"/api/restaurants/{bid}/orders", json=body)
            assert result.status_code == 200 and result.json()["id"] == order["id"]
        elif action == "conflict":
            altered = {**body, "notes": "different intent with same key"}
            assert (
                http("POST", f"/api/restaurants/{bid}/orders", json=altered).status_code
                == 409
            )
        elif action == "wrong_token":
            assert (
                http(
                    "GET",
                    "/api/orders/" + order["id"],
                    headers={"X-101-Order-Token": "invalid"},
                ).status_code
                == 401
            )
        elif action == "bad_webhook":
            assert webhook(order, valid=False).status_code == 401
        elif action == "pay":
            result = webhook(order)
            assert result.status_code == 200, result.text
            expected_payment = "paid"
            if expected_status == "awaiting_payment":
                expected_status = "placed"
        elif action == "advance":
            target = next_status.get(expected_status, "accepted")
            result = http(
                "PATCH",
                "/api/operator/orders/" + order["id"],
                operator=True,
                json={"status": target},
            )
            if expected_status in next_status:
                assert result.status_code == 200, result.text
                expected_status = target
            else:
                assert result.status_code == 409, result.text
        got = read_order(order)
        assert (
            got["id"],
            got["total_minor"],
            got["customer_name"],
            got["customer_phone"],
        ) == (
            order["id"],
            order["total_minor"],
            body["customer"]["name"],
            body["customer"]["phone"],
        )
        assert (got["status"], got["payment_status"]) == (
            expected_status,
            expected_payment,
        )
        assert (
            len(got["payments"]) == 1
            and got["payments"][0]["amount_minor"] == order["total_minor"]
        )


@seed(SEED + 1)
@BOUNDED
@given(
    consents=st.lists(st.tuples(st.booleans(), st.booleans()), min_size=2, max_size=8)
)
def test_guest_consent_sequences_do_not_rewrite_prior_snapshots(consents):
    COUNTS["consent_examples"] += 1
    bid, body, original = setup_order(whatsapp=consents[0][0], marketing=consents[0][1])
    for wa, marketing in consents:
        altered = {
            **body,
            "idempotency_key": "prop-consent-" + uuid4().hex,
            "customer": {
                **body["customer"],
                "name": "Different guest",
                "whatsapp_opt_in": wa,
                "marketing_opt_in": marketing,
            },
        }
        response = http("POST", f"/api/restaurants/{bid}/orders", json=altered)
        assert response.status_code == 200, response.text
        assert response.json()["customer_name"] == "Different guest"
        got = read_order(original)
        assert got["customer_name"] == body["customer"]["name"]
        outbox = http("GET", f"/api/operator/restaurants/{bid}/outbox", operator=True)
        assert outbox.status_code == 200
        assert not any(
            row["destination"] == body["customer"]["phone"] for row in outbox.json()
        )
        COUNTS["consent_transitions"] += 1


@seed(SEED + 2)
@BOUNDED
@given(
    invalid_quantity=st.one_of(
        st.integers(max_value=0), st.integers(min_value=51, max_value=100000)
    )
)
def test_rejected_quantity_does_not_consume_order_intent(invalid_quantity):
    COUNTS["rejected_examples"] += 1
    bid, body, original = setup_order()
    candidate = {
        **body,
        "idempotency_key": "prop-invalid-" + uuid4().hex,
        "items": [{**body["items"][0], "quantity": invalid_quantity}],
    }
    rejected = http("POST", f"/api/restaurants/{bid}/orders", json=candidate)
    assert rejected.status_code == 422, rejected.text
    repaired = {**candidate, "items": body["items"]}
    accepted = http("POST", f"/api/restaurants/{bid}/orders", json=repaired)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["id"] != original["id"]
    replay = http("POST", f"/api/restaurants/{bid}/orders", json=repaired)
    assert replay.status_code == 200 and replay.json()["id"] == accepted.json()["id"]


@seed(SEED + 3)
@settings(max_examples=8, deadline=None, database=None)
@given(
    payload=st.sampled_from(
        [
            '{"event_id":"\\ud800"}',
            '{"amount_minor":NaN}',
            '{"event_id":{},"provider_reference":[]}',
        ]
    )
)
def test_signed_malformed_payment_notifications_reject_without_500(payload):
    COUNTS["signed_malformed_examples"] += 1
    provider = cfg().get("payment_provider", "simulated")
    secret = cfg().get("webhook_secrets", {}).get(provider, cfg().get("webhook_secret"))
    assert secret, "Configured signed webhook test credentials are required"
    raw = payload.encode()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    response = http(
        "POST",
        "/api/webhooks/payments/" + provider,
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-101-Webhook-Signature": signature,
        },
    )
    assert response.status_code == 422, response.text


def test_cancel_then_paid_requires_reconciliation_obligation():
    _, _, order = setup_order()
    cancelled = http(
        "PATCH",
        "/api/operator/orders/" + order["id"],
        operator=True,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200, cancelled.text
    paid = webhook(order)
    assert paid.status_code == 200, paid.text
    got = read_order(order)
    # This is a release requirement, not a claim that M2 implemented it.
    assert not (got["status"] == "cancelled" and got["payment_status"] == "paid"), (
        "Known M3 gap: late payment leaves cancelled/paid without a surfaced reconciliation obligation",
        got["id"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["COMMERCE_PROPERTY_CONFIG"] = str(Path(args.config).resolve())
    os.environ["COMMERCE_PROPERTY_OUTPUT"] = str(output)
    started = datetime.now(UTC).isoformat()

    # pytest imports this file under its module name. Persist counts on pytest's
    # imported module through a plugin, rather than confusing it with __main__.
    class Receipt:
        def pytest_sessionfinish(self, session, exitstatus):
            module = sys.modules.get("properties")
            counts = dict(getattr(module, "COUNTS", COUNTS))
            result = {
                "tool": "Hypothesis + pytest",
                "version": importlib.metadata.version("hypothesis"),
                "started_at": started,
                "ended_at": datetime.now(UTC).isoformat(),
                "command": [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--config",
                    args.config,
                    "--output",
                    args.output,
                ],
                "revision": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "target": cfg()["base_url"],
                "seed": SEED,
                "exit_code": int(exitstatus),
                "collected_tests": session.testscollected,
                "failed_tests": session.testsfailed,
                "execution": "COMPLETE"
                if session.testscollected == 5 and exitstatus in (0, 1)
                else "PARTIAL",
                "outcome": "PASS"
                if exitstatus == 0 and session.testscollected
                else "FAIL"
                if exitstatus == 1
                else "UNASSESSED",
                "counts": counts,
                "limits": [
                    "Only configured global staff authority exists; scoped staff/customer login absent",
                    "Generated sequences bounded to30 examples per main property and10 actions; not exhaustive",
                    "No real money or external providers; controlled services only",
                ],
            }
            (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")

    code = pytest.main(
        [
            str(Path(__file__).resolve()),
            "-q",
            "--hypothesis-show-statistics",
            "--junitxml=" + str(output / "junit.xml"),
        ],
        plugins=[Receipt()],
    )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
