"""Business-owned SMS policy. Canonical customers/orders and shared jobs are reused."""
import json
import re
import unicodedata
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from fastapi import HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select,update
from . import campaigns as c
from .campaign_models import SmsSender,SmsEvidence,SmsSuppression,CampaignSettings,CampaignJob,CampaignRevision,ContactPermission
from .models import Customer
from .schemas import StrictModel
from .sms_delivery import segments,provider_reason


class SenderInput(StrictModel):
    account_sid:str=Field(pattern=r'^AC[a-fA-F0-9]{32}$')
    sender:str=Field(pattern=r'^(?:\+[1-9]\d{7,14}|\d{3,6})$')
    route:Literal['international_long_code','short_code','unverified']='unverified'
    link_origin:str=Field(max_length=300)
    status:Literal['UNVERIFIED','READY','RESTRICTED']='UNVERIFIED'
    inbound_supported:bool=False
    delivery_receipts:Literal['available','unavailable','unknown']='unknown'
    max_segments:int=Field(default=1,ge=1,le=10)
    unit_cost_microusd:int|None=Field(default=None,ge=0,le=10_000_000)
    source:str=Field(min_length=5,max_length=500)
    expires_at:datetime

    @model_validator(mode='after')
    def valid(self):
        p=urlsplit(self.link_origin)
        if p.scheme not in {'https','http'} or not p.hostname or p.username or p.password or p.path or p.query or p.fragment:
            raise ValueError('Use an origin without path/query/credentials')
        if self.expires_at.tzinfo is None:raise ValueError('Timezone required')
        if self.route=='international_long_code' and (not self.sender.startswith('+') or self.sender.startswith('+57')):
            raise ValueError('Colombia domestic long code not supported by this adapter route')
        if self.route=='short_code' and not re.fullmatch(r'\d{3,6}',self.sender):raise ValueError('Short code required')
        return self


def lock(session,business):
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id==business).values(dispatch_version=CampaignSettings.dispatch_version+1))


def sender_document(session,business):
    row=session.get(SmsSender,business)
    return json.loads(row.document) if row else None


def configure(session,business,payload,now):
    cfg=c.settings(session,business);lock(session,business)
    doc=payload.model_dump(mode='json');binding=c.digest(doc['account_sid']+':'+doc['sender'])
    other=session.scalar(select(SmsSender).where(SmsSender.binding_key==binding,SmsSender.business_id!=business))
    if other:raise HTTPException(409,'sms_sender_already_bound')
    if cfg.scope!='test':
        if not doc['link_origin'].startswith('https://'):raise HTTPException(422,'https_required')
        doc.update(status='UNVERIFIED',unit_cost_microusd=None,inbound_supported=False,delivery_receipts='unknown')
    row=session.get(SmsSender,business)
    if row is None:row=SmsSender(business_id=business,scope=cfg.scope,binding_key=binding);session.add(row)
    row.scope,row.binding_key,row.document,row.updated_at=cfg.scope,binding,c.canonical(doc),now
    session.commit();return readiness(session,business)


def readiness(session,business):
    cfg=c.settings(session,business);doc=sender_document(session,business)
    return {'scope':cfg.scope,'state':'unconfigured' if doc is None else 'simulation_only' if cfg.scope=='test' else 'configured_inactive',
        'sender':doc,'live_enabled':False,'provider_verified':False,
        'withdrawal':'Tracked unsubscribe link; reply STOP/BAJA only if this route supports inbound messages'}


def render(document,recipient,tracking_token,unsubscribe_token):
    snap=document['sms'];origin=snap['link_origin']
    body=document['content']['body'].replace('{name}',recipient['name'] or 'cliente')
    text=f"{document['brand']['name']}: {body}\n{document['content']['terms']}\nPide: {origin}/campaign-link/{tracking_token}\nBaja: {origin}/campaign-unsubscribe/{unsubscribe_token}"
    if snap['inbound_supported']:text+='\nO responde BAJA.'
    return {'text':text,**segments(text)}


def snapshot(session,business):
    doc=sender_document(session,business)
    if doc is None:raise HTTPException(409,'sms_unconfigured')
    return doc


def suppressed(session,business,scope,destination):
    return session.get(SmsSuppression,c.digest(business+':'+scope+':'+(destination or '')))


def eligibility(session,business,customer,document,now,exclude_job):
    current=sender_document(session,business);snap=document.get('sms');reasons=[]
    if not current or not snap:return ['sms_unconfigured']
    if current!=snap or document['sender']!=current['sender']:reasons.append('sms_sender_or_route_changed')
    if current['status']!='READY' or current['route']=='unverified':reasons.append('sms_route_unverified')
    if c.date(current['expires_at'])<=now:reasons.append('sms_route_evidence_stale')
    if current['unit_cost_microusd'] is None:reasons.append('sms_price_unknown')
    if not re.fullmatch(r'\+573\d{9}',customer.phone or ''):reasons.append('sms_colombia_mobile_required')
    if suppressed(session,business,document['scope'],customer.phone):reasons.append('sms_opt_out')
    recipient=next(r for r in document['recipients'] if r['id']==customer.id)
    try:
        size=render(document,recipient,'x'*43,'x'*43)
        if size['over_limit'] or size['segments']>current['max_segments']:reasons.append('sms_segment_limit')
    except ValueError:reasons.append('sms_invalid_content')
    return reasons


def opt_out(session,business,scope,destination,source,now):
    key=c.digest(business+':'+scope+':'+destination)
    if not session.get(SmsSuppression,key):session.add(SmsSuppression(id=key,business_id=business,scope=scope,destination=destination,source=source,at=now))
    for customer in session.scalars(select(Customer).where(Customer.business_id==business,Customer.phone==destination)):
        c.set_permission(session,business,customer.id,channel='sms',scope=scope,state='withdrawn',source=source,reason='sms_opt_out',now=now)


def ingest(session,integration,event,raw_sha,now):
    business,scope,adapter=integration['business_id'],integration['scope'],integration['adapter']
    lock(session,business);cfg=c.settings(session,business);sender=sender_document(session,business)
    if not sender or cfg.scope!=scope or sender['account_sid']!=adapter.account_sid or sender['sender']!=adapter.sender:
        raise HTTPException(409,'sms_integration_binding_changed')
    key=c.digest(business+':'+scope+':'+adapter.account_sid+':'+event['id'])
    evidence=c.canonical(event);old=session.get(SmsEvidence,key)
    if old:
        if old.document!=evidence:raise HTTPException(409,'sms_event_identity_conflict')
        return {'duplicate':True}
    job=None
    if event['kind']=='inbound':
        if not sender['inbound_supported']:raise HTTPException(409,'sms_inbound_unavailable')
        text=''.join(ch for ch in unicodedata.normalize('NFKD',event['text'].strip().casefold()) if not unicodedata.combining(ch)).strip(' .!')
        if text in {'stop','stopall','baja','salir','cancelar','no mas','no mas mensajes','unsubscribe','end','quit'}:
            opt_out(session,business,scope,event['destination'],'sms-inbound:'+event['message_id'],now)
        # HELP and ordinary replies are retained for staff, never auto-regrant consent.
    else:
        job=session.get(CampaignJob,event['key'])
        if not job or job.business_id!=business or job.channel!='sms' or job.destination!=event['destination']:
            raise HTTPException(404,'sms_delivery_not_bound')
        normalized={k:event[k] for k in ['id','key','message_id','kind']}
        normalized.update(at=now.isoformat(),provider_timestamp_unavailable=True,raw_sha256=raw_sha)
        c.ingest_event(session,integration,normalized,now,commit=False)
        if event['error']:
            job.reason=provider_reason(event['error'])
            if event['error']==21610:opt_out(session,business,scope,job.destination,'sms-provider:'+event['id'],now)
    session.add(SmsEvidence(id=key,business_id=business,scope=scope,job_id=job.id if job else None,
        kind=event['kind'],document=evidence,raw_sha256=raw_sha,received_at=now))
    session.commit();return {'duplicate':False}


def report_details(session,business,campaign_id,scope):
    revisions=list(session.scalars(select(CampaignRevision).where(CampaignRevision.campaign_id==campaign_id)))
    ids=[r.id for r in revisions];cost=0;units=0
    for rev in revisions:
        doc=json.loads(rev.document)
        if doc['scope']!=scope or not doc.get('sms'):continue
        for job in session.scalars(select(CampaignJob).where(CampaignJob.revision_id==rev.id,CampaignJob.attempts>0)):
            rec=next(r for r in doc['recipients'] if r['id']==job.customer_id)
            seg=render(doc,rec,job.tracking_token,job.unsubscribe_token)['segments'];units+=seg
            rate=doc['sms']['unit_cost_microusd']
            cost=None if rate is None or cost is None else cost+rate*seg
    events=session.scalars(select(SmsEvidence).join(CampaignJob,CampaignJob.id==SmsEvidence.job_id).where(
        SmsEvidence.business_id==business,SmsEvidence.scope==scope,CampaignJob.revision_id.in_(ids)))
    statuses={}
    for e in events:
        status=json.loads(e.document)['provider_status'];statuses.setdefault(status,set()).add(e.job_id)
    return {'estimated_submitted_segments':units,'estimated_delivery_cost_microusd':cost,
        'provider_status_counts':{k:len(v) for k,v in statuses.items()},'status_counts_are_historical_non_additive':True,
        'route_receipt_support':sorted({json.loads(r.document)['sms']['delivery_receipts'] for r in revisions if json.loads(r.document).get('sms') and json.loads(r.document)['scope']==scope}),
        'read_signals':'unavailable',
        'cost_note':'Estimate from frozen route rate; actual provider invoice/fees not verified. Simulation incurs zero cost.'}
