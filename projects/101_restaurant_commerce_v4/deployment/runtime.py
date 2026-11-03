"""Strict, loopback-only rehearsal runtime shared by compatible release bundles.

This file is copied beside each immutable release, including rollback artifacts.
No provider credentials or remote integrations are loaded by this entrypoint.
"""

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import stat
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def utc():
    return datetime.now(UTC).isoformat()


def private_dir(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("Runtime directories must be private (0700)")
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError("Runtime directory ancestors must not be symlinks")
    return path


def write_json(path, data):
    path = Path(path)
    directory = private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        sync_dir(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def config(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_mode & 0o077:
        raise ValueError("Configuration must be a private regular file (0600)")
    data = json.loads(path.read_text())
    allowed = {
        "mode",
        "database_url",
        "public_access_secret",
        "state_dir",
        "allow_writes",
        "interval_seconds",
        "heartbeat_seconds",
        "backlog_seconds",
        "backup_max_age_seconds",
    }
    if set(data) - allowed or data.get("mode") != "rehearsal":
        raise ValueError(
            "Only explicit rehearsal configuration is qualified; real money stays gated"
        )
    from sqlalchemy.engine import make_url

    url = make_url(data.get("database_url", ""))
    if (
        url.drivername != "postgresql+psycopg"
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", url.database or "")
        or url.host not in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("Explicit loopback PostgreSQL is required for rehearsal")
    if url.query:
        raise ValueError(
            "Database URL query options are not accepted; use explicit role/database configuration"
        )
    if len(data.get("public_access_secret", "")) < 32:
        raise ValueError("A stable private signing secret of at least32 characters is required")
    if not isinstance(data.get("allow_writes", False), bool):
        raise ValueError("allow_writes must be boolean")
    data.setdefault("allow_writes", False)
    for key, default in [
        ("interval_seconds", 1),
        ("heartbeat_seconds", 15),
        ("backlog_seconds", 60),
        ("backup_max_age_seconds", 86400),
    ]:
        data.setdefault(key, default)
        if not isinstance(data[key], (int, float)) or not 0 < data[key] <= 604800:
            raise ValueError("Invalid timing setting")
    data["state_dir"] = str(private_dir(data["state_dir"]).resolve())
    return data


class FileEventSink:
    """Fsync a private event-ID receipt before acknowledging the existing outbox.

    This is a local durable consumer spool, not message delivery or a human page.
    """

    def __init__(self, directory):
        self.directory = private_dir(directory)

    def publish(self, event):
        if not event.event_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event.event_id):
            raise ValueError("Stable safe event ID required")
        at = event.occurred_at
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        content = (
            json.dumps(
                {
                    "event_id": event.event_id,
                    "kind": event.kind,
                    "business_id": event.business_id,
                    "entity_id": event.entity_id,
                    "occurred_at": at.astimezone(UTC).isoformat(),
                    "dedupe_key": event.dedupe_key,
                    "payload": event.payload,
                },
                sort_keys=True,
            ).encode()
            + b"\n"
        )
        target = self.directory / (event.event_id + ".json")
        fd, tmp = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(tmp, target)
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != content:
                    raise ValueError("Event receipt conflict") from None
            sync_dir(self.directory)
        finally:
            os.unlink(tmp)


def database_id(data):
    from sqlalchemy.engine import make_url

    url = make_url(data["database_url"])
    return hashlib.sha256(
        json.dumps([url.host, url.port or 5432, url.database], sort_keys=True).encode()
    ).hexdigest()


def engine_for(data):
    from sqlalchemy import create_engine

    return create_engine(
        data["database_url"],
        pool_pre_ping=True,
        pool_timeout=5,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=10000"},
    )


def providers():
    from world_model.restaurant_commerce.payments import SimulatedPaymentProvider

    # Nonempty explicit maps prevent create_app from adding cash or live adapters.
    return {"simulated": SimulatedPaymentProvider()}


def options(data):
    from world_model.restaurant_commerce.deliveries import SimulatedDeliveryProvider

    return {
        "payment_providers": providers(),
        "delivery_providers": {"simulated_delivery": SimulatedDeliveryProvider()},
        "event_sink": FileEventSink(Path(data["state_dir"]) / "events"),
    }


def application(data, release):
    from fastapi.responses import JSONResponse
    from world_model.restaurant_commerce.api import create_app
    from world_model.restaurant_commerce.db import database_ready

    engine = engine_for(data)
    if not database_ready(engine):
        raise RuntimeError("Database/schema not ready; use explicit offline upgrade")
    app = create_app(
        engine=engine,
        environment="staging",
        demo_mode=True,
        seed=False,
        auto_init_schema=False,
        payment_recovery_enabled=False,
        provider_recovery_enabled=False,
        public_access_secret=data["public_access_secret"],
        **options(data),
    )

    @app.get("/deployment")
    def identity():
        return {
            "release": release,
            "pid": os.getpid(),
            "mode": "rehearsal",
            "writes_enabled": data["allow_writes"],
            "recovery": "separate-worker",
        }

    @app.middleware("http")
    async def quarantine(request, call_next):
        permitted = request.url.path in {
            "/api/staff/login",
            "/api/staff/logout",
            "/api/staff/logout-all",
        } or request.url.path.endswith("/orders/recover")
        if (
            not data["allow_writes"]
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and not permitted
        ):
            return JSONResponse(
                {"detail": "Restore quarantine: writes are paused pending verification"},
                status_code=503,
            )
        return await call_next(request)

    return app


def recover(data, release, once=False):
    from world_model.restaurant_commerce.db import database_ready, session_factory
    from world_model.restaurant_commerce.service import RestaurantCommerceService

    if not data["allow_writes"]:
        raise ValueError("Recovery is disabled in restore quarantine")
    engine = engine_for(data)
    if not database_ready(engine):
        raise RuntimeError("Database/schema not ready")
    state = Path(data["state_dir"])
    lock = (state / "worker.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sessions = session_factory(engine)
    opts = options(data)
    stop = False
    last_success = None

    def halt(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)
    while not stop:
        stages = {}
        for name, method in [
            ("payments", "recover_payments"),
            ("events", "drain_event_outbox"),
            ("financial", "recover_financial_operations"),
        ]:
            try:
                with sessions() as session:
                    getattr(RestaurantCommerceService(session, **opts), method)(limit=25)
                    stages[name] = {
                        "ok": True
                    }  # Per-row retries/errors remain visible in DB aggregates.
            except Exception as exc:
                stages[name] = {"ok": False, "error_class": type(exc).__name__}
        if all(x["ok"] for x in stages.values()):
            last_success = utc()
        write_json(
            state / "recovery.json",
            {
                "release": release,
                "pid": os.getpid(),
                "at": utc(),
                "last_success": last_success,
                "stages": stages,
                "remote_provider_recovery": "disabled",
                "database_id": database_id(data),
            },
        )
        if once:
            break
        until = time.monotonic() + data["interval_seconds"]
        while not stop and time.monotonic() < until:
            time.sleep(min(0.1, data["interval_seconds"]))
    engine.dispose()
    lock.close()


def snapshot(data):
    from sqlalchemy import func, or_, select
    from world_model.restaurant_commerce.db import database_ready
    from world_model.restaurant_commerce.models import (
        CommerceEventOutbox,
        FinancialOperation,
        PaymentIntent,
        PaymentNotificationInbox,
        PaymentReconciliation,
    )

    now = datetime.now(UTC)
    alerts = []
    result = {
        "at": now.isoformat(),
        "mode": "rehearsal",
        "alerts": alerts,
        "event_sink": "fsynced-local-spool",
        "remote_receivers": "UNASSESSED",
        "writes_enabled": data["allow_writes"],
    }
    engine = engine_for(data)
    try:
        if not database_ready(engine):
            raise RuntimeError("SchemaNotReady")
        queues = {}
        with engine.connect() as c:
            for name, model, states, age_column in [
                (
                    "payments",
                    PaymentIntent,
                    ["pending", "processing", "unknown"],
                    PaymentIntent.created_at,
                ),
                (
                    "financial",
                    FinancialOperation,
                    ["pending", "processing", "unknown"],
                    FinancialOperation.created_at,
                ),
                (
                    "events",
                    CommerceEventOutbox,
                    ["pending", "publishing"],
                    CommerceEventOutbox.occurred_at,
                ),
            ]:
                conditions = (
                    [model.state.in_(states)] if name != "events" else [model.status.in_(states)]
                )
                if name != "events":
                    conditions.append(
                        or_(model.next_attempt_at.is_(None), model.next_attempt_at <= now)
                    )
                conditions.append(or_(model.lease_until.is_(None), model.lease_until <= now))
                count, oldest = c.execute(
                    select(func.count(), func.min(age_column)).where(*conditions)
                ).one()
                age = (
                    0
                    if oldest is None
                    else max(
                        0,
                        (
                            now - (oldest.replace(tzinfo=UTC) if oldest.tzinfo is None else oldest)
                        ).total_seconds(),
                    )
                )
                queues[name] = {"due_count": count, "oldest_age_seconds": round(age, 3)}
                if count and age > data["backlog_seconds"]:
                    alerts.append(
                        {"code": name + "_backlog", "severity": "critical", "count": count}
                    )
            reviews = c.scalar(
                select(func.count())
                .select_from(PaymentReconciliation)
                .where(PaymentReconciliation.status == "open")
            )
            result["open_reviews"] = reviews
            result["notification_pending"] = c.scalar(
                select(func.count())
                .select_from(PaymentNotificationInbox)
                .where(PaymentNotificationInbox.state == "pending")
            )
            if reviews:
                alerts.append({"code": "financial_review", "severity": "warning", "count": reviews})
        result.update(database="ready", queues=queues)
    except Exception as exc:
        result.update(database="unavailable", queues=None, error_class=type(exc).__name__)
        alerts.append({"code": "database_unavailable", "severity": "critical"})
    finally:
        engine.dispose()
    state = Path(data["state_dir"])
    try:
        heartbeat = json.loads((state / "recovery.json").read_text())
        age = (now - datetime.fromisoformat(heartbeat["at"])).total_seconds()
        result["worker_age_seconds"] = round(age, 3)
        if data["allow_writes"] and heartbeat.get("database_id") != database_id(data):
            alerts.append({"code": "worker_wrong_database", "severity": "critical"})
        if data["allow_writes"] and (age < 0 or age > data["heartbeat_seconds"]):
            alerts.append({"code": "worker_stale", "severity": "critical"})
        if data["allow_writes"] and not all(s["ok"] for s in heartbeat["stages"].values()):
            alerts.append({"code": "worker_cycle_failed", "severity": "critical"})
    except (OSError, ValueError, KeyError, TypeError):
        result["worker_age_seconds"] = None
        if data["allow_writes"]:
            alerts.append({"code": "worker_missing", "severity": "critical"})
    try:
        backup = json.loads((state / "backup.json").read_text())
        age = (now - datetime.fromisoformat(backup["completed_at"])).total_seconds()
        result["backup_age_seconds"] = round(age, 3)
        if backup.get("database_id") != database_id(data):
            alerts.append({"code": "backup_wrong_database", "severity": "warning"})
        if age < 0 or age > data["backup_max_age_seconds"]:
            alerts.append({"code": "backup_stale", "severity": "warning"})
    except (OSError, ValueError, KeyError, TypeError):
        alerts.append({"code": "backup_missing", "severity": "warning"})
    return result


def monitor(data, once=False):
    state = Path(data["state_dir"])
    alerts_dir = private_dir(state / "alerts")
    lock = (state / "monitor.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    while True:
        current = snapshot(data)
        current["monitor_pid"] = os.getpid()
        try:
            previous = json.loads((state / "alert-state.json").read_text())
        except (OSError, ValueError):
            previous = []
        codes = sorted(a["code"] for a in current["alerts"])
        if codes != previous:
            receipt = {
                "at": current["at"],
                "opened": sorted(set(codes) - set(previous)),
                "resolved": sorted(set(previous) - set(codes)),
                "snapshot": current,
                "delivery": "local-durable-receipt-only",
            }
            write_json(alerts_dir / (str(time.time_ns()) + ".json"), receipt)
            write_json(state / "alert-state.json", codes)
        write_json(state / "status.json", current)
        if once:
            print(json.dumps(current))
            return 2 if current["alerts"] else 0
        time.sleep(data["interval_seconds"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["serve", "recover", "monitor"])
    p.add_argument("--config", required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--once", action="store_true")
    p.add_argument("--startup-fd", type=int, help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.startup_fd is not None:
        try:
            if os.read(args.startup_fd, 1) != b"1":
                return 1
        finally:
            os.close(args.startup_fd)
    data = config(args.config)
    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            application(data, args.release),
            host="127.0.0.1",
            port=args.port,
            access_log=False,
            log_level="warning",
        )
    elif args.command == "recover":
        recover(data, args.release, args.once)
    else:
        return monitor(data, args.once)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Config values/SQL/exception messages can contain credentials or customer data.
        print(json.dumps({"error_class": type(exc).__name__, "status": "failed"}), file=sys.stderr)
        raise SystemExit(1) from None
