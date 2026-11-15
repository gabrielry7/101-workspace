"""Offline social production. No provider calls or publication authority.

Owner assertions remain marketing inputs, never promoted to canonical Truth.
Original bytes and editable revisions remain separate from rendered outputs.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from sqlalchemy import ForeignKey, LargeBinary, String, Text, select, update
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, utcnow

VERSION = 'social-photo-v1'
MAX_BYTES = 12 * 1024 * 1024
TABLES = {'social_assets', 'social_packs', 'social_revisions', 'social_approvals'}


class Asset(Base):
    __tablename__ = 'social_assets'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), index=True)
    metadata_json: Mapped[str] = mapped_column(Text)
    original: Mapped[bytes] = mapped_column(LargeBinary)
    revoked: Mapped[bool] = mapped_column(default=False)


class Pack(Base):
    __tablename__ = 'social_packs'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'), index=True)
    revision: Mapped[int] = mapped_column(default=0)


class Revision(Base):
    __tablename__ = 'social_revisions'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey('social_packs.id'), index=True)
    document: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    image: Mapped[bytes] = mapped_column(LargeBinary)
    report: Mapped[str] = mapped_column(Text)


class Approval(Base):
    __tablename__ = 'social_approvals'
    revision_id: Mapped[str] = mapped_column(ForeignKey('social_revisions.id'), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    digest: Mapped[str] = mapped_column(String(64))
    approved_at: Mapped[str] = mapped_column(String(64))


def upgrade(engine):
    """Explicit additive offline migration; stop writers and back up first."""
    from .social_migrations import upgrade_social
    upgrade_social(engine)


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Fact(Strict):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    text: str = Field(min_length=1, max_length=600)
    source: str = Field(min_length=1, max_length=300)
    valid_until: AwareDatetime


class FactReference(Strict):
    context_version_id: str = Field(max_length=100)
    fact_id: str = Field(max_length=64)
    fact_revision: int = Field(ge=1)



class Brief(Strict):
    schema_version: Literal['1'] = '1'
    location_id: UUID | None = None
    context_version_id: str | None = Field(default=None, max_length=100)
    fact_refs: list[FactReference] = Field(default_factory=list, max_length=12)
    creative_version_id: str | None = Field(default=None, max_length=100)
    reference_ids: list[str] = Field(default_factory=list, max_length=12)
    question_id: str | None = Field(default=None, max_length=64)
    revision_reason: Literal['initial', 'factual_correction', 'brand_preference', 'strategy', 'layout'] = 'initial'
    proposal_decision_id: str | None = Field(default=None,max_length=64)
    request_id: UUID
    asset_id: str
    objective: str = Field(min_length=1, max_length=300)
    hypothesis: str = Field(min_length=1, max_length=600)
    question: str = Field(min_length=1, max_length=300)
    question_source: Literal['owner_suggestion', 'customer_question', 'hypothesis', 'platform_observation', 'manual_research']
    question_evidence: str = Field(min_length=1, max_length=500)
    facts: list[Fact] = Field(min_length=1, max_length=12)
    caption_fact_ids: list[str] = Field(min_length=1, max_length=12)
    # Restrained first family: real photo, editable focal point, caption assembled
    # only from explicitly confirmed statements. No fabricated generative copy.
    focal_x: float = Field(default=.5, ge=0, le=1)
    focal_y: float = Field(default=.5, ge=0, le=1)
    brand_direction: str = Field(min_length=1, max_length=600)
    reference_reason: str = Field(min_length=1, max_length=600)
    primary_measure: Literal['qualified_inquiries', 'orders', 'reach', 'owner_effort']
    confirmed: Literal[True]
    expected_revision: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def references(self):
        if len(set(self.reference_ids)) != len(self.reference_ids):
            raise ValueError('duplicate_reference')
        ids = [f.id for f in self.facts]
        if len(set(ids)) != len(ids) or not set(self.caption_fact_ids) <= set(ids):
            raise ValueError('unresolved_or_duplicate_fact')
        for fact in self.facts:
            if any(ord(c) < 32 and c not in '\n\t' for c in fact.text) or re.search(r'\[[^]]+\]', fact.text):
                raise ValueError('placeholder_or_control_character')
        if len({r.fact_id for r in self.fact_refs}) != len(self.fact_refs):
            raise ValueError('duplicate_fact_reference')
        return self


class Intake(Strict):
    data_base64: str = Field(max_length=700_000)
    rights_statement: str = Field(min_length=8, max_length=600)
    expires_at: AwareDatetime
    permitted_use: Literal['production', 'reference_only']
    captured_at: AwareDatetime | None = None
    fixture: bool = False


class Decision(Strict):
    digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    craft_reviewed: Literal[True]
    brand_reviewed: Literal[True]
    purpose_reviewed: Literal[True]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def require(condition, reason, status=409):
    if not condition:
        raise HTTPException(status, reason)


def future(value, now):
    return datetime.fromisoformat(value).astimezone(timezone.utc) > now.replace(tzinfo=timezone.utc)


def owned(session, model, identifier, business):
    row = session.get(model, identifier)
    require(row is not None and row.business_id == business, 'not_found', 404)
    return row


def asset_check(session, identifier, business, now):
    row = owned(session, Asset, identifier, business)
    meta = json.loads(row.metadata_json)
    require(not row.revoked and bool(row.original), 'source_deleted_or_revoked')
    require(meta['permitted_use'] == 'production', 'reference_only_asset')
    require(future(meta['expires_at'], now), 'asset_expired')
    return row, meta


def render(original, brief):
    started = time.monotonic()
    with Image.open(io.BytesIO(original)) as source:
        require(source.width * source.height <= 24_000_000, 'image_pixel_limit', 422)
        image = ImageOps.exif_transpose(source).convert('RGB')
        require(image.width >= 1080 and image.height >= 1350, 'photo_resolution_too_small', 422)
        # Photo-first, deliberately no text overlay: no clipped prices or glyphs.
        image = ImageOps.fit(image, (1080,1350), centering=(brief.focal_x,brief.focal_y))
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=94)
    return output.getvalue(), {'renderer':VERSION, 'width':1080, 'height':1350,
        'render_ms':round((time.monotonic()-started)*1000), 'model_calls':0,
        'provider_cost_usd':0, 'compute_cost_usd':None,
        'technical':'passed', 'craft':'requires_human_review', 'brand':'requires_human_review',
        'purpose':'requires_human_review', 'performance':'unavailable'}


def pack_state(session, business, pack_id, now):
    from .social_context import stale_reasons
    pack = owned(session, Pack, pack_id, business)
    rev = session.get(Revision, f'{pack.id}:{pack.revision}')
    require(rev is not None, 'missing_revision')
    doc = json.loads(rev.document)
    from .social_creative import stale_reasons as creative_stale
    reasons = stale_reasons(session, business, doc, now) + creative_stale(session, business, doc, now)
    for fact in doc['brief']['facts']:
        if not future(fact['valid_until'], now):
            reasons.append({'fact_id': fact['id'], 'reason': 'fact_expired'})
    media_available = True
    try:
        asset_check(session, doc['brief']['asset_id'], business, now)
    except HTTPException as error:
        reasons.append({'reason': error.detail})
        media_available = False
    if doc['brief'].get('proposal_decision_id'):
        from .social_proposals import current_decision
        try: current_decision(session,business,doc['brief']['proposal_decision_id'])
        except HTTPException as error: reasons.append({'reason':error.detail})
    approval = session.get(Approval, rev.id)
    return pack, rev, doc, approval, reasons, media_available


def current(session, business, pack_id, now):
    pack, rev, doc, approval, reasons, _ = pack_state(session, business, pack_id, now)
    require(not reasons, reasons[0]['reason'] if reasons else 'stale_draft')
    return pack, rev, doc, approval


def document(session, business, pack_id, now):
    pack, rev, doc, approval, reasons, media = pack_state(session,business,pack_id,now)
    return {'id':pack.id,'revision':pack.revision,'digest':rev.digest,'document':doc,
        'approved':not reasons and approval is not None and approval.digest == rev.digest,
        'stale':bool(reasons), 'stale_reasons':reasons, 'media_available':media,
        'historically_approved':approval is not None,
        'review':json.loads(rev.report), 'publication':{'status':'manual_export_only','post_id':None},
        'results':{'value':None,'reason':'not_published','search_traffic':None}}


def register(app, get_session, scoped_staff):
    from .social_migrations import require_ready
    def read(business_id: str, request: Request, session=Depends(get_session)):
        principal = scoped_staff(request,session,business_id,'growth.read')
        require_ready(session)
        return principal
    def write(business_id: str, request: Request, session=Depends(get_session)):
        principal = scoped_staff(request,session,business_id,'growth.write')
        require_ready(session)
        return principal
    from .social_context import register as register_context, validate_pack_context, attach_dependencies
    register_context(app, get_session, read, write)
    from .social_creative import register as register_creative, snapshot as creative_snapshot
    register_creative(app, get_session, read, write)
    from .social_proposals import register as register_proposals
    register_proposals(app, get_session, read, write)
    root='/api/operator/restaurants/{business_id}/social'

    @app.get(root, dependencies=[Depends(read)])
    def listing(business_id: str, session=Depends(get_session)):
        from .instagram_routes import status as instagram_status
        connection=instagram_status(session,business_id,getattr(app.state,'instagram',None))
        snapshot=connection.get('snapshot')
        baseline={'posts':None,'reach':None,'reason':'no_authorized_metrics_import'}
        if snapshot:
            baseline={**snapshot['baseline'],'posts':snapshot['coverage']['posts'],
                      'coverage':snapshot['coverage'],'observed_at':snapshot['observed_at'],
                      'account_id':snapshot['account_id'],'verification':connection['verification']}
        return {'packs':[{'id':p.id,'revision':p.revision} for p in session.scalars(select(Pack).where(Pack.business_id==business_id))],
            'capabilities':{'instagram':connection['state'],'generation':'deterministic_preview','publication':'manual_export_only'},
            'baseline':baseline}

    @app.post(root+'/assets')
    def intake(business_id: str, payload: Intake, principal=Depends(write), session=Depends(get_session)):
        require(future(payload.expires_at.isoformat(),utcnow()), 'asset_expired')
        try:
            raw=base64.b64decode(payload.data_base64,validate=True)
            require(len(raw)<=MAX_BYTES,'upload_limit',413)
            with Image.open(io.BytesIO(raw)) as image:
                require(image.format in {'JPEG','PNG'},'unsupported_photo',422)
                require(image.width*image.height<=24_000_000,'image_pixel_limit',422)
                image.verify()
        except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise HTTPException(422,'invalid_photo') from None
        identifier=uuid4().hex
        meta=payload.model_dump(mode='json',exclude={'data_base64'})
        meta.update(sha256=hashlib.sha256(raw).hexdigest(),uploaded_at=utcnow().isoformat(),actor_id=principal.actor_id)
        session.add(Asset(id=identifier,business_id=business_id,original=raw,metadata_json=canonical(meta)))
        session.commit()
        return {'id':identifier,**meta}

    @app.delete(root+'/assets/{asset_id}', dependencies=[Depends(write)])
    def revoke(business_id: str, asset_id: str, session=Depends(get_session)):
        asset=owned(session,Asset,asset_id,business_id)
        asset.revoked=True
        asset.original=b''
        # Purge derived pixels too; all future reads/exports fail closed.
        for rev in session.scalars(select(Revision).join(Pack).where(Pack.business_id==business_id)):
            if json.loads(rev.document)['brief']['asset_id']==asset_id:
                rev.image=b''
        from .social_jobs import purge_asset
        purge_asset(session, business_id, asset_id)
        session.commit()
        return {'revoked':True}

    def save(business, payload, principal, session, pack_id=None, *, prepare_only=False, rendered=None, snapshot=None, commit=True):
        now=utcnow()
        stable_id=hashlib.sha256((business+':'+str(payload.request_id)).encode()).hexdigest()[:32]
        if not prepare_only and pack_id is None and session.get(Pack,stable_id) is not None:
            existing=document(session,business,stable_id,now)
            require(Brief.model_validate(existing['document']['brief']).model_dump(mode='json')==payload.model_dump(mode='json'),'idempotency_conflict')
            return existing
        asset, meta=asset_check(session,payload.asset_id,business,now)
        require(all(future(f.valid_until.isoformat(),now) for f in payload.facts),'fact_expired')
        if payload.location_id:
            resolver = getattr(app.state, 'social_location_belongs_to_business', None)
            require(resolver is not None, 'canonical_location_validation_unavailable', 503)
            require(resolver(business, str(payload.location_id)), 'location_not_in_business', 404)
        business_brief = validate_pack_context(session, business, payload, now)
        creative = creative_snapshot(session, business, payload, now)
        facts={f.id:f.text for f in payload.facts}
        caption='\n\n'.join(facts[key] for key in payload.caption_fact_ids)
        proposal_snapshot=None
        if payload.proposal_decision_id:
            from .social_proposals import resolve_decision
            decision,ctx,proposal=resolve_decision(session,business,payload.proposal_decision_id,app)
            require(payload.context_version_id==ctx['context_version_id'] and payload.creative_version_id==ctx['brand_version_id'] and payload.asset_id==ctx['asset']['id'],'proposal_snapshot_mismatch')
            require(set(payload.caption_fact_ids)=={f['id'] for f in ctx['facts']},'proposal_fact_snapshot_mismatch')
            caption=decision['text'];proposal_snapshot={'proposal_id':proposal.id,'decision_id':payload.proposal_decision_id,'mode':proposal.mode,'review':decision}

        doc={'schema_version':'1','renderer':VERSION,'business_id':business,'brief':payload.model_dump(mode='json'),
            'caption':caption,'copy_mode':'reviewed_proposal' if proposal_snapshot else 'deterministic_confirmed_statements', 'proposal_snapshot':proposal_snapshot, 'asset_sha256':meta['sha256'],
            'fixture':meta['fixture'],'confirmed_by':principal.actor_id,'confirmed_at':now.isoformat(),
            'intended_action':'manual_export','destination_account':None, 'business_brief':business_brief, 'creative_snapshot':creative}
        if snapshot is not None:
            require(all(snapshot[k] == doc[k] for k in ('brief','asset_sha256','business_brief','creative_snapshot','renderer')), 'job_inputs_changed')
            doc = snapshot
        if prepare_only:
            if pack_id:
                require(owned(session, Pack, pack_id, business).revision == payload.expected_revision, 'revision_conflict')
            else:
                require(payload.expected_revision == 0, 'revision_conflict')
            return doc
        png, report = rendered if rendered is not None else render(asset.original, payload)
        if pack_id is None:
            require(payload.expected_revision==0,'revision_conflict')
            pack=Pack(id=stable_id,business_id=business,revision=1)
            session.add(pack)
            session.flush()
        else:
            pack=owned(session,Pack,pack_id,business)
            result=session.execute(update(Pack).where(Pack.id==pack_id,Pack.revision==payload.expected_revision).values(revision=Pack.revision+1))
            require(result.rowcount==1,'revision_conflict')
            session.refresh(pack)
        encoded=canonical(doc)
        digest=hashlib.sha256((encoded+hashlib.sha256(png).hexdigest()).encode()).hexdigest()
        session.add(Revision(id=f'{pack.id}:{pack.revision}',pack_id=pack.id,document=encoded,digest=digest,image=png,report=canonical(report)))
        session.flush()
        attach_dependencies(session, f'{pack.id}:{pack.revision}', payload)
        if commit:
            session.commit()
        return document(session,business,pack.id,now)

    from .social_jobs import register as register_jobs
    register_jobs(app, get_session, read, write, save)

    @app.post(root+'/packs')
    def create(business_id: str,payload: Brief,principal=Depends(write),session=Depends(get_session)):
        return save(business_id,payload,principal,session)
    @app.put(root+'/packs/{pack_id}')
    def edit(business_id: str,pack_id: str,payload: Brief,principal=Depends(write),session=Depends(get_session)):
        return save(business_id,payload,principal,session,pack_id)
    @app.get(root+'/packs/{pack_id}',dependencies=[Depends(read)])
    def preview(business_id: str,pack_id: str,session=Depends(get_session)):
        return document(session,business_id,pack_id,utcnow())
    @app.get(root+'/packs/{pack_id}/image',dependencies=[Depends(read)])
    def image(business_id: str,pack_id: str,session=Depends(get_session)):
        _,rev,doc,_,_,_=pack_state(session,business_id,pack_id,utcnow())
        asset_check(session,doc['brief']['asset_id'],business_id,utcnow())
        return Response(rev.image,media_type='image/jpeg',headers={'Cache-Control':'no-store'})
    @app.post(root+'/packs/{pack_id}/approve')
    def approve(business_id: str,pack_id: str,payload: Decision,principal=Depends(write),session=Depends(get_session)):
        pack,rev,_,old=current(session,business_id,pack_id,utcnow())
        require(rev.digest==payload.digest,'approval_changed')
        if old is None:
            session.add(Approval(revision_id=rev.id,actor_id=principal.actor_id,digest=rev.digest,approved_at=utcnow().isoformat()))
            session.commit()
        return document(session,business_id,pack_id,utcnow())
    @app.get(root+'/packs/{pack_id}/export',dependencies=[Depends(read)])
    def export(business_id: str,pack_id: str,session=Depends(get_session)):
        _,rev,doc,approval=current(session,business_id,pack_id,utcnow())
        require(approval is not None and approval.digest==rev.digest,'approval_required')
        result=io.BytesIO()
        asset,_=asset_check(session,doc['brief']['asset_id'],business_id,utcnow())
        with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('post.jpg',rev.image)
            archive.writestr('original',asset.original)
            archive.writestr('caption.txt',doc['caption'])
            archive.writestr('editable.json',rev.document)
            archive.writestr('approval.json',canonical({'digest':rev.digest,'actor_id':approval.actor_id,'at':approval.approved_at,'scope':'manual_export'}))
            from .social_job_models import ProductionJob
            from .social_jobs import info as job_info
            production = session.scalar(select(ProductionJob).where(ProductionJob.business_id==business_id,ProductionJob.result_revision==rev.id,ProductionJob.state=='succeeded').order_by(ProductionJob.created_at.desc()).limit(1))
            archive.writestr('production.json', canonical(job_info(session,production) if production else {'state':'legacy_synchronous','attempts':None,'total_cost_microusd':None}))
            provider_cost = 0
            if doc.get('proposal_snapshot'):
                from .social_proposals import proposal_info
                from .social_proposal_models import Proposal
                proposal = owned(session,Proposal,doc['proposal_snapshot']['proposal_id'],business_id)
                generation = session.get(ProductionJob,proposal.job_id)
                generation_info = job_info(session,generation)
                archive.writestr('proposal.json',canonical({'proposal':proposal_info(session,proposal,app),'generation':generation_info}))
                micro = generation_info['cost']['provider_microusd']
                provider_cost = micro/1_000_000 if micro is not None else None
            archive.writestr('measurement.json',canonical({'primary':doc['brief']['primary_measure'],'value':None,'reason':'not_published','provider_cost_usd':provider_cost,'compute_cost_usd':None}))
        return Response(result.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="social-{pack_id}.zip"','Cache-Control':'no-store'})
