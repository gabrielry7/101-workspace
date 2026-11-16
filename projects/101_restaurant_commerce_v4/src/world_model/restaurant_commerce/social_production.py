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
from .social_video_contracts import Timeline
from .social_design import Design, compile_scene, draw_scene, changes as design_changes, VERSION as DESIGN_VERSION

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



class Handoff(Strict):
    platform: Literal['unspecified', 'instagram', 'facebook', 'tiktok'] = 'unspecified'
    account_label: str = Field(default='', max_length=120)


class Brief(Strict):
    handoff: Handoff = Field(default_factory=Handoff)
    schema_version: Literal['1'] = '1'
    design: Design | None = None
    video: Timeline | None = None
    location_id: UUID | None = None
    context_version_id: str | None = Field(default=None, max_length=100)
    fact_refs: list[FactReference] = Field(default_factory=list, max_length=12)
    creative_version_id: str | None = Field(default=None, max_length=100)
    reference_ids: list[str] = Field(default_factory=list, max_length=12)
    question_id: str | None = Field(default=None, max_length=64)
    revision_reason: Literal['initial', 'factual_correction', 'brand_preference', 'strategy', 'layout'] = 'initial'
    learning_decision_id: str | None = Field(default=None,max_length=64)
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
        if self.video is not None and self.design is not None:
            raise ValueError('video_and_static_design_are_separate')
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
    review_id: str | None = Field(default=None, max_length=64)
    craft_reviewed: Literal[True] | None = None
    brand_reviewed: Literal[True] | None = None
    purpose_reviewed: Literal[True] | None = None


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def same_snapshot(expected, actual):
    # Legacy queued photo requests predate the optional video field. Resolve only
    # schema defaults; real fact/asset/brand changes still invalidate their work.
    keys=('brief','asset_sha256','business_brief','creative_snapshot','renderer','design','video_sources')
    for key in keys:
        a,b=expected.get(key),actual.get(key)
        if key=='brief':
            a=Brief.model_validate(a).model_dump(mode='json')
            b=Brief.model_validate(b).model_dump(mode='json')
        if a!=b:
            return False
    return True


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
    if brief.design is not None:
        scene = compile_scene(brief, original)
        data = draw_scene(original, scene)
        return data, {'renderer':DESIGN_VERSION,'width':1080,'height':1350,
            'render_ms':round((time.monotonic()-started)*1000),'model_calls':0,
            'provider_cost_usd':0,'compute_cost_usd':None,'technical':'passed',
            'scene_sha256':scene['sha256'],'fonts':scene['fonts'],
            'checks':['dimensions','decode','resolution','bounds','glyphs','overflow','contrast','exact_fact_text'],
            'craft':'requires_human_review','brand':'requires_human_review',
            'purpose':'requires_human_review','performance':'unavailable'}
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
    from .social_reviews import effective_approval
    if doc['brief'].get('learning_decision_id'):
        from .social_results import learning_context
        try: learning_context(session,business,doc['brief']['learning_decision_id'])
        except HTTPException as error: reasons.append({'reason':error.detail})
    from .social_video import source_reasons
    video_reasons = source_reasons(session, business, doc)
    reasons += video_reasons
    media_available = media_available and not video_reasons
    approval = effective_approval(session, rev, doc)
    return pack, rev, doc, approval, reasons, media_available


def current(session, business, pack_id, now):
    pack, rev, doc, approval, reasons, _ = pack_state(session, business, pack_id, now)
    require(not reasons, reasons[0]['reason'] if reasons else 'stale_draft')
    return pack, rev, doc, approval


def document(session, business, pack_id, now):
    pack, rev, doc, approval, reasons, media = pack_state(session,business,pack_id,now)
    from .social_reviews import state, ever_approved
    from .social_results import pack_receipt_summary
    receipt=pack_receipt_summary(session,business,pack.id,rev.id)
    return {'review_state':state(session,rev,doc,bool(reasons)),'id':pack.id,'revision':pack.revision,'digest':rev.digest,'document':doc,
        'approved':not reasons and approval is not None and approval.digest == rev.digest,
        'stale':bool(reasons), 'stale_reasons':reasons, 'media_available':media,
        'historically_approved':ever_approved(session,rev.id),
        'review':json.loads(rev.report), 'publication':receipt,
        'results':{'value':None,'reason':'see_sourced_observations' if receipt['post_id'] else 'not_published','search_traffic':None}}


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
    from .social_reviews import register as register_reviews
    register_reviews(app,get_session,read,write)
    from .social_results import register as register_results
    register_results(app,get_session,read,write)
    from .social_video import register as register_video
    register_video(app,get_session,read,write)
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

    @app.get(root+'/design/options',dependencies=[Depends(read)])
    def design_options(business_id: str):
        from .social_design import presets, font_record
        return {'presets':presets(),'fonts':[font_record()],'renderer':DESIGN_VERSION}

    @app.get(root+'/packs/{pack_id}/history',dependencies=[Depends(read)])
    def history(business_id: str,pack_id: str,before_revision: int | None=None,session=Depends(get_session)):
        pack=owned(session,Pack,pack_id,business_id)
        ceiling=min(before_revision or pack.revision+1,pack.revision+1)
        require(ceiling>0,'invalid_revision',422)
        result=[]
        for number in range(ceiling-1,max(0,ceiling-21),-1):
            rev=session.get(Revision,f'{pack.id}:{number}')
            if not rev: continue
            doc=json.loads(rev.document)
            from .social_reviews import ever_approved, latest
            assessment=latest(session,rev.id,'assessment')
            review_summary=json.loads(assessment.document) if assessment else None
            previous=session.get(Revision,f'{pack.id}:{number-1}') if number>1 else None
            result.append({'review_summary':review_summary,'revision':number,'digest':rev.digest,'caption':doc['caption'],
                'historically_approved':ever_approved(session,rev.id),'current':number==pack.revision,
                'at':doc.get('confirmed_at'),'reason':doc['brief'].get('revision_reason','initial'),
                'changes':doc.get('changes') or design_changes(json.loads(previous.document) if previous else None,doc),
                'media_kind':'video' if doc.get('video_output') else 'photo','layout':doc.get('design',{}).get('layout') if doc.get('design') else 'photo_only'})
        return {'revisions':result,'before_revision':result[-1]['revision'] if result and result[-1]['revision']>1 else None}

    @app.get(root+'/packs/{pack_id}/revisions/{number}/image',dependencies=[Depends(read)])
    def revision_image(business_id: str,pack_id: str,number: int,session=Depends(get_session)):
        pack=owned(session,Pack,pack_id,business_id)
        require(1<=number<=pack.revision,'not_found',404)
        rev=session.get(Revision,f'{pack.id}:{number}')
        require(rev is not None,'not_found',404)
        doc=json.loads(rev.document)
        asset_check(session,doc['brief']['asset_id'],business_id,utcnow())
        from .social_video import source_reasons
        require(not source_reasons(session,business_id,doc),'video_source_unavailable')
        return Response(rev.image,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

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
        from .social_video import purge
        purge(session,business_id,asset_id)
        from .social_jobs import purge_asset
        purge_asset(session, business_id, asset_id)
        session.commit()
        return {'revoked':True}

    def save(business, payload, principal, session, pack_id=None, *, prepare_only=False, rendered=None, snapshot=None, commit=True, video_files=None):
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
            require(payload.context_version_id==ctx['context_version_id'] and payload.creative_version_id==ctx['brand_version_id'] and (payload.asset_id==ctx['asset']['id'] or pack_id is not None),'proposal_snapshot_mismatch')
            require(set(payload.caption_fact_ids)=={f['id'] for f in ctx['facts']},'proposal_fact_snapshot_mismatch')
            caption=decision['text'];proposal_snapshot={'proposal_id':proposal.id,'decision_id':payload.proposal_decision_id,'mode':proposal.mode,'review':decision,'proposed_asset_id':ctx['asset']['id'],'owner_replaced_photo':payload.asset_id!=ctx['asset']['id']}

        learning=None
        if payload.learning_decision_id:
            from .social_results import learning_context
            learning=learning_context(session,business,payload.learning_decision_id)
            require(pack_id!=learning['source_pack_id'],'learning_requires_new_pack')
        require(meta.get('media_kind','photo') == 'photo','photo_anchor_required',422)
        require(payload.video is None or prepare_only or video_files is not None,'video_requires_durable_render')
        scene=None if payload.video else compile_scene(payload,asset.original)
        doc={'design':scene,'schema_version':'1','renderer':DESIGN_VERSION if scene else VERSION,'business_id':business,'brief':payload.model_dump(mode='json'),
            'caption':caption,'copy_mode':'reviewed_proposal' if proposal_snapshot else 'deterministic_confirmed_statements', 'proposal_snapshot':proposal_snapshot, 'asset_sha256':meta['sha256'],
            'fixture':meta['fixture'],'confirmed_by':principal.actor_id,'confirmed_at':now.isoformat(),
            'review_contract':'social-review-v1','intended_action':'manual_export','destination_account':{'authorization':'owner_manual_handoff',**payload.handoff.model_dump()}, 'business_brief':business_brief, 'creative_snapshot':creative}
        if payload.video:
            from .social_video import validate_timeline
            from .social_video_contracts import VERSION as VIDEO_VERSION
            doc['renderer']=VIDEO_VERSION
            doc['video_sources']=validate_timeline(session,business,payload.video,pack_id=pack_id,doc=doc,lock=True)
            doc['fixture']=doc['fixture'] or any(s['fixture'] for s in doc['video_sources'])
        if learning is not None: doc['learning_snapshot']=learning
        if snapshot is not None:
            require(same_snapshot(snapshot,doc), 'job_inputs_changed')
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
        previous = session.get(Revision,f'{pack.id}:{pack.revision-1}') if pack.revision>1 else None
        doc['changes'] = design_changes(json.loads(previous.document) if previous else None,doc)
        if scene:
            require(report.get('scene_sha256')==scene['sha256'],'design_render_changed')
        if payload.video:
            doc['video_output']={k:report[k] for k in ('files','width','height','duration_ms','fps','tool_version')}
        encoded=canonical(doc)
        digest=hashlib.sha256((encoded+hashlib.sha256(png).hexdigest()).encode()).hexdigest()
        session.add(Revision(id=f'{pack.id}:{pack.revision}',pack_id=pack.id,document=encoded,digest=digest,image=png,report=canonical(report)))
        session.flush()
        if payload.video:
            from .social_video_models import VideoOutput
            session.add(VideoOutput(revision_id=f'{pack.id}:{pack.revision}',business_id=business,final=video_files['video.mp4'],preview=video_files['preview.mp4'],cover=video_files['cover.jpg']))
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
        from .social_video import source_reasons
        require(not source_reasons(session,business_id,doc),'video_source_unavailable')
        return Response(rev.image,media_type='image/jpeg',headers={'Cache-Control':'no-store'})
    @app.post(root+'/packs/{pack_id}/approve')
    def approve(business_id: str,pack_id: str,payload: Decision,principal=Depends(write),session=Depends(get_session)):
        from .social_reviews import approve as approve_review
        approve_review(session,business_id,pack_id,payload,principal)
        return document(session,business_id,pack_id,utcnow())
    @app.get(root+'/packs/{pack_id}/export',dependencies=[Depends(read)])
    def export(business_id: str,pack_id: str,session=Depends(get_session)):
        from .social_exports import package
        result=package(session,business_id,pack_id,app)
        return Response(result,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="social-{pack_id}.zip"','Cache-Control':'no-store'})
