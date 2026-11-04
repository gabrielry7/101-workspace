"""Executed only on the owned S03 PostgreSQL deployment, never production."""

import base64
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import httpx
import pytest
import schemathesis
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st
from loyalty_security import ALLOCATION, PREVIEW, LoyaltyFixtures
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from world_model.restaurant_commerce.loyalty_execution_models import LoyaltyRefundAllocation
from world_model.restaurant_commerce.loyalty_wallet import reconcile
from world_model.restaurant_commerce.models import LoyaltyAccount
from world_model.restaurant_commerce.staff import provision

CONFIG = json.loads(Path(os.environ["COMMERCE_RECORD_CONFIG"]).read_text())
OUTPUT = Path(CONFIG["run_dir"]) / "loyalty-requests.ndjson"
SCHEMA = schemathesis.openapi.from_url(CONFIG["base_url"] + "/openapi.json")


@pytest.fixture(scope="module")
def f():
    fixtures = LoyaltyFixtures(CONFIG)
    with Session(fixtures.engine) as session:
        provision(
            session,
            "s03.viewer",
            CONFIG["staff_password"],
            fixtures.business,
            "viewer",
            actor="synthetic-test",
        )
    with httpx.Client(base_url=CONFIG["base_url"], trust_env=False) as client:
        client.post(
            "/api/staff/login",
            json={"username": "s03.viewer", "password": CONFIG["staff_password"]},
            headers={"X-101-Login": "1"},
        ).raise_for_status()
        me = client.get("/api/staff/me").json()
        fixtures.viewer = {
            "Cookie": "commerce_staff=" + client.cookies["commerce_staff"],
            "X-101-CSRF": me["csrf"],
        }
    yield fixtures
    fixtures.close()


def invoke(f, path, body, *, headers=None, method="POST", expected=None, unchanged=False, label=""):
    before = f.snapshot()
    started = time.monotonic()
    request_headers = {
        **(f.headers if headers is None else headers),
        "Content-Type": "application/json",
    }
    # Send escaped Unicode bytes: httpx's json= refuses lone surrogates locally,
    # which would otherwise test the client serializer rather than our server.
    response = f.http.request(
        method, path, headers=request_headers, content=json.dumps(body, ensure_ascii=True).encode()
    )
    after = f.snapshot()
    with OUTPUT.open("a") as out:
        out.write(
            json.dumps(
                {
                    "label": label,
                    "method": method,
                    "path": path,
                    "body": body,
                    "status": response.status_code,
                    "response": response.text[:3000],
                    "elapsed_ms": (time.monotonic() - started) * 1000,
                    "state_unchanged": before == after,
                    "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
                    "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
                    "protected_tables": f.invariant_tables,
                },
                default=str,
            )
            + "\n"
        )
    assert response.status_code < 500, response.text
    if expected is not None:
        assert response.status_code in expected, response.text
    if unchanged or response.status_code >= 400:
        assert before == after, "Read-only or rejected operation changed protected state"
    return response


def test_preview_real_success_and_hypothetical_balance_cannot_issue_points(f):
    ids, body = f.preview()
    for payload in [
        body,
        {**body, "assume_verified_identity": True, "assumed_available_points": 100000},
    ]:
        result = invoke(f, PREVIEW.format(**ids), payload, expected={200}, unchanged=True).json()
        assert result["result"]["mode"] == "hypothetical"
        assert result["result"]["execution_enabled"] is False


@pytest.mark.parametrize(
    "attack",
    [
        "anonymous",
        "customer_capability",
        "viewer_refund",
        "csrf",
        "foreign_business",
        "foreign_refund",
        "foreign_program",
        "foreign_version",
        "foreign_customer",
        "foreign_product",
    ],
)
def test_scope_and_roles(f, attack):
    ids, body = f.preview()
    other = CONFIG["business_ids"][1]
    headers = f.headers
    expected = {400, 403, 404, 422}
    template = PREVIEW
    if attack in {"viewer_refund", "foreign_refund"}:
        ids, body, _ = f.allocation(other if attack == "foreign_refund" else None)
        template = ALLOCATION
    if attack == "anonymous":
        headers, expected = {}, {401}
    elif attack == "customer_capability":
        headers, expected = {"X-101-Order-Token": CONFIG["baseline_order"]["access_token"]}, {401}
    elif attack == "viewer_refund":
        headers, expected = f.viewer, {403}
    elif attack == "csrf":
        headers, expected = {"Cookie": f.headers["Cookie"]}, {403}
    elif attack == "foreign_business":
        ids, body = f.preview(other)
        expected = {403}
    elif attack == "foreign_refund":
        ids["business_id"] = f.business
    elif attack == "foreign_program":
        ids["resource_id"] = f.programs[other]["resource_id"]
    elif attack == "foreign_version":
        ids["version_id"] = f.programs[other]["version_id"]
    elif attack == "foreign_customer":
        body["customer_id"] = CONFIG["customer_ids"][1]
    elif attack == "foreign_product":
        body["lines"][0]["product_id"] = f.programs[other]["item_id"]
    invoke(
        f,
        template.format(**ids),
        body,
        headers=headers,
        expected=expected,
        unchanged=True,
        label=attack,
    )


@pytest.mark.parametrize(
    "attack",
    [
        "negative",
        "boolean",
        "float",
        "string",
        "oversized",
        "wrong_sum",
        "foreign_line",
        "extra_field",
        "null_byte",
    ],
)
def test_rejected_refund_allocations_leave_wallet_untouched(f, attack):
    ids, body, _ = f.allocation()
    line = next(iter(body["lines"]))
    if attack in {"negative", "boolean", "float", "string", "oversized"}:
        body["lines"][line] = {
            "negative": -1,
            "boolean": True,
            "float": 1.5,
            "string": "1001",
            "oversized": 2**63,
        }[attack]
    elif attack == "wrong_sum":
        body["delivery_fee_minor"] = 1
    elif attack == "foreign_line":
        _, other, _ = f.allocation(CONFIG["business_ids"][1])
        body["lines"] = other["lines"]
    elif attack == "extra_field":
        body["actor"] = "attacker"
    else:
        body["lines"] = {"bad\x00line": 1001}
    invoke(f, ALLOCATION.format(**ids), body, expected={400, 422}, unchanged=True, label=attack)


@pytest.mark.parametrize("field", ["customer_id", "product_id", "line_id"])
@pytest.mark.parametrize("bad", ["bad\x00input", "bad\ud800input"])
def test_preview_invalid_unicode(f, field, bad):
    ids, body = f.preview()
    if field == "customer_id":
        body[field] = bad
    else:
        body["lines"][0][field] = bad
    invoke(
        f, PREVIEW.format(**ids), body, expected={400, 422}, unchanged=True, label="NUL-" + field
    )


@pytest.mark.parametrize("template", [PREVIEW, ALLOCATION])
def test_get_cannot_execute_json_post(f, template):
    ids, body = f.preview() if template == PREVIEW else f.allocation()[:2]
    invoke(
        f,
        template.format(**ids),
        body,
        method="GET",
        expected={405},
        unchanged=True,
        label="GET-for-POST",
    )


def test_concurrent_allocation_and_replay_compensate_exactly_once(f):
    ids, body, info = f.allocation()
    path = ALLOCATION.format(**ids)
    barrier = Barrier(4)

    def send(_):
        barrier.wait(timeout=10)
        return httpx.post(
            CONFIG["base_url"] + path, headers=f.headers, json=body, trust_env=False, timeout=20
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(send, range(4)))
    assert [r.status_code for r in responses] == [200] * 4, [r.text for r in responses]
    invoke(f, path, body, expected={200}, unchanged=True, label="exact-refund-replay")
    invoke(
        f,
        path,
        {"lines": {next(iter(body["lines"])): 1000}, "delivery_fee_minor": 1},
        expected={400, 422},
        unchanged=True,
        label="conflicting-allocation-replay",
    )
    with Session(f.engine) as session:
        account = session.get(LoyaltyAccount, info["account_id"])
        assert account.available_points < info["before_points"]
        assert account.available_points == 2 * ((info["total_minor"] - 1001) // 1000)
        assert reconcile(session, account)["reconciled"]
        assert (
            session.scalar(
                select(func.count())
                .select_from(LoyaltyRefundAllocation)
                .where(LoyaltyRefundAllocation.refund_id == ids["refund_id"])
            )
            == 1
        )
    (Path(CONFIG["run_dir"]) / "allocation-race.json").write_text(
        json.dumps(
            {
                "requests": 4,
                "statuses": [r.status_code for r in responses],
                "allocations": 1,
                "wallet_reconciled": True,
                "expected_points": 2 * ((info["total_minor"] - 1001) // 1000),
            }
        )
    )


@pytest.mark.parametrize("template", [PREVIEW, ALLOCATION])
@settings(
    max_examples=20,
    deadline=None,
    derandomize=True,
    database=None,
    phases=[Phase.generate],
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(data=st.data())
def test_schemathesis_optional_real_records(f, template, data):
    op = SCHEMA[template]["POST"]
    case = data.draw(
        st.one_of(
            op.as_strategy(), op.as_strategy(generation_mode=schemathesis.GenerationMode.NEGATIVE)
        )
    )
    ids, valid = f.preview() if template == PREVIEW else f.allocation()[:2]
    # Preserve generated body values; bind only path identifiers to actual records.
    case.path_parameters = {k: ids[k] for k in case.path_parameters}
    case.headers, case.cookies = f.headers, {}
    before = f.snapshot()
    response = case.call(base_url=CONFIG["base_url"], timeout=10)
    after = f.snapshot()
    with OUTPUT.open("a") as out:
        out.write(
            json.dumps(
                {
                    "label": "schemathesis",
                    "path": template,
                    "body": None if case.body is schemathesis.core.NOT_SET else case.body,
                    "path_parameters": case.path_parameters,
                    "status": response.status_code,
                    "response": response.text[:2000],
                    "state_unchanged": before == after,
                    "protected_tables": f.invariant_tables,
                },
                default=lambda v: (
                    {"base64": base64.b64encode(v).decode()} if isinstance(v, bytes) else str(v)
                ),
            )
            + "\n"
        )
    assert response.status_code not in {401, 403, 404}, "Real record/authentication setup lost"
    case.validate_response(response, checks=[schemathesis.checks.not_a_server_error])
    if template == PREVIEW or response.status_code >= 400:
        assert before == after
