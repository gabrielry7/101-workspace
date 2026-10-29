"""Execute M3b through the installed HTTP app, independent provider ledger and browser."""

import argparse
import concurrent.futures
import json
import os
import signal
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright
from run import process, stop, wait_http, write

p = argparse.ArgumentParser()
p.add_argument("--config", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
c = json.loads(a.config.read_text())
a.output.mkdir(exist_ok=False)
assert (
    c["base_url"].startswith("http://127.0.0.1:")
    and (Path(c["run_dir"]) / ".commerce-test-run").exists()
)
start = datetime.now(UTC).isoformat()
results = []
error = None
h = httpx.Client(base_url=c["base_url"], trust_env=False, timeout=15)
headers = c["single_staff_headers"]
root = "/api/finance/restaurants/" + c["business_ids"][0] + "/orders/"
env = {
    **os.environ,
    "PYTHONPATH": c["installed"] + os.pathsep + str(Path(__file__).parent),
    "COMMERCE_TEST_CONFIG": str(a.config),
}


def control(mode):
    httpx.post(
        c["provider_direct_url"] + "/control", json={"mode": mode}, trust_env=False
    ).raise_for_status()


def create():
    control("paid")
    response = h.post(
        "/api/restaurants/" + c["business_ids"][0] + "/orders",
        json={
            "customer": {"name": "Synthetic finance", "phone": "3005550730"},
            "items": c["cart"],
            "idempotency_key": "financial-" + uuid4().hex,
        },
    )
    response.raise_for_status()
    return response.json()


def action(order, kind):
    r = h.post(
        root + order["id"] + "/" + kind,
        json={"idempotency_key": uuid4().hex, "reason": "Controlled acceptance"},
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def history(order):
    r = h.get(root + order["id"], headers=headers)
    r.raise_for_status()
    return r.json()


def effects(order):
    return [
        r
        for r in httpx.get(c["provider_direct_url"] + "/financial/records", trust_env=False).json()
        if r["order_id"] == order["id"]
    ]


def wait_success(order):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        rows = history(order)["operations"]
        refund = next((x for x in rows if x["kind"] == "refund"), None)
        if refund and refund["state"] == "succeeded":
            return refund
        time.sleep(0.2)
    raise AssertionError("No autonomous confirmed refund within20s")


def record(name, **counts):
    results.append({"scenario": name, "execution": "COMPLETE", "outcome": "PASS", **counts})
    write(a.output / "results.json", results)


try:
    order = create()
    for head, bid, expected in [
        ({"X-101-Operator-Token": c["operator_token"]}, c["business_ids"][0], 401),
        (headers, c["business_ids"][1], 403),
    ]:
        url = "/api/finance/restaurants/" + bid + "/orders/" + order["id"] + "/refund"
        assert (
            h.post(
                url, json={"idempotency_key": "denied", "reason": "Denied case"}, headers=head
            ).status_code
            == expected
        )
    assert not effects(order)
    record("legacy token and wrong business denied", requests=2)
    lookup = action(order, "lookup")
    assert lookup["state"] == "succeeded" and lookup["result"]["status"] == "paid"
    record("independent provider settlement lookup", operations=1)
    control("refund_delay")
    unknown = action(order, "refund")
    assert unknown["state"] == "unknown"
    recovered = wait_success(order)
    again = action(order, "refund")
    assert recovered["id"] == again["id"] and len(effects(order)) == 1
    record("accepted refund response lost; original intent recovers", provider_effects=1)
    # Hard process interruption after independently observed provider acceptance.
    killed = create()
    control("refund_delay")
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(action, killed, "refund")
        deadline = time.monotonic() + 10
        while not effects(killed) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(effects(killed)) == 1
        os.killpg(c["processes"]["application"]["pid"], signal.SIGKILL)
        try:
            future.result(timeout=15)
        except httpx.HTTPError:
            pass
    control("normal")
    stop(c, "application")
    write(a.config, c)
    process(
        c,
        "application",
        [
            c["python"],
            "-m",
            "uvicorn",
            "runtime:application",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            c["app_port"],
            "--workers",
            "2",
        ],
        env,
    )
    wait_http(c["base_url"] + "/ready")
    recovered = wait_success(killed)
    assert len(effects(killed)) == 1
    record("process killed after provider refund; recovery without user retry", provider_effects=1)
    # Real browser -> real API -> independent provider ledger, no request mocks.
    browser_order = create()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.goto(c["base_url"] + "/admin")
        page.locator("#staffUsername").fill("synthetic.single")
        page.locator("#staffPassword").fill(c["staff_password"])
        page.get_by_role("button",name="Iniciar sesión",exact=True).click()
        expect(page.locator("#staffStatus")).to_contain_text("synthetic.single")
        page.locator("#financeOrder").fill(browser_order["id"])
        page.locator("#financeReason").fill("Controlled browser refund")
        page.get_by_role("button", name="Solicitar devolución completa", exact=True).click()
        expect(page.locator("#financeResult")).to_contain_text(
            "Confirmado por el proveedor", timeout=15000
        )
        page.get_by_role("button", name="Resolver con evidencia").click()
        expect(page.locator("#financeResult")).to_contain_text("Revisión resuelta", timeout=15000)
        assert len(effects(browser_order)) == 1 and not errors
        page.screenshot(path=str(a.output / "financial-mobile.png"), full_page=True)
        page.reload()
        assert page.locator("#staffPassword").input_value() == ""
        assert page.evaluate("() => Object.keys(localStorage).length") == 0
        browser.close()
    record(
        "mobile financial UI and reload credential containment", browser_cases=1, provider_effects=1
    )
except Exception as exc:  # noqa: BLE001 - retain a failure receipt for any runner error.
    error = type(exc).__name__ + ": " + str(exc)
    error = error.replace(c["financial_token"], "<redacted>").replace(
        c["operator_token"], "<redacted>"
    )
finally:
    control("normal")
    h.close()
    write(
        a.output / "receipt.json",
        {
            "command": [sys.executable, *sys.argv],
            "versions": {
                "python": sys.version,
                "httpx": version("httpx"),
                "playwright": version("playwright"),
            },
            "revision": c["revision"],
            "wheel_sha256": c["wheel_sha256"],
            "target": c["base_url"],
            "start": start,
            "end": datetime.now(UTC).isoformat(),
            "execution": "COMPLETE" if not error else "PARTIAL",
            "outcome": "PASS" if not error else "FAIL",
            "executed": len(results),
            "error": error,
            "exit_code": 1 if error else 0,
        },
    )
if error:
    raise SystemExit(error)
print("Financial acceptance scenarios:", len(results))
