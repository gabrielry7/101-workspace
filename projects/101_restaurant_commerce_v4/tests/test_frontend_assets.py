from fastapi.testclient import TestClient
import pytest
from world_model.restaurant_commerce.api import create_app


def test_scripts_are_served_with_strict_policy(tmp_path):
    app=create_app(database_url=f'sqlite:///{tmp_path / "assets.db"}')
    with TestClient(app) as c:
        for route in ['/','/admin','/delivery','/growth']:
            r=c.get(route)
            assert r.status_code==200
            policy=r.headers['content-security-policy']
            assert "script-src 'self';" in policy
            assert "script-src-attr 'none'" in policy
            assert "base-uri 'none'" in policy
            assert 'onclick=' not in r.text and 'oninput=' not in r.text
            assert '<script>' not in r.text
        for script in ['shared','index','admin','delivery','growth']:
            r=c.get('/assets/'+script+'.js')
            assert r.status_code==200
            assert r.headers['content-type'].startswith('text/javascript')
            assert r.headers['cache-control']=='no-cache'
            assert 'innerHTML' not in r.text and 'insertAdjacentHTML' not in r.text
        assert c.get('/assets/api.py').status_code==404
        assert c.get('/api/browser-policy').json()['checkout_origins']==[]


@pytest.mark.parametrize('origin',['http://example.test','https://user:pass@example.test','https://example.test/path',
                                   'https://example.test?x=1','https://example.test#x','https://example.test\\evil','https://example.test:bad'])
def test_invalid_browser_origins_fail_startup(origin):
    with pytest.raises(ValueError): create_app(checkout_url_origins=(origin,))


def test_body_replay_preserves_disconnect():
    import asyncio
    from world_model.restaurant_commerce.security import MaxBodySizeMiddleware
    received=[]
    async def run():
        incoming=iter([{'type':'http.request','body':b'hello','more_body':False}, {'type':'http.disconnect'}])
        async def receive(): return next(incoming)
        async def send(message): pass
        async def app(scope,receive,send):
            received.append(await receive())
            received.append(await receive())
        await MaxBodySizeMiddleware(app)({'type':'http','headers':[]},receive,send)
    asyncio.run(run())
    assert received==[{'type':'http.request','body':b'hello','more_body':False},{'type':'http.disconnect'}]
