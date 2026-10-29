import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("--config", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
c = json.loads(a.config.read_text())
a.output.mkdir(parents=True, exist_ok=True)
receipts = []
for profile, pattern, seconds in [
    ("public", r"^/api/restaurants/", 60),
    ("staff", r"^/api/operator/", 90),
    ("customer", r"^/api/orders/", 30),
]:
    out = a.output / profile
    out.mkdir(exist_ok=True)
    body = {
        "customer": {"name": "Fuzz synthetic", "phone": "3005550123"},
        "items": c["cart"],
        "idempotency_key": "fuzz-" + profile + "-" + str(time.time_ns()),
    }
    if profile == "customer":
        quoted = httpx.post(
            c["base_url"]
            + "/api/restaurants/"
            + c["business_ids"][0]
            + "/delivery/quote",
            json={
                "destination": {
                    "address_line": "Synthetic address",
                    "city": "Bogotá",
                    "latitude": 4.6697,
                    "longitude": -74.0549,
                }
            },
            trust_env=False,
            timeout=15,
        )
        quoted.raise_for_status()
        body.update(fulfillment_type="delivery", delivery_quote_id=quoted.json()["id"])
    response = httpx.post(
        c["base_url"] + "/api/restaurants/" + c["business_ids"][0] + "/orders",
        json=body,
        timeout=15,
        trust_env=False,
    )
    response.raise_for_status()
    cfg = {
        **c,
        "fuzz_profile": profile,
        "fuzz_order": response.json(),
        "fuzz_body": body,
        "fuzz_calls": str(out / "requests.jsonl"),
    }
    (out / "config.json").write_text(json.dumps(cfg))
    (out / "config.json").chmod(0o600)
    args = [
        str(Path(sys.executable).with_name("schemathesis")),
        "run",
        c["base_url"] + "/openapi.json",
        "--include-path-regex",
        pattern,
        "--phases",
        "examples,fuzzing",
        "--checks",
        "not_a_server_error,response_schema_conformance",
        "--max-examples",
        "15",
        "--seed",
        "101",
        "--request-timeout",
        "5",
        "--request-retries",
        "0",
        "--report",
        "junit,ndjson,json",
        "--report-dir",
        str(out),
        "--generation-database",
        "none",
        "--output-sanitize",
        "true",
        "--no-color",
    ]
    env = dict(
        os.environ,
        SCHEMATHESIS_HOOKS=str(Path(__file__).with_name("fuzz_hooks.py")),
        COMMERCE_FUZZ_CONFIG=str(out / "config.json"),
    )
    start = datetime.now(UTC).isoformat()
    with (out / "native.log").open("w") as log:
        try:
            code = subprocess.run(
                args,
                check=False,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=seconds + 30,
            ).returncode
        except subprocess.TimeoutExpired:
            code = 124
    calls = (
        [json.loads(x) for x in (out / "requests.jsonl").read_text().splitlines()]
        if (out / "requests.jsonl").exists()
        else []
    )
    receipt = {
        "profile": profile,
        "command": args,
        "version": subprocess.check_output([args[0], "--version"], text=True).strip(),
        "revision": c["revision"],
        "target": c["base_url"],
        "start": start,
        "end": datetime.now(UTC).isoformat(),
        "exit_code": code,
        "executed_requests": len(calls),
        "status_counts": dict(Counter(x["status"] for x in calls)),
        "operations": sorted({x["method"] + " " + x["path"] for x in calls}),
        "execution": "COMPLETE" if calls and code not in {2, 124} else "PARTIAL",
        "outcome": "PASS" if calls and code == 0 else "FAIL" if calls else "UNASSESSED",
        "gaps": [
            "customer capability only; no login/session feature",
            "opaque IDs bound via hooks; unknown delivery/message IDs can return404",
            "only server-error/schema checks enabled; authorization/business invariants tested separately",
        ],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    receipts.append(receipt)
(a.output / "summary.json").write_text(json.dumps(receipts, indent=2))
print(
    json.dumps(
        [
            {
                k: r[k]
                for k in [
                    "profile",
                    "executed_requests",
                    "status_counts",
                    "execution",
                    "outcome",
                ]
            }
            for r in receipts
        ]
    )
)

if any(r["outcome"] != "PASS" or r["execution"] != "COMPLETE" for r in receipts):
    raise SystemExit(1)
