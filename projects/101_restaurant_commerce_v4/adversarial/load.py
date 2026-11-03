import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psutil
from load_contract import accepted, validate_profiles, validate_target

p = argparse.ArgumentParser()
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
c = json.loads(a.config.read_text())
validate_target(c, a.config)
a.output.mkdir(parents=True, exist_ok=False)
# Explicit bounded local qualification, not a production capacity claim.
profiles = c.get(
    "load_profiles",
    [
        ("smoke", 2, 2, 15),
        ("baseline", 10, 5, 30),
        ("normal", 30, 10, 60),
        ("spike", 100, 20, 45),
        ("recovery", 5, 5, 30),
        ("sustained", 20, 5, 300),
    ],
)
validate_profiles(profiles)
receipts = []
for name, users, spawn, seconds in profiles:
    probe = httpx.post(
        c["base_url"] + "/api/restaurants/" + c["business_ids"][0] + "/orders/quote",
        json={"items": c["cart"]},
        timeout=15,
        trust_env=False,
    )
    if probe.status_code != 200:
        (a.output / "precondition-failure.json").write_text(
            json.dumps(
                {
                    "profile": name,
                    "status": probe.status_code,
                    "execution": "BLOCKED",
                    "outcome": "NOT RUN",
                    "reason": "Positive quote failed before load; fixture may be contaminated",
                }
            )
        )
        raise RuntimeError("Load precondition failed; no capacity claim permitted")
    preflight = httpx.post(
        c["base_url"] + "/api/restaurants/" + c["business_ids"][0] + "/orders",
        json={
            "items": c["cart"],
            "customer": {"name": "Load preflight", "phone": "3005550201"},
            "idempotency_key": "preflight-" + uuid.uuid4().hex,
            **(
                {"requested_pickup_at": c["load_pickup_slots"][0]}
                if c.get("load_pickup_slots")
                else {}
            ),
        },
        timeout=15,
        trust_env=False,
    )
    if preflight.status_code != 200:
        (a.output / "precondition-failure.json").write_text(
            json.dumps(
                {
                    "profile": name,
                    "status": preflight.status_code,
                    "execution": "BLOCKED",
                    "outcome": "NOT RUN",
                    "reason": "Positive checkout failed before load",
                }
            )
        )
        raise RuntimeError("Positive checkout failed before load")
    scope = name + "-" + uuid.uuid4().hex[:12]
    out = a.output / name
    out.mkdir(exist_ok=True)
    args = [
        str(Path(sys.executable).with_name("locust")),
        "-f",
        str(Path(__file__).with_name("locustfile.py")),
        "--headless",
        "--host",
        c["base_url"],
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn),
        "--run-time",
        str(seconds) + "s",
        "--stop-timeout",
        "30",
        "--csv",
        str(out / "stats"),
        "--csv-full-history",
        "--html",
        str(out / "report.html"),
        "--exit-code-on-error",
        "1",
    ]
    env = dict(
        os.environ,
        COMMERCE_TEST_CONFIG=str(a.config),
        COMMERCE_LOAD_PROFILE=scope,
        COMMERCE_LOAD_RECEIPT=str(out / "counts.json"),
    )
    start = datetime.now(UTC).isoformat()
    with (out / "native.log").open("w") as log:
        try:
            child = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + seconds + 60
            samples = []
            roots = [row["pid"] for row in c.get("processes", {}).values()]
            pg_pid = Path(
                c.get("database_pid_path", str(Path(c["run_dir"]) / "pgdata/postmaster.pid"))
            )
            if pg_pid.exists():
                roots.append(int(pg_pid.read_text().splitlines()[0]))
            while child.poll() is None:
                seen = {}
                for pid in roots + [child.pid]:
                    try:
                        parent = psutil.Process(pid)
                        for proc in [parent] + parent.children(recursive=True):
                            seen[proc.pid] = proc
                    except psutil.Error:
                        continue
                processes = []
                for proc in seen.values():
                    try:
                        cpu = proc.cpu_times()
                        processes.append(
                            {
                                "pid": proc.pid,
                                "name": proc.name(),
                                "rss_bytes": proc.memory_info().rss,
                                "cpu_seconds": cpu.user + cpu.system,
                            }
                        )
                    except psutil.Error:
                        continue
                samples.append(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "processes": processes,
                        "host_load_average": list(os.getloadavg()),
                        "host_available_bytes": psutil.virtual_memory().available,
                        "host_swap_used_bytes": psutil.swap_memory().used,
                    }
                )
                if time.monotonic() > deadline:
                    child.kill()
                    child.wait()
                    raise subprocess.TimeoutExpired(args, seconds + 60)
                time.sleep(1)
            code = child.returncode
            (out / "resources.json").write_text(json.dumps(samples, indent=2))
        except subprocess.TimeoutExpired:
            code = 124
    counts = json.loads((out / "counts.json").read_text()) if (out / "counts.json").exists() else {}
    provider = httpx.get(c["provider_direct_url"] + "/records", trust_env=False, timeout=10).json()
    effects = [x for x in provider["effects"] if ":load-" + scope + "-" in x["key"]]
    # Inspect actual application rows, not only returned HTTP status codes.
    sys.path.insert(0, c["installed"])
    from sqlalchemy import create_engine, text

    engine = create_engine(c["database_url"])
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT id,idempotency_key,payment_status FROM restaurant_orders "
                    "WHERE idempotency_key LIKE :prefix"
                ),
                {"prefix": "load-" + scope + "-%"},
            )
            .mappings()
            .all()
        )
        payments = conn.execute(
            text(
                "SELECT count(*) FROM restaurant_payments p JOIN "
                "restaurant_orders o ON p.order_id=o.id WHERE o.idempotency_key LIKE :prefix"
            ),
            {"prefix": "load-" + scope + "-%"},
        ).scalar()
    engine.dispose()
    audit = {
        "orders": len(rows),
        "payments": payments,
        "provider_effects": len(effects),
        "duplicate_intents": len(rows) - len({r["idempotency_key"] for r in rows}),
        "provider_calls": sum(e["calls"] for e in effects),
        "paid_orders": sum(r["payment_status"] == "paid" for r in rows),
    }
    receipt = {
        "profile": name,
        "budget": {
            "users": users,
            "spawn_per_second": spawn,
            "duration_seconds": seconds,
        },
        "command": args,
        "version": subprocess.check_output([args[0], "--version"], text=True).strip(),
        "revision": c["revision"],
        "target": c["base_url"],
        "start": start,
        "end": datetime.now(UTC).isoformat(),
        "exit_code": code,
        "execution": "COMPLETE" if counts and code != 124 else "PARTIAL",
        "outcome": "PASS" if accepted(counts, audit, users, code) else "FAIL",
        "counts": counts,
        "database_audit": audit,
        "limits": [
            "conservative local budgets; attachment budgets unavailable",
            "fresh unique intent per journey; capacity profile: "
            + c.get("load_capacity_profile", "untracked"),
            "synthetic provider and host-local network, not production capacity",
        ],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    receipts.append(receipt)
(a.output / "summary.json").write_text(json.dumps(receipts, indent=2))
print(
    json.dumps(
        [{k: r[k] for k in ["profile", "execution", "outcome", "database_audit"]} for r in receipts]
    )
)

if any(r["outcome"] != "PASS" or r["execution"] != "COMPLETE" for r in receipts):
    raise SystemExit(1)
