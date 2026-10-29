import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
c = json.loads(a.config.read_text())
a.output.mkdir(parents=True, exist_ok=True)
profiles = [
    ("smoke", 2, 2, 10),
    ("normal", 10, 5, 20),
    ("spike", 30, 30, 15),
    ("recovery", 3, 3, 15),
    ("sustained", 10, 5, 60),
]
receipts = []
for name, users, spawn, seconds in profiles:
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
        "10",
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
        COMMERCE_LOAD_PROFILE=name,
        COMMERCE_LOAD_RECEIPT=str(out / "counts.json"),
    )
    start = datetime.now(UTC).isoformat()
    with (out / "native.log").open("w") as log:
        try:
            code = subprocess.run(
                args,
                check=False,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=seconds + 30,
            ).returncode
        except subprocess.TimeoutExpired:
            code = 124
    counts = (
        json.loads((out / "counts.json").read_text())
        if (out / "counts.json").exists()
        else {}
    )
    provider = httpx.get(
        c["provider_direct_url"] + "/records", trust_env=False, timeout=10
    ).json()
    effects = [x for x in provider["effects"] if ":load-" + name + "-" in x["key"]]
    # Inspect actual application rows, not only returned HTTP status codes.
    sys.path.insert(0, c["installed"])
    from sqlalchemy import create_engine, text

    engine = create_engine(c["database_url"])
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT id,idempotency_key,payment_status FROM restaurant_orders WHERE idempotency_key LIKE :prefix"
                ),
                {"prefix": "load-" + name + "-%"},
            )
            .mappings()
            .all()
        )
        payments = conn.execute(
            text(
                "SELECT count(*) FROM restaurant_payments p JOIN restaurant_orders o ON p.order_id=o.id WHERE o.idempotency_key LIKE :prefix"
            ),
            {"prefix": "load-" + name + "-%"},
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
        "outcome": "PASS"
        if counts.get("completed_checkouts", 0) > 0
        and code == 0
        and audit["duplicate_intents"] == 0
        and len(rows) == payments == len(effects)
        else "FAIL",
        "counts": counts,
        "database_audit": audit,
        "limits": [
            "conservative local budgets; attachment budgets unavailable",
            "fresh unique intent per journey, no stock cap in current app",
            "synthetic provider and host-local network, not production capacity",
        ],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    receipts.append(receipt)
(a.output / "summary.json").write_text(json.dumps(receipts, indent=2))
print(
    json.dumps(
        [
            {k: r[k] for k in ["profile", "execution", "outcome", "database_audit"]}
            for r in receipts
        ]
    )
)

if any(r["outcome"] != "PASS" or r["execution"] != "COMPLETE" for r in receipts):
    raise SystemExit(1)
