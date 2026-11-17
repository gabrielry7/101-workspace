"""Fixture-only integration of the credential owner and evidence adapter."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from test_instagram_connections import connect
from test_instagram_connections import env as env
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce import connections as c
from world_model.restaurant_commerce.campaign_demo import BUSINESS, CLOCK
from world_model.restaurant_commerce.connection_google import ConnectionFailure
from world_model.restaurant_commerce.connection_instagram_evidence import EvidenceClient


def worker(env, tmp_path, permission=None):
    connect(env)
    _, _, runtime, _, factory, _ = env
    with factory() as session:
        row = c.find(session, BUSINESS, runtime)
        generation = row.generation
    checks = []

    def allow(session, business, permission):
        checks.append((business, permission))
        if business != BUSINESS:
            raise HTTPException(403, "wrong business")

    client = EvidenceClient(
        factory,
        runtime,
        business_id=BUSINESS,
        account_id="123",
        generation=generation,
        permission=permission or allow,
        state_path=tmp_path / "scope.json",
    )
    return client, checks


def test_scope_permission_and_metadata_without_credentials(env, tmp_path):
    client, checks = worker(env, tmp_path)
    assert client.authorize()["business_id"] == BUSINESS
    result = client.get("123/media", {"fields": "id,caption", "limit": 100})
    assert result["data"][0]["caption"] == "Historical test caption"
    assert checks and all(p == "settings.write" for _, p in checks)
    assert "fixture-private-token" not in (tmp_path / "scope.json").read_text()
    restarted = EvidenceClient(
        client.factory,
        client.runtime,
        business_id=BUSINESS,
        account_id="123",
        generation=client.generation,
        permission=client.permission,
        state_path=tmp_path / "scope.json",
    )
    assert "789" in restarted.allowed_media
    with pytest.raises(ConnectionFailure):
        client.get("999/children", {"fields": "id"})


def test_disconnect_and_permission_loss_stop_worker(env, tmp_path):
    client, _ = worker(env, tmp_path)
    with client.factory() as session:
        c.disconnect(session, BUSINESS, client.runtime)
        session.commit()
    with pytest.raises(ConnectionFailure):
        client.authorize()
    client.permission = lambda *args: (_ for _ in ()).throw(HTTPException(403, "revoked"))
    with pytest.raises(HTTPException):
        client.authorize()


def test_expiry_never_claims_refresh_success(env, tmp_path):
    from datetime import timedelta

    client, _ = worker(env, tmp_path)
    client.runtime.clock = lambda: CLOCK + timedelta(hours=2)
    with pytest.raises(ConnectionFailure) as failure:
        client.authorize()
    assert failure.value.reason == "reconnect_required"


def test_live_worker_requires_explicit_enablement(env, tmp_path):
    client, _ = worker(env, tmp_path)
    client.runtime.mode = "live"
    with pytest.raises(ConnectionFailure):
        EvidenceClient(
            client.factory,
            client.runtime,
            business_id=BUSINESS,
            account_id="123",
            generation=client.generation,
            permission=client.permission,
        )


def test_real_root_adapter_consumes_worker(env, tmp_path):
    import world_model

    root = Path("/home/t/101-world-model/src/world_model")
    if str(root) not in world_model.__path__:
        world_model.__path__.append(str(root))
    from world_model.business_evidence.official import OfficialAdapter

    client, _ = worker(env, tmp_path)
    adapter = OfficialAdapter(
        client, business_id=BUSINESS, account_id="123", generation=client.generation
    )
    account, _ = adapter.resolve("fixture_honorato")
    assert account.id == "123" and account.biography is None
    stream = adapter.stream(None, "posts")
    item = next(stream)
    post = adapter.normalize(item)
    assert post.id == "789" and post.caption == "Historical test caption"
    assert post.assets[0].url is None


def test_long_lived_exchange_refresh_and_expiry_contract():
    from datetime import timedelta

    from world_model.restaurant_commerce.connection_instagram_evidence import refresh_evidence_token

    class Adapter:
        client_secret = "fixture-secret"

        def __init__(self):
            self.calls = []

        def request(self, method, path, **kw):
            self.calls.append((method, path, kw))
            return dict(access_token="fixture-long-token", expires_in=5184000)

    a = Adapter()
    short = dict(
        access_token="fixture-short-token",
        user_id="123",
        expires_at=(CLOCK + timedelta(hours=1)).isoformat(),
    )
    long = refresh_evidence_token(a, short, CLOCK)
    assert a.calls[0][1] == "/access_token"
    assert long["evidence_token_kind"] == "long_lived"
    assert refresh_evidence_token(a, long, CLOCK + timedelta(days=1)) == long
    assert len(a.calls) == 1
    renewed = refresh_evidence_token(a, long, CLOCK + timedelta(days=55))
    assert a.calls[-1][1] == "/refresh_access_token"
    assert renewed["expires_at"] != long["expires_at"]
    with pytest.raises(ConnectionFailure):
        refresh_evidence_token(a, long, CLOCK + timedelta(days=61))
    assert len(a.calls) == 2


def test_worker_runs_real_pipeline_without_dashboard_snapshot_changes(env, tmp_path):
    import shutil

    import httpx

    import world_model

    root = Path("/home/t/101-world-model")
    if str(root / "src/world_model") not in world_model.__path__:
        world_model.__path__.append(str(root / "src/world_model"))
    from world_model.restaurant_commerce.connection_instagram_evidence import run_import

    from world_model.business_evidence.config import Config, Instagram
    from world_model.business_evidence.state import Runs
    from world_model.instagram_evidence.analysis.contracts import AnalysisConfig

    client, _ = worker(env, tmp_path)
    with client.factory() as session:
        before = c.find(session, BUSINESS, client.runtime).snapshot

    def handler(request):
        if request.url.path == "/access_token":
            return httpx.Response(
                200, json=dict(access_token="fixture-long-token", expires_in=5184000)
            )
        assert request.headers["authorization"] == "Bearer fixture-long-token"
        if request.url.path.endswith("/123"):
            return httpx.Response(200, json=dict(id="123", username="fixture_honorato"))
        if request.url.path.endswith("/123/media"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        dict(
                            id="789",
                            media_type="IMAGE",
                            media_url="https://scontent.cdninstagram.com/fixture.png",
                            caption="Fixture caption",
                        )
                    ]
                },
            )
        raise AssertionError(request.url.path)

    client.runtime.adapter.transport = httpx.MockTransport(handler)

    def download(url, path):
        shutil.copyfile(root / "tests/fixtures/instagram_exporter/source/image.png", path)
        return "image/png"

    config = Config(
        business_id=BUSINESS,
        label="Official fixture",
        profile="cloud",
        analysis=AnalysisConfig(),
        instagram=Instagram(
            route="official",
            mode="collect",
            archive=tmp_path / "archive",
            username="fixture_honorato",
            account_id="123",
        ),
    )
    runs = Runs(tmp_path / "runs")
    try:
        result = run_import(
            client.factory,
            client.runtime,
            config=config,
            runs=runs,
            permission=client.permission,
            downloader=download,
        )
        assert result["steps"]["instagram.collect"]["state"] == "complete", result["steps"]
        assert result["steps"]["instagram.analysis"]["result"]["states"] == {
            "ready": 2,
            "blocked": 1,
        }
        with client.factory() as session:
            assert c.find(session, BUSINESS, client.runtime).snapshot == before
    finally:
        runs.close()
