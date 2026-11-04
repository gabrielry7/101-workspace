"""Schemathesis/Hypothesis cases against fresh real resources, with state checks.

Invoke through the S01/S02 runner, never against a shared/production database.
Native JUnit and the private minimized Hypothesis report are retained by pytest.
"""

import base64
import json
import os
from pathlib import Path

import pytest
import schemathesis
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st
from load_contract import validate_target
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import response_schema_conformance
from security_fixtures import Fixtures

CONFIG_PATH = Path(os.environ["COMMERCE_RECORD_CONFIG"])
CONFIG = json.loads(CONFIG_PATH.read_text())
validate_target(CONFIG, CONFIG_PATH)
SCHEMA = schemathesis.openapi.from_url(CONFIG["base_url"] + "/openapi.json")
PATHS = [
    (method.upper(), path)
    for path, item in SCHEMA.raw_schema["paths"].items()
    for method in item
    if method in {"get", "post", "put", "patch"}
    if (
        "/campaigns" in path
        or "/finance/" in path
        or "{delivery_id}" in path
        or "{message_id}" in path
    )
]
OUTPUT = Path(os.environ["COMMERCE_RECORD_OUTPUT"])


@pytest.fixture(scope="module")
def records():
    f = Fixtures(CONFIG)
    yield f
    f.close()


def invoke(records, method, path, case, label, bind_evidence=False):
    ids, valid_body = records.prepare(method, path)
    case.path_parameters = {k: ids[k] for k in (case.path_parameters or {})}
    # Explicit success examples use freshly generated digests/operation IDs.
    if label == "valid":
        case.body = valid_body if valid_body is not None else schemathesis.core.NOT_SET
    if bind_evidence and isinstance(case.body, dict) and "operation_id" in case.body:
        case.body["operation_id"] = valid_body["operation_id"]
    if bind_evidence and isinstance(case.body, dict) and isinstance(valid_body, dict):
        if "customer_ids" in case.body and "customer_ids" in valid_body:
            case.body["customer_ids"] = valid_body["customer_ids"]
    expected_missing_audience = (
        label == "generated"
        and "/campaigns" in path
        and isinstance(case.body, dict)
        and isinstance(case.body.get("customer_ids"), list)
        and any(x not in records.config["customer_ids"][:1] for x in case.body["customer_ids"])
    )
    expected_missing_evidence = (
        label == "generated"
        and "{reconciliation_id}" in path
        and isinstance(case.body, dict)
        and case.body.get("operation_id") != valid_body["operation_id"]
    )
    case.headers = records.headers
    case.cookies = {}
    before = records.snapshot()
    response = case.call(base_url=CONFIG["base_url"], timeout=5)
    after = records.snapshot()
    row = {
        "method": method,
        "path": path,
        "label": label,
        "status": response.status_code,
        "state_unchanged": before == after,
        "bound_evidence": bind_evidence,
        "expected_missing_evidence": expected_missing_evidence,
        "expected_missing_audience": expected_missing_audience,
        "request_body": case.body if case.body is not schemathesis.core.NOT_SET else None,
        "query": case.query,
        "path_parameters": case.path_parameters,
        "media_type": case.media_type,
    }
    with OUTPUT.open("a") as out:
        out.write(
            json.dumps(
                row,
                default=lambda x: (
                    {"base64": base64.b64encode(x).decode()} if isinstance(x, bytes) else str(x)
                ),
            )
            + "\n"
        )
    assert response.status_code not in {401, 403}, "Fixture authentication failed"
    if response.status_code == 404:
        assert expected_missing_evidence or expected_missing_audience, (
            "Fixture failed to reach scoped records"
        )
    case.validate_response(response, checks=[not_a_server_error, response_schema_conformance])
    if response.status_code >= 400:
        assert before == after, "Rejected request changed protected financial/campaign state"
    return response


@pytest.mark.parametrize("method,path", PATHS)
def test_valid_record_success(records, method, path):
    # Resolve all path identifiers from real records; never generated unknown UUIDs.
    import re

    op = SCHEMA[path][method]
    case = op.Case(
        path_parameters={k: "fixture" for k in re.findall(r"{(.*?)}", path)},
        media_type="application/json" if op.body else None,
    )
    response = invoke(records, method, path, case, "valid")
    expected = 409 if path.endswith("/sent") else 200
    assert response.status_code == expected, response.text


@pytest.mark.parametrize("method,path", PATHS)
@settings(
    max_examples=8,
    deadline=None,
    derandomize=True,
    database=None,
    phases=[Phase.generate],  # Keep exact failures; do not spend the scan budget shrinking.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(data=st.data())
def test_generated_real_record_inputs(records, method, path, data):
    op = SCHEMA[path][method]
    strategies = [op.as_strategy()]
    if op.body or op.query:
        strategies.append(op.as_strategy(generation_mode=schemathesis.GenerationMode.NEGATIVE))
    case = data.draw(st.one_of(*strategies))
    invoke(records, method, path, case, "generated", bind_evidence=data.draw(st.booleans()))
