"""Real application/commerce boundaries, with explicitly fake delivery and signed forms."""
import json
import hashlib
from datetime import timedelta
from urllib.parse import urlencode,parse_qs
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from sqlalchemy import select,func
from twilio.request_validator import RequestValidator
from test_campaigns import env,factory,draft,create,approved,dispatch,report,checkout,payment_event,ROOT
from world_model.restaurant_commerce import campaigns as c,sms
from world_model.restaurant_commerce.campaign_demo import BUSINESS,OTHER,CLOCK,enable_sms_demo
from world_model.restaurant_commerce.campaign_models import SmsSender,SmsEvidence,SmsSuppression,CampaignJob,CampaignSettings,ProviderTestReview
from world_model.restaurant_commerce.sms_delivery import TwilioTransport,segments
from world_model.restaurant_commerce.campaign_delivery import Message
from world_model.restaurant_commerce.models import Customer

SMS='/api/operator/restaurants/'+BUSINESS+'/sms'


@pytest.fixture
def sm(env):
    with env.factory() as s:integration=enable_sms_demo(s)
    env.options['integrations']['sms']=integration;env.sms=integration['adapter']
    env.sms.callback_url=env.sms.callback_url.replace('honorato-sms-test','sms');env.sms.inbound_url=env.sms.inbound_url.replace('honorato-sms-test','sms')
    return env


def value(e,**changes):
    doc=draft(e,channel='sms',sender=e.sms.sender);doc.update(changes);return doc


def form(e,job=None,*,status='delivered',text=None,sid=None,error=None):
    with e.factory() as s:
        destination=s.get(CampaignJob,job['id']).destination if job else s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.email=='persona0@example.test')).phone
    data={'AccountSid':e.sms.account_sid,'MessageSid':sid or (job['message_id'] if job else 'SM'+'9'*32),
        'From':destination if text is not None else e.sms.sender,'To':e.sms.sender if text is not None else destination}
    if text is not None:data['Body']=text
    else:data['MessageStatus']=status
    if error:data['ErrorCode']=str(error)
    return data


def hook(e,data,job=None,*,signature=None,extra=''):
    incoming='Body' in data;key=None if incoming else job['id'];url=e.sms.inbound_url if incoming else e.sms.callback_url+'?key='+key
    sig=signature or RequestValidator(e.sms.auth_token).compute_signature(url,data)
    path='/api/sms-hooks/sms/'+('incoming' if incoming else 'status?key='+key)
    return e.client.post(path+extra,content=urlencode(data),headers={'Content-Type':'application/x-www-form-urlencoded','X-Twilio-Signature':sig})


@pytest.mark.parametrize('text,encoding,units,count',[
    ('a'*160,'GSM-7',160,1),('a'*161,'GSM-7',161,2),('^'*80,'GSM-7',160,1),
    ('^'*81,'GSM-7',162,2),('á'*70,'UCS-2',70,1),('á'*71,'UCS-2',71,2),
    ('😀'*35,'UCS-2',70,1),('😀'*36,'UCS-2',72,2),('éñ£€','GSM-7',5,1)])
def test_encoding_boundaries(text,encoding,units,count):
    result=segments(text);assert (result['encoding'],result['units'],result['segments'])==(encoding,units,count)
    assert not result['over_limit']


def test_sms_paid_refund_reordered_and_duplicate_receipts(sm):
    p=approved(sm,value(sm));assert p['eligible']==3
    dispatch(sm);r=report(sm,p);assert r['provider_accepted']==3
    job=next(j for j in r['deliveries'] if j['state']=='accepted')
    sent=sm.sms.messages[job['id']];assert '/campaign-link/' in sent.text and '/campaign-unsubscribe/' in sent.text
    assert hook(sm,form(sm,job),job).status_code==200
    assert hook(sm,form(sm,job,status='sent'),job).status_code==200
    assert hook(sm,form(sm,job),job).json()['duplicate'] is True
    order=checkout(sm,job);assert payment_event(sm,order).status_code==200;assert payment_event(sm,order).status_code==200
    r=report(sm,p);assert (r['paid_orders'],r['captured_revenue'],r['refunds'],r['net_revenue'])==(1,24900,5000,19900)
    assert r['provider_reported_delivery']==1 and r['read_signals']=='unavailable'
    assert r['sms']['provider_status_counts']=={'delivered':1,'sent':1}
    assert r['sms']['estimated_submitted_segments']==sum(segments(m.text)['segments'] for m in sm.sms.messages.values())
    assert sm.client.get(ROOT+'/'+p['id']+'/report?scope=live').json()['paid_orders']==0


def test_baja_after_scheduling_blocks_pending_and_greeting_does_not_regrant(sm):
    p=approved(sm,value(sm));data=form(sm,text='BAJA')
    assert hook(sm,data).status_code==200;assert hook(sm,data).status_code==200
    assert hook(sm,form(sm,text='Hola',sid='SM'+'8'*32)).status_code==200
    dispatch(sm);assert len(sm.sms.messages)==2
    r=report(sm,p);assert any('sms_opt_out' in (j['reason'] or '') for j in r['deliveries'])
    with sm.factory() as s:assert s.scalar(select(func.count()).select_from(SmsSuppression))==1


def test_signature_sender_account_scope_and_url_binding(sm):
    p=approved(sm,value(sm));dispatch(sm);job=next(j for j in report(sm,p)['deliveries'] if j['state']=='accepted')
    data=form(sm,job)
    assert hook(sm,data,job,signature='forged').status_code==401
    assert hook(sm,data,job,extra='&business_id='+OTHER).status_code==401
    assert hook(sm,{**data,'AccountSid':'AC'+'2'*32},job).status_code==401
    assert hook(sm,{**data,'From':'+15555550222'},job).status_code==401
    assert sm.client.get(SMS.replace(BUSINESS,OTHER)).status_code==403
    assert sm.client.put(SMS+'/sender',json={},headers={}).status_code==403
    assert hook(sm,data,job).status_code==200


def test_duplicate_fields_and_reordered_body(sm):
    p=approved(sm,value(sm));dispatch(sm);job=next(j for j in report(sm,p)['deliveries'] if j['state']=='accepted');data=form(sm,job)
    assert hook(sm,dict(reversed(list(data.items()))),job).status_code==200
    assert hook(sm,data,job).json()['duplicate'] is True
    bad=urlencode(data)+'&MessageStatus=failed'
    r=sm.client.post('/api/sms-hooks/sms/status?key='+job['id'],content=bad,headers={'Content-Type':'application/x-www-form-urlencoded','X-Twilio-Signature':RequestValidator(sm.sms.auth_token).compute_signature(sm.sms.callback_url+'?key='+job['id'],data)})
    assert r.status_code==401


def test_concurrent_workers_and_callbacks(sm):
    p=approved(sm,value(sm))
    with ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:dispatch(sm),range(2)))
    assert len(sm.sms.messages)==3
    job=next(j for j in report(sm,p)['deliveries'] if j['state']=='accepted');data=form(sm,job)
    with ThreadPoolExecutor(2) as pool:responses=list(pool.map(lambda _:hook(sm,data,job),range(2)))
    assert all(r.status_code==200 for r in responses)
    assert report(sm,p)['provider_reported_delivery']==1


def test_unknown_acceptance_no_blind_resend(sm):
    original=sm.sms.submit
    def lost(message):original(message);raise TimeoutError('response lost')
    sm.sms.submit=lost;p=approved(sm,value(sm));dispatch(sm);dispatch(sm)
    assert len(sm.sms.messages)==3 and report(sm,p)['unknown']==3
    job=next(j for j in report(sm,p)['deliveries'] if j['state']=='unknown')
    job['message_id']='SM'+hashlib.sha256(job['id'].encode()).hexdigest()[:32]
    assert hook(sm,form(sm,job),job).status_code==200
    assert report(sm,p)['unknown']==2


@pytest.mark.parametrize('change,reason',[
    ({'status':'RESTRICTED'},'sms_sender_or_route_changed'),({'expires_at':'2026-11-01T00:00:00Z'},'sms_sender_or_route_changed'),
    ({'max_segments':1},'sms_sender_or_route_changed'),({'unit_cost_microusd':None},'sms_sender_or_route_changed')])
def test_route_changes_block_already_approved_work(sm,change,reason):
    p=approved(sm,value(sm))
    with sm.factory() as s:
        row=s.get(SmsSender,BUSINESS);doc=json.loads(row.document);doc.update(change);row.document=c.canonical(doc);s.commit()
    dispatch(sm);assert not sm.sms.messages
    assert any(reason in (j['reason'] or '') for j in report(sm,p)['deliveries'])


def test_cost_counts_frozen_personalization_links_and_budget(sm):
    with sm.factory() as s:
        row=s.get(SmsSender,BUSINESS);doc=json.loads(row.document);doc['unit_cost_microusd']=1000;row.document=c.canonical(doc);s.commit()
    p=create(sm,value(sm));expected=sum(r['sms_cost_microusd'] for r in p['audience'] if r['status']=='allowed')
    assert p['estimated_cost_microusd']==expected and expected>3000
    assert sm.client.post(ROOT+'/'+p['id']+'/approve',json={'digest':p['digest']},headers=sm.headers).status_code==409
    d=value(sm,budget_microusd=1_000_000);d['content']['body']='Hola {name}, prueba.'
    p=approved(sm,d);dispatch(sm)
    for message in sm.sms.messages.values():assert '{name}' not in message.text


def test_unavailable_inbound_route_has_link_and_rejects_inbound(sm):
    with sm.factory() as s:
        row=s.get(SmsSender,BUSINESS);doc=json.loads(row.document);doc.update(inbound_supported=False,delivery_receipts='unavailable');row.document=c.canonical(doc);s.commit()
    p=approved(sm,value(sm));dispatch(sm)
    assert all('O responde BAJA' not in m.text and '/campaign-unsubscribe/' in m.text for m in sm.sms.messages.values())
    assert hook(sm,form(sm,text='BAJA')).status_code==409
    assert report(sm,p)['receipt_missing']==3


def test_optout_error_suppresses_and_unknown_contact_not_customer(sm):
    before=sm.client.get(SMS).json()['customers'];p=approved(sm,value(sm));dispatch(sm)
    job=next(j for j in report(sm,p)['deliveries'] if j['state']=='accepted')
    assert hook(sm,form(sm,job,status='undelivered',error=21610),job).status_code==200
    assert report(sm,p)['provider_reported_delivery']==0 and report(sm,p)['receipt_missing']==2
    data=form(sm,text='HELP');data['From']='+573009998888'
    assert hook(sm,data).status_code==200
    assert len(sm.client.get(SMS).json()['customers'])==len(before)


def real_adapter(handler):
    return TwilioTransport(account_sid='AC'+'1'*32,auth_token='synthetic-auth',sender='+15555550199',
        callback_url='https://example.test/api/sms-hooks/sms/status',inbound_url='https://example.test/api/sms-hooks/sms/incoming',
        client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_real_twilio_wire_contract_no_network():
    seen=[]
    def handler(request):
        seen.append(request);return httpx.Response(201,json={'sid':'SM'+'a'*32,'account_sid':'AC'+'1'*32,'from':'+15555550199','to':'+573005550100','status':'queued'})
    a=real_adapter(handler);m=Message('a'*64,a.sender,'+573005550100','','','Prueba','')
    result=a.submit(m);assert result.state=='accepted' and len(seen)==1
    form=parse_qs(seen[0].content.decode());assert form['Body']==['Prueba'] and form['StatusCallback']==[a.callback_url+'?key='+m.key]
    assert str(seen[0].url)==f'https://api.twilio.com/2010-04-01/Accounts/{a.account_sid}/Messages.json'
    assert a.capabilities['idempotency'] is False


@pytest.mark.parametrize('outcome',['timeout','server','malformed','foreign_response'])
def test_real_adapter_unknown_results_not_retried(outcome):
    calls=[]
    def handler(request):
        calls.append(request)
        if outcome=='timeout':raise httpx.ReadTimeout('lost response')
        return httpx.Response(503 if outcome=='server' else 201,json={'sid':'SM'+'a'*32} if outcome=='foreign_response' else {})
    a=real_adapter(handler);assert a.submit(Message('a'*64,a.sender,'+573005550100','','','Text','')).state=='unknown';assert len(calls)==1


@pytest.mark.parametrize('code,reason',[(21610,'sms_opt_out'),(21614,'sms_non_mobile'),(21408,'sms_country_permission'),(20429,'sms_rate_limit'),(30007,'sms_carrier_filtered')])
def test_real_adapter_rejections_are_terminal(code,reason):
    a=real_adapter(lambda r:httpx.Response(400,json={'code':code}));result=a.submit(Message('a'*64,a.sender,'+573005550100','','','Text',''))
    assert (result.state,result.reason)==('rejected',reason)


def test_provider_test_review_is_exact_stale_and_not_send_authorization(sm):
    p=create(sm,value(sm));data={'campaign_id':p['id'],'customer_id':p['document']['recipients'][0]['id'],
        'revision_digest':p['digest'],'max_cost_microusd':1_000_000,'recipient_authorization_source':'synthetic internal test consent',
        'expires_at':(CLOCK+timedelta(hours=1)).isoformat()}
    r=sm.client.post(ROOT+'/provider-test-reviews',json=data,headers=sm.headers);assert r.status_code==200,r.text
    review=r.json();assert review['document']['send_authorized'] is False and review['document']['max_messages']==1
    assert 'simulation_is_not_provider_verification' in review['document']['blockers']
    assert sm.client.get(ROOT.replace(BUSINESS,OTHER)+'/provider-test-reviews/'+review['id']).status_code==403
    assert sm.client.put(ROOT+'/'+p['id'],json=value(sm,budget_microusd=100),headers=sm.headers).status_code==200
    assert sm.client.get(ROOT+'/provider-test-reviews/'+review['id']).json()['state']=='stale'
    assert not sm.sms.messages


def test_real_readiness_probe_is_never_called_in_simulation(sm):
    r=sm.client.post(ROOT+'/provider-readiness/whatsapp/probe',headers=sm.headers)
    assert r.status_code==409 and 'simulation' in r.text
    ready=sm.client.get(ROOT+'/provider-readiness').json()
    assert ready['provider_test_enabled'] is False and ready['channels']['sms']['configured_adapter'] is None


def test_meta_account_membership_observation_uses_official_read_only_paths():
    from world_model.restaurant_commerce.whatsapp_delivery import WhatsAppCloudTransport
    calls=[]
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('/phone_numbers'):return httpx.Response(200,json={'data':[{'id':'10100000001'}]})
        if request.url.path.endswith('/message_templates'):return httpx.Response(200,json={'data':[]})
        return httpx.Response(200,json={'id':'10100000001','quality_rating':'GREEN','code_verification_status':'VERIFIED'})
    a=WhatsAppCloudTransport(phone_id='10100000001',waba_id='10100000002',version='v23.0',token='synthetic',app_secret='synthetic',verify_token='synthetic',client=httpx.Client(transport=httpx.MockTransport(handler)))
    observation=a.account_readiness()
    assert observation['phone_waba_binding_verified'] is True and observation['phone_catalogue_complete'] is True
    assert len(calls)==3 and all(r.method=='GET' for r in calls)


def test_unknown_inbound_stop_suppresses_future_existing_customer(sm):
    data=form(sm,text='STOP');data['From']='+573009998888'
    assert hook(sm,data).status_code==200
    with sm.factory() as s:
        assert sms.suppressed(s,BUSINESS,'test',data['From'])
        assert not s.scalar(select(Customer).where(Customer.business_id==BUSINESS,Customer.phone==data['From']))


def test_callback_nul_and_wrong_path_rejected(sm):
    assert hook(sm,form(sm,text='Hi\x00bad')).status_code==401
    params=form(sm,text='BAJA');sig=RequestValidator(sm.sms.auth_token).compute_signature(sm.sms.inbound_url,params)
    sm.options['integrations']['another']=sm.options['integrations']['sms']
    r=sm.client.post('/api/sms-hooks/another/incoming',content=urlencode(params),headers={'Content-Type':'application/x-www-form-urlencoded','X-Twilio-Signature':sig})
    assert r.status_code==401


def test_additive_sms_migration_preserves_customer_rows(factory):
    from world_model.restaurant_commerce.migrations import upgrade_campaigns
    from world_model.restaurant_commerce.models import Base
    engine=factory.kw['bind']
    with factory() as s:before=s.scalar(select(func.count()).select_from(Customer))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name.startswith('restaurant_campaign_sms_') or table.name=='restaurant_campaign_provider_test_reviews':table.drop(engine)
    upgrade_campaigns(engine)
    with factory() as s:assert s.scalar(select(func.count()).select_from(Customer))==before


@pytest.mark.parametrize('text', ['^'*153, '😀'*67])
def test_segment_boundaries_do_not_split_escape_or_surrogate_pairs(text):
    assert segments(text)['segments']==3


@pytest.mark.parametrize('text,units,count', [('👨‍👩‍👧‍👦'*7,77,2),('a\r\nb',4,1),('e\u0301'*67,134,3)])
def test_extended_graphemes_and_crlf(text,units,count):
    result=segments(text);assert (result['units'],result['segments'])==(units,count)


def test_unconfigured_preview_and_nontest_sender_cannot_claim_readiness(sm):
    from sqlalchemy import delete
    with sm.factory() as s:
        original=json.loads(s.get(SmsSender,BUSINESS).document)
        s.execute(delete(SmsSender).where(SmsSender.business_id==BUSINESS));s.commit()
    p=create(sm,value(sm));assert p['email']['text']=='SMS sin configurar' and p['eligible']==0
    with sm.factory() as s:
        cfg=s.get(CampaignSettings,BUSINESS);cfg.scope='provider_test';s.commit()
        original['link_origin']='https://example.test'
        sms.configure(s,BUSINESS,sms.SenderInput(**original),CLOCK)
        row=s.get(SmsSender,BUSINESS);assert row.scope=='provider_test'
        doc=json.loads(row.document)
        assert doc['status']=='UNVERIFIED' and doc['unit_cost_microusd'] is None and doc['inbound_supported'] is False
