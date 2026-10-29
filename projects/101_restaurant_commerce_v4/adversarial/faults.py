"""Real TCP faults and worker death; controlled provider ledger is authoritative evidence."""

import argparse
import json
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
from run import port, process, stop, wait_http, write
from sqlalchemy import create_engine, text

p = argparse.ArgumentParser()
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
c = json.loads(a.config.read_text())
a.output.mkdir(parents=True, exist_ok=True)
start = datetime.now(UTC).isoformat()
results = []
failure = None
api_port, db_proxy, provider_proxy = port(), port(), port()
env = dict(os.environ, COMMERCE_TEST_CONFIG=str(a.config), PYTHONPATH=c["installed"])
toxi = str(
    Path(os.environ.get("COMMERCE_TOOLCHAIN", "/tmp/101-commerce-toolchain"))
    / "toxiproxy-server"
)
process(c, "toxiproxy", [toxi, "-host", "127.0.0.1", "-port", api_port], env)
tox = f"http://127.0.0.1:{api_port}"
for _ in range(50):
    try:
        if httpx.get(tox + "/version", trust_env=False).status_code == 200:
            break
    except httpx.HTTPError:
        time.sleep(0.1)

toxi_version = httpx.get(tox + "/version", trust_env=False).text


def request(method, url, **kw):
    return httpx.request(method, url, trust_env=False, timeout=15, **kw)


def proxy(name, listen, upstream):
    request(
        "POST",
        tox + "/proxies",
        json={"name": name, "listen": listen, "upstream": upstream},
    ).raise_for_status()


def toxic(name, kind, attributes):
    request(
        "POST",
        tox + "/proxies/" + name + "/toxics",
        json={
            "name": "fault",
            "type": kind,
            "stream": "downstream",
            "attributes": attributes,
        },
    ).raise_for_status()


def clear(name):
    request("DELETE", tox + "/proxies/" + name + "/toxics/fault")


def restart():
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


def body(label):
    return {
        "customer": {"name": "Fault synthetic", "phone": "3005550300"},
        "items": c["cart"],
        "idempotency_key": "fault-" + label + "-" + str(time.time_ns()),
    }


def create(data):
    return request(
        "POST",
        c["base_url"] + "/api/restaurants/" + c["business_ids"][0] + "/orders",
        json=data,
    )


def effects(data):
    return [
        e
        for e in request("GET", c["provider_direct_url"] + "/records").json()["effects"]
        if e["key"].endswith(":" + data["idempotency_key"])
    ]


def rows(data):
    engine = create_engine(original_db)
    try:
        with engine.connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    text(
                        "SELECT id,status,payment_status FROM restaurant_orders WHERE idempotency_key=:key"
                    ),
                    {"key": data["idempotency_key"]},
                ).mappings()
            ]
    finally:
        engine.dispose()


def record(name, ok, **kw):
    results.append(
        {
            "scenario": name,
            "execution": "COMPLETE",
            "outcome": "PASS" if ok else "FAIL",
            **kw,
        }
    )
    write(a.output / "results.json", results)


original_db = c["database_url"]
original_provider = c["provider_url"]
proxy("postgres", f"127.0.0.1:{db_proxy}", f"127.0.0.1:{c['pg_port']}")
proxy(
    "provider", f"127.0.0.1:{provider_proxy}", c["provider_direct_url"].split("://")[1]
)
c["database_url"] = original_db.replace(
    ":" + str(c["pg_port"]) + "/", ":" + str(db_proxy) + "/"
)
c["provider_url"] = f"http://127.0.0.1:{provider_proxy}"
try:
    restart()
    toxic("postgres", "latency", {"latency": 200, "jitter": 0})
    t = time.monotonic()
    r = request("GET", c["base_url"] + "/ready")
    elapsed = time.monotonic() - t
    record(
        "database latency",
        r.status_code == 200 and elapsed >= 0.19,
        status=r.status_code,
        seconds=elapsed,
    )
    clear("postgres")
    toxic("postgres", "reset_peer", {"timeout": 0})
    r = request("GET", c["base_url"] + "/ready")
    record(
        "database reset surfaces unavailable",
        r.status_code == 503,
        status=r.status_code,
    )
    clear("postgres")
    recovery_started = time.monotonic()
    wait_http(c["base_url"] + "/ready")
    record("database recovery", True, seconds=time.monotonic() - recovery_started)
    toxic("provider", "latency", {"latency": 250, "jitter": 0})
    data = body("latency")
    t = time.monotonic()
    r = create(data)
    elapsed = time.monotonic() - t
    record(
        "provider latency",
        r.status_code == 200 and elapsed >= 0.24,
        status=r.status_code,
        seconds=elapsed,
        rows=rows(data),
        effects=effects(data),
    )
    clear("provider")
    toxic("provider", "reset_peer", {"timeout": 0})
    data = body("reset")
    r = create(data)
    before = rows(data)
    clear("provider")
    retry = create(data)
    record(
        "provider reset and retry",
        r.status_code == 503
        and retry.status_code == 200
        and not before
        and len(rows(data)) == 1,
        status=r.status_code,
        retry_status=retry.status_code,
        rows_before=before,
        rows_after=rows(data),
        effects=effects(data),
    )
    request("POST", c["provider_direct_url"] + "/control", json={"mode": "delay"})
    data = body("timeout")
    r = create(data)
    before = rows(data)
    remote = effects(data)
    request("POST", c["provider_direct_url"] + "/control", json={"mode": "normal"})
    retry = create(data)
    after = rows(data)
    record(
        "provider accepted but reply timed out",
        bool(before)
        and retry.status_code == 200
        and remote
        and remote[0]["order_id"] == after[0]["id"],
        status=r.status_code,
        retry_status=retry.status_code,
        rows_before=before,
        rows_after=after,
        effects=remote,
        required="durable local intent before provider call; current missing intent is FAIL",
    )
    request(
        "POST",
        c["provider_direct_url"] + "/control",
        json={"mode": "hold_after_success"},
    )
    data = body("worker-kill")
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(create, data)
        for _ in range(100):
            remote = effects(data)
            if remote:
                break
            time.sleep(0.03)
        assert remote, "provider acceptance barrier was not reached"
        os.killpg(c["processes"]["application"]["pid"], signal.SIGKILL)
        try:
            pending.result(timeout=15)
        except (httpx.HTTPError, TimeoutError) as exc:
            failure = type(exc).__name__
    before = rows(data)
    request("POST", c["provider_direct_url"] + "/control", json={"mode": "normal"})
    restart()
    retry = create(data)
    after = rows(data)
    record(
        "worker killed after simulated payment success",
        bool(before)
        and retry.status_code == 200
        and remote[0]["order_id"] == after[0]["id"],
        request_failure=failure,
        rows_before=before,
        rows_after=after,
        effects=remote,
        retry_status=retry.status_code,
    )
finally:
    request("POST", c["provider_direct_url"] + "/control", json={"mode": "normal"})
    clear("postgres")
    clear("provider")
    c["database_url"] = original_db
    c["provider_url"] = original_provider
    restart()
    stop(c, "toxiproxy")
    write(a.config, c)
    write(
        a.output / "receipt.json",
        {
            "command": [sys.executable, *sys.argv],
            "version": toxi_version,
            "revision": c["revision"],
            "target": c["base_url"],
            "start": start,
            "end": datetime.now(UTC).isoformat(),
            "exit_code": int(
                len(results) != 7 or any(r["outcome"] == "FAIL" for r in results)
            ),
            "execution": "COMPLETE" if len(results) == 7 else "PARTIAL",
            "outcome": "FAIL"
            if any(r["outcome"] == "FAIL" for r in results)
            else "PASS",
            "scenario_count": len(results),
            "results": results,
        },
    )

if len(results) != 7 or any(r["outcome"] == "FAIL" for r in results):
    raise SystemExit(1)
