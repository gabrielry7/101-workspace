"""P02/P03: installed-wheel HTTP timing with owned PostgreSQL/Toxiproxy faults.

Run with the existing COMMERCE_TOOLCHAIN; --output MUST be a new directory.
No provider traffic leaves loopback. Evidence/config use existing harness rules.
"""

import argparse
import asyncio
import json
import math
import os
import time
from pathlib import Path

import httpx
from run import PYTHON, TOOLS, cleanup, command, now, port, process, setup, stop, write


async def measure(base, name, expected, *, count=40, concurrency=10):
    semaphore = asyncio.Semaphore(concurrency)
    samples = []
    async with httpx.AsyncClient(base_url=base, trust_env=False, timeout=3) as client:

        async def one(path):
            async with semaphore:
                started = time.monotonic()
                try:
                    response = await client.get(path)
                    status, error = response.status_code, None
                except httpx.HTTPError as exc:
                    status, error = None, type(exc).__name__
                samples.append(
                    {
                        "path": path,
                        "seconds": time.monotonic() - started,
                        "status": status,
                        "error": error,
                    }
                )

        await asyncio.gather(*(one(path) for _ in range(count) for path in ["/health", "/ready"]))
    result = {"name": name, "expected_readiness": expected, "samples": samples}
    passed = True
    for path in ["/health", "/ready"]:
        rows = [s for s in samples if s["path"] == path]
        durations = sorted(r["seconds"] for r in rows)
        quantiles = {f"p{q}": durations[math.ceil(len(rows) * q / 100) - 1] for q in (50, 95, 99)}
        result[path] = {**quantiles, "max": max(durations), "count": len(rows)}
        passed &= all(r["status"] == (200 if path == "/health" else expected) for r in rows)
        passed &= max(durations) < (0.25 if path == "/health" else 1.5)
    result["outcome"] = "PASS" if passed else "FAIL"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    start = now()
    c = setup(args.output.resolve())
    config_path = Path(c["run_dir"]) / "config.json"
    results = []
    report = {
        "start": start,
        "revision": c["revision"],
        "wheel_sha256": c["wheel_sha256"],
        "gates": {
            "health_max_seconds": 0.25,
            "ready_max_seconds": 1.5,
            "ready_application_deadline_seconds": 1,
            "recovery_seconds": 8,
        },
        "results": results,
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
    }
    direct_url = c["database_url"]
    from sqlalchemy import create_engine, text
    from world_model.restaurant_commerce.loyalty_models import POSTGRES_PROTECTIONS

    engine = create_engine(direct_url)
    try:
        env = dict(
            os.environ, PYTHONPATH=c["installed"], COMMERCE_PAYMENT_TEST_DATABASE_URL=direct_url
        )
        tests = [
            "tests/test_bounded_readiness.py",
            "tests/test_readiness_roundtrips.py",
            "tests/test_loyalty_configuration.py",
            "tests/test_deployment_m6.py",
            "tests/test_m3_migrations.py",
            "tests/test_hardening_v4.py",
        ]
        code = command(
            c,
            "postgres-consumers",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-o",
                "pythonpath=",
                *tests,
                "--junitxml=" + str(args.output / "postgres-consumers.xml"),
            ],
            timeout=180,
            env=env,
        )
        report["consumer_exit_code"] = code
        assert code == 0, "PostgreSQL consumers failed; see native log"
        env.pop("COMMERCE_PAYMENT_TEST_DATABASE_URL")
        code = command(
            c,
            "sqlite-consumers",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-o",
                "pythonpath=",
                *tests,
                "--junitxml=" + str(args.output / "sqlite-consumers.xml"),
            ],
            timeout=180,
            env=env,
        )
        report["sqlite_consumer_exit_code"] = code
        assert code == 0, "SQLite consumers failed; see native log"
        toxi_port, proxy_port = port(), port()
        process(
            c,
            "readiness-toxiproxy",
            [TOOLS / "toxiproxy-server", "-host", "127.0.0.1", "-port", toxi_port],
            env,
        )
        write(config_path, c)
        with httpx.Client(
            base_url=f"http://127.0.0.1:{toxi_port}", trust_env=False, timeout=3
        ) as control:
            for _ in range(100):
                try:
                    version = control.get("/version")
                    version.raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.05)
            else:
                raise RuntimeError("Toxiproxy did not start")
            report["toxiproxy_version"] = version.text
            control.post(
                "/proxies",
                json={
                    "name": "pg",
                    "listen": f"127.0.0.1:{proxy_port}",
                    "upstream": f"127.0.0.1:{c['pg_port']}",
                },
            ).raise_for_status()
            stop(c, "application")
            c["database_url"] = direct_url.replace(f":{c['pg_port']}/", f":{proxy_port}/")
            c["payment_lease_seconds"] = 30
            c["timing_enabled"] = True
            write(config_path, c)
            env.update(COMMERCE_TEST_CONFIG=str(config_path))
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
                env,
            )
            write(config_path, c)

            def recover(name):
                started = time.monotonic()
                consecutive = 0
                with httpx.Client(base_url=c["base_url"], trust_env=False, timeout=2) as h:
                    while time.monotonic() - started < 8:
                        try:
                            status = h.get("/ready").status_code
                        except httpx.HTTPError:
                            status = None
                        consecutive = consecutive + 1 if status == 200 else 0
                        if consecutive >= 4:
                            break
                        time.sleep(0.05)
                elapsed = time.monotonic() - started
                results.append(
                    {
                        "name": name,
                        "seconds": elapsed,
                        "outcome": "PASS" if consecutive >= 4 and elapsed < 8 else "FAIL",
                    }
                )

            def phase(name, expected):
                started = now()
                result = asyncio.run(measure(c["base_url"], name, expected))
                result.update(start=started, end=now(), host_load=os.getloadavg())
                results.append(result)
                print(name, result["outcome"], result["/health"], result["/ready"], flush=True)
                write(args.output / "http-timing.json", report)

            recover("proxy_start")
            phase("healthy", 200)
            for name, kind, attributes in [
                ("latency_500ms", "latency", {"latency": 500, "jitter": 0}),
                ("reset_peer", "reset_peer", {"timeout": 0}),
                ("timeout_5000ms", "timeout", {"timeout": 5000}),
            ]:
                control.post(
                    "/proxies/pg/toxics",
                    json={
                        "name": "fault",
                        "type": kind,
                        "stream": "downstream",
                        "attributes": attributes,
                    },
                ).raise_for_status()
                fault_started = time.monotonic()
                try:
                    phase(name, 503)
                    if kind == "timeout":
                        # Exercise the actual TCP timeout, not only early removal.
                        time.sleep(max(0, 5.5 - (time.monotonic() - fault_started)))
                        phase(name + "_after_full_timeout", 503)
                    report.setdefault("fault_durations", {})[name] = (
                        time.monotonic() - fault_started
                    )
                finally:
                    control.delete("/proxies/pg/toxics/fault").raise_for_status()
                recover(name + "_recovery")
                phase(name + "_healthy_again", 200)
            # Actual server loss, then recovery using only this owned cluster.
            assert (
                command(
                    c,
                    "fault-postgres-stop",
                    ["pg_ctl", "-D", args.output / "pgdata", "-m", "fast", "-w", "stop"],
                )
                == 0
            )
            phase("postgres_unavailable", 503)
            assert (
                command(
                    c,
                    "fault-postgres-start",
                    [
                        "pg_ctl",
                        "-D",
                        args.output / "pgdata",
                        "-l",
                        args.output / "postgres.log",
                        "-o",
                        f"-h 127.0.0.1 -p {c['pg_port']} -k {args.output}",
                        "-w",
                        "start",
                    ],
                )
                == 0
            )
            recover("postgres_restart_recovery")
            phase("postgres_restarted", 200)
            engine.dispose()
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE restaurant_payment_intents "
                        "RENAME COLUMN last_error TO missing_error"
                    )
                )
            try:
                phase("schema_required_column_missing", 503)
            finally:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE restaurant_payment_intents "
                            "RENAME COLUMN missing_error TO last_error"
                        )
                    )
            recover("column_restored")
            trigger, (table, _, _) = next(iter(POSTGRES_PROTECTIONS.items()))
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
            try:
                phase("loyalty_guard_disabled", 503)
            finally:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
            recover("loyalty_guard_restored")
            phase("final_healthy", 200)
        timing = []
        for path in (args.output / "timing").glob("requests-*.jsonl"):
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            timing.append(
                {"file": path.name, "pid": rows[0]["pid"] if rows else None, "requests": len(rows)}
            )
        report["worker_observations"] = timing
        assert len(timing) == 2 and all(r["requests"] > 0 for r in timing)
        report["execution"] = "COMPLETE"
        report["outcome"] = "PASS" if all(r["outcome"] == "PASS" for r in results) else "FAIL"
    finally:
        engine.dispose()
        cleanup(c)
        report["end"] = now()
        write(args.output / "http-timing.json", report)
    return 0 if report["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
