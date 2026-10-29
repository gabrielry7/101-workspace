#!/usr/bin/env python3
"""Bounded real sandbox checks; starts/stops only its own loopback app.

Run against the installed commerce wheel. No real customer data or card numbers.
Provider mutations are capped at four POSTs; uncertain outcomes are never retried.
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
    args = parser.parse_args()
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
        "checks": [],
        "command": [
            sys.executable,
            str(Path(__file__).resolve()),
            "--run-dir",
            str(args.run_dir),
            "--execute-sandbox",
        ],
    }
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

                def provider(method, path, body=None, public=False):
                    if method == "POST":
                        report["remote_posts"] += 1
                        if report["remote_posts"] > 4:
                            raise RuntimeError("Sandbox mutation budget exceeded")
                    response = client.request(
                        method,
                        API + path,
                        json=body,
                        headers={
                            "Authorization": "Bearer " + (keys.public if public else keys.private)
                        },
                    )
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
                    tx = provider("POST", "/transactions", payment)
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
                report["execution"], report["outcome"] = "COMPLETE", "PASS"
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
