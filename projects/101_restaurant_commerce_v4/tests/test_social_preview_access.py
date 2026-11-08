import json
import pytest
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient
from world_model.restaurant_commerce.social_preview_access import PreviewAccess


def client(tmp_path):
    path = tmp_path / 'access.json'
    path.write_text(json.dumps({'password': 'fixture-password-at-least-24-characters'}))
    path.chmod(0o600)
    async def endpoint(request):
        response = Response('private output', headers={'Cache-Control': 'public, max-age=3600'})
        response.set_cookie('session', 'fixture', httponly=True)
        return response
    return TestClient(PreviewAccess(Starlette(routes=[Route('/private', endpoint)]), path)), path


def test_gate_covers_downloads_and_rejects_demo_password(tmp_path):
    c, _ = client(tmp_path)
    for auth in [None, ('101', '101'), ('wrong', 'fixture-password-at-least-24-characters')]:
        response = c.get('/private', auth=auth)
        assert response.status_code == 401
        assert response.headers['cache-control'] == 'no-store'
        assert 'private output' not in response.text


def test_success_keeps_private_cookie_and_cache_boundaries(tmp_path):
    c, _ = client(tmp_path)
    auth = ('101', 'fixture-password-at-least-24-characters')
    response = c.get('/private', auth=auth)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-robots-tag'] == 'noindex, nofollow'
    assert 'Secure' in response.headers['set-cookie']
    assert c.get('/', auth=auth, follow_redirects=False).headers['location'] == '/workspace/social'


def test_gate_fails_closed_for_exposed_file_or_weak_password(tmp_path):
    _, path = client(tmp_path)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        PreviewAccess(None, path)
    path.chmod(0o600)
    path.write_text(json.dumps({'password': '101'}))
    with pytest.raises(ValueError):
        PreviewAccess(None, path)
