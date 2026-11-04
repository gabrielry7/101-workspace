"""Read-only provider evidence and immutable review packets, never send authorization."""
import json
from datetime import datetime,timedelta
from fastapi import HTTPException
from pydantic import Field,model_validator
from sqlalchemy import select
from . import campaigns as c,whatsapp,sms
from .campaign_models import CampaignRevision,ProviderTestReview
from .models import Customer
from .schemas import StrictModel


class TestReviewInput(StrictModel):
    campaign_id:str=Field(max_length=36)
    customer_id:str=Field(max_length=36)
    revision_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    max_cost_microusd:int=Field(ge=0,le=10_000_000)
    recipient_authorization_source:str=Field(min_length=10,max_length=500)
    expires_at:datetime

    @model_validator(mode='after')
    def timezone_required(self):
        if self.expires_at.tzinfo is None:raise ValueError('Timezone required')
        return self


def readiness(session,business,integrations,now):
    cfg=c.settings(session,business);wa=whatsapp.sender_document(session,business);sm=sms.sender_document(session,business)
    channels={}
    for name,sender,provider in [('whatsapp',wa,'whatsapp_cloud'),('sms',sm,'twilio_sms')]:
        integration=next((v for v in integrations.values() if v['business_id']==business and v['scope']==cfg.scope and v['adapter'].name==provider),None)
        blockers=[]
        if cfg.scope=='test':blockers.append('simulation_is_not_provider_verification')
        if not sender:blockers.append('sender_unconfigured')
        if not integration:blockers.append('real_provider_unconfigured')
        elif integration['adapter'].validate():blockers.extend(integration['adapter'].validate())
        observed=sender.get('provider_observed_at') if sender else None
        if not observed or now-c.date(observed)>timedelta(hours=24) or c.date(observed)>now:blockers.append('current_provider_observation_required')
        if name=='whatsapp':
            if not sender or sender.get('provider_account_binding') is not True:blockers.append('phone_waba_binding_not_verified')
            blockers.extend(['current_account_allowance_review_required','current_price_review_required','public_webhook_receipt_verification_required'])
        else:blockers.extend(['colombia_route_and_registration_review_required','current_price_review_required','inbound_and_receipt_capability_verification_required'])
        channels[name]={'state':'blocked' if blockers else 'ready_for_review','blockers':blockers,
            'provider_observed_at':observed,'configured_adapter':provider if integration else None}
    return {'business_id':business,'scope':cfg.scope,'channels':channels,'live_enabled':False,
        'provider_test_enabled':False,'note':'Review preparation is not permission to send. No provider call on page load.'}


def prepare_test(session,business,payload,actor,integrations,now):
    # Freeze the exact current campaign and one of its existing recipients.
    sms.lock(session,business)
    campaign=c.scoped_campaign(session,business,payload.campaign_id)
    revision=session.get(CampaignRevision,campaign.revision_id);doc=json.loads(revision.document)
    if doc['channel'] not in {'whatsapp','sms'}:raise HTTPException(422,'Phone channel required')
    if revision.digest!=payload.revision_digest:raise HTTPException(409,'preview_changed')
    recipient=next((r for r in doc['recipients'] if r['id']==payload.customer_id),None)
    if not recipient:raise HTTPException(404,'Recipient not in approved audience definition')
    if not now<payload.expires_at<=now+timedelta(hours=24):raise HTTPException(422,'Test review expires within24hours')
    customer=session.get(Customer,payload.customer_id)
    if not customer or customer.business_id!=business:raise HTTPException(404,'Customer not found')
    preflight=readiness(session,business,integrations,now);channel=doc['channel']
    blockers=list(preflight['channels'][channel]['blockers'])
    eligible=c.eligibility(session,business,customer,doc,now,expected_destination=recipient['destination'])
    blockers.extend(eligible['reasons'])
    if doc['scope']!='provider_test':blockers.append('provider_test_campaign_required')
    if len(doc['recipients'])!=1:blockers.append('single_recipient_campaign_required')
    if channel=='whatsapp':
        if not doc.get('whatsapp'):raise HTTPException(409,'Template required')
        message=whatsapp.render(doc,recipient,'<allocated-tracking-token>')
        sender=whatsapp.sender_document(session,business)
        estimate=sender.get('unit_cost_microusd') if sender else None
    else:
        message=sms.render(doc,recipient,'x'*43,'x'*43);sender=sms.sender_document(session,business)
        rate=sender.get('unit_cost_microusd') if sender else None
        estimate=None if rate is None else rate*message['segments']
    if estimate is None or estimate>payload.max_cost_microusd:blockers.append('test_cost_unknown_or_over_limit')
    blockers.append('separate_exact_message_authorization_and_activation_required')
    document={'business_id':business,'channel':channel,'execution_mode':'provider_test','source_scope':doc['scope'],
        'campaign_id':campaign.id,'revision_id':revision.id,'revision_digest':revision.digest,
        'recipient':recipient,'sender':doc['sender'],'message':message,'schedule':doc['scheduled_at'],
        'campaign_expiry':doc['expires_at'],'max_messages':1,'max_cost_microusd':payload.max_cost_microusd,
        'estimated_cost_microusd':estimate,'cost_currency':'USD','sender_digest':c.digest(c.canonical(sender)),
        'recipient_authorization_source':payload.recipient_authorization_source,'expires_at':payload.expires_at.isoformat(),
        'blockers':sorted(set(blockers)),'send_authorized':False,'at':now.isoformat()}
    raw=c.canonical(document);row=ProviderTestReview(business_id=business,revision_id=revision.id,actor=actor,digest=c.digest(raw),document=raw)
    session.add(row);session.commit()
    return {'id':row.id,'digest':row.digest,'document':document,'state':'blocked'}


def review(session,business,review_id,now):
    row=session.get(ProviderTestReview,review_id)
    if not row or row.business_id!=business:raise HTTPException(404,'Review not found')
    doc=json.loads(row.document);campaign=c.scoped_campaign(session,business,doc['campaign_id'])
    sender=(whatsapp if doc['channel']=='whatsapp' else sms).sender_document(session,business)
    stale=(campaign.revision_id!=row.revision_id or now>=c.date(doc['expires_at']) or c.digest(c.canonical(sender))!=doc['sender_digest'])
    return {'id':row.id,'digest':row.digest,'document':doc,'state':'stale' if stale else 'blocked','send_authorized':False}
