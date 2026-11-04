"""101 owns approval, eligibility, durable dispatch and attributed sales."""
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, update, func, or_
from fastapi import HTTPException
from pydantic import ConfigDict, Field, field_validator, model_validator
from typing import Literal
from .models import Customer, Order, Payment, RestaurantCommerceProfile, utcnow
from .campaign_models import (CampaignSettings, ContactPermission, PermissionEvidence, Campaign,
    CampaignRevision, CampaignApproval, CampaignJob, CampaignAttempt, CampaignEvent, CampaignVisit, CampaignOrderCredit)
from .campaign_email import render, VERSION
from .campaign_delivery import Message, Submission
from .staff import aware
from .schemas import StrictModel


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def date(value):
    return aware(datetime.fromisoformat(value.replace('Z', '+00:00')))


class Copy(StrictModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    subject: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=4000)
    terms: str = Field(min_length=1, max_length=1000)

    @field_validator('subject')
    @classmethod
    def header(cls, v):
        if '\n' in v or '\r' in v:
            raise ValueError('Invalid subject')
        return v


class Draft(StrictModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    channel: Literal['email', 'whatsapp', 'sms'] = 'email'
    sender: str = Field(min_length=3, max_length=320)
    content: Copy
    customer_ids: list[str] = Field(min_length=1, max_length=500)
    scheduled_at: datetime
    expires_at: datetime
    scope: Literal['test', 'provider_test', 'live'] = 'test'
    budget_microusd: int = Field(ge=0, le=100_000_000)
    # An existing commerce promotion may be associated; no discount engine here.
    promotion_code: str | None = Field(default=None, max_length=80)

    @model_validator(mode='after')
    def window(self):
        if self.scheduled_at.tzinfo is None or self.expires_at.tzinfo is None or self.expires_at <= self.scheduled_at:
            raise ValueError('An explicit timezone and positive window are required')
        if len(set(self.customer_ids)) != len(self.customer_ids):
            raise ValueError('Duplicate audience member')
        return self


def settings(session, business):
    row = session.get(CampaignSettings, business)
    if not row:
        raise HTTPException(409, 'campaign_business_unconfigured')
    return row


def scoped_campaign(session, business, campaign_id):
    row = session.get(Campaign, campaign_id)
    if not row or row.business_id != business:
        raise HTTPException(404, 'Campaign not found')
    return row


def normalized(customer, channel):
    value = customer.email if channel == 'email' else customer.phone
    if not value:
        return None
    if channel == 'email':
        value = value.strip().lower()
        return value if re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', value) else None
    return value if re.fullmatch(r'\+57\d{10}', value) else None


def set_permission(session, business, customer_id, *, channel, scope, state, source,
                   registry=None, reason=None, now=None):
    customer = session.get(Customer, customer_id)
    if not customer or customer.business_id != business:
        raise HTTPException(404, 'Customer not found')
    if channel not in {'email','sms','whatsapp'} or state not in {'granted','withdrawn','suppressed','unknown'} or not source:
        raise HTTPException(422, 'Invalid permission evidence')
    if settings(session, business).scope != scope:
        raise HTTPException(409, 'permission_scope_mismatch')
    row = session.scalar(select(ContactPermission).where(ContactPermission.business_id == business,
        ContactPermission.customer_id == customer_id, ContactPermission.channel == channel,
        ContactPermission.scope == scope, ContactPermission.purpose == 'marketing'))
    if not row:
        row = ContactPermission(business_id=business, customer_id=customer_id, channel=channel, scope=scope)
        session.add(row)
    row.state, row.source, row.reason = state, source, reason
    row.destination = normalized(customer, channel) or ''
    row.at = now or utcnow()
    row.registry_json = canonical(registry or {})
    session.flush()
    session.add(PermissionEvidence(permission_id=row.id, evidence_json=canonical({
        'state': state, 'source': source, 'reason': reason, 'destination': row.destination,
        'registry': registry or {}, 'scope': scope}), at=row.at))
    session.flush()
    return row


def eligibility(session, business, customer, document, now, *, expected_destination=None, exclude_job=None):
    reasons, unknown = [], []
    config_row = settings(session, business)
    config = json.loads(config_row.config_json)
    channel, scope = document['channel'], document['scope']
    if config_row.paused: reasons.append('business_paused')
    if config_row.scope != scope: reasons.append('scope_mismatch')
    if customer.business_id != business: reasons.append('wrong_business')
    destination = normalized(customer, channel)
    if not destination: reasons.append('missing_or_invalid_destination')
    if expected_destination and destination != expected_destination: reasons.append('destination_changed')
    permission = session.scalar(select(ContactPermission).where(ContactPermission.business_id == business,
        ContactPermission.customer_id == customer.id, ContactPermission.channel == channel,
        ContactPermission.purpose == 'marketing', ContactPermission.scope == scope))
    if not permission: unknown.append('permission_missing')
    elif permission.state != 'granted': reasons.append(permission.reason or 'permission_' + permission.state)
    elif permission.destination != destination: reasons.append('permission_destination_changed')
    if destination and session.scalar(select(ContactPermission.id).where(ContactPermission.business_id == business,
            ContactPermission.channel == channel, ContactPermission.scope == scope,
            ContactPermission.destination == destination, ContactPermission.state.in_(['suppressed','withdrawn'])).limit(1)):
        reasons.append('destination_suppressed')
    if permission:
        registry = json.loads(permission.registry_json)
        if registry.get('state') == 'excluded': reasons.append('rne_excluded')
        elif (registry.get('state') != 'clear' or not registry.get('source') or not registry.get('expires_at')
              or date(registry['expires_at']) <= now or registry.get('scope') != scope):
            unknown.append('rne_missing_or_stale')
    local = now.astimezone(ZoneInfo('America/Bogota'))
    holidays = config.get('holidays', {})
    if str(local.year) not in holidays: unknown.append('holiday_calendar_missing')
    elif local.date().isoformat() in holidays[str(local.year)]: reasons.append('colombian_holiday')
    start, end = (8, 15) if local.weekday() == 5 else (7, 19)
    if local.weekday() == 6 or not start <= local.hour + local.minute / 60 < end:
        reasons.append('outside_colombia_sending_hours')
    # Shared business/customer limit across channels; unknown transmissions reserve a slot.
    recent = session.scalar(select(func.count()).select_from(CampaignJob).where(
        CampaignJob.business_id == business, or_(CampaignJob.customer_id == customer.id, CampaignJob.destination == (destination or '!missing')),
        CampaignJob.scope == scope, CampaignJob.id != (exclude_job or ''),
        CampaignJob.claimed_at > now - timedelta(hours=config.get('frequency_hours', 24)),
        CampaignJob.state.in_(['sending','accepted','unknown','delivered','bounced','complaint'])))
    if recent: reasons.append('shared_contact_limit')
    if channel != 'email': reasons.append(channel + '_unconfigured')
    if document['sender'] != config.get('sender'): reasons.append('sender_unconfigured_or_changed')
    if scope != 'test':
        review = config.get('legal_review', {})
        if not review.get('source') or not review.get('expires_at') or date(review['expires_at']) <= now:
            unknown.append('current_legal_review_required')
        unknown.append('live_activation_not_implemented')
    return {'status': 'blocked' if reasons else 'unknown' if unknown else 'allowed',
            'reasons': reasons + unknown, 'destination': destination}


def save_draft(session, business, draft, now, campaign_id=None):
    cfg = settings(session, business)
    config = json.loads(cfg.config_json)
    campaign = scoped_campaign(session, business, campaign_id) if campaign_id else Campaign(business_id=business)
    # Serialize edit/approve/schedule/cancel through the same business lock.
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business)
        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
    if draft.scope != cfg.scope: raise HTTPException(409, 'scope_mismatch')
    recipients, seen = [], set()
    for cid in sorted(draft.customer_ids):
        c = session.get(Customer, cid)
        if not c or c.business_id != business: raise HTTPException(404, 'Customer not found')
        destination = normalized(c, draft.channel)
        recipients.append({'id': c.id, 'name': c.name or '', 'destination': destination,
                           'duplicate_destination': bool(destination and destination in seen)})
        if destination: seen.add(destination)
    if draft.promotion_code:
        from .models import Promotion
        promo = session.scalar(select(Promotion).where(Promotion.business_id == business, Promotion.code == draft.promotion_code))
        if not promo: raise HTTPException(404, 'Existing promotion not found')
        # A code can belong to only one active campaign, preserving primary credit.
        for other in session.scalars(select(Campaign).where(Campaign.business_id == business, Campaign.id != (campaign.id or ''))):
            rev = session.get(CampaignRevision, other.revision_id)
            if rev and json.loads(rev.document).get('promotion_code') == draft.promotion_code:
                raise HTTPException(409, 'promotion_already_bound')
    doc = draft.model_dump(mode='json')
    doc.update({'recipients': recipients, 'brand': config.get('brand', {'name':'Demo'}),
        'renderer': VERSION, 'provider': 'simulated_email' if draft.scope == 'test' else 'ses',
        'unit_cost_microusd': 0 if draft.scope == 'test' else config.get('unit_cost_microusd'),
        'attribution_window_days': 7, 'policy_version': 'co-marketing-v1',
        'audience_rule': 'explicit-existing-customers-v1'})
    for recipient in recipients:
        result = eligibility(session, business, session.get(Customer, recipient['id']), doc,
                             draft.scheduled_at, expected_destination=recipient['destination'])
        recipient['snapshot_eligible'] = result['status'] == 'allowed' and not recipient['duplicate_destination']
        recipient['snapshot_reasons'] = result['reasons']
    session.add(campaign)
    session.flush()
    revision = CampaignRevision(campaign_id=campaign.id, document=canonical(doc), digest=digest(canonical(doc)))
    session.add(revision)
    session.flush()
    campaign.revision_id, campaign.state = revision.id, 'draft'
    session.commit()
    return preview(session, business, campaign.id, now)


def preview(session, business, campaign_id, now):
    campaign = scoped_campaign(session, business, campaign_id)
    revision = session.get(CampaignRevision, campaign.revision_id)
    doc = json.loads(revision.document)
    rows = []
    for recipient in doc['recipients']:
        result = eligibility(session, business, session.get(Customer, recipient['id']), doc,
            date(doc['scheduled_at']), expected_destination=recipient['destination'])
        if not recipient.get('snapshot_eligible', False):
            result = {'status':'blocked','reasons':recipient.get('snapshot_reasons') or ['audience_snapshot_excluded']}
        if recipient['duplicate_destination']: result = {'status':'blocked','reasons':['duplicate_destination']}
        rows.append({**recipient, **result})
    allowed = sum(r['status'] == 'allowed' for r in rows)
    cost = doc['unit_cost_microusd']
    return {'id': campaign.id, 'state': campaign.state, 'revision_id': revision.id, 'digest': revision.digest,
        'document': doc, 'audience': rows, 'eligible': allowed, 'excluded': len(rows)-allowed,
        'estimated_cost_microusd': None if cost is None else allowed * cost,
        'cost_currency': 'USD', 'simulation_clock': now.isoformat(),
        'email': render(doc, next((r for r in doc['recipients'] if r.get('snapshot_eligible')), doc['recipients'][0]), '#preview-ordering-link', '#preview-unsubscribe'),
        'approved': session.get(CampaignApproval, revision.id) is not None}


def approve(session, business, campaign_id, expected_digest, actor, now):
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business)
        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
    campaign = scoped_campaign(session, business, campaign_id)
    session.refresh(campaign)
    revision = session.get(CampaignRevision, campaign.revision_id)
    doc = json.loads(revision.document)
    if revision.digest != expected_digest or digest(revision.document) != expected_digest:
        raise HTTPException(409, 'preview_changed')
    if doc['scope'] != 'test': raise HTTPException(409, 'live_send_disabled')
    if doc['channel'] != 'email': raise HTTPException(409, doc['channel'] + '_unconfigured')
    if date(doc['expires_at']) <= now: raise HTTPException(409, 'campaign_expired')
    cost = doc['unit_cost_microusd']
    if cost is None or cost * len(doc['recipients']) > doc['budget_microusd']:
        raise HTTPException(409, 'budget_exceeded_or_unknown')
    if not session.get(CampaignApproval, revision.id):
        session.add(CampaignApproval(revision_id=revision.id, actor_id=actor, digest=expected_digest, scope=doc['scope']))
    if campaign.state != 'scheduled': campaign.state = 'approved'
    session.commit()
    return preview(session, business, campaign_id, now)


def schedule(session, business, campaign_id, expected_digest, now):
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business)
        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
    campaign = scoped_campaign(session, business, campaign_id)
    session.refresh(campaign)
    revision = session.get(CampaignRevision, campaign.revision_id)
    approval = session.get(CampaignApproval, revision.id)
    if not approval or campaign.state not in {'approved','scheduled'} or approval.digest != expected_digest or revision.digest != expected_digest:
        raise HTTPException(409, 'valid_approval_required')
    doc = json.loads(revision.document)
    if date(doc['expires_at']) <= now: raise HTTPException(409, 'campaign_expired')
    for recipient in doc['recipients']:
        key = digest(':'.join([business, revision.id, recipient['id'], doc['channel']]))
        if not session.get(CampaignJob, key):
            session.add(CampaignJob(id=key, business_id=business, revision_id=revision.id,
                customer_id=recipient['id'], destination=recipient['destination'] or '',
                channel=doc['channel'], scope=doc['scope'], provider=doc['provider'],
                due_at=date(doc['scheduled_at']), tracking_token=secrets.token_urlsafe(32),
                unsubscribe_token=secrets.token_urlsafe(32),
                state='queued' if recipient.get('snapshot_eligible') else 'skipped',
                reason=None if recipient.get('snapshot_eligible') else ','.join(recipient.get('snapshot_reasons') or ['duplicate_destination'])))
    campaign.state = 'scheduled'
    session.commit()
    return {'state':'scheduled'}


def cancel(session, business, campaign_id):
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business)
        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
    campaign = scoped_campaign(session, business, campaign_id)
    campaign.state = 'cancelled'
    revisions = select(CampaignRevision.id).where(CampaignRevision.campaign_id == campaign.id)
    session.execute(update(CampaignJob).where(CampaignJob.revision_id.in_(revisions), CampaignJob.state == 'queued')
                    .values(state='skipped', reason='campaign_cancelled'))
    session.commit()
    return {'state':'cancelled', 'note':'Submitted messages cannot be recalled'}


def dispatch(sessions, integrations, *, now=None, base_url='http://127.0.0.1:8799', limit=25, business=None):
    now = now or utcnow()
    # An expired transmission lease is UNKNOWN, never automatically requeued.
    with sessions() as session:
        session.execute(update(CampaignJob).where(CampaignJob.state == 'sending',
            CampaignJob.claimed_at < now-timedelta(minutes=2)).values(state='unknown', reason='worker_interrupted'))
        session.commit()
        query = select(CampaignJob.id).where(CampaignJob.state == 'queued', CampaignJob.due_at <= now)
        if business: query = query.where(CampaignJob.business_id == business)
        ids = list(session.scalars(query.order_by(CampaignJob.due_at, CampaignJob.id).limit(limit)))
    processed = 0
    for job_id in ids:
        with sessions() as session:
            job = session.get(CampaignJob, job_id)
            # Atomic UPDATE lock works for SQLite and PostgreSQL and serializes contact checks.
            session.execute(update(CampaignSettings).where(CampaignSettings.business_id == job.business_id)
                .values(dispatch_version=CampaignSettings.dispatch_version + 1))
            session.refresh(job)
            if job.state != 'queued':
                session.rollback()
                continue
            revision = session.get(CampaignRevision, job.revision_id)
            campaign = session.get(Campaign, revision.campaign_id)
            approval = session.get(CampaignApproval, revision.id)
            doc = json.loads(revision.document)
            reason = None
            if campaign.state != 'scheduled': reason = 'campaign_' + campaign.state
            elif campaign.revision_id != revision.id: reason = 'revision_superseded'
            elif not approval or approval.digest != revision.digest or digest(revision.document) != revision.digest or approval.scope != job.scope:
                reason = 'approval_invalid'
            elif doc['renderer'] != VERSION: reason = 'renderer_revision_changed'
            elif job.scope != 'test': reason = 'global_live_send_disabled'
            elif date(doc['expires_at']) <= now: reason = 'campaign_expired'
            elif date(doc['scheduled_at']) > now: reason = 'schedule_not_due'
            elif doc['unit_cost_microusd'] is None or doc['unit_cost_microusd'] * len(doc['recipients']) > doc['budget_microusd']:
                reason = 'budget_exceeded_or_unknown'
            adapter = next((v['adapter'] for v in integrations.values() if v['business_id'] == job.business_id
                and v['scope'] == job.scope and v['adapter'].name == job.provider), None)
            if not adapter or adapter.validate(): reason = reason or 'provider_unconfigured'
            elif job.scope == 'test' and adapter.capabilities.get('network') is not False:
                reason = reason or 'simulation_network_transport_forbidden'
            result = eligibility(session, job.business_id, session.get(Customer, job.customer_id), doc, now,
                expected_destination=job.destination, exclude_job=job.id)
            if result['status'] != 'allowed': reason = reason or ','.join(result['reasons'])
            if reason:
                job.state, job.reason = 'skipped', reason
                session.commit()
                processed += 1
                continue
            recipient = next(r for r in doc['recipients'] if r['id'] == job.customer_id)
            unsub = base_url + '/campaign-unsubscribe/' + job.unsubscribe_token
            email = render(doc, recipient, base_url + '/campaign-link/' + job.tracking_token, unsub)
            message = Message(job.id, doc['sender'], job.destination, email['subject'], email['html'], email['text'], unsub)
            job.state, job.claimed_at, job.attempts = 'sending', now, job.attempts + 1
            session.add(CampaignAttempt(job_id=job.id, state='sending', evidence_json=canonical({'attempt':job.attempts})))
            session.commit()  # Dispatch boundary: later cancellation cannot recall this attempt.
        try:
            outcome = adapter.submit(message)
        except Exception:
            outcome = Submission('unknown', reason='transport_interrupted')
        with sessions() as session:
            job = session.get(CampaignJob, job_id)
            if job.state in {'sending','unknown'}:
                job.state, job.provider_id, job.reason = outcome.state, outcome.message_id, outcome.reason
                if outcome.state == 'accepted': job.submitted_at = now
                if outcome.state == 'retryable':
                    job.state = 'queued' if job.attempts < 3 else 'failed'
                    job.due_at = now + timedelta(seconds=30 * 2 ** job.attempts)
            session.add(CampaignAttempt(job_id=job.id, state=outcome.state,
                evidence_json=canonical({'message_id':outcome.message_id,'reason':outcome.reason})))
            session.commit()
        processed += 1
    return {'processed': processed, 'mode':'test', 'real_provider_calls':0}


def ingest_event(session, integration, event, now):
    job = session.get(CampaignJob, event.get('key'))
    if not job or job.business_id != integration['business_id'] or job.scope != integration['scope'] or job.provider != integration['adapter'].name:
        raise HTTPException(404, 'Delivery not found for authenticated integration')
    if not job.attempts or job.state == 'skipped': raise HTTPException(409, 'delivery_not_submitted')
    if job.provider_id and job.provider_id != event.get('message_id'): raise HTTPException(409, 'provider_message_mismatch')
    if event.get('kind') not in {'accepted','delivered','bounced','complaint','rejected','delayed','unsubscribe'}:
        raise HTTPException(422, 'unsupported_event')
    key = digest(integration['adapter'].name + ':' + job.business_id + ':' + str(event['id']))
    existing = session.get(CampaignEvent, key)
    evidence = canonical(event)
    if existing:
        if existing.evidence_json != evidence: raise HTTPException(409, 'event_identity_conflict')
        return {'duplicate':True}
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    insert = pg_insert if session.bind.dialect.name == 'postgresql' else sqlite_insert
    session.execute(insert(CampaignEvent).values(id=key, job_id=job.id, kind=event['kind'],
        provider_at=date(event['at']), received_at=now, evidence_json=evidence).on_conflict_do_nothing(index_elements=['id']))
    session.flush()
    existing = session.get(CampaignEvent, key)
    if existing.evidence_json != evidence: raise HTTPException(409, 'event_identity_conflict')
    kinds = set(session.scalars(select(CampaignEvent.kind).where(CampaignEvent.job_id == job.id)))
    # Preserve history; derive projection independent of arrival order.
    for status in ('complaint','bounced','delivered','rejected','accepted'):
        if status in kinds:
            job.state = status
            break
    job.provider_id = event['message_id']
    if kinds & {'accepted','delivered','bounced','complaint'}: job.submitted_at = job.submitted_at or now
    if kinds & {'bounced','complaint','unsubscribe'}:
        set_permission(session, job.business_id, job.customer_id, channel=job.channel, scope=job.scope,
            state='suppressed', source='authenticated:' + key, reason=event['kind'], now=now)
    session.commit()
    return {'duplicate':False}


def unsubscribe(session, token, now):
    job = session.scalar(select(CampaignJob).where(CampaignJob.unsubscribe_token == token))
    if not job: raise HTTPException(404, 'Link not found')
    session.execute(update(CampaignSettings).where(CampaignSettings.business_id == job.business_id)
        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
    set_permission(session, job.business_id, job.customer_id, channel=job.channel, scope=job.scope,
        state='withdrawn', source='unsubscribe_link', reason='unsubscribed', now=now)
    session.commit()


def visit(session, token, now, user_agent):
    job = session.scalar(select(CampaignJob).where(CampaignJob.tracking_token == token))
    if not job or job.state not in {'accepted','delivered','unknown','complaint','bounced'}:
        raise HTTPException(404, 'Link not found')
    doc = json.loads(session.get(CampaignRevision, job.revision_id).document)
    if date(doc['expires_at']) <= now: raise HTTPException(410, 'Campaign expired')
    raw = secrets.token_urlsafe(32)
    scanner = bool(re.search(r'bot|spider|scanner|proofpoint|safelinks', user_agent, re.I))
    row = CampaignVisit(token_hash=digest(raw), job_id=job.id, at=now, scanner=scanner,
        evidence_json=canonical({'user_agent':user_agent[:300], 'identity':'not_verified'}))
    session.add(row)
    session.commit()
    return job.business_id, raw


def checkout_context(session, business, token, now, *, demo_mode):
    if not token: return None
    row = session.scalar(select(CampaignVisit).where(CampaignVisit.token_hash == digest(token)))
    if not row or row.scanner or aware(row.at) > now or aware(row.at) < now-timedelta(days=7): return None
    job = session.get(CampaignJob, row.job_id)
    if job.business_id != business or (job.scope == 'test' and not demo_mode) or (job.scope != 'test' and demo_mode): return None
    return {'source_channel':job.channel, 'external_source_ref':'campaign-visit:' + row.id}


def report(session, business, campaign_id, scope):
    campaign = scoped_campaign(session, business, campaign_id)
    revs = list(session.scalars(select(CampaignRevision).where(CampaignRevision.campaign_id == campaign.id)))
    jobs = list(session.scalars(select(CampaignJob).where(CampaignJob.revision_id.in_([r.id for r in revs]), CampaignJob.scope == scope)))
    visits = list(session.scalars(select(CampaignVisit).where(CampaignVisit.job_id.in_([j.id for j in jobs]))))
    paid_orders, captured, refunded, credited = 0, 0, 0, []
    credits = session.scalars(select(CampaignOrderCredit).where(
        CampaignOrderCredit.revision_id.in_([r.id for r in revs]), CampaignOrderCredit.scope == scope))
    for credit in credits:
        order = session.get(Order, credit.order_id)
        if order.business_id != business: continue
        confirmed = list(session.scalars(select(Payment).where(Payment.order_id == order.id, Payment.status.in_(['paid','refunded']))))
        if not confirmed or (scope == 'test') != all(p.provider == 'simulated' for p in confirmed): continue
        paid_orders += 1
        captured += order.total_minor
        from .refunds import refunded_total
        amount = max(refunded_total(session, p) for p in confirmed)
        refunded += amount
        credited.append({'order_id':order.id,'currency':order.currency,'captured':order.total_minor,'refunds':amount,
                         'net':order.total_minor-amount,'rule':'code-first-else-last-eligible-visit-7d-v1'})
    states = {}
    for job in jobs: states[job.state] = states.get(job.state, 0)+1
    events = list(session.scalars(select(CampaignEvent).where(CampaignEvent.job_id.in_([j.id for j in jobs]))))
    accepted = {j.id for j in jobs if j.submitted_at is not None}
    delivered = {e.job_id for e in events if e.kind == 'delivered'}
    return {'scope':scope,'states':states,'queued':states.get('queued',0),'provider_accepted':len(accepted),
        'provider_reported_delivery':len(delivered),'receipt_missing':len(accepted-delivered),
        'unknown':states.get('unknown',0),'tracked_visits':len(visits),'scanner_visits':sum(v.scanner for v in visits),
        'paid_orders':paid_orders,'captured_revenue':captured,'refunds':refunded,'net_revenue':captured-refunded,
        'currency':session.get(RestaurantCommerceProfile, business).currency,'accounting':'Whole COP pesos; order total includes discounts and delivery; no second discount subtraction.',
        'delivery_cost_microusd':0 if scope == 'test' else None,'cost_currency':'USD','orders':credited,
        'read_signals':'unavailable','profit':None,
        'limitations':['Attributed sales, not incremental lift.','Clicks may be scanners or forwarded links; identity is not established.',
                       'Seven-day browser context; cross-device and offline coverage incomplete.']}


def attach_order_credit(session, order):
    """Called inside the canonical order transaction after promo reservation.

    Never reads a raw client-supplied customer/campaign identifier. The API clears
    public source fields and replaces them only with a validated opaque visit.
    """
    from .models import PromotionRedemption, Promotion
    if session.get(CampaignOrderCredit, order.id): return
    cfg = session.get(CampaignSettings, order.business_id)
    if not cfg: return
    config = json.loads(cfg.config_json)
    now = date(config['simulation_clock']) if cfg.scope == 'test' and config.get('simulation_clock') else utcnow()
    visit_row, revision = None, None
    if (order.external_source_ref or '').startswith('campaign-visit:'):
        candidate = session.get(CampaignVisit, order.external_source_ref.split(':',1)[1])
        if candidate and not candidate.scanner and now-timedelta(days=7) <= aware(candidate.at) <= now:
            job = session.get(CampaignJob, candidate.job_id)
            if job.business_id == order.business_id and job.scope == cfg.scope:
                visit_row, revision = candidate, session.get(CampaignRevision, job.revision_id)
    redemption = session.scalar(select(PromotionRedemption).where(PromotionRedemption.order_id == order.id))
    if redemption and redemption.status == 'reserved':
        promo = session.get(Promotion, redemption.promotion_id)
        for rev in session.scalars(select(CampaignRevision).join(Campaign, Campaign.id == CampaignRevision.campaign_id)
                                  .where(Campaign.business_id == order.business_id).order_by(CampaignRevision.created_at.desc())):
            doc = json.loads(rev.document)
            if (doc.get('promotion_code') == promo.code and doc['scope'] == cfg.scope
                and session.get(CampaignApproval, rev.id) and date(doc['scheduled_at']) <= now < date(doc['expires_at'])):
                revision = rev
                break
    if revision:
        session.add(CampaignOrderCredit(order_id=order.id, revision_id=revision.id,
            visit_id=visit_row.id if visit_row else None, scope=cfg.scope,
            rule='code-first-else-last-eligible-visit-7d-v1'))
