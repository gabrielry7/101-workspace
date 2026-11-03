#!/usr/bin/env python3
"""Recreate and execute the disposable commerce verification environment."""

import argparse
import hashlib
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(os.environ.get("COMMERCE_TOOLCHAIN", "/tmp/101-commerce-toolchain"))
PYTHON = TOOLS / "venv/bin/python"


def now():
    return datetime.now(UTC).isoformat()


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def write(p, d):
    Path(p).write_text(json.dumps(d, indent=2, default=str) + "\n")


def command(c, name, args, timeout=180, env=None, cwd=ROOT):
    start = now()
    output = Path(c["run_dir"]) / (name + ".log")
    if output.exists():
        raise RuntimeError("Refusing to overwrite prior command evidence: " + str(output))
    code = None
    redacted = [
        str(a)
        .replace(c.get("operator_token", "__absent__"), "<operator-token>")
        .replace(c.get("access_secret", "__absent__"), "<access-secret>")
        for a in args
    ]
    with output.open("w") as out:
        try:
            child = subprocess.Popen(
                [str(x) for x in args],
                start_new_session=True,
                cwd=cwd,
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            # A descendant can ignore TERM after its parent has exited.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            code = 124
        except OSError as exc:
            out.write(str(exc))
            code = 127
    receipt = {
        "python_version": sys.version,
        "wheel_sha256": c.get("wheel_sha256"),
        "layer": name,
        "command": redacted,
        "cwd": str(cwd),
        "start": start,
        "end": now(),
        "exit_code": code,
        "revision": c.get("revision"),
        "target": c.get("base_url"),
        "output": str(output),
        "execution": "PARTIAL" if code in {124, 127} else "COMPLETE",
        "outcome": "UNASSESSED",
        "counts": "see native report",
    }
    write(Path(c["run_dir"]) / (name + ".receipt.json"), receipt)
    print(name, code, flush=True)
    return code


def process(c, name, args, env):
    out = open(Path(c["run_dir"]) / (name + ".log"), "a")  # noqa: SIM115 - child inherits fd, parent closes below
    p = subprocess.Popen(
        [str(x) for x in args],
        cwd=ROOT / "adversarial",
        env=env,
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    out.close()
    c.setdefault("processes", {})[name] = {
        "pid": p.pid,
        "start_ticks": Path(f"/proc/{p.pid}/stat").read_text().split()[21],
    }
    write(Path(c["run_dir"]) / "config.json", c)
    if name == "application":
        process(c, "recovery", [c["python"], ROOT / "adversarial/runtime.py"], env)
    return p


def stop(c, name):
    if name == "application":
        stop(c, "recovery")
    item = c.get("processes", {}).get(name)
    if not item:
        return
    pid = item["pid"]
    try:
        if Path(f"/proc/{pid}/stat").read_text().split()[21] != item["start_ticks"]:
            return
        os.killpg(pid, signal.SIGTERM)
        for _ in range(50):
            if not Path(f"/proc/{pid}").exists():
                break
            time.sleep(0.1)
        else:
            os.killpg(pid, signal.SIGKILL)
    except (FileNotFoundError, ProcessLookupError):
        pass


def wait_http(url):
    import httpx

    for _ in range(100):
        try:
            r = httpx.get(url, timeout=1, trust_env=False)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.01)
        time.sleep(0.2)
    raise RuntimeError("Service did not become ready: " + url)


def seed(c):
    sys.path.insert(0, c["installed"])
    from sqlalchemy import text
    from world_model.restaurant_commerce.db import (
        init_schema,
        make_engine,
        session_factory,
    )
    from world_model.restaurant_commerce.models import (
        Customer,
        LoyaltyAccount,
        Menu,
        MenuCategory,
        MenuItem,
        RestaurantCommerceProfile,
    )
    from world_model.restaurant_commerce.seed import seed_demo

    eng = make_engine(c["database_url"])
    init_schema(eng)
    with session_factory(eng)() as s:
        seed_demo(s)
        b = RestaurantCommerceProfile(
            business_id=c["business_ids"][1],
            slug="synthetic-b",
            display_name="Synthetic B",
            payment_provider="simulated",
            pickup_enabled=True,
        )
        s.add(b)
        s.flush()
        m = Menu(business_id=b.business_id, name="Test menu")
        s.add(m)
        s.flush()
        cat = MenuCategory(menu_id=m.id, name="Test category")
        s.add(cat)
        s.flush()
        s.add(
            MenuItem(
                category_id=cat.id,
                name="Test B item",
                base_price_minor=10000,
                currency="COP",
                enabled=True,
            )
        )
        customer_ids = []
        for i, bid in enumerate(c["business_ids"]):
            customer = Customer(
                business_id=bid,
                phone=f"300555000{i}",
                name=f"Synthetic account {i}",
                whatsapp_opt_in=False,
                marketing_opt_in=False,
            )
            s.add(customer)
            s.flush()
            customer_ids.append(customer.id)
            s.add(
                LoyaltyAccount(
                    business_id=bid,
                    customer_id=customer.id,
                    available_points=100,
                    lifetime_earned_points=100,
                )
            )
        s.commit()
        from world_model.restaurant_commerce.models import StaffMembership
        from world_model.restaurant_commerce.staff import provision

        for name in ("single", "dual"):
            actor = provision(
                s,
                "synthetic." + name,
                c["staff_password"],
                c["business_ids"][0],
                "manager",
                actor="test-harness",
            )
            if name == "dual":
                s.add(
                    StaffMembership(
                        account_id=actor.id, business_id=c["business_ids"][1], role="manager"
                    )
                )
                s.commit()
        c["customer_ids"] = customer_ids
        write(
            Path(c["run_dir"]) / "database-proof.json",
            {
                "version": s.scalar(text("SELECT version()")),
                "database": s.scalar(text("SELECT current_database()")),
                "port": s.scalar(text("SHOW port")),
                "businesses": c["business_ids"],
                "staff_identity_model": (
                    "Named single- and dual-business staff; real HTTP-issued sessions"
                ),
                "workers": (
                    "2 Uvicorn API processes with embedded recovery disabled; "
                    "separate installed recovery runner process"
                ),
            },
        )
    eng.dispose()


def _setup(run_dir):
    (run_dir / ".commerce-test-run").write_text("owned disposable commerce verification run\n")
    pg, app, provider = port(), port(), port()
    c = {
        "run_dir": str(run_dir),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_path": str(ROOT),
        "python": str(PYTHON),
        "base_url": f"http://127.0.0.1:{app}",
        "provider_url": f"http://127.0.0.1:{provider}",
        "provider_direct_url": f"http://127.0.0.1:{provider}",
        "app_port": app,
        "pg_port": pg,
        "database_url": (
            f"postgresql+psycopg://{__import__('getpass').getuser()}@127.0.0.1:{pg}/commerce_test"
        ),
        "business_ids": ["demo-restaurant-bogota", "synthetic-business-b"],
        "operator_token": secrets.token_hex(32),
        "financial_token": secrets.token_hex(32),
        "staff_password": secrets.token_hex(24),
        "access_secret": secrets.token_hex(32),
        "webhook_secrets": {
            "simulated": secrets.token_hex(32),
            "simulated_delivery": secrets.token_hex(32),
        },
        "installed": str(run_dir / "installed"),
        "rate_limit_per_minute": 100000,
    }
    write(run_dir / "config.json", c)
    (run_dir / "config.json").chmod(0o600)
    inventory = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ["src", "adversarial", "tests"]
        for p in (ROOT / folder).rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".js", ".ts", ".json", ".toml", ".sh", ".txt", ".md"}
        and not any(x in p.parts for x in ["node_modules", "__pycache__", ".cache", "test-results"])
    }
    write(run_dir / "source-inventory.json", inventory)
    write(
        run_dir / "git-state.json",
        {
            "revision": c["revision"],
            "status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        },
    )
    assert (
        command(
            c,
            "build",
            [
                PYTHON,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                run_dir / "wheel",
            ],
        )
        == 0
    )
    wheel = next((run_dir / "wheel").glob("*.whl"))
    c["wheel"] = str(wheel)
    c["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert (
        command(
            c,
            "install",
            [
                PYTHON,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                c["installed"],
                wheel,
            ],
        )
        == 0
    )
    assert (
        command(
            c,
            "initdb",
            [
                "initdb",
                "-D",
                run_dir / "pgdata",
                "-A",
                "trust",
                "--no-locale",
                "--encoding=UTF8",
            ],
        )
        == 0
    )
    assert (
        command(
            c,
            "postgres-start",
            [
                "pg_ctl",
                "-D",
                run_dir / "pgdata",
                "-l",
                run_dir / "postgres.log",
                "-o",
                f"-h 127.0.0.1 -p {pg} -k {run_dir}",
                "-w",
                "start",
            ],
        )
        == 0
    )
    assert (
        command(
            c,
            "createdb",
            ["createdb", "-h", "127.0.0.1", "-p", str(pg), "commerce_test"],
        )
        == 0
    )
    try:
        seed(c)
    except Exception:
        cleanup(c)
        raise
    write(run_dir / "config.json", c)
    env = dict(
        os.environ,
        COMMERCE_TEST_CONFIG=str(run_dir / "config.json"),
        PYTHONPATH=c["installed"],
    )
    process(
        c,
        "provider",
        [
            PYTHON,
            "-m",
            "uvicorn",
            "provider:app",
            "--host",
            "127.0.0.1",
            "--port",
            provider,
        ],
        env,
    )
    wait_http(c["provider_url"] + "/health")
    process(
        c,
        "application",
        [
            PYTHON,
            "-m",
            "uvicorn",
            "runtime:application",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            app,
            "--workers",
            "2",
        ],
        env,
    )
    wait_http(c["base_url"] + "/ready")
    import httpx

    for name in ("single", "dual"):
        with httpx.Client(base_url=c["base_url"], trust_env=False) as staff_client:
            staff_client.post(
                "/api/staff/login",
                json={"username": "synthetic." + name, "password": c["staff_password"]},
                headers={"X-101-Login": "1"},
            ).raise_for_status()
            me = staff_client.get("/api/staff/me")
            me.raise_for_status()
            c[name + "_staff_headers"] = {
                "Cookie": "commerce_staff=" + staff_client.cookies["commerce_staff"],
                "X-101-CSRF": me.json()["csrf"],
            }
    write(run_dir / "config.json", c)
    from world_model.restaurant_commerce import api

    write(
        run_dir / "artifact-proof.json",
        {
            "module": api.__file__,
            "wheel_sha256": c["wheel_sha256"],
            "api_version": __import__("httpx")
            .get(c["base_url"] + "/openapi.json", trust_env=False)
            .json()["info"]["version"],
            "pid": c["processes"]["application"],
            "source_import_forbidden": str(ROOT / "src") not in api.__file__,
        },
    )
    return c


def setup(run_dir):
    # Creation is outside the catch: a preexisting run never belongs to this invocation.
    run_dir.mkdir(parents=True, exist_ok=False)
    try:
        return _setup(run_dir)
    except Exception:
        config_path = run_dir / "config.json"
        if config_path.exists():
            cleanup(json.loads(config_path.read_text()))
        raise


def cleanup(c):
    # Fault layers replace owned process IDs in the private config. The parent
    # must not use its stale pre-restart snapshot or leak the replacement worker.
    recorded = Path(c["run_dir"]) / "config.json"
    if recorded.exists():
        latest = json.loads(recorded.read_text())
        if Path(latest["run_dir"]).resolve() != Path(c["run_dir"]).resolve():
            raise RuntimeError("Cleanup config changed its owned run directory")
        c = latest
    if not (Path(c["run_dir"]) / ".commerce-test-run").exists():
        raise RuntimeError("Refusing cleanup without owned run marker")
    for name in list(c.get("processes", {})):
        stop(c, name)
    if (Path(c["run_dir"]) / "pgdata/postmaster.pid").exists():
        command(
            c,
            "postgres-stop",
            ["pg_ctl", "-D", Path(c["run_dir"]) / "pgdata", "-m", "fast", "-w", "stop"],
        )
    # Retain artifacts/data for inspection; never delete outside this run.


def baseline_journey(c):
    import httpx

    with httpx.Client(base_url=c["base_url"], trust_env=False, timeout=15) as h:
        store = h.get("/api/restaurants/" + c["business_ids"][0] + "/storefront").json()
        item = next(
            i
            for m in store["menus"]
            for cat in m["categories"]
            for i in cat["items"]
            if not i["modifier_groups"]
        )
        c["cart"] = [{"menu_item_id": item["id"], "quantity": 1, "modifiers": []}]
        body = {
            "customer": {"name": "Baseline synthetic", "phone": "3005550999"},
            "items": c["cart"],
            "idempotency_key": "baseline-" + secrets.token_hex(8),
        }
        r = h.post("/api/restaurants/" + c["business_ids"][0] + "/orders", json=body)
        r.raise_for_status()
        order = r.json()
        h.post(
            "/api/payments/simulated/" + order["payments"][0]["provider_reference"] + "/complete"
        ).raise_for_status()
        for state in ["accepted", "preparing", "ready", "completed"]:
            h.patch(
                "/api/operator/orders/" + order["id"],
                json={"status": state},
                headers=c["single_staff_headers"],
            ).raise_for_status()
        status = h.get(
            "/api/orders/" + order["id"],
            headers={"X-101-Order-Token": order["access_token"]},
        )
        status.raise_for_status()
        assert status.json()["status"] == "completed"
        c["baseline_order"] = order
        write(
            Path(c["run_dir"]) / "baseline-journey.json",
            {
                "order": status.json(),
                "provider_records": h.get(c["provider_direct_url"] + "/records").json(),
                "execution": "COMPLETE",
                "outcome": "PASS",
            },
        )
        write(Path(c["run_dir"]) / "openapi.json", h.get("/openapi.json").json())
    write(Path(c["run_dir"]) / "config.json", c)


def baseline(c):
    baseline_journey(c)
    env = dict(
        os.environ,
        PYTHONPATH=c["installed"],
        COMMERCE_BROWSER_EXECUTABLE="/usr/bin/chromium",
        COMMERCE_TEST_CONFIG=str(Path(c["run_dir"]) / "config.json"),
        COMMERCE_M5_ARTIFACTS=str(Path(c["run_dir"]) / "m5-browser"),
        COMMERCE_BROWSER_ARTIFACTS=str(Path(c["run_dir"]) / "security-browser"),
        COMMERCE_PAYMENT_TEST_DATABASE_URL=c["database_url"],
        COMMERCE_MIGRATION_TEST_DATABASE_URL=c["database_url"],
    )
    # Pytest creates its own applications; keep PostgreSQL, release idle HTTP memory.
    stop(c, "application")
    stop(c, "provider")
    try:
        return command(
            c,
            "existing-tests",
            [
                PYTHON,
                "-m",
                "pytest",
                "tests",
                "adversarial/test_runner_safety.py",
                "adversarial/test_load_contract.py",
                "adversarial/test_provider_storage.py",
                "adversarial/test_fixture_state.py",
                "-q",
                "--junitxml=" + str(Path(c["run_dir"]) / "existing-tests.xml"),
            ],
            timeout=1800,
            env=env,
        )
    finally:
        runtime_env = dict(
            os.environ,
            COMMERCE_TEST_CONFIG=str(Path(c["run_dir"]) / "config.json"),
            PYTHONPATH=c["installed"],
        )
        process(
            c,
            "provider",
            [
                PYTHON,
                "-m",
                "uvicorn",
                "provider:app",
                "--host",
                "127.0.0.1",
                "--port",
                c["provider_direct_url"].rsplit(":", 1)[1],
            ],
            runtime_env,
        )
        wait_http(c["provider_direct_url"] + "/health")
        process(
            c,
            "application",
            [
                PYTHON,
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
            runtime_env,
        )
        wait_http(c["base_url"] + "/ready")


def validate_layers(value):
    names = value.split(",")
    allowed = {
        "baseline",
        "financial",
        "races",
        "authorization",
        "browser",
        "properties",
        "schemathesis",
        "locust",
        "faults",
        "scanners",
    }
    if any(name not in allowed for name in names):
        raise ValueError("Unknown or empty layer; choose: " + ",".join(sorted(allowed)))
    return names


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument(
        "--layers",
        default="baseline,financial,authorization,races,browser,properties,schemathesis,locust,faults,scanners",
    )
    p.add_argument("--keep", action="store_true")
    p.add_argument("--cleanup", action="store_true")
    a = p.parse_args()
    selected_layers = validate_layers(a.layers)
    c = (
        json.loads(a.config.read_text())
        if a.config
        else setup(a.run_dir or Path("/tmp/101-commerce-runs") / ("run-" + str(int(time.time()))))
    )
    from urllib.parse import urlsplit

    if urlsplit(c["base_url"]).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Only disposable loopback targets allowed")
    run_root = Path(c["run_dir"]).resolve()
    if not (run_root / ".commerce-test-run").exists():
        raise RuntimeError("Target has no owned disposable-run marker")
    if a.config and a.config.resolve() != run_root / "config.json":
        raise RuntimeError("Config does not belong to the recorded run directory")
    if a.cleanup:
        cleanup(c)
        return
    failures = []
    try:
        for layer in selected_layers:
            if layer == "baseline":
                code = baseline(c)
                if code:
                    failures.append({"layer": layer, "exit_code": code})
                    raise RuntimeError(
                        "Baseline failed; inspect evidence before starting negative layers"
                    )
            elif layer in {
                "financial",
                "races",
                "authorization",
                "browser",
                "properties",
                "scanners",
                "schemathesis",
                "locust",
                "faults",
            }:
                script = {
                    "financial": "financial.py",
                    "races": "races.py",
                    "authorization": "authorization.py",
                    "browser": "browser_runner.py",
                    "properties": "properties.py",
                    "scanners": "scanners.py",
                    "schemathesis": "fuzz.py",
                    "locust": "load.py",
                    "faults": "faults.py",
                }[layer]
                code = command(
                    c,
                    layer,
                    [
                        PYTHON,
                        ROOT / "adversarial" / script,
                        "--config",
                        Path(c["run_dir"]) / "config.json",
                        "--output",
                        Path(c["run_dir"]) / layer,
                    ],
                    timeout=1800,
                )
                if code:
                    failures.append({"layer": layer, "exit_code": code})
        write(
            Path(c["run_dir"]) / "suite-execution.json",
            {
                "revision": c["revision"],
                "layers": a.layers.split(","),
                "nonzero_layers": failures,
                "note": (
                    "Per-layer native receipts determine coverage and outcome; "
                    "nonzero known release gaps remain failures."
                ),
            },
        )
        print("Evidence:", c["run_dir"], flush=True)
    finally:
        from summarize import summarize

        try:
            summarize(c)
        finally:
            if not a.keep:
                cleanup(c)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
