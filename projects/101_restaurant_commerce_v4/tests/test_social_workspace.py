"""Social joins the normal workspace DB, login and membership boundary."""

import io
import os
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from test_social_production import approval, brief, photo
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.db import init_schema, make_engine
from world_model.restaurant_commerce.models import StaffMembership
from world_model.restaurant_commerce.social_migrations import (
    schema_ready,
    social_tables,
    upgrade_social,
)
from world_model.restaurant_commerce.workspace_demo import app_for_demo

ROOT = "/api/operator/restaurants/" + BUSINESS


def login(client):
    response = client.post(
        "/api/staff/login",
        json={"username": "101", "password": "101"},
        headers={"X-101-Login": "1"},
    )
    assert response.status_code == 200, response.text
    return {"X-101-CSRF": client.get("/api/staff/me").json()["csrf"]}


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
def test_existing_workspace_upgrade_restart_and_revocation(tmp_path, backend):
    url = "sqlite:///" + str(tmp_path / "shared.db")
    if backend == "postgres":
        url = os.environ.get("SOCIAL_TEST_DISPOSABLE_POSTGRES_URL")
        if not url:
            pytest.skip("Explicitly disposable PostgreSQL required; test drops social tables")
    app = app_for_demo(url, size=8)
    engine = app.state.engine
    # Rehearse an installation predating social, preserving its contacts/campaigns.
    for table in reversed(social_tables()):
        table.drop(engine)
    with TestClient(app) as client:
        headers = login(client)
        before = client.get(ROOT + "/customers").json()["total"]
        assert before >= 8
        assert client.get(ROOT + "/social").status_code == 503
        assert client.get(ROOT.replace(BUSINESS, OTHER) + "/social").status_code == 403
    upgrade_social(engine)
    upgrade_social(engine)
    assert schema_ready(engine)
    with TestClient(app) as client:
        headers = login(client)
        env = SimpleNamespace(client=client, headers=headers)
        asset = photo(env).json()["id"]
        response = client.post(ROOT + "/social/packs", json=brief(asset), headers=headers)
        assert response.status_code == 200, response.text
        pack = response.json()
        assert approval(env, pack).status_code == 200
        assert client.get(ROOT + "/customers").json()["total"] == before
        assert client.get(ROOT + "/campaigns").status_code == 200
        cookies = dict(client.cookies)
    engine.dispose()
    # A new process/app composition can consume the saved pack with the SAME session.
    restarted = create_app(database_url=url, payment_recovery_enabled=False)
    with TestClient(restarted) as client:
        client.cookies.update(cookies)
        assert client.get("/api/staff/me").status_code == 200
        route = ROOT + "/social/packs/" + pack["id"]
        assert client.get(route).json()["approved"]
        exported = client.get(route + "/export")
        assert exported.status_code == 200
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            assert archive.read("caption.txt").decode() == "Fotografía de prueba."
        with restarted.state.session_factory.begin() as session:
            member = session.scalar(
                select(StaffMembership).where(StaffMembership.business_id == BUSINESS)
            )
            session.delete(member)
        assert client.get(route + "/export").status_code == 403
        assert client.get(ROOT + "/customers").status_code == 403
    restarted.state.engine.dispose()


def test_social_not_auto_migrated_into_existing_database(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "existing.db"))
    init_schema(engine)
    for table in reversed(social_tables()):
        table.drop(engine)
    init_schema(engine)
    assert not schema_ready(engine)
    assert not any(t.name in inspect(engine).get_table_names() for t in social_tables())
    upgrade_social(engine)
    assert schema_ready(engine)
    engine.dispose()


def test_upgrade_rejects_incomplete_schema_without_mutating_other_tables(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "broken.db"))
    init_schema(engine)
    for table in reversed(social_tables()):
        table.drop(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE social_assets (id TEXT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="Incomplete social schema"):
        upgrade_social(engine)
    assert "social_packs" not in inspect(engine).get_table_names()
    engine.dispose()
