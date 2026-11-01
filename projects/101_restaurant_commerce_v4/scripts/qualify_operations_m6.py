#!/usr/bin/env python3
"""Run M6a against disposable PostgreSQL and two hash-locked installed artifacts.

No live provider calls. No existing database, service or deployment is modified.
Only this fresh run directory's processes are stopped. Private DB/config files stay
inside it; share only evidence/ after inspecting it for accidental sensitive data.
"""

import argparse
import importlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import traceback
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment"))
import commerce_release as release  # noqa: E402
import database  # noqa: E402
import runtime  # noqa: E402


class Run:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.evidence = runtime.private_dir(self.path / "evidence")
        self.commands = []
        self.scenarios = []
        self.stage = "setup"
        self.started = runtime.utc()

    def command(self, name, args, *, env=None, cwd=ROOT, expected=0, timeout=180):
        start = runtime.utc()
        stamp = time.monotonic()
        result = subprocess.run(
            [str(a) for a in args], cwd=cwd, env=env, capture_output=True, timeout=timeout
        )
        # These commands contain paths and synthetic identifiers, never credentials.
        (self.evidence / (name + ".log")).write_bytes(result.stdout + result.stderr)
        entry = {
            "name": name,
            "command": [str(a) for a in args],
            "cwd": str(cwd),
            "started_at": start,
            "ended_at": runtime.utc(),
            "seconds": round(time.monotonic() - stamp, 3),
            "exit_code": result.returncode,
            "expected_exit": expected,
        }
        self.commands.append(entry)
        self.save()
        if result.returncode != expected:
            raise RuntimeError(name + " unexpected exit; see native log")
        return result.stdout.decode()

    @contextmanager
    def scenario(self, name):
        self.stage = name
        start = runtime.utc()
        stamp = time.monotonic()
        try:
            yield
        except Exception as exc:
            self.scenarios.append(
                {
                    "name": name,
                    "outcome": "FAIL",
                    "error_class": type(exc).__name__,
                    "started_at": start,
                    "ended_at": runtime.utc(),
                }
            )
            self.save()
            raise
        else:
            self.scenarios.append(
                {
                    "name": name,
                    "outcome": "PASS",
                    "started_at": start,
                    "ended_at": runtime.utc(),
                    "seconds": round(time.monotonic() - stamp, 3),
                }
            )
            self.save()
            print(name + ": PASS", flush=True)

    def save(self, **extra):
        runtime.write_json(
            self.evidence / "execution.json",
            {
                "driver_command": [sys.executable, *sys.argv],
                "started_at": self.started,
                "updated_at": runtime.utc(),
                "commands": self.commands,
                "scenarios": self.scenarios,
                **extra,
            },
        )


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(check, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.15)
    raise AssertionError("Condition did not recover before deadline")


def expect_rejected(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("Unsafe operation was accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--wheelhouse", required=True)
    parser.add_argument("--previous-wheel")
    parser.add_argument("--previous-revision", default="58629356fe5b9a6291ffe1745ecdd7525e490ee5")
    args = parser.parse_args()
    run = Run(args.run_dir)
    cluster = run.path / "postgres"
    pgport, webport, restoredport = port(), port(), port()
    site, restoredsite = run.path / "site", run.path / "restore-site"
    started_pg = False
    clients = []
    engines = []
    pg_ctl = ["pg_ctl", "-D", cluster, "-l", run.path / "postgres.log", "-w"]
    status = "FAIL"
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        with run.scenario("offline_artifact_install"):
            wheelout = run.path / "build"
            run.command(
                "build",
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    wheelout,
                    ROOT,
                ],
            )
            wheel = next(wheelout.glob("*.whl"))
            if args.previous_wheel:
                oldwheel = Path(args.previous_wheel).resolve()
            else:
                oldsrc = run.path / "previous-source"
                oldsrc.mkdir()
                archive = run.path / "previous.tar"
                run.command(
                    "previous-archive",
                    [
                        "git",
                        "archive",
                        "--format=tar",
                        "-o",
                        archive,
                        args.previous_revision + ":projects/101_restaurant_commerce_v4",
                    ],
                    cwd=ROOT.parents[1],
                )
                with tarfile.open(archive) as tar:
                    tar.extractall(oldsrc, filter="data")
                oldout = run.path / "previous-build"
                run.command(
                    "previous-build",
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "wheel",
                        "--no-deps",
                        "--no-build-isolation",
                        "--wheel-dir",
                        oldout,
                        oldsrc,
                    ],
                )
                oldwheel = next(oldout.glob("*.whl"))
            bundles = {}
            for label, source, rev in [
                ("new", wheel, revision),
                ("old", oldwheel, args.previous_revision),
            ]:
                bundle = run.path / (label + "-bundle")
                packed = json.loads(
                    run.command(
                        label + "-pack",
                        [
                            sys.executable,
                            ROOT / "scripts/commerce_release.py",
                            "pack",
                            "--wheel",
                            source,
                            "--wheelhouse",
                            args.wheelhouse,
                            "--output",
                            bundle,
                            "--revision",
                            rev,
                        ],
                    )
                )
                sha = packed["manifest_sha256"]
                installed = json.loads(
                    run.command(
                        label + "-install",
                        [
                            sys.executable,
                            ROOT / "scripts/commerce_release.py",
                            "install",
                            "--bundle",
                            bundle,
                            "--manifest-sha256",
                            sha,
                            "--site",
                            site,
                        ],
                    )
                )
                bundles[label] = {
                    "id": installed["release"],
                    "sha256": sha,
                    "wheel_sha256": release.digest(source),
                }
            new, old = bundles["new"]["id"], bundles["old"]["id"]
            target = site / "releases" / new
            installed_packages = next((target / "venv/lib").glob("python*/site-packages"))
            sys.path.insert(0, str(installed_packages))
            importlib.invalidate_caches()
            import httpx
            import world_model.restaurant_commerce.api as installed_api
            from sqlalchemy import func, select, text
            from world_model.restaurant_commerce import staff
            from world_model.restaurant_commerce.db import (
                database_ready,
                init_schema,
                session_factory,
            )
            from world_model.restaurant_commerce.models import (
                CommerceEventOutbox,
                ItemStock,
                Order,
                Payment,
                PaymentIntent,
                PickupPolicy,
                RestaurantCommerceProfile,
                StaffSession,
                utcnow,
            )
            from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
            from world_model.restaurant_commerce.seed import seed_demo

            assert Path(installed_api.__file__).is_relative_to(installed_packages)
            sourcefiles = ROOT / "src/world_model/restaurant_commerce"
            compared = 0
            for f in sourcefiles.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    assert release.digest(f) == release.digest(
                        installed_packages
                        / "world_model/restaurant_commerce"
                        / f.relative_to(sourcefiles)
                    )
                    compared += 1
            runtime.write_json(
                run.evidence / "artifact.json",
                {
                    "revision": revision,
                    "dirty": dirty,
                    "bundles": bundles,
                    "installed_module": str(installed_api.__file__),
                    "identical_package_files": compared,
                    "python": sys.version,
                    "platform": sys.platform,
                    "runtime_scope": "loopback rehearsal, simulated providers only",
                },
            )
        with run.scenario("postgres_and_previous_release_baseline"):
            run.command(
                "initdb", ["initdb", "-D", cluster, "-A", "trust", "--no-locale", "-E", "UTF8"]
            )
            with (cluster / "postgresql.conf").open("a") as f:
                f.write(
                    f"\nlisten_addresses='127.0.0.1'\nport={pgport}\nunix_socket_directories=''\nmax_connections=40\nshared_buffers='16MB'\n"
                )
            run.command("postgres-start", [*pg_ctl, "start"])
            started_pg = True
            for name in ["commerce", "restored", "tamper", "empty", "legacy"]:
                run.command("createdb-" + name, ["createdb", "-h", "127.0.0.1", "-p", pgport, name])
            secret = "synthetic-only-m6-signing-secret-for-disposable-drill"

            def cfg(name, writes=False):
                value = {
                    "mode": "rehearsal",
                    "database_url": f"postgresql+psycopg://{os.environ['USER']}@127.0.0.1:{pgport}/{name}",
                    "public_access_secret": secret,
                    "state_dir": str(run.path / (name + "-state")),
                    "allow_writes": writes,
                    "interval_seconds": 0.3,
                    "heartbeat_seconds": 2,
                    "backlog_seconds": 1,
                    "backup_max_age_seconds": 86400,
                }
                path = run.path / (name + ("-writable" if writes else "-quarantine") + ".json")
                runtime.write_json(path, value)
                return path, runtime.config(path)

            sourcepath, source = cfg("commerce", True)
            restorepath, restored = cfg("restored")
            emptypath, empty = cfg("empty", True)
            _, tamper = cfg("tamper")
            _, legacy = cfg("legacy")
            engine = runtime.engine_for(source)
            engines.append(engine)
            init_schema(engine)
            sessions = session_factory(engine)
            with sessions() as s:
                seed_demo(s)
                s.add(
                    RestaurantCommerceProfile(
                        business_id="other", slug="other", display_name="Synthetic other"
                    )
                )
                s.commit()
                staff.provision(
                    s,
                    "m6.manager",
                    "synthetic test passphrase only",
                    BID,
                    "manager",
                    actor="offline-test",
                )
                staff.provision(
                    s,
                    "m6.other",
                    "synthetic test passphrase only",
                    "other",
                    "viewer",
                    actor="offline-test",
                )
                revoked = staff.login(
                    s, "m6.manager", "synthetic test passphrase only", "synthetic"
                )
                s.get(StaffSession, staff.digest(revoked)).revoked = True
                s.commit()
            record = release.activate(site, old, sourcepath, webport)
            base = f"http://127.0.0.1:{webport}"
            client = httpx.Client(base_url=base, timeout=10, trust_env=False)
            clients.append(client)
            assert client.get("/deployment").json()["release"] == old
            store = client.get(f"/api/restaurants/{BID}/storefront").json()
            item = next(
                i
                for m in store["menus"]
                for c in m["categories"]
                for i in c["items"]
                if not i["modifier_groups"]
            )

            def checkout(key):
                body = {
                    "customer": {"name": "Synthetic M6", "phone": "3005550600"},
                    "items": [{"menu_item_id": item["id"], "quantity": 1}],
                    "idempotency_key": key,
                    "recovery_secret": "a" * 64,
                }
                r = client.post(f"/api/restaurants/{BID}/orders", json=body)
                assert r.status_code == 200, "Synthetic checkout status " + str(r.status_code)
                return r.json()

            order = checkout("m6-before-deploy")
            reference = order["payments"][0]["provider_reference"]
            assert client.post(f"/api/payments/simulated/{reference}/complete").status_code == 200
            assert (
                client.post(
                    "/api/staff/login",
                    headers={"X-101-Login": "1"},
                    json={"username": "m6.manager", "password": "synthetic test passphrase only"},
                ).status_code
                == 200
            )
            session_cookie = client.cookies.get("commerce_staff")
            assert client.get(f"/api/operator/restaurants/{BID}/orders").status_code == 200
            assert client.get("/api/operator/restaurants/other/orders").status_code == 403
        with run.scenario("controller_death_before_journal_cannot_start_child"):
            helper = run.path / "gate-fault.py"
            marker = run.path / "gate-child.json"
            helper.write_text(
                "import sys,time\nfrom pathlib import Path\n"
                "sys.path.insert(0, sys.argv[1])\nimport commerce_release as release\n"
                "original=release.write_json\n"
                "def interrupted(path,value):\n"
                "    if Path(path).name=='pending.json':\n"
                "        original(Path(sys.argv[6]),value['processes'][-1])\n"
                "        time.sleep(60)\n"
                "    original(path,value)\n"
                "release.write_json=interrupted\n"
                "release.launch(Path(sys.argv[2]),sys.argv[3],sys.argv[4],int(sys.argv[5]))\n"
            )
            unused_port = port()
            controller = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(helper),
                    str(ROOT / "scripts"),
                    str(site),
                    new,
                    str(sourcepath),
                    str(unused_port),
                    str(marker),
                ],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            child = None
            try:
                wait_for(marker.exists)
                child = json.loads(marker.read_text())
                controller.kill()
                controller.wait(timeout=5)
                wait_for(lambda: release.ticks(child["pid"]) != child["ticks"])
                with socket.socket() as probe:
                    assert probe.connect_ex(("127.0.0.1", unused_port)) != 0
                assert client.get("/ready").status_code == 200
            finally:
                if controller.poll() is None:
                    controller.kill()
                    controller.wait(timeout=5)
                if child:
                    release.terminate({"processes": [child]})
        with run.scenario("upgrade_activate_new_artifact"):
            record = release.activate(site, new, sourcepath, webport)
            assert client.get("/deployment").json()["release"] == new
            assert client.get("/openapi.json").json()["info"]["version"] == "0.11.0"
            later = checkout("m6-after-deploy")
            recovery_body = {"idempotency_key": "m6-before-deploy", "recovery_secret": "a" * 64}
            recover_route = f"/api/restaurants/{BID}/orders/recover"
            assert client.post(recover_route, json=recovery_body).json()["id"] == order["id"]
        with run.scenario("worker_termination_alert_and_recovery"):
            worker = next(p for p in record["processes"] if p["role"] == "recover")
            release.terminate({"processes": [worker]})
            state = Path(source["state_dir"])

            def alerted(code):
                return code in {
                    a["code"] for a in json.loads((state / "status.json").read_text())["alerts"]
                }

            wait_for(lambda: alerted("worker_stale"))
            assert client.post(recover_route, json=recovery_body).json()["id"] == order["id"]
            record = release.activate(site, new, sourcepath, webport)
            wait_for(lambda: not alerted("worker_stale"))
        with run.scenario("event_write_failure_retains_then_drains"):
            events = state / "events"
            events.chmod(0o500)
            blocked_order = checkout("m6-event-write-fault")
            wait_for(lambda: alerted("events_backlog"))
            with sessions() as s:
                pending = list(
                    s.scalars(
                        select(CommerceEventOutbox).where(CommerceEventOutbox.status == "pending")
                    )
                )
                assert pending
                assert not any((events / (row.id + ".json")).exists() for row in pending)
            events.chmod(0o700)
            wait_for(lambda: not alerted("events_backlog"))
            with sessions() as s:
                assert (
                    s.scalar(
                        select(func.count())
                        .select_from(CommerceEventOutbox)
                        .where(CommerceEventOutbox.status != "published")
                    )
                    == 0
                )
                for row in s.scalars(select(CommerceEventOutbox)):
                    assert (events / (row.id + ".json")).is_file()
            assert (
                client.post(
                    recover_route, json={**recovery_body, "idempotency_key": "m6-event-write-fault"}
                ).json()["id"]
                == blocked_order["id"]
            )
        with run.scenario("api_termination_preserves_replay"):
            api = next(p for p in record["processes"] if p["role"] == "serve")
            release.terminate({"processes": [api]})
            record = release.activate(site, new, sourcepath, webport)
            assert checkout("m6-after-deploy")["id"] == later["id"]
            with sessions() as s:
                assert (
                    s.scalar(
                        select(func.count())
                        .select_from(Payment)
                        .where(Payment.order_id == later["id"])
                    )
                    == 1
                )
        with run.scenario("database_outage_is_unknown_and_recovers"):
            for e in engines:
                e.dispose()
            run.command("postgres-outage", [*pg_ctl, "-m", "fast", "stop"])
            started_pg = False
            wait_for(lambda: alerted("database_unavailable"))
            snap = json.loads((state / "status.json").read_text())
            assert snap["queues"] is None
            run.command("postgres-restart", [*pg_ctl, "start"])
            started_pg = True
            wait_for(lambda: not alerted("database_unavailable"))
            assert client.get("/ready").status_code == 200
            assert client.post(recover_route, json=recovery_body).json()["id"] == order["id"]
        with run.scenario("snapshot_backup_and_post_snapshot_gap"):
            expired_order = checkout("m6-expired-recovery")
            with sessions() as s:
                intent = s.scalar(
                    select(PaymentIntent).where(PaymentIntent.order_id == expired_order["id"])
                )
                intent.created_at = utcnow() - timedelta(days=2)
                s.commit()
            backed = json.loads(
                run.command(
                    "backup",
                    [
                        target / "venv/bin/python",
                        "-I",
                        "-B",
                        target / "database.py",
                        "backup",
                        "--config",
                        sourcepath,
                        "--directory",
                        run.path / "backup",
                    ],
                )
            )
            post_snapshot = checkout("m6-after-snapshot")
            assert post_snapshot["id"] != order["id"]
            assert (run.path / "backup/database.dump").stat().st_mode & 0o077 == 0
        with run.scenario("tamper_wrong_secret_and_nonempty_restore_rejected"):
            copied = run.path / "corrupt-backup"
            shutil.copytree(run.path / "backup", copied)
            with (copied / "database.dump").open("ab") as f:
                f.write(b"corrupt")
            expect_rejected(
                lambda: database.restore(tamper, copied, backed["manifest_sha256"], "tamper", True)
            )
            expect_rejected(
                lambda: database.restore(
                    {**tamper, "public_access_secret": "different" * 10},
                    run.path / "backup",
                    backed["manifest_sha256"],
                    "tamper",
                    True,
                )
            )
            expect_rejected(
                lambda: database.restore(
                    {**source, "allow_writes": False},
                    run.path / "backup",
                    backed["manifest_sha256"],
                    "commerce",
                    True,
                )
            )
            te = runtime.engine_for(tamper)
            engines.append(te)
            with te.begin() as c:
                assert (
                    c.scalar(
                        text(
                            "SELECT count(*) FROM information_schema.tables "
                            "WHERE table_schema='public'"
                        )
                    )
                    == 0
                )
                c.execute(text("CREATE TABLE preserved_marker (id int)"))
                c.execute(text("INSERT INTO preserved_marker VALUES (101)"))
            expect_rejected(
                lambda: database.restore(
                    tamper, run.path / "backup", backed["manifest_sha256"], "tamper", True
                )
            )
            with te.connect() as c:
                assert c.scalar(text("SELECT id FROM preserved_marker")) == 101
        with run.scenario("restore_quarantine_preserves_identity_and_revocation"):
            result = json.loads(
                run.command(
                    "restore",
                    [
                        target / "venv/bin/python",
                        "-I",
                        "-B",
                        target / "database.py",
                        "restore",
                        "--config",
                        restorepath,
                        "--directory",
                        run.path / "backup",
                        "--manifest-sha256",
                        backed["manifest_sha256"],
                        "--expected-database",
                        "restored",
                        "--offline",
                    ],
                )
            )
            assert result["database_schema_ready"] and result["quarantine"]
            rid = release.install(run.path / "new-bundle", bundles["new"]["sha256"], restoredsite)
            restore_record = release.activate(restoredsite, rid, restorepath, restoredport)
            assert not any(p["role"] == "recover" for p in restore_record["processes"])
            rc = httpx.Client(
                base_url=f"http://127.0.0.1:{restoredport}", trust_env=False, timeout=10
            )
            clients.append(rc)
            assert rc.post(f"/api/restaurants/{BID}/orders", json={}).status_code == 503
            assert rc.post(f"/api/payments/simulated/{reference}/complete").status_code == 503
            assert (
                rc.post(
                    recover_route, json={**recovery_body, "wompi_transaction_id": "123456-test"}
                ).status_code
                == 503
            )
            recovered = rc.post(recover_route, json=recovery_body)
            assert recovered.status_code == 200 and recovered.json()["id"] == order["id"]
            assert recovered.json()["payments"][0]["provider_reference"] == reference
            assert (
                rc.get(
                    f"/api/orders/{order['id']}",
                    headers={"X-101-Order-Token": order["access_token"]},
                ).status_code
                == 200
            )
            assert (
                rc.get(
                    "/api/staff/me", headers={"Cookie": "commerce_staff=" + session_cookie}
                ).status_code
                == 200
            )
            assert (
                rc.get(
                    "/api/operator/restaurants/other/orders",
                    headers={"Cookie": "commerce_staff=" + session_cookie},
                ).status_code
                == 403
            )
            assert (
                rc.get("/api/staff/me", headers={"Cookie": "commerce_staff=" + revoked}).status_code
                == 401
            )
            assert (
                rc.post(
                    recover_route, json={**recovery_body, "idempotency_key": "m6-expired-recovery"}
                ).status_code
                == 410
            )
            assert (
                rc.post(
                    recover_route, json={**recovery_body, "idempotency_key": "m6-after-snapshot"}
                ).status_code
                == 404
            )
            runtime.write_json(run.evidence / "restore-measurement.json", result)
        with run.scenario("failed_candidate_automatically_restores_previous"):
            try:
                release.activate(site, new, emptypath, webport)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Uninitialized database accepted")
            assert client.get("/deployment").json()["release"] == new
            assert checkout("m6-after-deploy")["id"] == later["id"]
        with run.scenario("application_rollback_keeps_newer_orders"):
            release.activate(site, old, sourcepath, webport)
            assert client.get("/deployment").json()["release"] == old
            assert checkout("m6-after-deploy")["id"] == later["id"]
            assert checkout("m6-after-snapshot")["id"] == post_snapshot["id"]
            with sessions() as s:
                assert s.scalar(select(func.count()).select_from(Order)) == 5
                assert s.scalar(select(func.count()).select_from(Payment)) == 5
        with run.scenario("populated_legacy_restore_requires_explicit_offline_upgrade"):
            release.stop(restoredsite)
            re = runtime.engine_for(restored)
            engines.append(re)
            with re.begin() as c:
                assert c.scalar(select(func.count()).select_from(PickupPolicy)) == 0
                assert c.scalar(select(func.count()).select_from(ItemStock)) == 0
                PickupPolicy.__table__.drop(c)
                ItemStock.__table__.drop(c)
            assert not database_ready(re)
            legacy_backup = database.backup(restored, run.path / "legacy-backup")
            legacy_restored = database.restore(
                legacy, run.path / "legacy-backup", legacy_backup["manifest_sha256"], "legacy", True
            )
            assert not legacy_restored["database_schema_ready"]
            le = runtime.engine_for(legacy)
            engines.append(le)
            from world_model.restaurant_commerce.migrations import upgrade_operations

            upgrade_operations(le)
            assert database_ready(le)
            with le.connect() as c:
                assert c.scalar(select(func.count()).select_from(Order)) == 4
            upgrade_operations(le)
            with le.connect() as c:
                assert c.scalar(select(func.count()).select_from(Order)) == 4
        with run.scenario("retained_postgresql_regressions"):
            env = {
                **os.environ,
                "PYTHONPATH": str(installed_packages),
                "COMMERCE_PAYMENT_TEST_DATABASE_URL": source["database_url"],
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            run.command(
                "postgres-tests",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_deployment_m6.py",
                    "tests/test_operations_m5.py",
                    "tests/test_payment_durability_m3.py",
                    "tests/test_staff_m4.py",
                    "--junitxml=" + str(run.evidence / "postgres-tests.xml"),
                ],
                env=env,
                timeout=240,
            )
            import xml.etree.ElementTree as ET

            suite = ET.parse(run.evidence / "postgres-tests.xml").getroot().find("testsuite")
            assert int(suite.attrib["tests"]) > 0 and int(suite.attrib["skipped"]) == 0
        receipts = [json.loads(p.read_text()) for p in (state / "alerts").glob("*.json")]
        opened = {c for r in receipts for c in r["opened"]}
        resolved_codes = {c for r in receipts for c in r["resolved"]}
        assert {"worker_stale", "events_backlog", "database_unavailable"} <= opened & resolved_codes
        runtime.write_json(
            run.evidence / "alerts.json",
            {"receipts": receipts, "human_delivery": "UNASSESSED: local receipts only"},
        )
        status = "PASS"
    except Exception:
        (run.path / "private-error.txt").write_text(traceback.format_exc())
        print(
            "Qualification failed at " + run.stage + "; inspect private-error.txt", file=sys.stderr
        )
    finally:
        for client in clients:
            client.close()
        for e in engines:
            e.dispose()
        cleanup = []
        for ownedsite in [restoredsite, site]:
            if (ownedsite / "active.json").exists():
                try:
                    release.stop(ownedsite)
                    cleanup.append({"site": str(ownedsite), "stopped": True})
                except Exception as exc:
                    cleanup.append(
                        {
                            "site": str(ownedsite),
                            "stopped": False,
                            "error_class": type(exc).__name__,
                        }
                    )
                    status = "FAIL"
        if started_pg:
            try:
                run.command("postgres-final-stop", [*pg_ctl, "-m", "fast", "stop"])
            except Exception:
                status = "FAIL"
        run.save(
            execution="COMPLETE" if status == "PASS" else "PARTIAL",
            outcome=status,
            ended_at=runtime.utc(),
            cleanup=cleanup,
            gaps=[
                "No remote deployment/TLS/provider traffic",
                "No offsite encrypted backup or WAL/PITR",
                "No human alert delivery",
                "No production RPO/RTO commitment",
            ],
        )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
