"""Server environment, not demo data or browser preferences, exposes internal tools."""
import pytest
from fastapi.testclient import TestClient
from world_model.restaurant_commerce.api import create_app


@pytest.mark.parametrize("environment,demo,internal", [
    ("development", True, False), ("development", False, False),
    ("internal", True, True), ("internal", False, True),
    ("production", False, False),
])
def test_internal_policy_and_direct_route(tmp_path, environment, demo, internal):
    app = create_app(database_url=f"sqlite:///{tmp_path / 'policy.db'}",
                     environment=environment, demo_mode=demo,
                     public_access_secret="synthetic-test-only-secret-at-least-32-characters")
    with TestClient(app) as client:
        policy = client.get("/api/browser-policy").json()
        assert policy["demo_mode"] is demo
        assert policy["internal_tools"] is internal
        response = client.get("/workspace/identity?pairing=lime&internal_tools=true")
        assert response.status_code == (200 if internal else 404)
        assert client.get("/workspace/home").status_code == 200
