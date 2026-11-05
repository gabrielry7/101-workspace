"""Local owner journey and consequential connection lifecycle boundaries."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_payment_durability_m3 import factory
from world_model.restaurant_commerce import connections as c
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo, BUSINESS, OTHER, CLOCK, PASSWORD
from world_model.restaurant_commerce.connection_google import FakeGoogleBusinessAdapter, GoogleBusinessAdapter, ConnectionFailure, SCOPE
from world_model.restaurant_commerce.connection_models import BusinessConnection, ConnectionAuthorization, ConnectionJob, TABLES, upgrade_connections
from world_model.restaurant_commerce.models import StaffMembership

ROOT='/api/operator/restaurants/'+BUSINESS+'/connections'


@pytest.fixture
def env(factory):
    now=[CLOCK]
    runtime=c.ConnectionRuntime(FakeGoogleBusinessAdapter(),Fernet.generate_key(),clock=lambda:now[0],worker=False)
    app=create_app(engine=factory.kw['bind'],demo_mode=True,payment_recovery_enabled=False,connections_runtime=runtime)
    with factory() as s: seed_campaign_demo(s)
    with TestClient(app) as client:
        r=client.post('/api/staff/login',json={'username':'campaign.manager','password':PASSWORD},headers={'X-101-Login':'1'})
        assert r.status_code==200,r.text
        headers={'X-101-CSRF':client.get('/api/staff/me').json()['csrf']}
        yield SimpleNamespace(client=client,runtime=runtime,factory=factory,now=now,headers=headers,app=app)


def post(e,path,**kwargs):
    return e.client.post(ROOT+'/google/'+path,headers=e.headers,**kwargs)


def authorize(e):
    r=post(e,'authorize');assert r.status_code==200,r.text
    return parse_qs(urlsplit(r.json()['url']).query)['state'][0]


def callback(e,state,**kwargs):
    return e.client.post('/connections/google/complete',json={'state':state,**kwargs},headers=e.headers)


def connected(e):
    state=authorize(e)
    assert callback(e,state,code='synthetic-owner-grant').status_code==200
    assert c.dispatch_one(e.factory,e.runtime)
    data=e.client.get(ROOT).json()['google'];assert data['state']=='choose_location'
    assert post(e,'select',json={'location':data['assets'][0]['key']}).status_code==200
    assert c.dispatch_one(e.factory,e.runtime)
    return e.client.get(ROOT).json()['google']


def test_owner_journey_cache_and_disconnect(env):
    data=connected(env)
    assert data['state']=='connected' and data['mode']=='test'
    assert data['snapshot']['sections']['metrics']['multiDailyMetricTimeSeries'][0]['dailyMetricTimeSeries'][0]['timeSeries']['datedValues'][0]['value']=='12'
    assert 'secret' not in data and 'synthetic-access' not in json.dumps(data)
    with env.factory() as s:
        row=s.scalar(select(BusinessConnection));assert 'synthetic-access' not in row.secret
    assert post(env,'disconnect').status_code==200
    data=env.client.get(ROOT).json()['google'];assert not data['snapshot'] and not data['assets']
    c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['state']=='disconnected'
    with env.factory() as s:
        assert s.scalar(select(ConnectionJob)).secret is None


def test_scope_csrf_and_unknown_location(env):
    assert env.client.get(ROOT.replace(BUSINESS,OTHER)).status_code==403
    assert env.client.post(ROOT+'/google/authorize').status_code==403
    connected(env)
    assert post(env,'select',json={'location':'accounts/888/locations/999'}).status_code==403
    assert env.client.post(ROOT.replace(BUSINESS,OTHER)+'/google/disconnect',headers=env.headers).status_code==403
    assert env.client.get(ROOT.replace(BUSINESS,OTHER)).status_code==403


def test_authorization_session_binding_replay_and_tampering(env):
    state=authorize(env)
    with TestClient(env.app) as other:
        other.post('/api/staff/login',json={'username':'campaign.manager','password':PASSWORD},headers={'X-101-Login':'1'})
        assert other.post('/connections/google/complete',json={'state':state,'code':'synthetic-owner-grant'},headers={'X-101-CSRF':other.get('/api/staff/me').json()['csrf']}).status_code==400
    assert callback(env,state+'x',code='synthetic-owner-grant').status_code==400
    assert callback(env,state,code='synthetic-owner-grant').status_code==200
    assert callback(env,state,code='synthetic-owner-grant').status_code==400


def test_denied_expired_and_removed_membership(env):
    state=authorize(env);assert callback(env,state,error='access_denied').status_code==200
    assert env.client.get(ROOT).json()['google']['state']=='access_denied'
    state=authorize(env);env.now[0]+=timedelta(minutes=11)
    assert callback(env,state,code='synthetic-owner-grant').status_code==400
    state=authorize(env)
    with env.factory() as s:
        membership=s.scalar(select(StaffMembership).where(StaffMembership.business_id==BUSINESS,StaffMembership.role=='manager'))
        s.delete(membership);s.commit()
    assert callback(env,state,code='synthetic-owner-grant').status_code==403


def test_reconnect_supersedes_old_state(env):
    a,b=authorize(env),authorize(env)
    assert callback(env,a,code='synthetic-owner-grant').status_code==400
    assert callback(env,b,code='synthetic-owner-grant').status_code==200


def test_concurrent_workers_one_claim_and_restart(env):
    state=authorize(env);callback(env,state,code='synthetic-owner-grant')
    calls=[];original=env.runtime.adapter.discover
    def discover(tokens):
        calls.append(1);return original(tokens)
    env.runtime.adapter.discover=discover
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _:c.dispatch_one(env.factory,env.runtime),range(2)))
    assert len(calls)==1
    data=env.client.get(ROOT).json()['google'];post(env,'select',json={'location':data['assets'][0]['key']})
    with env.factory() as s:
        job=s.scalar(select(ConnectionJob));job.state='running';job.lease='crashed-worker';job.lease_until=env.now[0]+timedelta(seconds=5);s.commit()
    assert not c.dispatch_one(env.factory,env.runtime)
    env.now[0]+=timedelta(seconds=6)
    restarted=c.ConnectionRuntime(env.runtime.adapter,Fernet.generate_key(),worker=False)
    # Simulate a new process reading the same durable job and persisted key.
    restarted.cipher=env.runtime.cipher;restarted.clock=env.runtime.clock
    assert c.dispatch_one(env.factory,restarted)
    assert env.client.get(ROOT).json()['google']['state']=='connected'


def test_disconnect_during_provider_read_cannot_restore_data(env):
    state=authorize(env);callback(env,state,code='synthetic-owner-grant')
    original=env.runtime.adapter.discover
    def discover(tokens):
        assert post(env,'disconnect').status_code==200
        return original(tokens)
    env.runtime.adapter.discover=discover
    c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['assets']==[]
    assert env.client.get(ROOT).json()['google']['state']=='disconnecting'
    c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['state']=='disconnected'


def test_retries_bounded_and_not_a_success(env):
    state=authorize(env);callback(env,state,code='synthetic-owner-grant')
    def failure(tokens):raise ConnectionFailure('provider_network_error',retry=True)
    env.runtime.adapter.discover=failure
    for _ in range(3):
        assert c.dispatch_one(env.factory,env.runtime)
        env.now[0]+=timedelta(minutes=2)
    assert not c.dispatch_one(env.factory,env.runtime)
    data=env.client.get(ROOT).json()['google'];assert data['state']=='sync_error' and data['job']['attempts']==3
    assert not data['snapshot']


def test_expired_content_hidden_and_purged(env):
    connected(env);env.now[0]+=timedelta(days=2)
    data=env.client.get(ROOT).json()['google'];assert data['snapshot'] is None and data['assets']==[]
    with env.factory() as s:
        c.maintenance(s,env.runtime)
        row=s.scalar(select(BusinessConnection));assert row.snapshot is None and row.assets is None
    c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['snapshot']


def test_partial_metrics_not_zero_and_reconnect_error(env):
    original=env.runtime.adapter.snapshot
    def snapshot(*args):
        data=original(*args);del data['sections']['metrics'];data['errors']['metrics']='provider_access_denied';return data
    env.runtime.adapter.snapshot=snapshot
    data=connected(env);assert data['state']=='partial' and 'metrics' not in data['snapshot']['sections']
    env.now[0]+=timedelta(minutes=2)
    def failure(*args):raise ConnectionFailure('reconnect_required')
    env.runtime.adapter.refresh=failure
    post(env,'refresh');c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['state']=='reconnect_required'


def test_disconnected_job_never_discovers_and_unconfigured_rejects(env):
    state=authorize(env);callback(env,state,code='synthetic-owner-grant');post(env,'disconnect')
    env.runtime.adapter.discover=lambda _:pytest.fail('disconnected job ran')
    c.dispatch_one(env.factory,env.runtime)
    app=create_app(engine=env.factory.kw['bind'],payment_recovery_enabled=False)
    with TestClient(app) as client:
        client.cookies.update(env.client.cookies)
        assert client.get(ROOT).json()['google']['state']=='unconfigured'
        assert client.post(ROOT+'/google/authorize',headers=env.headers).status_code==409
        assert client.get('/connections/demo-authorize').status_code==404


def test_permission_removed_before_callback_and_duplicate_parameters(env):
    state=authorize(env)
    response=env.client.get('/connections/google/callback',params=[('state',state),('state','wrong'),('code','synthetic-owner-grant')])
    assert response.status_code==400
    assert callback(env,state,code='synthetic-owner-grant',error='access_denied').status_code==400


def test_offline_migration_required_and_idempotent(factory):
    engine=factory.kw['bind']
    from world_model.restaurant_commerce.models import Base
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in TABLES:table.drop(connection)
    runtime=c.ConnectionRuntime(FakeGoogleBusinessAdapter(),Fernet.generate_key(),worker=False)
    with pytest.raises(RuntimeError,match='upgrade-connections'):
        create_app(engine=engine,connections_runtime=runtime)
    upgrade_connections(engine);upgrade_connections(engine)
    create_app(engine=engine,connections_runtime=runtime)


def test_simulator_forbidden_outside_demo(factory):
    runtime=c.ConnectionRuntime(FakeGoogleBusinessAdapter(),Fernet.generate_key(),worker=False)
    with pytest.raises(RuntimeError,match='demo mode'):
        create_app(engine=factory.kw['bind'],demo_mode=False,connections_runtime=runtime)


def real_adapter(handler):
    return GoogleBusinessAdapter('client-id','client-secret','https://example.test/connections/google/callback',transport=httpx.MockTransport(handler))


def test_google_oauth_and_refresh_contract():
    requests=[]
    def handler(request):
        requests.append(request)
        assert request.url==httpx.URL('https://oauth2.googleapis.com/token')
        body=parse_qs(request.content.decode());assert body['client_id']==['client-id']
        if 'code' in body:assert body['code_verifier']==['proof'] and body['redirect_uri']==['https://example.test/connections/google/callback']
        return httpx.Response(200,json={'access_token':'access','refresh_token':'refresh','expires_in':3600,'token_type':'Bearer','scope':SCOPE})
    adapter=real_adapter(handler)
    query=parse_qs(urlsplit(adapter.authorize_url('state','proof')).query)
    assert query['state']==['state'] and query['code_challenge_method']==['S256'] and query['access_type']==['offline']
    tokens=adapter.exchange('code','proof',CLOCK);assert tokens['refresh_token']=='refresh'
    assert adapter.refresh(tokens,CLOCK)==tokens and len(requests)==1
    adapter.refresh(tokens,CLOCK+timedelta(hours=2));assert len(requests)==2


def test_google_discovery_pagination_and_snapshot_contract():
    seen=[]
    def handler(r):
        seen.append(str(r.url));assert r.headers['authorization']=='Bearer access'
        host=r.url.host;path=r.url.path
        if host=='mybusinessaccountmanagement.googleapis.com':
            if r.url.params.get('pageToken')=='p2':return httpx.Response(200,json={'accounts':[]})
            return httpx.Response(200,json={'accounts':[{'name':'accounts/101'}],'nextPageToken':'p2'})
        if path.endswith('/locations'):return httpx.Response(200,json={'locations':[{'name':'locations/1001','title':'Test location'}]})
        if host=='mybusinessbusinessinformation.googleapis.com':return httpx.Response(200,json={'name':'locations/1001','title':'Test location'})
        if host=='mybusiness.googleapis.com':
            assert path=='/v4/accounts/101/locations/1001/reviews';return httpx.Response(200,json={'reviews':[]})
        assert host=='businessprofileperformance.googleapis.com'
        assert r.url.params.get_list('dailyMetrics')==['WEBSITE_CLICKS','CALL_CLICKS','BUSINESS_DIRECTION_REQUESTS']
        assert 'dailyRange.startDate.year' in r.url.params
        return httpx.Response(200,json={'multiDailyMetricTimeSeries':[]})
    adapter=real_adapter(handler);tokens={'access_token':'access'}
    assets=adapter.discover(tokens);assert assets[0]['key']=='accounts/101/locations/1001'
    snapshot=adapter.snapshot(tokens,assets[0]['key'],CLOCK);assert snapshot['errors']=={} and snapshot['sections']['reviews']=={'reviews':[]}
    assert len(seen)==6


@pytest.mark.parametrize('status,reason,retry',[(401,'reconnect_required',False),(403,'provider_access_denied',False),(429,'provider_temporarily_unavailable',True),(500,'provider_temporarily_unavailable',True),(302,'provider_request_rejected',False)])
def test_google_errors_do_not_become_empty_success(status,reason,retry):
    adapter=real_adapter(lambda _:httpx.Response(status,json={'error':'secret response must not escape'}))
    with pytest.raises(ConnectionFailure) as exc:adapter.discover({'access_token':'access'})
    assert exc.value.reason==reason and exc.value.retry==retry


def test_google_partial_response_and_revocation_contract():
    seen=[]
    def handler(r):
        seen.append(str(r.url))
        if r.url.path=='/revoke':
            assert parse_qs(r.content.decode())=={'token':['refresh']};return httpx.Response(200)
        if r.url.host=='mybusinessbusinessinformation.googleapis.com':return httpx.Response(200,json={'title':'test'})
        return httpx.Response(403,json={})
    adapter=real_adapter(handler)
    snapshot=adapter.snapshot({'access_token':'a'},'accounts/1/locations/2',CLOCK)
    assert set(snapshot['errors'])=={'reviews','metrics'} and set(snapshot['sections'])=={'listing'}
    adapter.revoke({'refresh_token':'refresh'})


def test_google_page_cycle_and_token_permission():
    adapter=real_adapter(lambda _:httpx.Response(200,json={'accounts':[],'nextPageToken':'same'}))
    with pytest.raises(ConnectionFailure,match='pagination_cycle'):adapter.discover({'access_token':'a'})
    adapter=real_adapter(lambda _:httpx.Response(200,json={'access_token':'a','token_type':'Bearer','refresh_token':'r','expires_in':3600,'scope':'email'}))
    with pytest.raises(ConnectionFailure,match='required_permission_missing'):adapter.exchange('c','v',CLOCK)


def test_exchange_timeout_requires_new_authorization(env):
    def failure(*args):raise ConnectionFailure('provider_network_error',retry=True)
    env.runtime.adapter.exchange=failure
    state=authorize(env);assert callback(env,state,code='synthetic-owner-grant').status_code==200
    assert env.client.get(ROOT).json()['google']['state']=='reconnect_required'
    assert not c.dispatch_one(env.factory,env.runtime)
    assert callback(env,state,code='synthetic-owner-grant').status_code==400


def test_concurrent_callback_consumes_code_once(env):
    calls=[]
    original=env.runtime.adapter.exchange
    def exchange(*args):
        calls.append(1);return original(*args)
    env.runtime.adapter.exchange=exchange
    state=authorize(env)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:callback(env,state,code='synthetic-owner-grant').status_code,range(2)))
    assert statuses.count(200)==1 and set(statuses).issubset({200,400,409})
    assert len(calls)==1


def test_cross_site_return_bridge_has_no_authority_without_completion(env):
    state=authorize(env)
    with TestClient(env.app) as anonymous:
        r=anonymous.get('/connections/google/callback',params={'state':state,'code':'synthetic-owner-grant'},headers={'Sec-Fetch-Site':'cross-site'})
        assert r.status_code==200 and 'connections-callback.js' in r.text
        assert anonymous.post('/connections/google/complete',json={'state':state,'code':'synthetic-owner-grant'}).status_code==401
    assert env.client.get(ROOT).json()['google']['state']=='authorizing'
    assert callback(env,state,code='synthetic-owner-grant').status_code==200


def test_maintenance_during_exchange_and_discovery_does_not_invalidate_grant(env):
    original=env.runtime.adapter.exchange
    def exchange(*args):
        with env.factory() as s:c.maintenance(s,env.runtime)
        return original(*args)
    env.runtime.adapter.exchange=exchange
    assert connected(env)['state']=='connected'


def test_refresh_cooldown_and_missing_values(env):
    connected(env)
    assert post(env,'refresh').status_code==429
    env.now[0]+=timedelta(seconds=61)
    assert post(env,'refresh').status_code==200
    assert post(env,'refresh').status_code==200
    c.dispatch_one(env.factory,env.runtime)
    with env.factory() as s:
        assert len(s.scalars(select(ConnectionJob)).all())==1


def test_revocation_outage_retention_and_no_cached_data(env):
    connected(env)
    def failure(*args):raise ConnectionFailure('provider_network_error',retry=True)
    env.runtime.adapter.revoke=failure
    post(env,'disconnect')
    for _ in range(3):
        c.dispatch_one(env.factory,env.runtime);env.now[0]+=timedelta(minutes=2)
    data=env.client.get(ROOT).json()['google'];assert data['state']=='disconnecting' and not data['snapshot']
    env.now[0]+=timedelta(days=8)
    with env.factory() as s:
        c.maintenance(s,env.runtime)
        assert s.scalar(select(ConnectionJob)) is None
    assert env.client.get(ROOT).json()['google']['error']=='revoke_in_google_account'


def test_authorization_in_flight_does_not_orphan_token(env):
    original=env.runtime.adapter.exchange
    def exchange(*args):
        assert post(env,'disconnect').status_code==409
        assert post(env,'authorize').status_code==409
        return original(*args)
    env.runtime.adapter.exchange=exchange
    connected(env)
    assert post(env,'disconnect').status_code==200
    c.dispatch_one(env.factory,env.runtime)
    assert env.client.get(ROOT).json()['google']['state']=='disconnected'


def test_revoke_already_invalid_token_is_terminal():
    adapter=real_adapter(lambda _:httpx.Response(400,json={'error':'invalid_token'}))
    adapter.revoke({'refresh_token':'revoked'})
