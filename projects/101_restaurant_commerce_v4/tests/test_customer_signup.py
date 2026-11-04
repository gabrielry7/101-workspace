import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, inspect
from test_payment_durability_m3 import factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo, BUSINESS, OTHER, CLOCK, PASSWORD
from world_model.restaurant_commerce.customer_signup_delivery import FakePhoneVerifier, TwilioPhoneVerifier, SesEmailVerifier
from world_model.restaurant_commerce.customer_signup_models import CustomerAccount, CustomerMembership, SignupChallenge, SignupEvent, CustomerLoginSession
from world_model.restaurant_commerce.models import Customer
from world_model.restaurant_commerce.service import RestaurantCommerceService

ROOT='/api/customer/signup/'+BUSINESS
H={'X-101-Signup':'1'}


@pytest.fixture
def env(factory):
    clock=[CLOCK]
    options={'mode':'test','public_origin':'http://testserver','adapters':{'phone':FakePhoneVerifier(),'email':FakePhoneVerifier('synthetic-email')},'clock':lambda:clock[0]}
    # Only loopback origins are accepted even in test mode.
    options['public_origin']='http://127.0.0.1:8803'
    app=create_app(engine=factory.kw['bind'],demo_mode=True,payment_recovery_enabled=False,signup_options=options)
    with factory() as s:seed_campaign_demo(s)
    with TestClient(app) as client:
        yield SimpleNamespace(client=client,factory=factory,options=options,clock=clock,app=app)


def start(e,channel='phone',destination='+573005550100',business=BUSINESS):
    r=e.client.post('/api/customer/signup/'+business+'/start',json={'channel':channel,'destination':destination,'source':'qr'},headers=H)
    assert r.status_code==200,r.text
    return r.json()


def verify(e,p,business=BUSINESS):
    return e.client.post('/api/customer/signup/'+business+'/verify',json={'challenge_id':p['challenge_id'],'code':p['demo_code']},headers=H)


def login(e,channel='phone',destination='+573005550100'):
    p=start(e,channel,destination);r=verify(e,p);assert r.status_code==200,r.text
    return e.client.get(ROOT).json()['account']


def auth(e):
    return {**H,'X-101-Customer-CSRF':e.client.get(ROOT).json()['account']['csrf']}


def test_phone_existing_customer_and_no_marketing_grant(env):
    with env.factory() as s:
        original=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.phone=='+573005550100'))
        before=s.scalar(select(func.count()).select_from(Customer));cid=original.id
        original.whatsapp_opt_in=False;original.marketing_opt_in=False;s.commit()
    p=start(env);response=verify(env,p);assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie']
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(Customer))==before
        m=s.scalar(select(CustomerMembership));assert m.customer_id==cid
        customer=s.get(Customer,cid);assert not customer.whatsapp_opt_in and not customer.marketing_opt_in
    assert env.client.get(ROOT).json()['account']['member'] is True
    assert verify(env,p).status_code==401


def test_email_only_signup_case_normalization_and_return(env):
    me=login(env,'email','Person+tag@Example.test')
    assert me['identifier']=='person+tag@example.test' and me['email_verified']
    with env.factory() as s:
        member=s.scalar(select(CustomerMembership));c=s.get(Customer,member.customer_id)
        assert c.phone is None and c.email=='person+tag@example.test'
        assert RestaurantCommerceService(s).customer_summary(BUSINESS,c.id).phone is None
    env.client.post(ROOT+'/logout',headers=auth(env));env.clock[0]+=timedelta(seconds=61)
    login(env,'email','PERSON+tag@EXAMPLE.test')
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CustomerAccount))==1
        assert s.scalar(select(func.count()).select_from(CustomerMembership))==1
        assert s.scalar(select(func.count()).select_from(SignupEvent).where(SignupEvent.stage=='membership_created'))==1


def test_one_identity_two_memberships_and_scoped_email(env):
    login(env)
    other=ROOT.replace(BUSINESS,OTHER)
    assert env.client.get(other).json()['account']['member'] is False
    assert env.client.post(other+'/join',json={'source':'website'},headers=auth(env)).status_code==200
    assert env.client.post(other+'/join',json={'source':'website'},headers=auth(env)).status_code==200
    original_email=env.client.get(other).json()['account']['email']
    assert env.client.put(ROOT+'/email',json={'email':'optional@example.test'},headers=auth(env)).status_code==200
    assert env.client.get(other).json()['account']['email']==original_email
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CustomerAccount))==1
        assert s.scalar(select(func.count()).select_from(CustomerMembership))==2
        assert len(set(s.scalars(select(CustomerMembership.customer_id))))==2


def test_wrong_expired_used_and_foreign_codes(env):
    p=start(env,'email','one@example.test')
    assert verify(env,p,OTHER).status_code==401
    with TestClient(env.app) as stranger:
        assert stranger.post(ROOT+'/verify',json={'challenge_id':p['challenge_id'],'code':p['demo_code']},headers=H).status_code==401
    wrong='000000' if p['demo_code']!='000000' else '111111'
    for _ in range(5):assert env.client.post(ROOT+'/verify',json={'challenge_id':p['challenge_id'],'code':wrong},headers=H).status_code==422
    assert verify(env,p).status_code==409
    env.clock[0]+=timedelta(minutes=11);p=start(env,'email','one@example.test');env.clock[0]+=timedelta(minutes=11)
    assert verify(env,p).status_code==409
    with env.factory() as s:assert s.scalar(select(func.count()).select_from(CustomerAccount))==0


def test_resend_unknown_and_no_automatic_provider_retry(env):
    p=start(env)
    assert env.client.post(ROOT+'/start',json={'channel':'phone','destination':'+573005550100'},headers=H).status_code==429
    assert len(env.options['adapters']['phone'].calls)==1
    def timeout(*_):raise TimeoutError()
    env.options['adapters']['email'].start=timeout
    r=env.client.post(ROOT+'/start',json={'channel':'email','destination':'x@example.test'},headers=H)
    assert r.status_code==503
    with env.factory() as s:assert s.scalar(select(SignupChallenge).where(SignupChallenge.channel=='email')).state=='unknown'
    assert verify(env,p).status_code==200


def test_concurrent_verification_creates_one_account_and_membership(env):
    p=start(env,'email','race@example.test')
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:verify(env,p),range(2)))
    assert sum(r.status_code==200 for r in results)==1
    assert all(r.status_code in {200,401,409} for r in results)
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CustomerAccount))==1
        assert s.scalar(select(func.count()).select_from(CustomerMembership))==1


def test_logout_expiry_and_unconfigured_channel(env):
    login(env);headers=auth(env)
    assert env.client.post(ROOT+'/logout',headers=H).status_code==403
    assert env.client.post(ROOT+'/logout',headers=headers).status_code==200
    assert env.client.get(ROOT).json()['account'] is None
    env.clock[0]+=timedelta(seconds=61);login(env);env.clock[0]+=timedelta(days=31)
    assert env.client.get(ROOT).json()['account'] is None
    env.options['adapters'].pop('email')
    assert env.client.get(ROOT).json()['channels']['email'] is False
    assert env.client.post(ROOT+'/start',json={'channel':'email','destination':'x@example.test'},headers=H).status_code==503


def test_owner_qr_and_funnel_are_business_scoped(env):
    root='/api/operator/restaurants/'+BUSINESS+'/signup'
    assert env.client.get(root).status_code==401
    env.client.post('/api/staff/login',headers={'X-101-Login':'1'},json={'username':'campaign.manager','password':PASSWORD})
    assert env.client.get(root.replace(BUSINESS,OTHER)).status_code==403
    assert env.client.get(root.replace(BUSINESS,OTHER)+'/qr.png').status_code==403
    data=env.client.get(root,headers={'Host':'evil.test'}).json()
    assert data['qr_url']=='http://127.0.0.1:8803/join/'+BUSINESS+'?source=qr'
    png=env.client.get(root+'/qr.png');svg=env.client.get(root+'/qr.svg')
    assert png.content.startswith(b'\x89PNG') and b'<svg' in svg.content
    assert env.client.get(root+'/qr.png').content==png.content
    assert 'attachment' in png.headers['Content-Disposition']
    env.client.post(ROOT+'/opened',json={'source':'qr'},headers=H);login(env,'email','qr@example.test')
    stages={r['stage']:r['count'] for r in env.client.get(root).json()['funnel']}
    assert stages=={'page_opened':1,'code_requested':1,'identifier_verified':1,'membership_created':1}


def test_invalid_inputs_and_fake_production_rejected(env):
    for channel,destination in [('email','not-an-email'),('email','a..b@example.test'),('phone','3005550100'),('phone','+57000')]:
        assert env.client.post(ROOT+'/start',json={'channel':channel,'destination':destination},headers=H).status_code==422
    assert env.client.post(ROOT+'/start',json={'channel':'email','destination':'ok@example.test'},headers={**H,'Origin':'https://evil.test'}).status_code==403
    with pytest.raises(RuntimeError):create_app(engine=env.factory.kw['bind'],environment='production',demo_mode=False,signup_options=env.options)


def test_real_twilio_wire_contract_and_ambiguous_response():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(201,json={'sid':'VE'+'3'*32,'service_sid':'VA'+'2'*32,'account_sid':'AC'+'1'*32,'to':'+573005550100','channel':'sms','status':'approved' if request.url.path.endswith('VerificationCheck') else 'pending'})
    a=TwilioPhoneVerifier('AC'+'1'*32,'synthetic-secret','VA'+'2'*32,client=httpx.Client(transport=httpx.MockTransport(handler)))
    p=a.start('+573005550100','nonce');assert p.state=='pending'
    assert a.check('+573005550100',p.provider_id,'123456').state=='approved'
    assert b'VerificationSid=VE' in calls[1].content and len(calls)==2
    a.client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(503)))
    assert a.start('+573005550100','nonce').state=='unknown'


def test_real_email_transactional_code_contract():
    class Client:
        def send_email(self,**kwargs):self.sent=kwargs;return {'MessageId':'provider-message'}
    client=Client();a=SesEmailVerifier(client,sender='login@example.test',configuration_set='signup',code_secret='synthetic-code-key-32bytes-minimum')
    result=a.start('person@example.test','nonce');assert result.state=='pending'
    code=a.code('person@example.test',result.provider_id)
    assert code in client.sent['Content']['Simple']['Body']['Text']['Data']
    assert 'Headers' not in client.sent['Content']['Simple']
    assert a.check('person@example.test',result.provider_id,code).state=='approved'
    assert a.check('other@example.test',result.provider_id,code).state=='denied'


def test_email_never_claims_an_unverified_existing_customer(env):
    with env.factory() as s:
        before=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona0@example.test'));cid=before.id
    login(env,'email','persona0@example.test')
    with env.factory() as s:
        link=s.scalar(select(CustomerMembership));assert link.customer_id!=cid
        assert s.get(Customer,link.customer_id).phone is None
        assert s.get(Customer,cid).phone=='+573005550100'


def test_signup_session_survives_new_application_instance(env):
    login(env,'email','restart@example.test')
    token=env.client.cookies.get('commerce_customer')
    app=create_app(engine=env.factory.kw['bind'],demo_mode=True,payment_recovery_enabled=False,signup_options=env.options)
    with TestClient(app) as client:
        client.cookies.set('commerce_customer',token)
        assert client.get(ROOT).json()['account']['member'] is True


def test_budget_reserved_before_send_and_no_call_when_disabled(env):
    env.options['daily_request_limit']=1
    start(env,'email','first@example.test')
    assert env.client.post(ROOT+'/start',json={'channel':'email','destination':'second@example.test'},headers=H).status_code==429
    assert len(env.options['adapters']['email'].calls)==1
    env.options['mode']='live'
    assert env.client.post(ROOT+'/start',json={'channel':'phone','destination':'+573005550100'},headers=H).status_code==503
    assert env.options['adapters']['phone'].calls==[]


def test_email_only_contact_cannot_queue_a_phone_delivery(env):
    from world_model.restaurant_commerce.growth import RestaurantGrowthService
    from world_model.restaurant_commerce.models import AutomationRule
    login(env,'email','only@example.test')
    with env.factory() as s:
        contact=s.get(Customer,s.scalar(select(CustomerMembership)).customer_id)
        rule=s.scalar(select(AutomationRule).where(AutomationRule.business_id==BUSINESS))
        if rule is None:
            # Canonical demo business has no rules; use the normal growth bootstrap.
            g=RestaurantGrowthService(s);g.ensure_program(BUSINESS)
            rule=AutomationRule(business_id=BUSINESS,name='Fixture',trigger_kind='order_paid',channel='whatsapp',purpose='marketing',template_text='Fixture',delay_minutes=0,enabled=True)
            s.add(rule);s.flush()
        job=RestaurantGrowthService(s)._queue_message(rule=rule,customer=contact,order=None,message_kind='test',values={},dedupe_key='email-only-contact',now=CLOCK)
        assert job.status=='suppressed' and job.suppression_reason=='CONTACT_PHONE_REQUIRED'


def test_email_contact_is_usable_by_existing_campaign_audience(env):
    login(env,'email','audience@example.test')
    env.client.post('/api/staff/login',headers={'X-101-Login':'1'},json={'username':'campaign.manager','password':PASSWORD})
    root='/api/operator/restaurants/'+BUSINESS+'/campaigns'
    data=env.client.get(root).json()
    customer=next(c for c in data['customers'] if c['email']=='audience@example.test')
    assert customer['phone'] is None
    headers={'X-101-CSRF':env.client.get('/api/staff/me').json()['csrf']}
    payload={'sender':data['sender'],'content':{'subject':'Test','title':'Test','body':'Test human copy','terms':'No offer'},'customer_ids':[customer['id']],'scheduled_at':CLOCK.isoformat(),'expires_at':(CLOCK+timedelta(days=1)).isoformat(),'scope':'test','budget_microusd':0}
    r=env.client.post(root,json=payload,headers=headers);assert r.status_code==200,r.text
    assert r.json()['eligible']==0 and 'permission_missing' in r.text
