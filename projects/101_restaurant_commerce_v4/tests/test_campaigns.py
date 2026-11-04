"""Real commerce boundary acceptance: synthetic contacts, no provider network."""
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, update
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.campaign_demo import seed_campaign_demo, BUSINESS, OTHER, CLOCK, PASSWORD
from world_model.restaurant_commerce.campaign_delivery import FakeTransport, Submission
from world_model.restaurant_commerce import campaigns as c
from world_model.restaurant_commerce.campaign_models import *
from world_model.restaurant_commerce.models import Customer, Order, Payment, utcnow
from world_model.restaurant_commerce.security import sign_webhook

ROOT = '/api/operator/restaurants/' + BUSINESS + '/campaigns'


@pytest.fixture
def env(factory):
    with factory() as s:
        seed_campaign_demo(s)
        engine = s.get_bind()
    adapter = FakeTransport()
    options = {'clock':lambda:CLOCK,'integrations':{'test':{'business_id':BUSINESS,'scope':'test','adapter':adapter}}}
    app = create_app(engine=engine,demo_mode=True,payment_recovery_enabled=False,campaign_options=options,
                     webhook_secrets={'simulated':'payment-secret'})
    with TestClient(app) as client:
        r=client.post('/api/staff/login',json={'username':'campaign.manager','password':PASSWORD},headers={'X-101-Login':'1'})
        assert r.status_code==200,r.text
        headers={'X-101-CSRF':client.get('/api/staff/me').json()['csrf']}
        yield SimpleNamespace(client=client,headers=headers,options=options,adapter=adapter,factory=factory)


def draft(env, **changes):
    data=env.client.get(ROOT).json()
    value={'sender':data['sender'],'content':{'subject':'Una invitación · demo','title':'La mesa está puesta.',
        'body':'Contenido humano de demostración.','terms':'Producto ficticio. Sin descuento.'},
        'customer_ids':[x['id'] for x in data['customers']], 'scheduled_at':CLOCK.isoformat(),
        'expires_at':(CLOCK+timedelta(days=5)).isoformat(),'scope':'test','budget_microusd':0}
    value.update(changes)
    return value


def create(env, value=None):
    r=env.client.post(ROOT,json=value or draft(env),headers=env.headers)
    assert r.status_code==200,r.text
    return r.json()


def approved(env, value=None):
    preview=create(env,value)
    r=env.client.post(ROOT+'/'+preview['id']+'/approve',json={'digest':preview['digest']},headers=env.headers)
    assert r.status_code==200,r.text
    r=env.client.post(ROOT+'/'+preview['id']+'/schedule',json={'digest':preview['digest']},headers=env.headers)
    assert r.status_code==200,r.text
    return preview


def dispatch(env, now=CLOCK):
    return c.dispatch(env.factory,env.options['integrations'],now=now)


def report(env, preview):
    r=env.client.get(ROOT+'/'+preview['id']+'/report')
    assert r.status_code==200,r.text
    return r.json()


def receipt(env, job, *, kind='delivered', event_id=None, integration='test'):
    body=c.canonical({'id':event_id or kind+job['id'],'key':job['id'],'message_id':job['message_id'] or 'sim-'+job['id'],
                      'kind':kind,'at':CLOCK.isoformat()}).encode()
    signature=hmac.new(env.adapter.secret.encode(),body,hashlib.sha256).hexdigest()
    return env.client.post('/api/campaign-hooks/'+integration,content=body,headers={'X-Campaign-Signature':signature})


def checkout(env, job, *, pay=True):
    assert env.client.get(job['tracking_url'],follow_redirects=False).status_code==303
    store=env.client.get('/api/restaurants/'+BUSINESS+'/storefront').json()
    item=store['menus'][0]['categories'][0]['items'][0]
    value={'customer':{'phone':'+573005550100','name':'Compra ficticia'},'items':[{'menu_item_id':item['id'],'quantity':1}],
           'payment_provider':'simulated','idempotency_key':'campaign-checkout','recovery_secret':'a'*64}
    r=env.client.post('/api/restaurants/'+BUSINESS+'/orders',json=value)
    assert r.status_code==200,r.text
    order=r.json()
    if pay:
        payment=order['payments'][0]
        r=env.client.post('/api/payments/simulated/'+payment['provider_reference']+'/complete',
                          headers={'X-101-Order-Token':order['access_token']})
        assert r.status_code==200,r.text
    return order


def payment_event(env, order, *, status='partially_refunded', amount=5000, event='refund-event', reference='refund-1'):
    value={'event_id':event,'provider_reference':order['payments'][0]['provider_reference'],
           'status':status,'amount_minor':order['total_minor'],'currency':'COP'}
    if status=='partially_refunded':value.update(refund_reference=reference,refund_amount_minor=amount)
    body=json.dumps(value).encode()
    return env.client.post('/api/webhooks/payments/simulated',content=body,
                           headers={'X-101-Webhook-Signature':sign_webhook('payment-secret',body)})


def test_complete_campaign_checkout_and_partial_refund(env):
    preview=approved(env)
    assert preview['eligible']==2 and preview['excluded']==5
    assert preview['estimated_cost_microusd']==0
    dispatch(env)
    r=report(env,preview)
    assert r['provider_accepted']==2 and r['provider_reported_delivery']==0 and r['paid_orders']==0
    job=next(j for j in r['deliveries'] if j['state']=='accepted')
    assert receipt(env,job).status_code==200
    assert receipt(env,job).json()['duplicate'] is True
    assert receipt(env,job,kind='accepted').status_code==200
    assert report(env,preview)['provider_reported_delivery']==1
    order=checkout(env,job,pay=False)
    assert report(env,preview)['paid_orders']==0
    assert payment_event(env,order,status='paid',event='paid').status_code==200
    assert payment_event(env,order,status='paid',event='paid').status_code==200
    result=report(env,preview)
    assert (result['paid_orders'],result['captured_revenue'],result['refunds'],result['net_revenue'])==(1,24900,0,24900)
    assert payment_event(env,order).status_code==200
    assert payment_event(env,order).status_code==200
    assert payment_event(env,order,event='different-event-same-refund').status_code==200
    result=report(env,preview)
    assert (result['paid_orders'],result['captured_revenue'],result['refunds'],result['net_revenue'])==(1,24900,5000,19900)
    with env.factory() as s:
        from world_model.restaurant_commerce.service import RestaurantCommerceService
        daily=RestaurantCommerceService(s).daily_finance(BUSINESS,utcnow().astimezone(__import__("zoneinfo").ZoneInfo("America/Bogota")).date())
        assert daily['confirmed_partial_refunds_minor']==5000 and daily['known_balance_minor']==19900
    assert env.client.get(ROOT+'/'+preview['id']+'/report?scope=live').json()['paid_orders']==0
    assert len(env.adapter.messages)==2


def test_unsubscribe_after_schedule_blocks_pending_job(env):
    preview=approved(env)
    before=report(env,preview)
    target=next(j for j in before['deliveries'] if j['customer_id']==next(r['id'] for r in preview['document']['recipients'] if r['snapshot_eligible']))
    assert env.client.post(target['unsubscribe_url']).status_code==200
    dispatch(env)
    assert next(j for j in report(env,preview)['deliveries'] if j['id']==target['id'])['reason'].startswith('unsubscribed')
    assert target['id'] not in env.adapter.messages


def test_cross_business_ids_senders_reports_callbacks_and_csrf(env):
    assert env.client.get(ROOT.replace(BUSINESS,OTHER)).status_code==403
    data=draft(env)
    with env.factory() as s:
        other=s.scalar(select(Customer).where(Customer.business_id==OTHER))
        other_id=other.id
    assert env.client.post(ROOT,json={**data,'customer_ids':[other_id]},headers=env.headers).status_code==404
    assert env.client.post(ROOT,json=data).status_code==403
    preview=approved(env)
    assert env.client.get(ROOT.replace(BUSINESS,OTHER)+'/'+preview['id']).status_code==403
    assert env.client.get(ROOT.replace(BUSINESS,OTHER)+'/'+preview['id']+'/report').status_code==403
    modified={**data,'sender':'other@example.test'}
    p=approved(env,modified)
    dispatch(env)
    assert all(j['state']=='skipped' for j in report(env,p)['deliveries'])
    env.options['integrations']['other']={'business_id':OTHER,'scope':'test','adapter':env.adapter}
    job=next(j for j in report(env,preview)['deliveries'] if j['state']=='accepted')
    assert receipt(env,job,integration='other').status_code==404
    assert env.client.post('/api/campaign-hooks/test',content=b'{}').status_code==401
    assert env.client.post('/api/webhooks/payments/simulated',content=b'{}').status_code==401


def test_edited_offer_invalidates_approval_and_stops_old_jobs(env):
    p=approved(env)
    value=draft(env);value['content']['terms']='Nueva condición de prueba.'
    r=env.client.put(ROOT+'/'+p['id'],json=value,headers=env.headers)
    assert r.status_code==200 and r.json()['digest']!=p['digest']
    assert env.client.post(ROOT+'/'+p['id']+'/schedule',json={'digest':p['digest']},headers=env.headers).status_code==409
    dispatch(env)
    assert not env.adapter.messages


@pytest.mark.parametrize('action',['cancel','expire','pause'])
def test_cancel_expiry_and_pause(env,action):
    p=approved(env)
    if action=='cancel':env.client.post(ROOT+'/'+p['id']+'/cancel',headers=env.headers)
    elif action=='pause':env.client.post(ROOT+'/pause',json={'paused':True},headers=env.headers)
    dispatch(env,CLOCK+timedelta(days=6) if action=='expire' else CLOCK)
    assert not env.adapter.messages
    assert report(env,p)['states']['skipped']==7


def test_concurrent_workers_and_restart_do_not_duplicate(env):
    p=approved(env)
    with ThreadPoolExecutor(4) as pool:list(pool.map(lambda _:dispatch(env),range(4)))
    assert len(env.adapter.messages)==2
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CampaignJob))==7
    # Fresh transport/process sees persistent accepted jobs and cannot resend them.
    env.options['integrations']['test']['adapter']=FakeTransport()
    dispatch(env)
    assert not env.options['integrations']['test']['adapter'].messages


def test_timeout_after_acceptance_stays_unknown_until_callback(env):
    class Ambiguous(FakeTransport):
        def submit(self,message):
            super().submit(message)
            raise TimeoutError('accepted then timeout')
    adapter=Ambiguous();env.adapter=adapter;env.options['integrations']['test']['adapter']=adapter
    p=approved(env);dispatch(env);dispatch(env)
    result=report(env,p)
    assert result['unknown']==2 and len(adapter.messages)==2
    job=next(j for j in result['deliveries'] if j['state']=='unknown')
    assert receipt(env,job).status_code==200
    assert report(env,p)['unknown']==1


def test_worker_crash_lease_recovers_to_unknown_not_resend(env):
    p=approved(env)
    with env.factory() as s:
        job=s.scalar(select(CampaignJob).where(CampaignJob.state=='queued'))
        job.state='sending';job.attempts=1;job.claimed_at=CLOCK-timedelta(minutes=3);key=job.id;s.commit()
    dispatch(env)
    assert key not in env.adapter.messages
    assert next(j for j in report(env,p)['deliveries'] if j['id']==key)['state']=='unknown'


def test_tampered_expired_scanner_and_cross_business_links(env):
    p=approved(env);dispatch(env)
    job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    assert env.client.get(job['tracking_url']+'tampered').status_code==404
    env.client.get(job['tracking_url'],headers={'User-Agent':'Known link scanner'})
    with env.factory() as s:
        cookie=env.client.cookies.get('campaign_visit_'+c.digest(BUSINESS)[:16])
        assert c.checkout_context(s,BUSINESS,cookie,CLOCK,demo_mode=True) is None
    env.client.get(job['tracking_url'])
    cookie=env.client.cookies.get('campaign_visit_'+c.digest(BUSINESS)[:16])
    with env.factory() as s:
        assert c.checkout_context(s,OTHER,cookie,CLOCK,demo_mode=True) is None
        assert c.checkout_context(s,BUSINESS,cookie,CLOCK+timedelta(days=8),demo_mode=True) is None
        assert c.checkout_context(s,BUSINESS,cookie,CLOCK,demo_mode=False) is None
        assert c.checkout_context(s,BUSINESS,cookie+'x',CLOCK,demo_mode=True) is None


@pytest.mark.parametrize('at,reason',[('2026-11-03T03:00:00+00:00','outside_colombia_sending_hours'),
    ('2026-11-02T15:00:00+00:00','colombian_holiday'),('2026-11-08T15:00:00+00:00','outside_colombia_sending_hours')])
def test_colombia_time_holiday_and_registry_controls(env,at,reason):
    data=draft(env);data['scheduled_at']=at;data['expires_at']=(c.date(at)+timedelta(days=1)).isoformat()
    p=create(env,data)
    assert p['eligible']==0
    assert all(reason in r['reasons'] for r in p['audience'])
    assert any('rne_missing_or_stale' in r['reasons'] for r in p['audience'])


def test_unconfigured_channels_and_live_mode_reject(env):
    for channel in ['sms','whatsapp']:
        p=create(env,draft(env,channel=channel))
        assert env.client.post(ROOT+'/'+p['id']+'/approve',json={'digest':p['digest']},headers=env.headers).status_code==409
    assert env.client.post(ROOT,json=draft(env,scope='live'),headers=env.headers).status_code==409


def test_audience_expansion_and_revision_tampering(env):
    data=draft(env);data['customer_ids']=data['customer_ids'][:1]
    p=approved(env,data)
    r=env.client.put(ROOT+'/'+p['id'],json=draft(env),headers=env.headers)
    assert r.json()['approved'] is False
    with env.factory() as s:
        rev=s.get(CampaignRevision,p['revision_id']);rev.document=rev.document.replace('La mesa','Otra mesa');s.commit()
    dispatch(env)
    assert not env.adapter.messages


def test_missing_personalization_escaped_copy_and_plain_text(env):
    data=draft(env);data['content']['title']='<img src=x onerror=alert(1)>'
    p=create(env,data)
    assert '&lt;img' in p['email']['html'] and '<img src=x' not in p['email']['html']
    from world_model.restaurant_commerce.campaign_email import render
    output=render(p['document'],{'name':''},'https://example.test/t','https://example.test/u')
    assert 'amigo de la casa' in output['html'] and 'Dejar de recibir promociones' in output['text']


def test_full_refund_and_out_of_order_paid_event_remain_stable(env):
    p=approved(env);dispatch(env)
    job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    order=checkout(env,job)
    assert payment_event(env,order,status='refunded',event='full').status_code==200
    assert payment_event(env,order,status='paid',event='late-paid').status_code==200
    r=report(env,p)
    assert (r['paid_orders'],r['refunds'],r['net_revenue'])==(1,24900,0)


def test_refund_amount_conflict_and_overcapture_rejected(env):
    p=approved(env);dispatch(env);job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    order=checkout(env,job)
    assert payment_event(env,order).status_code==200
    assert payment_event(env,order,amount=6000,event='conflict').status_code==409
    assert payment_event(env,order,amount=25000,reference='too-much',event='too-much').status_code in {409,503}
    assert report(env,p)['refunds']==5000


def test_complaint_suppresses_even_when_delivery_arrives_later(env):
    p=approved(env);dispatch(env);job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    assert receipt(env,job,kind='complaint').status_code==200
    assert receipt(env,job).status_code==200
    with env.factory() as s:
        permission=s.scalar(select(ContactPermission).where(ContactPermission.customer_id==job['customer_id'],ContactPermission.scope=='test'))
        assert permission.state=='suppressed'
    assert next(j for j in report(env,p)['deliveries'] if j['id']==job['id'])['state']=='complaint'


def test_bounded_safe_retry_has_backoff_and_no_infinite_retry(env):
    class Rejected(FakeTransport):
        def submit(self,message):return Submission('retryable',reason='known_not_accepted')
    env.options['integrations']['test']['adapter']=Rejected()
    p=approved(env)
    dispatch(env);dispatch(env)
    with env.factory() as s:assert max(s.scalars(select(CampaignJob.attempts)))==1
    dispatch(env,CLOCK+timedelta(minutes=2));dispatch(env,CLOCK+timedelta(minutes=6))
    assert report(env,p)['states']['failed']==2


def test_contact_destination_change_and_shared_frequency_limit(env):
    p=approved(env);dispatch(env)
    q=approved(env);dispatch(env)
    assert report(env,q)['provider_accepted']==0
    assert any('shared_contact_limit' in (j['reason'] or '') for j in report(env,q)['deliveries'])
    with env.factory() as s:
        contact=s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona0@example.test'))
        contact.email='changed@example.test';s.commit()
    q=create(env)
    assert any('permission_destination_changed' in a['reasons'] for a in q['audience'])


def test_migration_is_explicit_additive_and_idempotent(factory):
    from world_model.restaurant_commerce.db import database_ready,init_schema
    from world_model.restaurant_commerce.migrations import upgrade_campaigns
    with factory() as s:engine=s.get_bind()
    CampaignOrderCredit.__table__.drop(engine)
    assert not database_ready(engine)
    with pytest.raises(RuntimeError):init_schema(engine)
    upgrade_campaigns(engine);upgrade_campaigns(engine)
    assert database_ready(engine)


def test_network_transport_is_rejected_in_simulation(env):
    class Network(FakeTransport):
        capabilities={'network':True}
        def submit(self,message):raise AssertionError('must not call provider')
    env.options['integrations']['test']['adapter']=Network()
    p=approved(env);dispatch(env)
    assert sum(j['reason']=='simulation_network_transport_forbidden' for j in report(env,p)['deliveries'])==2


def test_last_visit_is_one_primary_credit_across_channels_and_refund(env):
    p=approved(env);dispatch(env)
    job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    env.client.get(job['tracking_url'])
    # Contract-only SMS interaction fixture: no SMS configuration or dispatch is implied.
    q=approved(env)
    with env.factory() as s:
        second=s.scalar(select(CampaignJob).where(CampaignJob.revision_id==q['revision_id']))
        second.channel='sms';second.state='accepted';second.attempts=1;second.submitted_at=CLOCK
        second.provider_id='test-sms-interaction';s.commit()
        job2={'tracking_url':'/campaign-link/'+second.tracking_token}
    order=checkout(env,job2)
    assert payment_event(env,order).status_code==200
    assert report(env,p)['paid_orders']==0
    r=report(env,q)
    assert (r['paid_orders'],r['refunds'],r['net_revenue'])==(1,5000,19900)
    with env.factory() as s:
        assert s.scalar(select(func.count()).select_from(CampaignOrderCredit))==1
        assert s.get(Order,order['id']).source_channel=='sms'


def test_permission_granted_after_snapshot_cannot_expand_approved_audience(env):
    p=approved(env)
    excluded=next(r for r in p['document']['recipients'] if 'permission_missing' in r['snapshot_reasons'])
    with env.factory() as s:
        c.set_permission(s,BUSINESS,excluded['id'],channel='email',scope='test',state='granted',source='later-test-grant',
            registry={'state':'clear','scope':'test','source':'later-test-review','expires_at':'2026-11-10T00:00:00Z'},now=CLOCK)
        s.commit()
    dispatch(env)
    result=report(env,p)
    assert next(j for j in result['deliveries'] if j['customer_id']==excluded['id'])['state']=='skipped'
    assert result['provider_accepted']==2


def test_existing_redeemed_promotion_has_priority_and_refund_preserves_credit(env):
    from world_model.restaurant_commerce.models import Promotion
    with env.factory() as s:
        s.add(Promotion(business_id=BUSINESS,code='CAMPAIGNDEMO',name='Synthetic offer',value=1000))
        s.commit()
    code_campaign=approved(env,draft(env,promotion_code='CAMPAIGNDEMO'))
    click_campaign=approved(env)
    # Dispatch the clicked campaign first; all channels still share limits.
    with env.factory() as s:
        s.execute(update(CampaignJob).where(CampaignJob.revision_id==code_campaign['revision_id']).values(due_at=CLOCK+timedelta(hours=1)))
        s.commit()
    dispatch(env)
    job=next(j for j in report(env,click_campaign)['deliveries'] if j['state']=='accepted')
    env.client.get(job['tracking_url'])
    store=env.client.get('/api/restaurants/'+BUSINESS+'/storefront').json()
    item=store['menus'][0]['categories'][0]['items'][0]
    response=env.client.post('/api/restaurants/'+BUSINESS+'/orders',json={
        'customer':{'phone':'+573005550100','name':'Synthetic code redemption'},'items':[{'menu_item_id':item['id'],'quantity':1}],
        'payment_provider':'simulated','promo_code':'CAMPAIGNDEMO','idempotency_key':'code-priority','recovery_secret':'b'*64})
    assert response.status_code==200,response.text
    order=response.json()
    assert order['total_minor']==23900
    assert payment_event(env,order,status='paid',event='code-paid').status_code==200
    assert report(env,click_campaign)['paid_orders']==0
    assert report(env,code_campaign)['net_revenue']==23900
    assert payment_event(env,order,status='refunded',event='code-full-refund').status_code==200
    assert report(env,code_campaign)['refunds']==23900
    assert report(env,code_campaign)['paid_orders']==1


def test_cancellation_cannot_recall_submitted_messages(env):
    p=approved(env);dispatch(env)
    env.client.post(ROOT+'/'+p['id']+'/cancel',headers=env.headers)
    result=report(env,p)
    assert result['provider_accepted']==2 and result['states']['accepted']==2


def test_existing_background_recovery_worker_dispatches_campaign_jobs(env):
    import time
    from world_model.restaurant_commerce.recovery import start_recovery
    p=approved(env)
    stop,thread=start_recovery(env.factory,interval_seconds=.05,service_options={},campaign_options=env.options)
    try:
        for _ in range(100):
            if len(env.adapter.messages)==2:break
            time.sleep(.05)
        assert len(env.adapter.messages)==2
    finally:
        stop.set();thread.join(timeout=5)
        assert not thread.is_alive()


def test_pre_upgrade_payment_callback_can_be_replayed_after_refund_schema_extension(env):
    from world_model.restaurant_commerce.models import PaymentNotificationInbox
    from world_model.restaurant_commerce.reliability import request_fingerprint
    p=approved(env);dispatch(env)
    job=next(j for j in report(env,p)['deliveries'] if j['state']=='accepted')
    order=checkout(env,job,pay=False)
    assert payment_event(env,order,status='paid',event='legacy-payment').status_code==200
    with env.factory() as s:
        row=s.scalar(select(PaymentNotificationInbox).where(PaymentNotificationInbox.event_id=='legacy-payment'))
        historical=json.loads(row.payload_json)
        historical.pop('refund_reference',None);historical.pop('refund_amount_minor',None)
        row.payload_json=json.dumps(historical,sort_keys=True)
        row.payload_sha256=request_fingerprint(historical);s.commit()
    assert payment_event(env,order,status='paid',event='legacy-payment').status_code==200
    assert report(env,p)['paid_orders']==1


@pytest.mark.parametrize('method',['POST','PUT'])
@pytest.mark.parametrize('field',['customer_ids','sender','subject','promotion_code'])
def test_campaign_nul_rejected_without_partial_writes(env,method,field):
    value=draft(env)
    campaign=create(env,value)
    if field=='subject': value['content']['subject']='before\x00after'
    elif field=='customer_ids': value[field]=['invalid\x00customer']
    else: value[field]='before\x00after'
    from sqlalchemy import func
    from world_model.restaurant_commerce.campaign_models import Campaign,CampaignRevision
    def counts():
        with env.factory() as session:
            return (session.scalar(select(func.count()).select_from(Campaign)),
                    session.scalar(select(func.count()).select_from(CampaignRevision)))
    before=counts()
    response=env.client.request(method,ROOT+('/'+campaign['id'] if method=='PUT' else ''),
                                json=value,headers=env.headers)
    assert response.status_code==422
    assert counts()==before
