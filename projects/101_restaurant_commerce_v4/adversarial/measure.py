"""Repeated local timing experiment; fixed workload, reversed condition order."""

import argparse
import json
import os
import platform
import re
import threading
import time
from collections import Counter
from pathlib import Path

import psutil
import run


def restart(c):
    run.stop(c, "application")
    run.write(Path(c["run_dir"]) / "config.json", c)
    env = dict(
        os.environ,
        COMMERCE_TEST_CONFIG=str(Path(c["run_dir"]) / "config.json"),
        PYTHONPATH=c["installed"],
    )
    run.process(
        c,
        "application",
        [
            run.PYTHON,
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
    run.wait_http(c["base_url"] + "/ready")


def sample(c, output, done):
    from sqlalchemy import create_engine, text

    engine = create_engine(c["database_url"], connect_args={"application_name": "timing_sampler"})
    try:
        with engine.connect() as conn, output.open("w") as f:
            while not done.is_set():
                start = time.perf_counter()
                rows = (
                    conn.execute(
                        text("""SELECT state,wait_event_type,wait_event,count(*) AS n
                  FROM pg_stat_activity WHERE datname=current_database()
                  AND application_name <> 'timing_sampler'
                  GROUP BY state,wait_event_type,wait_event""")
                    )
                    .mappings()
                    .all()
                )
                blocked = conn.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                        "AND cardinality(pg_blocking_pids(pid))>0"
                    )
                ).scalar()
                waiting = (
                    conn.execute(
                        text(
                            "SELECT query FROM pg_stat_activity WHERE datname=current_database() "
                            "AND wait_event_type='Lock'"
                        )
                    )
                    .scalars()
                    .all()
                )
                tables = Counter(
                    ",".join(re.findall(r"(?:FROM|UPDATE|JOIN)\s+([a-z_]+)", query, re.I))
                    for query in waiting
                )
                conn.commit()  # refresh statistics snapshot each sample
                f.write(
                    json.dumps(
                        {
                            "utc_ns": time.time_ns(),
                            "states": [dict(r) for r in rows],
                            "blocked_connections": blocked,
                            "blocked_statement_tables": dict(tables),
                            "sample_ms": (time.perf_counter() - start) * 1000,
                        }
                    )
                    + "\n"
                )
                f.flush()
                done.wait(0.25)
    finally:
        engine.dispose()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Fresh output required")
    a.output.mkdir(parents=True)
    conditions = [
        ("shared1", True, False),
        ("distinct1", True, True),
        ("control1", False, True),
        ("control2", False, True),
        ("distinct2", True, True),
        ("shared2", True, False),
    ]
    run.write(
        a.output / "protocol.json",
        {
            "conditions": conditions,
            "phases": [["warmup", 2, 2, 10], ["normal", 30, 10, 30], ["spike", 100, 20, 45]],
            "cpu_count": psutil.cpu_count(),
            "memory_bytes": psutil.virtual_memory().total,
            "platform": platform.platform(),
            "limitations": [
                "Shared development host",
                "Database grows across blocks; reversed order only partially controls this",
                "Single business/cart; distinct synthetic customer per virtual user",
                "Closed-loop users; no fixed arrival-rate claim",
                "Spans overlap: commit includes SQL; do not sum percentiles",
                "Acquire includes connection creation; dispatch excludes dependency scheduling",
            ],
        },
    )
    c = run.setup(a.output / "environment")
    results = []
    try:
        run.baseline_journey(c)
        for name, enabled, distinct in conditions:
            print("START", name, run.now(), flush=True)
            c.update(
                timing_enabled=enabled,
                distinct_customers=distinct,
                load_profiles=[
                    ["warmup", 2, 2, 10],
                    ["normal", 30, 10, 30],
                    ["spike", 100, 20, 45],
                ],
            )
            restart(c)
            out = a.output / name
            done = threading.Event()
            sampler_errors = []

            def collect_samples(name=name, done=done, errors=sampler_errors):
                try:
                    sample(c, a.output / (name + "-postgres.jsonl"), done)
                except Exception as exc:
                    errors.append(type(exc).__name__)

            sampler = threading.Thread(target=collect_samples)
            sampler.start()
            start = run.now()
            try:
                code = run.command(
                    c,
                    "measure-" + name,
                    [
                        run.PYTHON,
                        run.ROOT / "adversarial/load.py",
                        "--config",
                        Path(c["run_dir"]) / "config.json",
                        "--output",
                        out,
                    ],
                    timeout=240,
                )
            finally:
                done.set()
                sampler.join(timeout=15)
            if sampler.is_alive() or sampler_errors:
                code = code or 1
            results.append(
                {
                    "condition": name,
                    "start": start,
                    "end": run.now(),
                    "exit_code": code,
                    "sampler_errors": sampler_errors,
                }
            )
            run.write(a.output / "execution.json", results)
            print("END", name, code, flush=True)
    finally:
        run.cleanup(c)
    if any(r["exit_code"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
