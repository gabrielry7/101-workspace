#!/usr/bin/env python3
"""Bounded signed-fixture qualification of the dedicated deployed sandbox inbox.

No Wompi API calls or payments. Retains a disposable SQLite receipt database and
redacted result. Never acknowledges unrelated receipts. Requires explicit opt-in.
"""

import argparse
import copy
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from sqlalchemy import select
from world_model.restaurant_commerce.db import init_schema, make_engine, session_factory
from world_model.restaurant_commerce.errors import PaymentError
from world_model.restaurant_commerce.models import WompiSandboxLookup
from world_model.restaurant_commerce.service import RestaurantCommerceService
from world_model.restaurant_commerce.wompi_receiver import SandboxReceiver
from world_model.restaurant_commerce.wompi_sandbox import NAME, SandboxKeys, WompiSandboxProvider

ORIGIN = "https://101-wompi-sandbox-receiver.reader-101.workers.dev"
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--execute-sandbox", action="store_true")
    p.add_argument(
        "--credentials",
        type=Path,
        default=Path.home() / ".config/101-world-model/wompi-sandbox/credentials.json",
    )
    p.add_argument(
        "--receiver-config",
        type=Path,
        default=Path.home() / ".config/101-world-model/wompi-sandbox/receiver.json",
    )
    args = p.parse_args()
    if not args.execute_sandbox:
        p.error("Requires --execute-sandbox; sends bounded signed synthetic receipts")
    run = args.run_dir.resolve()
    run.mkdir(parents=True, mode=0o700, exist_ok=False)
    keys = SandboxKeys.load(args.credentials)
    receiver = SandboxReceiver.load(args.receiver_config)
    assert receiver.url == ORIGIN, "This probe is restricted to the dedicated sandbox receiver"
    report = {
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": sys.argv,
        "target": ORIGIN,
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {n: importlib.metadata.version(n) for n in ("httpx", "sqlalchemy")},
        "checks": [],
        "http_requests": [],
        "authenticated_requests": [],
        "execution": "PARTIAL",
        "outcome": "FAIL",
        "limits": [
            "Signed synthetic fixture, not native Wompi delivery.",
            "No settlement, provider calls, real payments or load certification.",
        ],
    }
    real_request = receiver.request

    def recorded_request(method, path, body=None):
        result = real_request(method, path, body)
        report["authenticated_requests"].append({"method": method, "path": path, "status": 200})
        return result

    receiver.request = recorded_request
    engine = make_engine("sqlite:///" + str(run / "receipt.sqlite"))
    init_schema(engine)
    factory = session_factory(engine)
    txid = "fixture-" + uuid.uuid4().hex
    timestamp = int(time.time())
    checksum = hashlib.sha256(f"{txid}APPROVED10000{timestamp}{keys.events}".encode()).hexdigest()
    event = {
        "event": "transaction.updated",
        "environment": "test",
        "timestamp": timestamp,
        "data": {
            "transaction": {
                "id": txid,
                "status": "APPROVED",
                "amount_in_cents": 10000,
                "customer_email": "must-not-persist@example.invalid",
            }
        },
        "signature": {
            "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"],
            "checksum": checksum,
        },
    }

    def call(method, path, body=None):
        with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as c:
            r = c.request(method, ORIGIN + path, json=body)
        report["http_requests"].append({"method": method, "path": path, "status": r.status_code})
        return r

    try:
        assert call("GET", "/health").json() == {
            "service": "101-wompi-sandbox-receiver",
            "version": 1,
            "sandbox": True,
        }
        assert call("GET", "/private/events").status_code == 401
        assert call("POST", "/private/ack", {"ids": [checksum]}).status_code == 401
        report["checks"].append("health and unauthenticated read/ack rejection")
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(
                pool.map(lambda _: call("POST", "/events", event).status_code, range(8))
            )
        assert statuses == [200] * 8
        rows = receiver.request("GET", "/private/events")["events"]
        ours = [r for r in rows if r["id"] == checksum]
        assert len(ours) == 1
        assert "customer_email" not in json.dumps(ours)
        report["checks"].append(
            "eight concurrent identical deliveries persist one sanitized receipt"
        )
        variants = []
        for kind in ("amount", "environment", "timestamp", "fields", "oversized"):
            bad = copy.deepcopy(event)
            if kind == "amount":
                bad["data"]["transaction"]["amount_in_cents"] += 1
            if kind == "environment":
                bad["environment"] = "prod"
            if kind == "timestamp":
                bad["timestamp"] = 1
            if kind == "fields":
                bad["signature"]["properties"] = []
            if kind == "oversized":
                bad["padding"] = "x" * 40000
            assert call("POST", "/events", bad).status_code == 401
            variants.append(kind)
        report["checks"].append({"rejected_variants": variants})
        adapter = WompiSandboxProvider(
            keys, business_id=str(uuid.uuid4()), return_url="http://127.0.0.1:8765/"
        )
        original_request = receiver.request
        consumer_calls = []

        def only_ours(method, path, body=None):
            consumer_calls.append({"method": method, "path": path})
            if method == "GET":
                data = original_request(method, path, body)
                return {"events": [r for r in data["events"] if r["id"] == checksum]}
            assert body == {"ids": [checksum]}
            with factory() as independent:
                assert len(independent.scalars(select(WompiSandboxLookup)).all()) == 1
            original_request(method, path, body)
            raise PaymentError("Controlled response loss after actual remote acknowledgement")

        receiver.request = only_ours
        with factory() as session:
            svc = RestaurantCommerceService(session, payment_providers={NAME: adapter})
            try:
                receiver.drain(svc)
                raise AssertionError("Expected controlled acknowledgement response loss")
            except PaymentError as exc:
                assert str(exc).startswith("Controlled response loss")
        assert call("POST", "/events", event).status_code == 200
        with factory() as restarted:
            svc = RestaurantCommerceService(restarted, payment_providers={NAME: adapter})
            assert receiver.drain(svc) == 0
            assert len(restarted.scalars(select(WompiSandboxLookup)).all()) == 1
        assert not any(
            r["id"] == checksum for r in original_request("GET", "/private/events")["events"]
        )
        report["consumer_requests"] = consumer_calls
        report["checks"].append(
            "real consumer commits before remote ack; lost ack, new session and replay "
            "preserve one local job"
        )
        report["execution"], report["outcome"] = "COMPLETE", "PASS"
    except Exception as exc:
        report["error_type"] = type(exc).__name__  # Never serialize exception text/credentials.
    finally:
        engine.dispose()
        report["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        report["executed_check_groups"] = len(report["checks"])
        report["exit_code"] = 0 if report["outcome"] == "PASS" else 1
        (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "execution": report["execution"],
                    "outcome": report["outcome"],
                    "check_groups": len(report["checks"]),
                    "report": str(run / "result.json"),
                }
            )
        )
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
