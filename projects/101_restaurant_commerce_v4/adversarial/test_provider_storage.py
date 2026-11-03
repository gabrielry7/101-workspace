"""Provider inspection must not stall writes or duplicate replay effects."""

import importlib.util
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


@pytest.fixture
def provider(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"run_dir": str(tmp_path)}))
    monkeypatch.setenv("COMMERCE_TEST_CONFIG", str(config))
    spec = importlib.util.spec_from_file_location(
        "isolated_test_provider", Path(__file__).with_name("provider.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inspecting_provider_ledger_does_not_block_checkout_commit(provider):
    body = dict(
        order_id="synthetic-reader-order",
        idempotency_key="synthetic-reader-key",
        amount_minor=11900,
        currency="COP",
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        reader = sqlite3.connect(provider.db)
        try:
            reader.execute("BEGIN")
            reader.execute("SELECT COUNT(*) FROM effects").fetchone()
            result = pool.submit(provider.checkout, body).result(timeout=2)
            assert result["provider_reference"] == "sim_synthetic-reader-order"
        finally:
            reader.rollback()
            reader.close()
    with sqlite3.connect(provider.db) as check:
        assert check.execute("SELECT COUNT(*) FROM effects").fetchone()[0] == 1


def test_concurrent_provider_replays_keep_one_effect(provider):
    body = dict(
        order_id="synthetic-race-order",
        idempotency_key="synthetic-race-key",
        amount_minor=11900,
        currency="COP",
    )
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(provider.checkout, [body] * 20))
    assert all(result == results[0] for result in results)
    with sqlite3.connect(provider.db) as check:
        assert check.execute("SELECT COUNT(*) FROM effects").fetchone()[0] == 1
