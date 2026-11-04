"""WhatsApp-specific constraints and inbox; campaign/customer/order authority reused."""
import json
import re
import unicodedata
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update, func
from . import campaigns as c
from .campaign_models import (CampaignSettings, CampaignJob, WhatsAppSender, WhatsAppTemplate,
    WhatsAppConversation, WhatsAppEvidence, WhatsAppReply)
from .campaign_delivery import Message, Submission
from .models import Customer
from .staff import aware
from .whatsapp_delivery import error_reason


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='after')
    def valid_text(self):
        if '\\u0000' in self.model_dump_json(): raise ValueError('NUL is not accepted')
        return self


class SenderInput(Input):
    phone_id: str = Field(pattern=r'^\d{5,30}$')
    waba_id: str = Field(pattern=r'^\d{5,30}$')
    version: str = Field(pattern=r'^v\d{2}\.0$')
    display_phone: str = Field(pattern=r'^\+57\d{10}$')
    support_owner: str = Field(min_length=1, max_length=100)
    link_origin: str = Field(max_length=200)
    status: str = Field(pattern=r'^(READY|UNVERIFIED|RESTRICTED)$')
    quality: str = Field(pattern=r'^(GREEN|YELLOW|RED|UNKNOWN)$')
    allowance: int = Field(ge=0, le=100000)
    source: str = Field(min_length=1, max_length=300)
    expires_at: str
    unit_cost_microusd: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def origin(self):
        u = urlsplit(self.link_origin)
        if u.scheme not in {'http','https'} or not u.hostname or u.path or u.query or u.fragment or u.username:
            raise ValueError('A public HTTPS origin, or explicit local demo origin, is required')
        c.date(self.expires_at)
        return self


class TemplateInput(Input):
    provider_id: str = Field(pattern=r'^\d{5,30}$')
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,100}$')
    language: str = Field(pattern=r'^[a-z]{2,3}(?:_[A-Z]{2})?$')
    category: str = Field(pattern=r'^MARKETING$')
    status: str = Field(pattern=r'^(APPROVED|PENDING|PAUSED|DISABLED|REJECTED)$')
    body: str = Field(min_length=1, max_length=1024)
    footer: str = Field(min_length=1, max_length=60)
    source: str = Field(min_length=1, max_length=300)
    expires_at: str

    @model_validator(mode='after')
    def parameters(self):
        numbers = sorted(set(int(n) for n in re.findall(r'\{\{(\d+)\}\}', self.body)))
        if numbers != list(range(1, len(numbers)+1)) or len(numbers)>5: raise ValueError('Use contiguous positional parameters 1–5')
        stripped = re.sub(r'\{\{\d+\}\}', '', self.body)
        if '{{' in stripped or '}}' in stripped: raise ValueError('Unsupported parameter syntax')
        c.date(self.expires_at)
        return self


def lock(session, business):
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business)
        .values(dispatch_version=CampaignSettings.dispatch_version+1))


def sender_document(session, business):
    row = session.get(WhatsAppSender, business)
    return json.loads(row.document) if row else None


def binding(doc):
    return {k:doc[k] for k in ['phone_id','waba_id','version','link_origin']}


def configure(session, business, payload, now):
    lock(session, business)
    cfg = c.settings(session, business)
    if cfg.scope != 'test':
        if not payload.link_origin.startswith('https://'): raise HTTPException(422,'https_origin_required')
        payload=payload.model_copy(update={'status':'UNVERIFIED','quality':'UNKNOWN','allowance':0,
            'unit_cost_microusd':None,'source':'operator configuration; provider readiness unverified'})
    for other in session.scalars(select(WhatsAppSender).where(WhatsAppSender.business_id != business)):
        if json.loads(other.document)['phone_id'] == payload.phone_id:
            raise HTTPException(409, 'sender_already_bound_to_another_business')
    row = session.get(WhatsAppSender, business)
    if row is None:
        row = WhatsAppSender(business_id=business, scope=cfg.scope, phone_id=payload.phone_id); session.add(row)
    row.scope = cfg.scope
    row.phone_id = payload.phone_id
    row.document, row.updated_at = c.canonical(payload.model_dump()), now
    from sqlalchemy.exc import IntegrityError
    try: session.commit()
    except IntegrityError:
        session.rollback(); raise HTTPException(409,'sender_already_bound') from None
    return readiness(session, business, now)


def put_template(session, business, payload, now):
    lock(session, business)
    if c.settings(session,business).scope != 'test': raise HTTPException(409, 'manual_template_status_is_test_only')
    sender = sender_document(session,business)
    if not sender: raise HTTPException(409,'whatsapp_unconfigured')
    doc = payload.model_dump(exclude={'status'})
    doc.update(url=sender['link_origin']+'/campaign-link/{{1}}', url_button='Ver la carta', opt_out_button='Dejar de recibir', opt_out_payload='STOP')
    row = session.scalar(select(WhatsAppTemplate).where(WhatsAppTemplate.business_id==business,
        WhatsAppTemplate.provider_id==payload.provider_id, WhatsAppTemplate.language==payload.language))
    if row is None:
        row=WhatsAppTemplate(business_id=business,provider_id=payload.provider_id,language=payload.language);session.add(row)
    row.document, row.digest = c.canonical(doc), c.digest(c.canonical(doc))
    row.status, row.status_at = payload.status, now
    session.commit()
    return template_out(row)


def template_out(row):
    return {'id':row.id,'digest':row.digest,'status':row.status, **json.loads(row.document)}


def readiness(session,business,now):
    sender = sender_document(session,business)
    return {'scope':c.settings(session,business).scope, 'live_enabled':False,
        'state':'unconfigured' if not sender else 'simulation_only' if c.settings(session,business).scope=='test' else 'configured_inactive', 'sender':sender,
        'templates':[template_out(t) for t in session.scalars(select(WhatsAppTemplate).where(WhatsAppTemplate.business_id==business))],
        'provider_readiness':'not_verified_live', 'reply_policy':'Staff only; genuine inbound opens 24 hours; no automatic response'}


def snapshot(session,business,template_id,parameters):
    row = session.get(WhatsAppTemplate,template_id)
    if not row or row.business_id != business: raise HTTPException(404,'WhatsApp template not found')
    sender = sender_document(session,business)
    if not sender: raise HTTPException(409,'whatsapp_unconfigured')
    doc=json.loads(row.document)
    if row.status=='UNSUPPORTED' or not {'body','expires_at','url'} <= doc.keys(): raise HTTPException(409,'unsupported_template_shape')
    count=len(set(re.findall(r'\{\{\d+\}\}',doc['body'])))
    if len(parameters)!=count: raise HTTPException(422,'whatsapp_template_parameters')
    return {'id':row.id,'digest':row.digest,'definition':doc,'parameters':parameters,'sender':binding(sender)}


def eligibility(session,business,customer,document,now,exclude_job):
    reasons=[];sender=sender_document(session,business); snap=document.get('whatsapp')
    if not sender or not snap: return ['whatsapp_unconfigured']
    if document['sender'] != sender['phone_id'] or binding(sender)!=snap['sender']: reasons.append('whatsapp_sender_changed')
    if sender['status']!='READY' or sender['quality'] not in {'GREEN','YELLOW'}: reasons.append('whatsapp_sender_not_ready')
    if c.date(sender['expires_at'])<=now: reasons.append('whatsapp_account_evidence_stale')
    template=session.get(WhatsAppTemplate,snap['id'])
    if not template or template.business_id!=business or template.digest!=snap['digest']: reasons.append('whatsapp_template_changed')
    elif not {'body','expires_at','url'} <= json.loads(template.document).keys(): reasons.append('whatsapp_template_unsupported')
    elif template.status!='APPROVED': reasons.append('whatsapp_template_'+template.status.lower())
    elif c.date(json.loads(template.document)['expires_at'])<=now: reasons.append('whatsapp_template_evidence_stale')
    recent=session.scalar(select(func.count()).select_from(CampaignJob).where(CampaignJob.business_id==business,
        CampaignJob.channel=='whatsapp',CampaignJob.scope==document['scope'],CampaignJob.id!=(exclude_job or ''),
        CampaignJob.claimed_at>now-timedelta(hours=24),CampaignJob.state.in_(['sending','accepted','unknown','delivered','read','failed'])))
    if recent>=sender['allowance']: reasons.append('whatsapp_account_allowance')
    blocked=session.scalar(select(WhatsAppConversation.id).where(WhatsAppConversation.business_id==business,
        WhatsAppConversation.scope==document['scope'],WhatsAppConversation.destination==customer.phone,
        WhatsAppConversation.opted_out.is_(True)).limit(1))
    if blocked: reasons.append('whatsapp_opt_out')
    return reasons


def render(doc,recipient,tracking_token):
    snap=doc['whatsapp']; definition=snap['definition']
    params=[p.replace('{name}',recipient.get('name') or 'amigo de la casa') for p in snap['parameters']]
    text=definition['body']
    for i,value in enumerate(params,1): text=text.replace('{{'+str(i)+'}}',value)
    components=[]
    if params: components.append({'type':'body','parameters':[{'type':'text','text':p} for p in params]})
    components.extend([{'type':'button','sub_type':'url','index':'0','parameters':[{'type':'text','text':tracking_token}]},
        {'type':'button','sub_type':'quick_reply','index':'1','parameters':[{'type':'payload','payload':'STOP'}]}])
    return {'text':text+'\n'+definition['footer'], 'template':{'name':definition['name'],
        'language':{'code':definition['language']},'components':components}}


def opt_out(session,business,scope,destination,now,source):
    for customer in session.scalars(select(Customer).where(Customer.business_id==business,Customer.phone==destination)):
        c.set_permission(session,business,customer.id,channel='whatsapp',scope=scope,state='withdrawn',
            source=source,reason='whatsapp_opt_out',now=now)


def conversation(session,business,scope,phone,destination):
    row=session.scalar(select(WhatsAppConversation).where(WhatsAppConversation.business_id==business,
        WhatsAppConversation.scope==scope,WhatsAppConversation.phone_id==phone,WhatsAppConversation.destination==destination))
    if not row:
        row=WhatsAppConversation(business_id=business,scope=scope,phone_id=phone,destination=destination)
        session.add(row);session.flush()
    return row


def ingest(session,integration,events,raw_sha,now):
    business,scope=integration['business_id'],integration['scope'];adapter=integration['adapter']
    lock(session,business)
    sender=sender_document(session,business)
    if not sender or sender['phone_id']!=adapter.phone_id or sender['waba_id']!=adapter.waba_id or c.settings(session,business).scope!=scope:
        raise HTTPException(409,'whatsapp_integration_binding_changed')
    applied=0
    for event in events:
        # Validate the entire transaction; malformed/foreign items roll back the batch.
        if len(c.canonical(event))>12000 or '\\u0000' in c.canonical(event): raise HTTPException(422,'invalid_whatsapp_event')
        at=c.date(event['at'])
        if at>now+timedelta(minutes=5): raise HTTPException(422,'future_whatsapp_event')
        key=c.digest(business+':'+scope+':'+adapter.phone_id+':'+event['id'])
        existing=session.get(WhatsAppEvidence,key)
        if existing:
            if existing.document!=c.canonical(event): raise HTTPException(409,'event_identity_conflict')
            continue
        evidence=WhatsAppEvidence(id=key,business_id=business,scope=scope,kind=event['kind'],
            document=c.canonical(event),raw_sha256=raw_sha,provider_at=at,received_at=now)
        if event['kind']=='template_status':
            template=session.scalar(select(WhatsAppTemplate).where(WhatsAppTemplate.business_id==business,
                WhatsAppTemplate.provider_id==event['template_id'],WhatsAppTemplate.language==event['language']))
            if not template:
                session.add(evidence);session.flush();applied+=1;continue
            allowed={'APPROVED','PENDING','PAUSED','DISABLED','REJECTED','IN_APPEAL','PENDING_DELETION','DELETED','LIMIT_EXCEEDED'}
            if event['status'] not in allowed: raise HTTPException(422,'unknown_template_status')
            # A tie never clears a restriction; a later true status update may.
            if at>aware(template.status_at) or (at==aware(template.status_at) and event['status']!='APPROVED'):
                # Approval/status callbacks do not contain the actual definition.
                # Refetch it before resuming, since Meta can approve an edited body.
                template.status=('SYNC_REQUIRED' if event['status']=='APPROVED' else event['status']) if 'body' in json.loads(template.document) else 'UNSUPPORTED'
                template.status_at=at
        else:
            destination=event['destination']
            if not re.fullmatch(r'\+\d{8,15}',destination): raise HTTPException(422,'invalid_whatsapp_destination')
            convo=conversation(session,business,scope,adapter.phone_id,destination);evidence.conversation_id=convo.id
            if event['kind']=='inbound':
                if not convo.last_inbound_at or at>aware(convo.last_inbound_at): convo.last_inbound_at=at
                convo.state='needs_staff'
                normalized=''.join(ch for ch in unicodedata.normalize('NFKD',event['text'].strip().casefold()) if not unicodedata.combining(ch)).strip(' .!')
                if normalized in {'stop','baja','salir','cancelar','no mas','no mas mensajes','unsubscribe','dejar de recibir'}:
                    convo.opted_out=True;opt_out(session,business,scope,destination,now,'whatsapp-inbound:'+event['id'])
            else:
                job=session.get(CampaignJob,event.get('key')) if event.get('key') else session.scalar(select(CampaignJob).where(
                    CampaignJob.business_id==business,CampaignJob.provider_id==event['message_id'],CampaignJob.channel=='whatsapp'))
                reply=session.get(WhatsAppReply,event.get('key')) if event.get('key') else session.scalar(select(WhatsAppReply).where(
                    WhatsAppReply.business_id==business,WhatsAppReply.provider_id==event['message_id']))
                if job:
                    if job.channel!='whatsapp' or job.business_id!=business or job.destination!=destination: raise HTTPException(404,'delivery_not_bound')
                    normalized_event={k:event[k] for k in ['id','message_id','kind','at']};normalized_event['key']=job.id
                    c.ingest_event(session,integration,normalized_event,now,commit=False)
                    if event.get('errors'): job.reason=error_reason(event['errors'][0])
                elif reply:
                    if reply.business_id!=business or reply.conversation_id!=convo.id or not reply.claimed_at: raise HTTPException(404,'reply_not_bound')
                    if reply.provider_id and reply.provider_id!=event['message_id']: raise HTTPException(409,'provider_message_mismatch')
                    ranks={'queued':0,'sending':0,'unknown':0,'accepted':1,'failed':2,'delivered':3,'read':4}
                    if ranks[event['kind']]>=ranks.get(reply.state,0): reply.state=event['kind']
                    reply.provider_id=event['message_id']
                else: raise HTTPException(409,'message_not_bound_yet')
                if 131050 in event.get('errors',[]):
                    convo.opted_out=True;opt_out(session,business,scope,destination,now,'whatsapp-provider:'+event['id'])
        session.add(evidence);session.flush();applied+=1
    session.commit()
    return {'applied':applied,'duplicates':len(events)-applied}


class ReplyInput(Input):
    body: str = Field(min_length=1,max_length=2000)
    request_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,100}$')


def queue_reply(session,business,conversation_id,payload,actor,now):
    lock(session,business)
    row=session.get(WhatsAppConversation,conversation_id)
    if not row or row.business_id!=business: raise HTTPException(404,'Conversation not found')
    if row.scope!='test': raise HTTPException(409,'live_reply_disabled')
    if row.opted_out: raise HTTPException(409,'whatsapp_opt_out')
    if not row.last_inbound_at or not aware(row.last_inbound_at)<=now<aware(row.last_inbound_at)+timedelta(hours=24):
        raise HTTPException(409,'whatsapp_service_window_closed')
    sender=sender_document(session,business)
    if not sender or sender['phone_id']!=row.phone_id or c.settings(session,business).scope!=row.scope:
        raise HTTPException(409,'whatsapp_conversation_sender_changed')
    key=c.digest(business+':reply:'+payload.request_key)
    existing=session.get(WhatsAppReply,key)
    if existing:
        if existing.conversation_id!=row.id or existing.body!=payload.body: raise HTTPException(409,'reply_key_conflict')
        return {'id':key,'state':existing.state}
    session.add(WhatsAppReply(id=key,business_id=business,conversation_id=row.id,body=payload.body,
        actor=actor,sender_digest=c.digest(c.canonical(binding(sender)))))
    row.assigned_to=actor;row.state='assigned';session.commit()
    return {'id':key,'state':'queued'}


def dispatch_replies(sessions,integrations,now,business=None):
    with sessions() as session:
        session.execute(update(WhatsAppReply).where(WhatsAppReply.state=='sending',WhatsAppReply.claimed_at<now-timedelta(minutes=2)).values(state='unknown',reason='worker_interrupted'))
        session.commit()
        query=select(WhatsAppReply.id).where(WhatsAppReply.state=='queued')
        if business: query=query.where(WhatsAppReply.business_id==business)
        ids=list(session.scalars(query.limit(25)))
    for key in ids:
        with sessions() as session:
            reply=session.get(WhatsAppReply,key);lock(session,reply.business_id);session.refresh(reply)
            if reply.state!='queued': continue
            convo=session.get(WhatsAppConversation,reply.conversation_id);sender=sender_document(session,reply.business_id)
            adapter=next((v['adapter'] for v in integrations.values() if v['business_id']==reply.business_id and v['scope']==convo.scope and v['adapter'].name=='simulated_whatsapp'),None)
            reason=None
            if convo.scope!='test': reason='live_reply_disabled'
            elif c.settings(session,reply.business_id).scope!=convo.scope: reason='scope_mismatch'
            elif c.settings(session,reply.business_id).paused: reason='business_paused'
            elif convo.opted_out: reason='whatsapp_opt_out'
            elif not convo.last_inbound_at or now>=aware(convo.last_inbound_at)+timedelta(hours=24): reason='whatsapp_service_window_closed'
            elif not sender or sender['phone_id']!=convo.phone_id or c.digest(c.canonical(binding(sender)))!=reply.sender_digest: reason='whatsapp_sender_changed'
            elif sender['status']!='READY' or c.date(sender['expires_at'])<=now: reason='whatsapp_sender_not_ready'
            elif not adapter or adapter.capabilities.get('network') is not False or adapter.phone_id!=sender['phone_id']: reason='simulation_transport_required'
            if reason:
                reply.state,reply.reason='skipped',reason;session.commit();continue
            message=Message(reply.id,sender['phone_id'],convo.destination,'','',reply.body,'')
            reply.state,reply.claimed_at='sending',now;session.commit()
        try: outcome=adapter.submit(message)
        except Exception: outcome=Submission('unknown',reason='transport_interrupted')
        with sessions() as session:
            reply=session.get(WhatsAppReply,key)
            if reply.state in {'sending','unknown'}: reply.state,reply.provider_id,reply.reason=outcome.state,outcome.message_id,outcome.reason
            session.commit()
    return len(ids)


def sync_provider(session,business,adapter,now,observation=None):
    """Explicit provider read, retaining only supported exact template definitions.

    Does not establish account allowance, legal eligibility or live activation.
    Caller must use the business-bound integration, never a browser-supplied account.
    """
    sender=sender_document(session,business)
    if not sender or adapter.name!='whatsapp_cloud' or adapter.phone_id!=sender['phone_id'] or adapter.waba_id!=sender['waba_id']:
        raise HTTPException(409,'whatsapp_integration_binding_changed')
    if c.settings(session,business).scope=='test': raise HTTPException(409,'real_provider_evidence_cannot_enter_simulation')
    observation=observation if observation is not None else adapter.readiness()
    if observation['phone'].get('id')!=sender['phone_id']: raise HTTPException(409,'provider_phone_mismatch')
    if not observation['templates_complete']: raise HTTPException(409,'provider_template_catalogue_incomplete')
    lock(session,business)
    current=sender_document(session,business)
    if binding(current)!=binding(sender): raise HTTPException(409,'sender_changed_during_sync')
    scope=c.settings(session,business).scope
    if scope=='test': raise HTTPException(409,'real_provider_evidence_cannot_enter_simulation')
    observed=set()
    for raw in observation['templates']:
        observed.add((str(raw['id']),raw['language']))
        row=session.scalar(select(WhatsAppTemplate).where(WhatsAppTemplate.business_id==business,
            WhatsAppTemplate.provider_id==str(raw['id']),WhatsAppTemplate.language==raw['language']))
        if row is None:
            row=WhatsAppTemplate(business_id=business,provider_id=str(raw['id']),language=raw['language']);session.add(row)
        components=raw.get('components',[]);parts={p['type']:p for p in components}
        buttons=parts.get('BUTTONS',{}).get('buttons',[])
        supported=(raw['category']=='MARKETING' and len(parts)==len(components) and set(parts)<={'BODY','FOOTER','BUTTONS'}
            and len(buttons)==2 and buttons[0].get('type')=='URL' and buttons[0].get('url')==sender['link_origin']+'/campaign-link/{{1}}'
            and buttons[1].get('type')=='QUICK_REPLY')
        try:
            parsed=TemplateInput(provider_id=str(raw['id']),name=raw['name'],language=raw['language'],category=raw['category'],
                status=raw['status'],body=parts['BODY']['text'],footer=parts['FOOTER']['text'],
                source='authenticated Cloud API account '+sender['waba_id'],expires_at=(now+timedelta(hours=24)).isoformat())
        except (ValueError,KeyError): supported=False
        if supported:
            doc=parsed.model_dump(exclude={'status'})
            doc.update(url=buttons[0]['url'],url_button=buttons[0]['text'],opt_out_button=buttons[1]['text'],opt_out_payload='STOP')
            row.document,row.digest=c.canonical(doc),c.digest(c.canonical(doc));row.status=raw['status']
        else:
            # Never reinterpret media, authentication/utility or unsupported layouts as marketing.
            row.document=c.canonical({'provider_id':str(raw['id']),'name':raw['name'],'language':raw['language'],
                'source':'authenticated Cloud API; unsupported template shape','provider_observation':raw})
            row.digest=c.digest(row.document);row.status='UNSUPPORTED'
        row.status_at=now
    for row in session.scalars(select(WhatsAppTemplate).where(WhatsAppTemplate.business_id==business)):
        if (row.provider_id,row.language) not in observed: row.status='MISSING';row.status_at=now
    sender['provider_account_binding']=observation.get('phone_waba_binding_verified') is True
    sender['provider_observed_at']=now.isoformat()
    sender['provider_phone']=observation['phone']
    sender['provider_allowance']='requires_current_account_review'
    session.get(WhatsAppSender,business).document=c.canonical(sender)
    # Stable raw evidence fingerprint; no access token/headers or credentials retained.
    key=c.digest(business+':provider-sync:'+now.isoformat()+c.canonical(observation))
    if not session.get(WhatsAppEvidence,key):session.add(WhatsAppEvidence(id=key,business_id=business,scope=scope,
        kind='provider_sync',document=c.canonical(observation),raw_sha256=c.digest(c.canonical(observation)),provider_at=now,received_at=now))
    session.commit()
    return readiness(session,business,now)
