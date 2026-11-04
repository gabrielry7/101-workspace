"""Official WhatsApp wire contracts and campaign/inbox integration; no provider calls."""
import hashlib
import hmac
import json
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import httpx
import pytest
from sqlalchemy import select
from test_campaigns import env, factory, draft, approved, dispatch, report, checkout, payment_event
from world_model.restaurant_commerce import campaigns as c, whatsapp as w
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, CLOCK, enable_whatsapp_demo
from world_model.restaurant_commerce.campaign_delivery import Message
from world_model.restaurant_commerce.whatsapp_delivery import WhatsAppCloudTransport
from world_model.restaurant_commerce.campaign_models import (WhatsAppTemplate,WhatsAppConversation,WhatsAppReply,
    WhatsAppEvidence,CampaignJob,CampaignOrderCredit)

ROOT='/api/operator/restaurants/'+BUSINESS+'/whatsapp'


@pytest.fixture
def wa(env):
    with env.factory() as session:
        integration=enable_whatsapp_demo(session)
    env.options['integrations']['wa']=integration
    env.wa=integration['adapter']
    env.template=env.client.get(ROOT).json()['templates'][0]
    return env


def campaign(e,**changes):
    value=draft(e,channel='whatsapp',sender=e.wa.phone_id,whatsapp_template_id=e.template['id'],
        whatsapp_parameters=['{name}','Oferta ficticia, solo demostración.'])
    value.update(changes)
    return approved(e,value)


def envelope(e,*,messages=None,statuses=None,template=None):
    if template:
        change={'field':'message_template_status_update','value':template}
    else:
        change={'field':'messages','value':{'messaging_product':'whatsapp',
            'metadata':{'phone_number_id':e.wa.phone_id},'messages':messages or [],'statuses':statuses or []}}
    return {'object':'whatsapp_business_account','entry':[{'id':e.wa.waba_id,'time':int(CLOCK.timestamp()),'changes':[change]}]}


def hook(e,body):
    raw=json.dumps(body).encode();sig='sha256='+hmac.new(e.wa.app_secret.encode(),raw,hashlib.sha256).hexdigest()
    return e.client.post('/api/whatsapp-hooks/wa',content=raw,headers={'X-Hub-Signature-256':sig})


def inbound(e,text='Hola',mid='wamid.incoming',at=CLOCK):
    phone=e.client.get(ROOT).json()['customers'][0]['phone']
    return envelope(e,messages=[{'id':mid,'from':phone[1:],'timestamp':str(int(at.timestamp())),
        'type':'text','text':{'body':text}}])


def status(e,job,kind='delivered',errors=None):
    with e.factory() as session: dest=session.get(CampaignJob,job['id']).destination
    return envelope(e,statuses=[{'id':job['message_id'] or 'wamid.simulated.'+job['id'],
        'recipient_id':dest[1:],'status':kind,'timestamp':str(int(CLOCK.timestamp())),
        'biz_opaque_callback_data':job['id'],'errors':errors or []}])


def test_whatsapp_paid_checkout_partial_refund_uses_common_authority(wa):
    p=campaign(wa);assert p['eligible']==3
    dispatch(wa);r=report(wa,p);assert r['provider_accepted']==3
    job=next(j for j in r['deliveries'] if j['state']=='accepted')
    sent=wa.wa.messages[job['id']]
    assert sent.template['name']=='honorato_demo' and sent.template['language']=={'code':'es'}
    assert sent.template['components'][-1]['parameters'][0]['payload']=='STOP'
    assert hook(wa,status(wa,job,'read')).status_code==200
    assert hook(wa,status(wa,job,'delivered')).status_code==200
    assert hook(wa,status(wa,job,'read')).json()['duplicates']==1
    r=report(wa,p);assert r['read_signals']==1 and r['provider_reported_delivery']==1
    order=checkout(wa,job);assert payment_event(wa,order).status_code==200
    r=report(wa,p);assert (r['paid_orders'],r['captured_revenue'],r['refunds'],r['net_revenue'])==(1,24900,5000,19900)
    assert wa.client.get('/api/operator/restaurants/'+BUSINESS+'/campaigns/'+p['id']+'/report?scope=live').json()['paid_orders']==0
    with wa.factory() as session: assert len(list(session.scalars(select(CampaignOrderCredit))))==1


def test_sender_templates_and_inbox_are_business_scoped(wa):
    assert wa.client.get(ROOT.replace(BUSINESS,OTHER)).status_code==403
    assert wa.client.put(ROOT+'/sender',json={},headers={}).status_code==403
    with wa.factory() as s:
        t=s.get(WhatsAppTemplate,wa.template['id']);t.business_id=OTHER;s.commit()
    response=wa.client.post('/api/operator/restaurants/'+BUSINESS+'/campaigns',json=draft(wa,channel='whatsapp',
        sender=wa.wa.phone_id,whatsapp_template_id=wa.template['id'],whatsapp_parameters=['Name','Text']),headers=wa.headers)
    assert response.status_code==404
    assert hook(wa,inbound(wa)).status_code==200
    convo=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    assert wa.client.post(ROOT.replace(BUSINESS,OTHER)+'/conversations/'+convo['id']+'/reply',json={'body':'Reply','request_key':'reply-123'},headers=wa.headers).status_code==403


@pytest.mark.parametrize('status_value',['PAUSED','DISABLED','REJECTED','PENDING'])
def test_template_status_at_dispatch_blocks_pending_campaign(wa,status_value):
    p=campaign(wa)
    body=envelope(wa,template={'message_template_id':wa.template['provider_id'],
        'message_template_language':'es','event':status_value})
    assert hook(wa,body).status_code==200
    dispatch(wa)
    assert not wa.wa.messages
    assert any('whatsapp_template_'+status_value.lower() in (j['reason'] or '') for j in report(wa,p)['deliveries'])


def test_stale_template_approval_event_cannot_unpause(wa):
    body=envelope(wa,template={'message_template_id':wa.template['provider_id'],'message_template_language':'es','event':'PAUSED'})
    assert hook(wa,body).status_code==200
    body['entry'][0]['value']='unused'
    body['entry'][0]['time']-=60;body['entry'][0]['changes'][0]['value']['event']='APPROVED'
    assert hook(wa,body).status_code==200
    assert wa.client.get(ROOT).json()['templates'][0]['status']=='PAUSED'


def test_changed_template_definition_requires_new_campaign_approval(wa):
    p=campaign(wa)
    with wa.factory() as s:
        data={k:wa.template[k] for k in w.TemplateInput.model_fields};data['body']='Nuevo texto {{1}}. {{2}}'
        w.put_template(s,BUSINESS,w.TemplateInput(**data),CLOCK)
    dispatch(wa);assert not wa.wa.messages
    assert any(j['reason']=='whatsapp_template_changed' for j in report(wa,p)['deliveries'])


@pytest.mark.parametrize('field,value,reason',[('allowance',0,'allowance'),('status','RESTRICTED','sender_not_ready'),
    ('quality','RED','sender_not_ready'),('expires_at','2026-11-01T00:00:00Z','evidence_stale')])
def test_sender_current_restrictions_block_dispatch(wa,field,value,reason):
    p=campaign(wa)
    data=wa.client.get(ROOT).json()['sender'];data[field]=value
    assert wa.client.put(ROOT+'/sender',json=data,headers=wa.headers).status_code==200
    dispatch(wa);assert not wa.wa.messages
    assert any(reason in (j['reason'] or '') for j in report(wa,p)['deliveries'])


def test_opt_out_after_scheduling_and_duplicate_inbound(wa):
    p=campaign(wa);body=inbound(wa,'BAJA')
    assert hook(wa,body).json()['applied']==1
    assert hook(wa,body).json()['duplicates']==1
    dispatch(wa)
    phone='+'+body['entry'][0]['changes'][0]['value']['messages'][0]['from']
    assert all(m.destination!=phone for m in wa.wa.messages.values())
    convo=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    assert convo['opted_out'] and len(convo['messages'])==1
    assert wa.client.post(ROOT+'/conversations/'+convo['id']+'/reply',json={'body':'Hi','request_key':'reply-stop'},headers=wa.headers).status_code==409


def test_receipts_never_open_window_inbound_opens_reply_rechecks_expiry(wa):
    p=campaign(wa);dispatch(wa);job=next(j for j in report(wa,p)['deliveries'] if j['state']=='accepted')
    assert hook(wa,status(wa,job,'read')).status_code==200
    assert not wa.client.get(ROOT+'/conversations').json()['conversations'][0]['service_window_open']
    assert hook(wa,inbound(wa)).status_code==200
    convo=next(x for x in wa.client.get(ROOT+'/conversations').json()['conversations'] if x['service_window_open'])
    payload={'body':'Respuesta del equipo, solo prueba.','request_key':'reply-0001'}
    r=wa.client.post(ROOT+'/conversations/'+convo['id']+'/reply',json=payload,headers=wa.headers)
    assert r.status_code==200
    assert wa.client.post(ROOT+'/conversations/'+convo['id']+'/reply',json=payload,headers=wa.headers).json()['id']==r.json()['id']
    dispatch(wa,CLOCK+timedelta(hours=24))
    with wa.factory() as s: assert s.get(WhatsAppReply,r.json()['id']).reason=='whatsapp_service_window_closed'


def test_staff_reply_dispatch_and_opt_out_recheck(wa):
    assert hook(wa,inbound(wa)).status_code==200
    convo=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    path=ROOT+'/conversations/'+convo['id']+'/reply'
    r=wa.client.post(path,json={'body':'Hola, te atiende el equipo.','request_key':'reply-0002'},headers=wa.headers)
    dispatch(wa);assert r.json()['id'] in wa.wa.messages
    assert wa.wa.messages[r.json()['id']].template is None
    second=wa.client.post(path,json={'body':'Más información','request_key':'reply-0003'},headers=wa.headers).json()
    assert hook(wa,inbound(wa,'STOP','wamid.stop')).status_code==200
    dispatch(wa);assert second['id'] not in wa.wa.messages
    with wa.factory() as s: assert s.get(WhatsAppReply,second['id']).reason=='whatsapp_opt_out'


def test_challenge_signature_account_phone_and_future_timestamp(wa):
    path='/api/whatsapp-hooks/wa'
    assert wa.client.get(path,params={'hub.mode':'subscribe','hub.verify_token':wa.wa.verify_token,'hub.challenge':'12345'}).text=='12345'
    assert wa.client.get(path,params={'hub.mode':'subscribe','hub.verify_token':'wrong','hub.challenge':'12345'}).status_code==403
    assert wa.client.post(path,content=b'{}').status_code==401
    for mutate in ['account','phone']:
        body=inbound(wa)
        if mutate=='account':body['entry'][0]['id']='99999999'
        else:body['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']='9999999'
        assert hook(wa,body).status_code==401
    assert hook(wa,inbound(wa,at=CLOCK+timedelta(hours=1))).status_code==422


def test_callback_batch_is_atomic_and_rebatching_is_idempotent(wa):
    body=inbound(wa);good=body['entry'][0]['changes'][0]['value']['messages'][0]
    bad={**good,'id':'wamid.bad','from':'invalid'}
    body['entry'][0]['changes'][0]['value']['messages'].append(bad)
    assert hook(wa,body).status_code==422
    assert wa.client.get(ROOT+'/conversations').json()['conversations']==[]
    body['entry'][0]['changes'][0]['value']['messages']=[good]
    assert hook(wa,body).json()['applied']==1
    body['entry'][0]['changes'][0]['value']['messages'].append({**good,'id':'wamid.second'})
    assert hook(wa,body).json()=={'applied':1,'duplicates':1}


def test_concurrent_callbacks_and_workers_no_duplicate_projection(wa):
    p=campaign(wa)
    with ThreadPoolExecutor(3) as pool:list(pool.map(lambda _:dispatch(wa),range(3)))
    assert len(wa.wa.messages)==3
    job=next(j for j in report(wa,p)['deliveries'] if j['state']=='accepted')
    with ThreadPoolExecutor(3) as pool:
        results=list(pool.map(lambda kind:hook(wa,status(wa,job,kind)),['read','delivered','sent']))
    assert all(r.status_code==200 for r in results)
    r=report(wa,p);assert r['read_signals']==1 and r['provider_reported_delivery']==1
    assert next(j for j in r['deliveries'] if j['id']==job['id'])['state']=='read'


def test_provider_opt_out_failed_receipt_suppresses(wa):
    p=campaign(wa);dispatch(wa);job=next(j for j in report(wa,p)['deliveries'] if j['state']=='accepted')
    assert hook(wa,status(wa,job,'failed',[{'code':131050}])).status_code==200
    convo=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    assert convo['opted_out']
    assert next(j for j in report(wa,p)['deliveries'] if j['id']==job['id'])['reason']=='whatsapp_opt_out'


def adapter(handler):
    return WhatsAppCloudTransport(phone_id='10100000001',waba_id='10100000002',version='v23.0',
        token='synthetic-token',app_secret='synthetic-secret',verify_token='synthetic-verify',client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_cloud_wire_request_and_readiness_offline():
    seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(200,json={'messages':[{'id':'wamid.provider-accepted'}]})
    a=adapter(handler)
    template={'name':'demo','language':{'code':'es'},'components':[]}
    result=a.submit(Message('local-key',a.phone_id,'+573005550100','','','Text','',template))
    assert result.state=='accepted'
    body=json.loads(seen[0].content)
    assert body['template']==template and body['biz_opaque_callback_data']=='local-key' and body['to']=='573005550100'
    assert str(seen[0].url)=='https://graph.facebook.com/v23.0/10100000001/messages'
    assert a.capabilities['idempotency'] is False


@pytest.mark.parametrize('code,reason',[(131049,'whatsapp_recipient_marketing_limit'),(131048,'whatsapp_quality_limit'),
    (131050,'whatsapp_opt_out'),(132015,'whatsapp_template_paused'),(132016,'whatsapp_template_disabled'),(130429,'whatsapp_throughput_limit')])
def test_provider_errors_terminal_no_blind_retry(code,reason):
    calls=[]
    def handler(request):calls.append(request);return httpx.Response(400,json={'error':{'code':code}})
    a=adapter(handler);r=a.submit(Message('key',a.phone_id,'+573005550100','','','Hello',''))
    assert r.state=='rejected' and r.reason==reason and len(calls)==1


@pytest.mark.parametrize('outcome',['timeout','5xx','malformed'])
def test_provider_ambiguous_outcome_stays_unknown(outcome):
    def handler(request):
        if outcome=='timeout':raise httpx.ReadTimeout('synthetic lost response')
        return httpx.Response(503 if outcome=='5xx' else 200,json={})
    a=adapter(handler);assert a.submit(Message('key',a.phone_id,'+573005550100','','','Hello','')).state=='unknown'


def test_unknown_acceptance_reconciles_without_resend(wa):
    original=wa.wa.submit
    def lost(message):original(message);raise TimeoutError('accepted then lost response')
    wa.wa.submit=lost
    p=campaign(wa);dispatch(wa);dispatch(wa)
    assert len(wa.wa.messages)==3 and report(wa,p)['unknown']==3
    job=next(j for j in report(wa,p)['deliveries'] if j['state']=='unknown')
    assert hook(wa,status(wa,job)).status_code==200
    assert report(wa,p)['unknown']==2


def test_inbound_reordering_system_notice_and_withdrawal_never_regrant(wa):
    assert hook(wa,inbound(wa,'STOP')).status_code==200
    assert hook(wa,inbound(wa,'Hola','wamid.older',CLOCK-timedelta(hours=3))).status_code==200
    body=inbound(wa,'Notice','wamid.system');body['entry'][0]['changes'][0]['value']['messages'][0]['type']='system'
    assert hook(wa,body).json()['applied']==0
    row=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    assert row['opted_out'] and c.date(row['last_inbound_at'])==CLOCK


def test_unknown_contact_stays_transport_conversation_not_new_customer(wa):
    before=len(wa.client.get(ROOT).json()['customers'])
    body=inbound(wa);body['entry'][0]['changes'][0]['value']['messages'][0]['from']='573009998888'
    assert hook(wa,body).status_code==200
    assert len(wa.client.get(ROOT).json()['customers'])==before


def test_explicit_additive_whatsapp_migration(factory):
    from world_model.restaurant_commerce.db import database_ready
    from world_model.restaurant_commerce.migrations import upgrade_campaigns
    from world_model.restaurant_commerce.models import Base,RestaurantCommerceProfile
    engine=factory.kw['bind']
    with factory() as session: before=len(list(session.scalars(select(RestaurantCommerceProfile))))
    tables=[t for t in reversed(Base.metadata.sorted_tables) if t.name.startswith('restaurant_campaign_whatsapp_')]
    for table in tables: table.drop(engine)
    assert not database_ready(engine)
    upgrade_campaigns(engine);upgrade_campaigns(engine)
    assert database_ready(engine)
    with factory() as session: assert len(list(session.scalars(select(RestaurantCommerceProfile))))==before


def test_server_config_and_signed_nul_are_rejected_without_database_error(wa):
    sender=wa.client.get(ROOT).json()['sender'];sender['support_owner']='bad\x00owner'
    assert wa.client.put(ROOT+'/sender',json=sender,headers=wa.headers).status_code==422
    assert hook(wa,inbound(wa,'bad\x00message')).status_code==422


def test_optional_readiness_probe_is_explicit_and_reports_partial_catalogue():
    seen=[]
    def handler(request):
        seen.append(request)
        if request.url.path.endswith('/message_templates'):
            return httpx.Response(200,json={'data':[],'paging':{'next':'https://graph.facebook.com/next'}})
        return httpx.Response(200,json={'id':'10100000001','quality_rating':'GREEN'})
    a=adapter(handler)
    assert not seen
    readiness=a.readiness()
    assert readiness['templates_complete'] is False and readiness['allowance']=='requires_current_account_review'
    assert len(seen)==2 and all(r.method=='GET' for r in seen)


def test_real_provider_sync_cannot_write_simulation_or_fabricate_allowance(wa):
    from world_model.restaurant_commerce.campaign_models import CampaignSettings,WhatsAppSender
    a=Mock(name='provider');a.name='whatsapp_cloud';a.phone_id=wa.wa.phone_id;a.waba_id=wa.wa.waba_id
    definition={'id':'10100000003','name':'honorato_demo','language':'es','status':'APPROVED','category':'MARKETING',
        'components':[{'type':'BODY','text':'Hola {{1}}. {{2}}'},{'type':'FOOTER','text':'Responde BAJA.'},
            {'type':'BUTTONS','buttons':[{'type':'URL','text':'Ver carta','url':'https://example.test/campaign-link/{{1}}'},
                {'type':'QUICK_REPLY','text':'Dejar de recibir'}]}]}
    a.readiness.return_value={'phone':{'id':a.phone_id,'quality_rating':'GREEN'},'templates':[definition],
        'templates_complete':True,'allowance':'requires_current_account_review'}
    with wa.factory() as s:
        with pytest.raises(Exception,match='real_provider_evidence_cannot_enter_simulation'):
            w.sync_provider(s,BUSINESS,a,CLOCK)
        a.readiness.assert_not_called();s.rollback()
        cfg=s.get(CampaignSettings,BUSINESS);cfg.scope='provider_test';s.commit()
        values=json.loads(s.get(WhatsAppSender,BUSINESS).document);values['link_origin']='https://example.test'
        w.configure(s,BUSINESS,w.SenderInput(**values),CLOCK)
        result=w.sync_provider(s,BUSINESS,a,CLOCK)
        assert result['sender']['status']=='UNVERIFIED' and result['sender']['allowance']==0
        assert result['templates'][0]['status']=='APPROVED' and result['live_enabled'] is False
        definition['components'][0]={'type':'HEADER','format':'IMAGE'}
        result=w.sync_provider(s,BUSINESS,a,CLOCK+timedelta(minutes=1))
        assert result['templates'][0]['status']=='UNSUPPORTED'
        with pytest.raises(Exception,match='unsupported_template_shape'):
            w.snapshot(s,BUSINESS,result['templates'][0]['id'],[])


def test_approved_webhook_requires_definition_refresh_before_send(wa):
    p=campaign(wa)
    body=envelope(wa,template={'message_template_id':wa.template['provider_id'],'message_template_language':'es','event':'APPROVED'})
    body['entry'][0]['time']+=60
    assert hook(wa,body).status_code==200
    dispatch(wa);assert not wa.wa.messages
    assert wa.client.get(ROOT).json()['templates'][0]['status']=='SYNC_REQUIRED'


def test_old_sender_service_window_cannot_authorize_new_sender(wa):
    assert hook(wa,inbound(wa)).status_code==200
    convo=wa.client.get(ROOT+'/conversations').json()['conversations'][0]
    values=wa.client.get(ROOT).json()['sender'];values['phone_id']='10100000009'
    assert wa.client.put(ROOT+'/sender',json=values,headers=wa.headers).status_code==200
    result=wa.client.post(ROOT+'/conversations/'+convo['id']+'/reply',json={'body':'Reply','request_key':'new-sender'},headers=wa.headers)
    assert result.status_code==409 and result.json()['detail']=='whatsapp_conversation_sender_changed'
