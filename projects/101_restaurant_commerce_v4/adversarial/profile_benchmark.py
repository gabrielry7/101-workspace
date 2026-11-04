"""Paired local capacity-profile benchmark; real PostgreSQL, no remote traffic.

Compare an explicitly retained baseline wheel with current source. Every block gets
fresh database rows/provider ledger, identical workers and reversed repeat order.
"""

import argparse
import hashlib
import json
import os
import platform
import threading
from pathlib import Path

import psutil
import run
from latency_contract import TARGETS, assess
from load_contract import validate_target
from measure import restart, sample
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-wheel", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path, help="Reuse only an owned local disposable environment"
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=("untracked", "finite", "scheduled"),
        default=["untracked", "finite", "scheduled"],
    )
    parser.add_argument(
        "--payment-lease-seconds",
        type=int,
        default=5,
        help="Stress harness default 5; application default is 30",
    )
    args = parser.parse_args()
    if not 1 <= args.payment_lease_seconds <= 300:
        parser.error("Payment lease must be 1..300 seconds")
    if len(set(args.profiles)) != len(args.profiles):
        parser.error("Profiles must be unique")
    if not args.baseline_wheel.is_file():
        parser.error("Baseline wheel must exist")
    args.output.mkdir(parents=True, exist_ok=False)
    if args.config:
        parent = json.loads(args.config.read_text())
        validate_target(parent, args.config)
    else:
        parent = run.setup(args.output / "environment")
    run.stop(parent, "application")
    run.stop(parent, "provider")
    try:
        assert (
            run.command(
                parent,
                "profile-fixed-build",
                [
                    run.PYTHON,
                    "-m",
                    "build",
                    "--wheel",
                    "--no-isolation",
                    "--outdir",
                    args.output / "wheel",
                ],
            )
            == 0
        )
        fixed_wheel = next((args.output / "wheel").glob("*.whl"))
        wheels = {"old": args.baseline_wheel.resolve(), "new": fixed_wheel.resolve()}
        installs = {}
        for label, wheel in wheels.items():
            installs[label] = str((args.output / (label + "-installed")).resolve())
            assert (
                run.command(
                    parent,
                    "profile-install-" + label,
                    [
                        run.PYTHON,
                        "-m",
                        "pip",
                        "install",
                        "--no-deps",
                        "--target",
                        installs[label],
                        wheel,
                    ],
                )
                == 0
            )
        # This runner imports model classes once when seeding blocks. Reject
        # schema-changing comparisons rather than reusing cached old models.
        for module in ("models.py", "db.py", "migrations.py"):
            files = [
                Path(installs[label]) / "world_model/restaurant_commerce" / module
                for label in ("old", "new")
            ]
            if files[0].read_bytes() != files[1].read_bytes():
                raise ValueError("Profile benchmark requires matching database schema: " + module)
        conditions = [
            (p, label, rep)
            for rep in (1, 2)
            for p in args.profiles
            for label in (("old", "new") if rep == 1 else ("new", "old"))
        ]
        phases = [["warmup", 2, 2, 10], ["normal", 30, 10, 30], ["spike", 100, 20, 45]]
        run.write(
            args.output / "protocol.json",
            {
                "start": run.now(),
                "conditions": conditions,
                "phases": phases,
                "latency_targets_ms": TARGETS,
                "payment_lease_seconds": args.payment_lease_seconds,
                "artifacts": {
                    k: {"wheel": str(w), "sha256": hashlib.sha256(w.read_bytes()).hexdigest()}
                    for k, w in wheels.items()
                },
                "workers": 2,
                "distinct_customers": True,
                "timing_enabled": True,
                "cpu_count": psutil.cpu_count(),
                "memory_bytes": psutil.virtual_memory().total,
                "platform": platform.platform(),
                "limitations": [
                    "Shared development host; no production capacity or SLA claim",
                    "Local PostgreSQL on output filesystem; "
                    "tmpfs is not comparable to prior disk-backed runs",
                    "Closed-loop randomized journeys; two repeats, not statistical significance",
                    "One hot item/business; finite stock 100000; capacity 500 across eight slots",
                    "Raised test rate limits; controlled provider; no external services",
                ],
            },
        )
        admin = create_engine(parent["database_url"])
        results = []
        for profile, label, rep in conditions:
            name = f"{profile}-{label}-{rep}"
            out = args.output / name
            out.mkdir()
            (out / ".commerce-test-run").write_text("owned disposable commerce verification run\n")
            schema = "profile_" + name.replace("-", "_")
            with admin.begin() as conn:
                conn.execute(text("CREATE SCHEMA " + schema))
            url = make_url(parent["database_url"]).update_query_dict(
                {"options": "-csearch_path=" + schema}
            )
            c = dict(
                parent,
                run_dir=str(out.resolve()),
                database_url=url.render_as_string(hide_password=False),
                installed=installs[label],
                wheel=str(wheels[label]),
                wheel_sha256=hashlib.sha256(wheels[label].read_bytes()).hexdigest(),
                processes={},
                timing_enabled=True,
                distinct_customers=True,
                load_profiles=phases,
                load_capacity_profile=profile,
                payment_lease_seconds=args.payment_lease_seconds,
                load_pickup_slots=[],
                revision=parent["revision"]
                + ":"
                + label
                + ":"
                + hashlib.sha256(wheels[label].read_bytes()).hexdigest(),
                database_pid_path=str(Path(parent["run_dir"]) / "pgdata/postmaster.pid"),
            )
            run.seed(c)
            # Same existing model schema in both artifacts; configure only synthetic data.
            from world_model.restaurant_commerce.db import session_factory
            from world_model.restaurant_commerce.models import ItemStock, MenuItem, PickupPolicy
            from world_model.restaurant_commerce.operations import PickupSettings
            from world_model.restaurant_commerce.service import RestaurantCommerceService

            eng = create_engine(c["database_url"])
            with session_factory(eng)() as s:
                item_id = s.scalar(select(MenuItem.id).where(MenuItem.name == "Papas de la casa"))
                c["cart"] = [{"menu_item_id": item_id, "quantity": 1, "modifiers": []}]
                assert s.get(MenuItem, item_id) is not None
                if profile != "untracked":
                    s.add(ItemStock(item_id=item_id, remaining=100000))
                if profile == "scheduled":
                    policy = PickupSettings(
                        expected_version=0,
                        ordering_enabled=True,
                        scheduled=True,
                        opens=0,
                        closes=1440,
                        lead_minutes=5,
                        capacity=500,
                        reason="Synthetic benchmark",
                    )
                    s.add(
                        PickupPolicy(
                            business_id=c["business_ids"][0],
                            policy_json=json.dumps(
                                policy.model_dump(
                                    mode="json", exclude={"expected_version", "reason"}
                                )
                            ),
                        )
                    )
                    s.flush()
                    c["load_pickup_slots"] = [
                        slot["at"]
                        for slot in RestaurantCommerceService(s).pickup_slots(c["business_ids"][0])[
                            "slots"
                        ][2:10]
                    ]
                    assert len(c["load_pickup_slots"]) == 8
                s.commit()
            run.write(out / "config.json", c)
            (out / "config.json").chmod(0o600)
            env = dict(
                os.environ, COMMERCE_TEST_CONFIG=str(out / "config.json"), PYTHONPATH=c["installed"]
            )
            errors = []
            done = threading.Event()

            def collect(c=c, out=out, done=done, errors=errors):
                try:
                    sample(c, out / "postgres.jsonl", done)
                except Exception as exc:
                    errors.append(type(exc).__name__)

            sampler = threading.Thread(target=collect)
            print("START", name, run.now(), flush=True)
            started = run.now()
            try:
                run.process(
                    c,
                    "provider",
                    [
                        run.PYTHON,
                        "-m",
                        "uvicorn",
                        "provider:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        c["provider_direct_url"].rsplit(":", 1)[1],
                    ],
                    env,
                )
                run.wait_http(c["provider_direct_url"] + "/health")
                restart(c)
                sampler.start()
                code = run.command(
                    c,
                    "profile-load",
                    [
                        run.PYTHON,
                        run.ROOT / "adversarial/load.py",
                        "--config",
                        out / "config.json",
                        "--output",
                        out / "load",
                    ],
                    timeout=240,
                )
            finally:
                done.set()
                if sampler.ident:
                    sampler.join(timeout=15)
                run.stop(c, "application")
                run.stop(c, "provider")
            with eng.connect() as conn:
                stock = conn.execute(
                    text("SELECT remaining FROM restaurant_item_stock WHERE item_id=:item"),
                    {"item": item_id},
                ).scalar_one_or_none()
                units = conn.execute(
                    text(
                        "SELECT COALESCE(sum(quantity),0) FROM restaurant_order_items "
                        "WHERE menu_item_id=:item"
                    ),
                    {"item": item_id},
                ).scalar_one()
                max_slot = conn.execute(
                    text(
                        "SELECT COALESCE(max(n),0) FROM (SELECT count(*) n FROM restaurant_orders "
                        "WHERE requested_pickup_at IS NOT NULL GROUP BY requested_pickup_at) x"
                    )
                ).scalar_one()
            correct = (
                stock is None if profile == "untracked" else stock == 100000 - units
            ) and max_slot <= 500
            result = {
                "condition": name,
                "artifact": label,
                "start": started,
                "end": run.now(),
                "exit_code": code,
                "sampler_errors": errors,
                "stock_remaining": stock,
                "ordered_units": units,
                "max_slot_orders": max_slot,
                "capacity_correct": correct,
                "outcome": "PASS"
                if code == 0 and correct and not errors and not sampler.is_alive()
                else "FAIL",
            }
            result["latency_gates"] = [
                {"phase": receipt["profile"], **assess(receipt)}
                for receipt in json.loads((out / "load/summary.json").read_text())
            ]
            results.append(result)
            run.write(args.output / "execution.json", results)
            print("END", name, result["outcome"], flush=True)
            eng.dispose()
        admin.dispose()
        if len(results) != len(conditions) or any(
            r["outcome"] != "PASS"
            or (r["artifact"] == "new" and any(g["outcome"] == "FAIL" for g in r["latency_gates"]))
            for r in results
        ):
            raise SystemExit(1)
    finally:
        run.cleanup(parent)


if __name__ == "__main__":
    main()
