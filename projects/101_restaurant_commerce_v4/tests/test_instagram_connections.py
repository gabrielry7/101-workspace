"""Mock-transport qualification; never live account evidence."""
import json
from datetime import timedelta
from urllib.parse import urlsplit,parse_qs
import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory
from world_model.restaurant_commerce import connections as c
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo,BUSINESS,OTHER,PASSWORD,CLOCK
from world_model.restaurant_commerce.connection_instagram import InstagramAdapter
from world_model.restaurant_commerce.connection_google import FakeGoogleBusinessAdapter
from world_model.restaurant_commerce.connection_models import BusinessConnection

ROOT='/api/operator/restaurants/'+BUSINESS+'/social/instagram'
class FixtureInstagram(InstagramAdapter):mode='test'

@pytest.fixture
def env(factory):
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        path=request.url.path
        if path=='/oauth/access_token':return httpx.Response(200,json={'access_token':'fixture-private-token','user_id':'123','expires_in':3600})
        assert request.headers['authorization']=='Bearer fixture-private-token'
        if path.endswith('/123'):return httpx.Response(200,json={'user_id':'123','username':'fixture_honorato'})
        if path.endswith('/123/media'):return httpx.Response(200,json={'data':[{'id':'789','caption':'Historical test caption','media_type':'IMAGE','timestamp':'2026-11-01T18:37:12-0500'},{'id':'790','media_type':'VIDEO','timestamp':'2026-11-02'}]})
        if path.endswith('/789'):return httpx.Response(200,json={'like_count':0,'comments_count':4})
        if path.endswith('/790'):return httpx.Response(403,json={'error':{'code':10,'message':'private provider text'}})
        raise AssertionError(path)
    runtime=c.ConnectionRuntime(FixtureInstagram('1234','fixture-secret','https://101.example/connections/instagram/callback','v23.0',transport=httpx.MockTransport(handler)),Fernet.generate_key(),clock=lambda:CLOCK,worker=False)
    google=c.ConnectionRuntime(FakeGoogleBusinessAdapter(),Fernet.generate_key(),clock=lambda:CLOCK,worker=False)
    with factory() as s:seed_campaign_demo(s)
    app=create_app(engine=factory.kw['bind'],demo_mode=True,payment_recovery_enabled=False,instagram_runtime=runtime,connections_runtime=google)
    with TestClient(app) as client:
        client.post('/api/staff/login',json={'username':'campaign.manager','password':PASSWORD},headers={'X-101-Login':'1'})
        headers={'X-101-CSRF':client.get('/api/staff/me').json()['csrf']}
        yield client,headers,runtime,google,factory,calls

def connect(env):
    client,h,runtime,google,factory,calls=env
    result=client.post(ROOT+'/authorize',headers=h)
    assert result.status_code==200,result.text
    state=parse_qs(urlsplit(result.json()['url']).query)['state'][0]
    result=client.post('/connections/instagram/complete',headers=h,json={'state':state,'code':'fixture-code'})
    assert result.status_code==200,result.text
    assert not c.dispatch_one(factory,google) # no cross-provider job consumption
    assert c.dispatch_one(factory,runtime)
    assert client.get(ROOT).json()['state']=='choose_location'
    assert client.post(ROOT+'/select',headers=h,json={'account_id':'999'}).status_code==403
    assert client.post(ROOT+'/select',headers=h,json={'account_id':'123'}).status_code==200
    assert c.dispatch_one(factory,runtime)
    return state

def test_read_import_zero_unknown_and_disconnect(env):
    client,h,runtime,google,factory,calls=env
    state=connect(env)
    data=client.get(ROOT).json()
    assert data['state']=='partial' and data['verification']=='fixture'
    posts=data['snapshot']['posts']
    assert posts[0]['metrics']['likes']['value']==0
    assert posts[1]['metrics']['likes']['value'] is None
    assert posts[1]['metrics']['likes']['reason']=='permission_or_field_unavailable'
    assert posts[0]['published_at_utc']=='2026-11-01T23:37:12+00:00'
    assert posts[1]['timestamp_precision']=='day'
    assert 'fixture-private-token' not in json.dumps(data)
    assert all('fixture-private-token' not in url for url in calls)
    with factory() as s:
        row=s.scalar(select(BusinessConnection).where(BusinessConnection.provider=='instagram'))
        assert 'fixture-private-token' not in row.secret
    assert client.post('/connections/instagram/complete',headers=h,json={'state':state,'code':'again'}).status_code==400
    assert client.post(ROOT+'/disconnect',headers=h).status_code==200
    assert client.get(ROOT).json()['snapshot'] is None
    c.dispatch_one(factory,runtime)
    assert client.get(ROOT).json()['error']=='revoke_in_instagram_settings'

def test_denial_tenant_csrf_and_provider_binding(env):
    client,h,runtime,google,factory,calls=env
    assert client.get(ROOT.replace(BUSINESS,OTHER)).status_code==403
    assert client.post(ROOT+'/authorize').status_code==403
    state=parse_qs(urlsplit(client.post(ROOT+'/authorize',headers=h).json()['url']).query)['state'][0]
    wrong=client.post('/connections/google/complete',headers=h,json={'state':state,'code':'fixture-code'})
    assert wrong.status_code==409
    denied=client.post('/connections/instagram/complete',headers=h,json={'state':state,'error':'access_denied'})
    assert denied.status_code==200
    assert client.get(ROOT).json()['state']=='access_denied'
    assert not calls

def test_pagination_budget_and_untrusted_next_url():
    calls=[]
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('/media'):
            page=1 if request.url.params.get('after') else 0
            return httpx.Response(200,json={'data':[{'id':str(100+page*20+i),'media_type':'IMAGE'} for i in range(20)],'paging':{'next':'https://malicious.invalid/steal','cursors':{'after':'next-cursor'}}})
        return httpx.Response(200,json={'like_count':1})
    adapter=InstagramAdapter('id','secret','https://101.example/callback','v23.0',transport=httpx.MockTransport(handler))
    result=adapter.snapshot({'user_id':'123','access_token':'private'},'123',CLOCK)
    assert result['coverage']=={'posts':40,'requests':7,'maximum_requests':7,'has_more':True,'history':'bounded_current_window'}
    assert len(calls)==7 and all(r.url.host=='graph.instagram.com' for r in calls)
    assert result['posts'][0]['metrics']['comments']['value'] is None
    assert result['posts'][5]['metrics']['likes']['reason']=='outside_probe_limit'


def test_expired_authorization_and_no_cached_snapshot_after_expiry(env):
    client,h,runtime,google,factory,calls=env
    connect(env)
    runtime.clock=lambda:CLOCK+timedelta(hours=2)
    assert client.get(ROOT).json()['state']=='reconnect_required'
    runtime.clock=lambda:CLOCK+timedelta(days=2)
    assert client.get(ROOT).json()['snapshot'] is None
