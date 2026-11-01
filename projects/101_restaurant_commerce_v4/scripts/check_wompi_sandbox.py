#!/usr/bin/env python3
"""Bounded real sandbox checks; starts/stops only its own loopback app.

Run against the installed commerce wheel. No real customer data or card numbers.
Provider mutations: four POSTs, or 12 with --edge-cases.
Uncertain outcomes are never retried.
"""

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from world_model.restaurant_commerce.wompi_sandbox import API, NAME, SandboxKeys


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=Path.home() / ".config/101-world-model/wompi-sandbox/credentials.json",
    )
    parser.add_argument("--execute-sandbox", action="store_true", required=True)
    parser.add_argument(
        "--edge-cases",
        action="store_true",
        help="Bounded crash/no-return, duplicate-reference, signature and refund contract probes",
    )
    parser.add_argument(
        "--payment-edges-only",
        action="store_true",
        help="Run payment edges; explicitly leave remote refunds unassessed",
    )
    args = parser.parse_args()
    if args.payment_edges_only and not args.edge_cases:
        parser.error("--payment-edges-only requires --edge-cases")
    keys = SandboxKeys.load(args.keys_file)
    args.run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    import world_model.restaurant_commerce as package

    package_root = Path(package.__file__).parent
    files = sorted(p for p in package_root.rglob("*") if p.suffix in {".py", ".js", ".html"})
    digest = hashlib.sha256(
        b"".join(p.relative_to(package_root).as_posix().encode() + p.read_bytes() for p in files)
    ).hexdigest()
    report = {
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target": API,
        "artifact_code_sha256": digest,
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
        "remote_posts": 0,
        "remote_gets": 0,
        "gaps": [],
        "failed_checks": [],
        "checks": [],
        "command": [
            sys.executable,
            str(Path(__file__).resolve()),
            "--run-dir",
            str(args.run_dir),
            "--execute-sandbox",
        ],
    }
    if args.edge_cases:
        report["command"].append("--edge-cases")
    if args.payment_edges_only:
        report["command"].append("--payment-edges-only")
        report["gaps"].append("Refund contract probes not executed in payment-only run")
    with (args.run_dir / "app.log").open("w") as log:
        command = [
            sys.executable,
            "-m",
            "world_model.restaurant_commerce.wompi_sandbox_demo",
            "--run-dir",
            str(args.run_dir / "app"),
            "--keys-file",
            str(args.keys_file),
            "--port",
            str(port),
            "--api-only",
        ]
        child = subprocess.Popen(command, stdout=log, stderr=log)
        try:
            with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
                base = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    if child.poll() is not None:
                        raise RuntimeError("Local app exited during startup")
                    try:
                        policy = client.get(base + "/api/browser-policy").json()
                        if policy.get("wompi_sandbox") is True:
                            break
                    except (httpx.HTTPError, ValueError):
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Local app readiness timeout")

                def provider(method, path, body=None, public=False, allow_rejection=False):
                    if method == "POST":
                        report["remote_posts"] += 1
                        if report["remote_posts"] > (12 if args.edge_cases else 4):
                            raise RuntimeError("Sandbox mutation budget exceeded")
                    if method == "GET":
                        report["remote_gets"] += 1
                        if report["remote_gets"] > 80:
                            raise RuntimeError("Sandbox read budget exceeded")
                    response = client.request(
                        method,
                        API + path,
                        json=body,
                        headers={
                            "Authorization": "Bearer " + (keys.public if public else keys.private)
                        },
                    )
                    if allow_rejection:
                        body = response.json()
                        data = body.get("data", {})
                        # Return only protocol fields, not provider diagnostics/PII.
                        error = body.get("error", {})
                        return {
                            "http_status": response.status_code,
                            "id": data.get("id") if isinstance(data, dict) else None,
                            "status": data.get("status") if isinstance(data, dict) else None,
                            "error_type": error.get("type") if isinstance(error, dict) else None,
                            "signature_error": any(
                                word in json.dumps(error).lower() for word in ("signature", "firma")
                            ),
                            "error_fields": sorted(error.get("messages", {}))
                            if isinstance(error, dict) and isinstance(error.get("messages"), dict)
                            else [],
                        }
                    if response.status_code not in (200, 201):
                        # No provider body, request URL with public key, or exception dump.
                        report["provider_error"] = {
                            "operation": path.split("/")[1],
                            "http_status": response.status_code,
                        }
                        raise RuntimeError("Sandbox operation rejected; see redacted evidence")
                    return response.json()["data"]

                merchant = provider("GET", "/merchants/" + keys.public, public=True)
                assert merchant["public_key"] == keys.public
                biz = "demo-restaurant-bogota"
                route = f"/api/restaurants/{biz}"
                store = client.get(base + route + "/storefront").json()
                assert store["payment_provider"] == NAME
                item = next(
                    i
                    for menu in store["menus"]
                    for category in menu["categories"]
                    for i in category["items"]
                    if not i["modifier_groups"]
                )
                for scenario, card, expected in [
                    ("approved", "4242424242424242", "paid"),
                    ("declined", "4111111111111111", "failed"),
                ]:
                    merchant = provider("GET", "/merchants/" + keys.public, public=True)
                    key, secret = secrets.token_hex(16), secrets.token_hex(32)
                    recovery = {"idempotency_key": key, "recovery_secret": secret}
                    private_json(args.run_dir / (scenario + "-recovery.json"), recovery)
                    body = {
                        "customer": {
                            "name": "Synthetic sandbox",
                            "phone": "3005550199",
                            "email": "sandbox-check@example.invalid",
                            "whatsapp_opt_in": False,
                            "marketing_opt_in": False,
                        },
                        "items": [{"menu_item_id": item["id"], "quantity": 1}],
                        "payment_provider": NAME,
                        **recovery,
                    }
                    response = client.post(base + route + "/orders", json=body)
                    response.raise_for_status()
                    order = response.json()
                    query = parse_qs(urlsplit(order["payments"][0]["checkout_url"]).query)
                    token = provider(
                        "POST",
                        "/tokens/cards",
                        {
                            "number": card,
                            "cvc": "123",
                            "exp_month": "12",
                            "exp_year": "30",
                            "card_holder": "SYNTHETIC TEST",
                        },
                        public=True,
                    )
                    payment = {
                        "amount_in_cents": order["total_minor"] * 100,
                        "currency": "COP",
                        "customer_email": "sandbox-check@example.invalid",
                        "reference": order["payments"][0]["provider_reference"],
                        "signature": query["signature:integrity"][0],
                        "payment_method": {"type": "CARD", "token": token["id"], "installments": 1},
                        "acceptance_token": merchant["presigned_acceptance"]["acceptance_token"],
                    }
                    if merchant.get("presigned_personal_data_auth"):
                        payment["accept_personal_auth"] = merchant["presigned_personal_data_auth"][
                            "acceptance_token"
                        ]
                    if args.edge_cases and scenario == "approved":
                        child.kill()
                        child.wait(timeout=10)
                        check_started = time.monotonic()
                    tx = provider("POST", "/transactions", payment)
                    if args.edge_cases and scenario == "approved":
                        child = subprocess.Popen(command + ["--resume"], stdout=log, stderr=log)
                        for _ in range(100):
                            try:
                                if client.get(base + "/api/browser-policy").status_code == 200:
                                    break
                            except httpx.HTTPError:
                                pass
                            time.sleep(0.1)
                        # No transaction ID or native callback is delivered to commerce.
                        # A real wall-clock wait exercises the normal 60s polling delay.
                        recovered = None
                        for _ in range(90):
                            response = client.post(base + route + "/orders/recover", json=recovery)
                            if response.status_code == 200:
                                recovered = response.json()
                                if recovered["payment_status"] == "paid":
                                    break
                            time.sleep(1)
                        assert recovered and recovered["id"] == order["id"]
                        assert recovered["payment_status"] == "paid"
                        report["checks"].append(
                            {
                                "scenario": "process_killed_before_provider_success_no_return",
                                "outcome": "PASS",
                                "recovery_seconds": round(time.monotonic() - check_started, 2),
                                "transaction_hint_sent": False,
                            }
                        )
                    private_json(
                        args.run_dir / (scenario + "-transaction.json"),
                        {"transaction_id": tx["id"], "order_id": order["id"]},
                    )
                    for _ in range(15):
                        tx = provider("GET", "/transactions/" + tx["id"])
                        if tx["status"] != "PENDING":
                            break
                        time.sleep(2)
                    recovery["wompi_transaction_id"] = tx["id"]
                    check = {
                        "scenario": scenario,
                        "transaction_id": tx["id"],
                        "order_id": order["id"],
                        "provider_status": tx["status"],
                        "pesos": order["total_minor"],
                        "cents": tx["amount_in_cents"],
                    }
                    report["checks"].append(check)
                    for _ in range(2):
                        response = client.post(base + route + "/orders/recover", json=recovery)
                        response.raise_for_status()
                        result = response.json()
                        assert result["id"] == order["id"] and result["payment_status"] == expected
                    assert tx["amount_in_cents"] == order["total_minor"] * 100
                    check["local_status"] = result["payment_status"]
                    check["replay_same_order"] = True
                    if args.edge_cases and scenario == "approved":
                        extra_token = provider(
                            "POST",
                            "/tokens/cards",
                            {
                                "number": "4242424242424242",
                                "cvc": "123",
                                "exp_month": "12",
                                "exp_year": "30",
                                "card_holder": "SYNTHETIC TEST",
                            },
                            public=True,
                        )
                        duplicate = {
                            **payment,
                            "payment_method": {
                                "type": "CARD",
                                "token": extra_token["id"],
                                "installments": 1,
                            },
                        }
                        # Use a fresh, unsubmitted reference: otherwise Wompi's
                        # duplicate-reference validation masks signature validation.
                        tamper_recovery = {
                            "idempotency_key": secrets.token_hex(16),
                            "recovery_secret": secrets.token_hex(32),
                        }
                        private_json(args.run_dir / "tamper-recovery.json", tamper_recovery)
                        fresh = client.post(
                            base + route + "/orders", json={**body, **tamper_recovery}
                        )
                        fresh.raise_for_status()
                        fresh_order = fresh.json()
                        fresh_payment = fresh_order["payments"][0]
                        fresh_query = parse_qs(urlsplit(fresh_payment["checkout_url"]).query)
                        bad = provider(
                            "POST",
                            "/transactions",
                            {
                                **duplicate,
                                "reference": fresh_payment["provider_reference"],
                                "signature": fresh_query["signature:integrity"][0],
                                "amount_in_cents": fresh_order["total_minor"] * 100 + 100,
                            },
                            allow_rejection=True,
                        )
                        report["checks"].append({"scenario": "tampered_signed_amount", **bad})
                        assert bad["http_status"] in (400, 401, 403, 422)
                        assert bad["signature_error"], (
                            "Rejection did not prove signature validation"
                        )
                        merchant = provider("GET", "/merchants/" + keys.public, public=True)
                        duplicate["acceptance_token"] = merchant["presigned_acceptance"][
                            "acceptance_token"
                        ]
                        if merchant.get("presigned_personal_data_auth"):
                            duplicate["accept_personal_auth"] = merchant[
                                "presigned_personal_data_auth"
                            ]["acceptance_token"]
                        dupe = provider("POST", "/transactions", duplicate, allow_rejection=True)
                        report["checks"].append(
                            {"scenario": "second_transaction_same_reference", **dupe}
                        )
                        if dupe["http_status"] in (200, 201):
                            report["gaps"].append(
                                "Provider accepted a second transaction for the reference; "
                                "charge uniqueness requires review"
                            )
                        # Separate sandbox-only API contract probes. These do not claim
                        # commerce's audited refund workflow is connected to Wompi.
                        for refund_state in (
                            ()
                            if args.payment_edges_only
                            else ("declined", "error", "cancelled", "approved")
                        ):
                            refund = provider(
                                "POST",
                                "/refunds",
                                {
                                    "transaction_id": tx["id"],
                                    "amount_in_cents": 10000,
                                    "reason": "Synthetic sandbox qualification",
                                    "test_scenario": refund_state,
                                    "reference": "101-edge-" + secrets.token_hex(8),
                                },
                                allow_rejection=True,
                            )
                            refund_check = {"scenario": "refund_" + refund_state, **refund}
                            report["checks"].append(refund_check)
                            if refund["http_status"] != 201:
                                report["gaps"].append(
                                    "Refund V2 not qualified: HTTP " + str(refund["http_status"])
                                )
                                break
                            if refund["status"] == "PENDING" and refund["id"] is not None:
                                for _ in range(15):
                                    observed = provider("GET", "/refunds/" + str(refund["id"]))
                                    refund["final_status"] = observed.get("status")
                                    refund["reported_sandbox_scenario"] = observed.get(
                                        "sandbox_test_scenario"
                                    )
                                    if observed.get("status") != "PENDING":
                                        break
                                    time.sleep(2)
                            refund_check.update(refund)
                            if refund.get("final_status", refund["status"]) != refund_state.upper():
                                report["failed_checks"].append(
                                    "refund_" + refund_state + "_provider_contract"
                                )
                                report["gaps"].append(
                                    "Refund simulator did not return documented outcome; "
                                    "remaining refund writes stopped"
                                )
                                break

                report["execution"] = "PARTIAL" if report["gaps"] else "COMPLETE"
                report["outcome"] = "FAIL" if report["failed_checks"] else "PASS"
        except Exception as error:
            report["outcome"] = "FAIL"
            report["error_type"] = type(error).__name__
        finally:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
    report["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["exit_code"] = 0 if report["outcome"] == "PASS" else 1
    (args.run_dir / "evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
