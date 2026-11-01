"""M6 strict startup, durable event receipts, aggregate alerts and restore guards."""

import json
import sys
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory as factory
from test_payment_durability_m3 import request as order_request
from world_model.restaurant_commerce.events import CommerceEvent
from world_model.restaurant_commerce.models import CommerceEventOutbox, utcnow
from world_model.restaurant_commerce.service import RestaurantCommerceService

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deployment"))
import database
import runtime


def data(tmp_path):
    return {
        "mode": "rehearsal",
        "database_url": "postgresql+psycopg://test@127.0.0.1/test",
        "state_dir": str(tmp_path / "state"),
        "public_access_secret": "synthetic-signing-secret-not-for-production",
        "allow_writes": False,
        "interval_seconds": 1,
        "heartbeat_seconds": 5,
        "backlog_seconds": 10,
        "backup_max_age_seconds": 60,
    }


def config_file(tmp_path, **changes):
    value = {**data(tmp_path), **changes}
    p = tmp_path / "private.json"
    p.write_text(json.dumps(value))
    p.chmod(0o600)
    return p


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "prodution"},
        {"mode": "production"},
        {"database_url": "sqlite:///oops.db"},
        {"database_url": "postgresql+psycopg://test@remote/production"},
        {"public_access_secret": "short"},
        {"allow_writes": "false"},
        {"interval_seconds": 0},
        {"database_url": "postgresql+psycopg://test@127.0.0.1/test?options=anything"},
        {"unexpected_provider_key": "never-load-this"},
    ],
)
def test_configuration_fails_closed(tmp_path, change):
    with pytest.raises(ValueError):
        runtime.config(config_file(tmp_path, **change))
    assert not (tmp_path / "oops.db").exists()


def test_configuration_private_and_quarantine_default(tmp_path):
    p = config_file(tmp_path)
    value = json.loads(p.read_text())
    value.pop("allow_writes")
    p.write_text(json.dumps(value))
    assert runtime.config(p)["allow_writes"] is False
    p.chmod(0o644)
    with pytest.raises(ValueError):
        runtime.config(p)


def test_fsynced_event_receipts_deduplicate_and_reject_conflict(tmp_path):
    sink = runtime.FileEventSink(tmp_path / "events")
    event = CommerceEvent(
        "order.created",
        "synthetic",
        "entity",
        utcnow(),
        {"value": "synthetic"},
        event_id="stable-id",
    )
    sink.publish(event)
    sink.publish(event)
    assert len(list(sink.directory.iterdir())) == 1
    assert (sink.directory / "stable-id.json").stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError):
        sink.publish(replace(event, payload={"value": "conflict"}))
    with pytest.raises(ValueError):
        sink.publish(replace(event, event_id="../escape"))


def test_event_disk_failure_retains_outbox_until_real_receipt(factory, tmp_path, monkeypatch):
    sink = runtime.FileEventSink(tmp_path / "events")
    actual = runtime.tempfile.mkstemp
    monkeypatch.setattr(
        runtime.tempfile,
        "mkstemp",
        lambda **kw: (_ for _ in ()).throw(OSError("synthetic disk full")),
    )
    with factory() as session:
        service = RestaurantCommerceService(session, event_sink=sink)
        order = service.create_order("demo-restaurant-bogota", order_request(service))
        rows = list(session.scalars(select(CommerceEventOutbox)))
        assert rows and all(row.status == "pending" for row in rows)
        assert not list(sink.directory.iterdir())
        monkeypatch.setattr(runtime.tempfile, "mkstemp", actual)
        service.drain_event_outbox()
        session.expire_all()
        rows = list(session.scalars(select(CommerceEventOutbox)))
        assert all(row.status == "published" for row in rows)
        assert {p.stem for p in sink.directory.iterdir()} == {row.id for row in rows}
        assert service.order_out(order.id).id == order.id


def test_quarantine_and_no_implicit_database(factory, tmp_path, monkeypatch):
    with factory() as s:
        engine = s.get_bind()
    monkeypatch.setattr(runtime, "engine_for", lambda _: engine)
    value = runtime.config(config_file(tmp_path))
    with TestClient(runtime.application(value, "qualified-artifact")) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/deployment").json()["writes_enabled"] is False
        assert (
            client.post("/api/restaurants/demo-restaurant-bogota/orders", json={}).status_code
            == 503
        )
        assert client.post("/api/payments/simulated/anything/complete").status_code == 503
        assert (
            client.post(
                "/api/restaurants/demo-restaurant-bogota/orders/recover", json={}
            ).status_code
            == 422
        )
    assert not (tmp_path / "restaurant_commerce.db").exists()


def test_monitor_retains_open_and_resolved_receipts_without_pii(
    factory, tmp_path, monkeypatch, capsys
):
    with factory() as s:
        engine = s.get_bind()
        s.add(
            CommerceEventOutbox(
                id="alert-test",
                kind="private",
                business_id="private-tenant",
                entity_id="private-id",
                occurred_at=utcnow() - timedelta(seconds=60),
                payload_json='{"phone":"3001234567"}',
            )
        )
        s.commit()
    monkeypatch.setattr(runtime, "engine_for", lambda _: engine)
    value = runtime.config(config_file(tmp_path, allow_writes=True))
    assert runtime.monitor(value, once=True) == 2
    captured = capsys.readouterr().out
    assert "events_backlog" in captured and "worker_missing" in captured
    assert "3001234567" not in captured and "private-tenant" not in captured
    with factory() as s:
        row = s.get(CommerceEventOutbox, "alert-test")
        row.status = "published"
        s.commit()
    runtime.write_json(
        Path(value["state_dir"]) / "recovery.json",
        {
            "at": utcnow().isoformat(),
            "stages": {"events": {"ok": True}},
            "database_id": runtime.database_id(value),
        },
    )
    runtime.write_json(
        Path(value["state_dir"]) / "backup.json",
        {"completed_at": utcnow().isoformat(), "database_id": runtime.database_id(value)},
    )
    assert runtime.monitor(value, once=True) == 0
    receipts = [
        json.loads(p.read_text()) for p in (Path(value["state_dir"]) / "alerts").glob("*.json")
    ]
    assert len(receipts) == 2 and any("events_backlog" in r["resolved"] for r in receipts)


def test_unavailable_database_is_unknown_not_empty(tmp_path, monkeypatch):
    value = runtime.config(config_file(tmp_path))

    class Down:
        def connect(self):
            raise OSError("private-host/password-do-not-export")

        def dispose(self):
            pass

    monkeypatch.setattr(runtime, "engine_for", lambda _: Down())
    result = runtime.snapshot(value)
    assert result["database"] == "unavailable" and result["queues"] is None
    assert "password-do-not-export" not in json.dumps(result)
    assert "database_unavailable" in {a["code"] for a in result["alerts"]}


def test_restore_requires_quarantine_and_exact_target(tmp_path):
    value = runtime.config(config_file(tmp_path, allow_writes=True))
    with pytest.raises(ValueError, match="quarantine"):
        database.restore(value, tmp_path, "x", "test", True)
    value["allow_writes"] = False
    with pytest.raises(ValueError, match="confirmation"):
        database.restore(value, tmp_path, "x", "wrong", True)
    assert value["database_url"] not in json.dumps(database.pg_env(value))


def test_quarantine_rejects_provider_work_and_reports_process_identity(
    factory, tmp_path, monkeypatch
):
    import os

    with factory() as s:
        engine = s.get_bind()
    monkeypatch.setattr(runtime, "engine_for", lambda _: engine)
    value = runtime.config(config_file(tmp_path))
    with TestClient(runtime.application(value, "qualified-artifact")) as client:
        assert client.get("/deployment").json()["pid"] == os.getpid()
        response = client.post(
            "/api/restaurants/demo-restaurant-bogota/orders/recover",
            json={
                "idempotency_key": "existing",
                "recovery_secret": "a" * 64,
                "wompi_transaction_id": "12345-6789",
            },
        )
        assert response.status_code == 503


def test_database_name_cannot_override_libpq_destination(tmp_path):
    for name in ["host=remote", "postgresql:remote", "x%3Dhost", "a" * 64]:
        with pytest.raises(ValueError):
            runtime.config(
                config_file(tmp_path, database_url="postgresql+psycopg://test@127.0.0.1/" + name)
            )


def test_release_inventory_rejects_added_code_and_mutation(tmp_path):
    import importlib.util

    module_path = Path(__file__).resolve().parents[1] / "scripts/commerce_release.py"
    spec = importlib.util.spec_from_file_location("release_test", module_path)
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    site = runtime.private_dir(tmp_path / "site")
    bundle = runtime.private_dir(tmp_path / "bundle")
    (bundle / "app.py").write_text("# immutable\n")
    runtime.write_json(
        bundle / "manifest.json",
        {"format": 1, "files": {"app.py": release.digest(bundle / "app.py")}},
    )
    import shutil

    name = release.digest(bundle / "manifest.json")[:20]
    target = site / "releases" / name
    shutil.copytree(bundle, target)
    runtime.write_json(site / "receipts" / (name + ".json"), release.inventory(target))
    assert release.check_release(site, name) == target
    (target / "injected.pth").write_text("import bad\n")
    with pytest.raises(ValueError, match="tree changed"):
        release.check_release(site, name)
    (target / "injected.pth").unlink()
    (target / "installed-files.json").write_text("{}")
    with pytest.raises(ValueError, match="tree changed"):
        release.check_release(site, name)
    (target / "installed-files.json").unlink()
    (target / "app.py").write_text("# altered\n")
    with pytest.raises(ValueError):
        release.check_release(site, name)


def test_failed_activation_uses_saved_config_and_cleans_pending(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_test", Path(__file__).resolve().parents[1] / "scripts/commerce_release.py"
    )
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    site = runtime.private_dir(tmp_path / "site")
    config_path = config_file(tmp_path, allow_writes=True)
    monkeypatch.setattr(release, "check_release", lambda *_: site)
    stopped = []
    monkeypatch.setattr(release, "terminate", lambda record: stopped.append(record["release"]))
    launched = []

    def launch(site, name, path, port):
        value = runtime.config(path)
        launched.append((name, value["database_url"]))
        if name == "bad":
            raise RuntimeError("Candidate failure")
        record = {"release": name, "config": str(path), "port": port, "processes": []}
        runtime.write_json(site / "pending.json", record)
        return record

    monkeypatch.setattr(release, "launch", launch)
    release.activate(site, "old", config_path, 12345)
    original = runtime.config(config_path)["database_url"]
    runtime.write_json(
        config_path, {**data(tmp_path), "database_url": original.replace("/test", "/different")}
    )
    runtime.write_json(site / "pending.json", {"release": "interrupted", "processes": []})
    with pytest.raises(RuntimeError):
        release.activate(site, "bad", config_path, 12345)
    assert launched[-1] == ("old", original)
    assert "interrupted" in stopped
    assert not (site / "pending.json").exists()
    assert json.loads((site / "active.json").read_text())["release"] == "old"


def test_backup_and_worker_freshness_bound_to_database(factory, tmp_path, monkeypatch):
    with factory() as s:
        engine = s.get_bind()
    monkeypatch.setattr(runtime, "engine_for", lambda _: engine)
    value = runtime.config(config_file(tmp_path, allow_writes=True))
    state = Path(value["state_dir"])
    runtime.write_json(
        state / "backup.json", {"completed_at": runtime.utc(), "database_id": "other"}
    )
    runtime.write_json(
        state / "recovery.json",
        {"at": runtime.utc(), "database_id": "other", "stages": {"events": {"ok": True}}},
    )
    codes = {a["code"] for a in runtime.snapshot(value)["alerts"]}
    assert {"backup_wrong_database", "worker_wrong_database"} <= codes


def test_bundle_extras_rejected_before_install(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_test", Path(__file__).resolve().parents[1] / "scripts/commerce_release.py"
    )
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    bundle = runtime.private_dir(tmp_path / "bundle")
    runtime.write_json(bundle / "manifest.json", {"format": 1, "files": {}})
    sha = release.digest(bundle / "manifest.json")
    assert release.verify(bundle, sha, bundle_only=True)
    (bundle / "venv").mkdir()
    with pytest.raises(ValueError):
        release.verify(bundle, sha, bundle_only=True)
    (bundle / "venv" / "injected.pth").write_text("import bad\n")
    with pytest.raises(ValueError):
        release.install(bundle, sha, tmp_path / "site")
    assert not (tmp_path / "site").exists()
