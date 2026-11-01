#!/usr/bin/env python3
"""One real fake-card hosted journey on a disposable HTTPS tunnel; always cleanup.

Requires official cloudflared locally and explicit --execute-sandbox. The tunnel
is temporary and is NOT the stable Events URL. No dashboard changes are made.
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--cloudflared", type=Path, required=True)
    p.add_argument("--execute-sandbox", action="store_true", required=True)
    a = p.parse_args()
    a.run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    report = {
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
        "transaction_posts": 0,
        "checks": [],
        "cloudflared_sha256": hashlib.sha256(a.cloudflared.read_bytes()).hexdigest(),
    }
    children = []
    try:
        with (a.run_dir / "tunnel.log").open("w") as log:
            children.append(
                subprocess.Popen(
                    [
                        str(a.cloudflared),
                        "tunnel",
                        "--protocol",
                        "http2",
                        "--url",
                        f"http://127.0.0.1:{port}",
                    ],
                    stdout=log,
                    stderr=log,
                )
            )
        origin = None
        for _ in range(120):
            match = re.search(
                r"https://[a-z0-9-]+\.trycloudflare\.com", (a.run_dir / "tunnel.log").read_text()
            )
            if match:
                origin = match.group()
                break
            if children[0].poll() is not None:
                raise RuntimeError("tunnel_start_failed")
            time.sleep(0.25)
        if not origin:
            raise RuntimeError("tunnel_url_unavailable")
        report["target"] = origin
        with (a.run_dir / "app.log").open("w") as log:
            children.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "world_model.restaurant_commerce.wompi_sandbox_demo",
                        "--run-dir",
                        str(a.run_dir / "app"),
                        "--port",
                        str(port),
                        "--return-url",
                        origin + "/",
                    ],
                    stdout=log,
                    stderr=log,
                )
            )
        import httpx

        report["step"] = "public_https_readiness"
        with httpx.Client(trust_env=False, timeout=3) as client:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                try:
                    if client.get(origin + "/api/browser-policy").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("public_app_unavailable")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=os.environ.get("COMMERCE_BROWSER_EXECUTABLE", "/usr/bin/chromium"),
            )
            context = browser.new_context(viewport={"width": 360, "height": 740})
            context.tracing.start(screenshots=True, snapshots=True, sources=False)
            page = context.new_page()
            page.set_default_timeout(30000)
            cdp = context.new_cdp_session(page)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            checkouts = []

            def guard(route):
                req = route.request
                u = urlsplit(req.url)
                if u.path.startswith("/v1/") and (u.hostname or "").endswith("wompi.co"):
                    if u.hostname not in {"sandbox.wompi.co", "api-sandbox.wompi.co"}:
                        report["blocked_production"] = True
                        route.abort()
                        return
                    if req.method == "POST" and u.path == "/v1/transactions":
                        report["transaction_posts"] += 1
                        if report["transaction_posts"] > 1:
                            route.abort()
                            return
                if (
                    u.hostname == urlsplit(origin).hostname
                    and req.method == "POST"
                    and re.fullmatch(r"/api/restaurants/[^/]+/orders", u.path)
                ):
                    r = route.fetch()
                    checkouts.append(r.json())
                    route.fulfill(response=r)
                    return
                route.continue_()

            context.route("**/*", guard)
            try:
                report["step"] = "storefront"
                page.goto(origin, wait_until="domcontentloaded")
                page.locator("#menu article").filter(has_text="Papas").get_by_role("button").click()
                page.locator("#cName").fill("Synthetic hosted test")
                page.locator("#cPhone").fill("3991111111")
                page.locator("#cEmail").fill("hosted-check@example.invalid")
                page.locator("#checkoutButton").click()
                page.wait_for_url("https://checkout.wompi.co/**", timeout=45000)
                assert len(checkouts) == 1
                order = checkouts[0]
                q = parse_qs(urlsplit(order["payments"][0]["checkout_url"]).query)
                assert q["public-key"][0].startswith("pub_test_")
                assert int(q["amount-in-cents"][0]) == order["total_minor"] * 100
                report["order_id"] = order["id"]
                report["step"] = "hosted_card"
                page.get_by_role("button").filter(has_text="Tarjeta débito o crédito").click()
                page.locator("#fullName").fill("SYNTHETIC TEST")
                page.locator("#email").fill("hosted-check@example.invalid")
                page.locator("#number").fill("3991111111")
                page.get_by_role("button", name="Continuar con tu pago").click()
                page.locator("#cardNumber").fill("4242424242424242")
                page.locator("#expirationMonth").select_option("12")
                page.locator("#expirationYear").select_option("30")
                page.locator("#code").fill("123")
                page.locator("#cardHolder").fill("SYNTHETIC TEST")
                page.locator("#legal_id_option").select_option("CC")
                page.locator("#legal_id_number").fill("1111111111")
                page.locator("#installments").select_option("1")
                page.wait_for_timeout(1500)
                for selector in ("#acceptance", "#acceptancePersonal"):
                    for _ in range(3):
                        if page.locator(selector).is_checked():
                            break
                        try:
                            page.locator(selector).check(timeout=3000)
                        except Exception:
                            pass
                        page.wait_for_timeout(250)
                    expect(page.locator(selector)).to_be_checked()
                page.get_by_role("button", name="Continuar con tu pago").click()
                report["step"] = "official_return_button"
                page.get_by_role("button").filter(has_text="Volver al comercio").click(
                    timeout=60000
                )
                page.wait_for_url(origin + "/**", timeout=45000)
                report["step"] = "confirmed_order"
                expect(page.locator("#checkoutRecovery")).to_contain_text(
                    "Pago confirmado", timeout=45000
                )
                page.reload()
                expect(page.locator("#checkoutRecovery")).to_contain_text(
                    "Pago confirmado", timeout=30000
                )
                report["step"] = "offline_reconnect"
                context.set_offline(True)
                try:
                    page.reload(timeout=10000)
                except Exception:
                    pass
                context.set_offline(False)
                page.goto(origin)
                expect(page.locator("#checkoutRecovery")).to_contain_text(
                    "Pago confirmado", timeout=30000
                )
                assert report["transaction_posts"] == 1
                assert not report.get("blocked_production")
                report.update(
                    execution="COMPLETE",
                    outcome="PASS",
                    checks=[
                        "360px_viewport_4x_cpu_throttle",
                        "signed_amount_matches_order",
                        "official_hosted_return_button",
                        "verified_paid_after_return",
                        "reload_and_offline_reconnect_preserve_order",
                        "exactly_one_transaction_post",
                    ],
                )
            except Exception as error:
                report.update(outcome="FAIL", error_type=type(error).__name__)
                context.tracing.stop(path=str(a.run_dir / "failure-trace.zip"))
                os.chmod(a.run_dir / "failure-trace.zip", 0o600)
            finally:
                browser.close()
    except Exception as error:
        report.update(outcome="FAIL", error_type=type(error).__name__)
    finally:
        for child in reversed(children):
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        report["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        report["exit_code"] = 0 if report["outcome"] == "PASS" else 1
        (a.run_dir / "evidence.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
