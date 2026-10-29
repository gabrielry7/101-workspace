"""Bind opaque IDs/credentials to disposable fixtures; leave schema-generated data intact."""

import json
import os
from pathlib import Path

import schemathesis
from hypothesis import strategies as st

c = json.loads(Path(os.environ["COMMERCE_FUZZ_CONFIG"]).read_text())


@schemathesis.hook
def before_call(ctx, case, kwargs):
    ids = {
        "business_id": c["business_ids"][0],
        "order_id": c["fuzz_order"]["id"],
        "customer_id": c["customer_ids"][0],
        "provider_reference": c["fuzz_order"]["payments"][0]["provider_reference"],
    }
    for key, value in ids.items():
        if case.path_parameters and key in case.path_parameters:
            case.path_parameters[key] = value
    if c["fuzz_profile"] == "staff":
        case.headers = {
            **(case.headers or {}),
            **c["single_staff_headers"],
        }
    if c["fuzz_profile"] == "customer":
        case.headers = {
            **(case.headers or {}),
            "X-101-Order-Token": c["fuzz_order"]["access_token"],
        }


@schemathesis.hook
def before_generate_body(ctx, strategy):
    path = ctx.operation.path
    if path.endswith("/orders") and ctx.operation.method.lower() == "post":
        return st.one_of(strategy, st.just(c["fuzz_body"]))
    if path.endswith("/orders/quote"):
        return st.one_of(strategy, st.just({"items": c["cart"]}))
    return strategy


@schemathesis.hook
def after_call(ctx, case, response):
    with open(c["fuzz_calls"], "a") as out:
        out.write(
            json.dumps(
                {
                    "method": case.method,
                    "path": case.operation.path,
                    "status": response.status_code,
                }
            )
            + "\n"
        )
