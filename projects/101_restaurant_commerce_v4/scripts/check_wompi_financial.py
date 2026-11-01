#!/usr/bin/env python3
"""Read-only live Wompi qualification using a COPY of a retained synthetic run.

Requires installed commerce and Playwright. Never creates a provider transaction
or refund. Only synthetic source runs from check_wompi_sandbox.py are supported.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import make_engine, session_factory
from world_model.restaurant_commerce.models import RestaurantCommerceProfile
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.staff import provision
from world_model.restaurant_commerce.wompi_financial import WompiSandboxFinancialProvider
from world_model.restaurant_commerce.wompi_sandbox import SandboxKeys, WompiSandboxProvider

KEYS_FILE = Path.home() / ".config/101-world-model/wompi-sandbox/credentials.json"


def private_json(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        json.dump(value, f)


def adapter_for(run):
    class BoundedReadProvider(WompiSandboxProvider):
        reads = 0

        def _get(self, path, **kwargs):
            self.reads += 1
            if self.reads > 10:
                raise RuntimeError("Read-only qualification budget exhausted")
            with (run / "provider-reads.jsonl").open("a") as f:
                f.write(
                    json.dumps({"method": "GET", "resource": path.split("/")[1].split("?")[0]})
                    + "\n"
                )
            return super()._get(path, **kwargs)

    return BoundedReadProvider(
        SandboxKeys.load(KEYS_FILE), business_id=BID, return_url="http://127.0.0.1:8765/"
    )


def serve(run):
    import uvicorn

    config = json.loads((run / "private-config.json").read_text())
    app = create_app(
        engine=make_engine("sqlite:///" + str(run / "copy.sqlite")),
        wompi_sandbox=adapter_for(run),
        payment_recovery_enabled=False,
        public_access_secret=config["access_secret"],
        demo_mode=False,
    )
    uvicorn.run(app, host="127.0.0.1", port=config["port"], access_log=False, log_level="error")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--source-run", type=Path)
    p.add_argument("--contract-evidence-dir", type=Path)
    p.add_argument("--execute-sandbox", action="store_true")
    p.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    run = args.run_dir.resolve()
    if args.serve:
        return serve(run)
    if not args.execute_sandbox or not args.source_run or not args.contract_evidence_dir:
        p.error("Requires --execute-sandbox, --source-run and --contract-evidence-dir")
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution": "PARTIAL",
        "outcome": "FAIL",
        "command": sys.argv,
        "provider_mutations": 0,
        "checks": [],
        "versions": {
            n: importlib.metadata.version(n) for n in ("httpx", "sqlalchemy", "playwright")
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    source = args.source_run.resolve()
    prior = json.loads((source / "evidence.json").read_text())
    assert prior["target"] == "https://sandbox.wompi.co/v1" and prior["outcome"] == "PASS"
    order = next(c["order_id"] for c in prior["checks"] if c["scenario"] == "approved")
    before = hashlib.sha256((source / "app/sandbox.db").read_bytes()).hexdigest()
    with sqlite3.connect(f"file:{source}/app/sandbox.db?mode=ro", uri=True) as original:
        with sqlite3.connect(run / "copy.sqlite") as copied:
            original.backup(copied)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    password = secrets.token_urlsafe(30)
    private_json(
        run / "private-config.json",
        {"port": port, "password": password, "access_secret": secrets.token_hex(32)},
    )
    engine = make_engine("sqlite:///" + str(run / "copy.sqlite"))
    with session_factory(engine)() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id="other-financial-test",
                slug="other-financial-test",
                display_name="Other synthetic business",
            )
        )
        s.commit()
        provision(s, "sandbox.finance", password, BID, "finance", actor="sandbox-qualification")
    engine.dispose()
    child = None
    try:
        with (run / "app.log").open("w") as log:
            child = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--run-dir", str(run), "--serve"],
                stdout=log,
                stderr=log,
            )
            base = f"http://127.0.0.1:{port}"
            with httpx.Client(base_url=base, timeout=30, trust_env=False) as c:
                for _ in range(100):
                    assert child.poll() is None
                    try:
                        if c.get("/api/browser-policy").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                assert (
                    c.post(
                        "/api/staff/login",
                        json={"username": "sandbox.finance", "password": password},
                        headers={"X-101-Login": "1"},
                    ).status_code
                    == 200
                )
                headers = {"X-101-CSRF": c.get("/api/staff/me").json()["csrf"]}
                route = f"/api/finance/restaurants/{BID}/orders/{order}"
                initial = c.get(route).json()
                assert initial["capabilities"]["lookup"] and not initial["capabilities"]["refund"]
                body = {
                    "idempotency_key": "live-lookup",
                    "reason": "Read-only sandbox qualification",
                }
                response = c.post(route + "/lookup", json=body, headers=headers)
                assert response.status_code == 200
                result = response.json()
                assert result["state"] == "succeeded" and result["result"]["status"] == "paid"
                assert (
                    c.post(route + "/lookup", json=body, headers=headers).json()["id"]
                    == result["id"]
                )
                report["checks"].append(
                    {
                        "scenario": "live_verified_payment_lookup_and_replay",
                        "state": result["state"],
                    }
                )
                n = len(c.get(route).json()["operations"])
                assert (
                    c.post(
                        route + "/refund",
                        json={**body, "idempotency_key": "blocked-write"},
                        headers=headers,
                    ).status_code
                    >= 400
                )
                assert len(c.get(route).json()["operations"]) == n
                assert (
                    c.post(
                        route.replace(BID, "other-financial-test") + "/lookup",
                        json=body,
                        headers=headers,
                    ).status_code
                    == 403
                )
                report["checks"].append(
                    {"scenario": "write_gate_and_wrong_business_rejected_without_new_operation"}
                )
                # Existing refund belongs to a different real sandbox order.
                original_refund = json.loads(
                    (args.contract_evidence_dir / "original_refund.json").read_text()
                )["data"]
                original_tx = json.loads(
                    (args.contract_evidence_dir / "original_transaction.json").read_text()
                )["data"]
                inspect_body = {
                    **body,
                    "idempotency_key": "foreign-refund",
                    "refund_reference": str(original_refund["id"]),
                }
                inspected = c.post(route + "/lookup", json=inspect_body, headers=headers).json()
                assert (
                    inspected["state"] == "review_required"
                    and inspected["result"]["error"] == "invalid_financial_evidence"
                )
                report["checks"].append(
                    {
                        "scenario": "actual_foreign_refund_cannot_change_payment",
                        "state": inspected["state"],
                    }
                )
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        headless=True,
                        executable_path=os.getenv(
                            "COMMERCE_BROWSER_EXECUTABLE", "/usr/bin/chromium"
                        ),
                    )
                    context = browser.new_context(viewport={"width": 390, "height": 844})
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(type(error).__name__))
                    context.tracing.start(screenshots=True, snapshots=True)
                    try:
                        page.goto(base + "/admin")
                        page.locator("#staffUsername").fill("sandbox.finance")
                        page.locator("#staffPassword").fill(password)
                        page.locator("#staffSignIn").click()
                        expect(page.locator("#staffLogout")).to_be_visible()
                        for _ in range(2):
                            page.locator("#business").fill(BID)
                            page.locator("#financeOrder").fill(order)
                            page.locator('[data-click="financeHistory"]').click()
                            expect(page.locator("#financeAvailability")).to_contain_text(
                                "contrato del proveedor"
                            )
                            expect(page.locator("#financeRefundButton")).to_be_disabled()
                            expect(page.locator("#financeResult")).to_contain_text(
                                "Requiere investigación"
                            )
                            page.screenshot(
                                path=str(run / "staff-financial-mobile.png"), full_page=True
                            )
                            page.reload()
                        assert not errors
                        report["checks"].append(
                            {
                                "scenario": "real_mobile_browser_history_reload_gate",
                                "javascript_errors": 0,
                            }
                        )
                    except Exception:
                        context.tracing.stop(path=str(run / "failure-trace.zip"))
                        raise
                    finally:
                        browser.close()
            # Inspect the historical refund against its actual merchant/order without
            # importing or fabricating a local historical order/financial balance.
            a = WompiSandboxFinancialProvider(adapter_for(run))
            observation = a.inspect_refund(
                order_id=original_tx["reference"][6:],
                provider_reference=original_tx["reference"],
                refund_reference=str(original_refund["id"]),
            )
            assert observation.status == "review_required"
            report["historical_refund_observation"] = asdict(observation)
            report["checks"].append({"scenario": "actual_refund_contradiction_remains_review"})
            report["execution"], report["outcome"] = "COMPLETE", "PASS"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    finally:
        if child:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        report["source_database_unchanged"] = (
            hashlib.sha256((source / "app/sandbox.db").read_bytes()).hexdigest() == before
        )
        report["provider_reads"] = (
            len((run / "provider-reads.jsonl").read_text().splitlines())
            if (run / "provider-reads.jsonl").exists()
            else 0
        )
        report["owned_app_stopped"] = child is None or child.poll() is not None
        report["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        report["exit_code"] = 0 if report["outcome"] == "PASS" else 1
        (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
