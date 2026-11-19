"""Campaign routes share commerce staff, CSRF, tenant and database dependencies."""
import json
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from . import campaigns as c
from .campaign_models import Campaign, CampaignSettings, CampaignJob, CampaignRevision
from .models import Customer, utcnow


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    digest: str = Field(pattern=r'^[a-f0-9]{64}$')


class PauseInput(BaseModel):
    paused: bool


def register(app, get_session, scoped_staff, options, demo_mode):
    integrations = options.get('integrations', {})
    now = options.get('clock', utcnow)
    base_url = options.get('base_url', 'http://127.0.0.1:8799').rstrip('/')

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, 'growth.read')

    def write(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, 'growth.write')

    from .whatsapp_routes import register as register_whatsapp
    register_whatsapp(app,get_session,read,write,integrations,now,demo_mode)

    from .sms_routes import register as register_sms
    register_sms(app,get_session,read,write,integrations,now,demo_mode)
    from .channel_workspace import register as register_channel_workspace
    register_channel_workspace(app,get_session,read,write,integrations,now,demo_mode)

    root = '/api/operator/restaurants/{business_id}/campaigns'

    from . import provider_readiness as readiness

    @app.get(root+'/provider-readiness',dependencies=[Depends(read)])
    def provider_readiness(business_id:str,session:Session=Depends(get_session)):
        return readiness.readiness(session,business_id,integrations,now())

    @app.post(root+'/provider-readiness/whatsapp/probe',dependencies=[Depends(write)])
    def provider_probe(business_id:str,session:Session=Depends(get_session)):
        from . import whatsapp
        cfg=c.settings(session,business_id)
        if cfg.scope=='test':raise HTTPException(409,'real_provider_evidence_cannot_enter_simulation')
        integration=next((v for v in integrations.values() if v['business_id']==business_id and v['scope']==cfg.scope and v['adapter'].name=='whatsapp_cloud'),None)
        if not integration:raise HTTPException(409,'real_provider_unconfigured')
        adapter=integration['adapter'];sender=whatsapp.sender_document(session,business_id)
        if not sender or sender['phone_id']!=adapter.phone_id or sender['waba_id']!=adapter.waba_id:raise HTTPException(409,'whatsapp_integration_binding_changed')
        if adapter.validate():raise HTTPException(409,'provider_configuration_incomplete')
        try:observation=adapter.account_readiness()
        except Exception:raise HTTPException(502,'provider_readiness_probe_failed') from None
        if observation.get('phone_waba_binding_verified') is not True or observation.get('phone_catalogue_complete') is not True:
            raise HTTPException(409,'provider_account_binding_incomplete')
        whatsapp.sync_provider(session,business_id,adapter,now(),observation=observation)
        return readiness.readiness(session,business_id,integrations,now())

    @app.post(root+'/provider-test-reviews')
    def prepare_provider_test(business_id:str,payload:readiness.TestReviewInput,principal=Depends(write),session:Session=Depends(get_session)):
        return readiness.prepare_test(session,business_id,payload,principal.actor_id,integrations,now())

    @app.get(root+'/provider-test-reviews/{review_id}',dependencies=[Depends(read)])
    def get_provider_test(business_id:str,review_id:str,session:Session=Depends(get_session)):
        return readiness.review(session,business_id,review_id,now())

    @app.get('/campaigns')
    def campaign_page():
        return FileResponse(Path(__file__).parent / 'web/campaigns.html')

    @app.get(root, dependencies=[Depends(read)])
    def campaign_list(business_id: str, session: Session = Depends(get_session)):
        cfg = c.settings(session, business_id)
        return {'campaigns':[{'id':row.id,'state':row.state} for row in session.scalars(select(Campaign).where(Campaign.business_id == business_id))],
                'channels':{'email':'simulation_only','whatsapp':__import__(__package__+'.whatsapp',fromlist=['readiness']).readiness(session,business_id,now())['state'],'sms':__import__(__package__+'.sms',fromlist=['readiness']).readiness(session,business_id)['state']},
                'live_send_enabled':False,'scope':cfg.scope,'paused':cfg.paused,'clock':now().isoformat(),
                'sender':json.loads(cfg.config_json).get('sender'),
                'customers':[{'id':x.id,'name':x.name,'email':x.email,'phone':x.phone} for x in session.scalars(select(Customer).where(Customer.business_id == business_id).limit(500))]}

    @app.post(root, dependencies=[Depends(write)])
    def campaign_create(business_id: str, payload: c.Draft, session: Session = Depends(get_session)):
        return c.save_draft(session, business_id, payload, now(), origin=base_url)

    @app.post(root + '/pause', dependencies=[Depends(write)])
    def campaign_pause(business_id: str, payload: PauseInput, session: Session = Depends(get_session)):
        session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business_id).values(paused=payload.paused))
        session.commit()
        return {'paused':payload.paused}

    @app.get('/assets/email-fonts/{filename}')
    def email_font(filename: str):
        import re
        from .campaign_react_email import RUNTIME
        if not re.fullmatch(r'[a-z-]+-latin-(400|500|600)-normal\.woff2',filename): raise HTTPException(404,'font_not_found')
        path=RUNTIME/'fonts'/filename
        if not path.is_file(): raise HTTPException(404,'font_not_found')
        return FileResponse(path,media_type='font/woff2',headers={'Cache-Control':'public,max-age=86400'})

    @app.get(root + '/email-templates', dependencies=[Depends(read)])
    def email_templates(business_id: str):
        from .campaign_react_email import catalog
        return catalog()

    @app.get(root + '/{campaign_id}', dependencies=[Depends(read)])
    def campaign_preview(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
        return c.preview(session, business_id, campaign_id, now())

    @app.get(root + '/{campaign_id}/email', dependencies=[Depends(read)])
    def campaign_email_preview(business_id: str, campaign_id: str, request: Request,
                               session: Session = Depends(get_session), template_id: str | None = None):
        from .campaign_preview_security import secure_preview
        if template_id is not None:
            from .campaign_react_email import EmailDesign, preview_selected
            try: template_id = EmailDesign(template_id=template_id).template_id
            except ValueError: raise HTTPException(422, 'email_template_invalid') from None
            rendered = preview_selected(session, business_id, campaign_id, template_id, origin=base_url)['html']
        else:
            rendered = c.preview(session, business_id, campaign_id, now())['email']['html']
        use_remote = template_id != 'legacy' if template_id is not None else bool(c.preview(session, business_id, campaign_id, now())['document'].get('email_design'))
        rendered, request.state.campaign_preview_csp = secure_preview(rendered, remote_assets=use_remote)
        return HTMLResponse(rendered)

    @app.get(root + '/{campaign_id}/email-content', dependencies=[Depends(read)])
    def email_content(business_id: str, campaign_id: str, template_id: str, session: Session = Depends(get_session)):
        from .campaign_react_email import EmailDesign, preview_selected
        try: template_id = EmailDesign(template_id=template_id).template_id
        except ValueError: raise HTTPException(422, 'email_template_invalid') from None
        return preview_selected(session, business_id, campaign_id, template_id, origin=base_url)

    @app.post(root + '/{campaign_id}/design', dependencies=[Depends(write)])
    def campaign_design(business_id: str, campaign_id: str, payload: dict, session: Session = Depends(get_session)):
        from .campaign_react_email import EmailDesign
        if set(payload) != {'digest', 'email_design'}: raise HTTPException(422, 'email_design_invalid')
        try: design = EmailDesign.model_validate(payload['email_design'])
        except ValueError: raise HTTPException(422, 'email_design_invalid') from None
        session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business_id)
                        .values(dispatch_version=CampaignSettings.dispatch_version + 1))
        campaign = c.scoped_campaign(session, business_id, campaign_id)
        revision = session.get(CampaignRevision, campaign.revision_id)
        if revision.digest != payload['digest']: raise HTTPException(409, 'preview_changed')
        document = json.loads(revision.document)
        if document['channel'] != 'email': raise HTTPException(422, 'email_design_requires_email_channel')
        # Retain all existing copy/offer/audience/schedule fields; only the design is replaced.
        values = {k:v for k,v in document.items() if k in c.Draft.model_fields and k != 'email_design'}
        draft = c.Draft.model_validate({**values, 'email_design': design.model_dump()})
        return c.save_draft(session, business_id, draft, now(), campaign_id, origin=base_url)

    @app.put(root + '/{campaign_id}', dependencies=[Depends(write)])
    def campaign_edit(business_id: str, campaign_id: str, payload: c.Draft, session: Session = Depends(get_session)):
        return c.save_draft(session, business_id, payload, now(), campaign_id, origin=base_url)

    @app.post(root + '/{campaign_id}/approve')
    def campaign_approve(business_id: str, campaign_id: str, payload: ApprovalInput,
                         principal=Depends(write), session: Session = Depends(get_session)):
        return c.approve(session, business_id, campaign_id, payload.digest, principal.actor_id, now())

    @app.post(root + '/{campaign_id}/schedule', dependencies=[Depends(write)])
    def campaign_schedule(business_id: str, campaign_id: str, payload: ApprovalInput, session: Session = Depends(get_session)):
        return c.schedule(session, business_id, campaign_id, payload.digest, now())

    @app.post(root + '/{campaign_id}/cancel', dependencies=[Depends(write)])
    def campaign_cancel(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
        return c.cancel(session, business_id, campaign_id)

    @app.get(root + '/{campaign_id}/report', dependencies=[Depends(read)])
    def campaign_report(business_id: str, campaign_id: str, scope: str = 'test', session: Session = Depends(get_session)):
        if scope not in {'test','provider_test','live'}: raise HTTPException(422, 'Invalid scope')
        result = c.report(session, business_id, campaign_id, scope)
        revisions = select(CampaignRevision.id).where(CampaignRevision.campaign_id == campaign_id)
        from . import sms
        result['sms']=sms.report_details(session,business_id,campaign_id,scope)
        result['deliveries'] = [{'id':j.id,'customer_id':j.customer_id,'state':j.state,'reason':j.reason,
            'message_id':j.provider_id,'tracking_url':'/campaign-link/'+j.tracking_token,
            'unsubscribe_url':'/campaign-unsubscribe/'+j.unsubscribe_token} for j in session.scalars(select(CampaignJob).where(
                CampaignJob.business_id == business_id, CampaignJob.revision_id.in_(revisions), CampaignJob.scope == scope))]
        return result

    @app.get('/campaign-link/{token}')
    def campaign_link(token: str, request: Request, session: Session = Depends(get_session)):
        business, cookie = c.visit(session, token, now(), request.headers.get('user-agent',''))
        from urllib.parse import quote
        response = RedirectResponse('/?business_id=' + quote(business, safe=''), status_code=303)
        response.set_cookie('campaign_visit_' + c.digest(business)[:16], cookie,
            httponly=True, secure=not demo_mode, samesite='lax', max_age=7*86400)
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.get('/campaign-unsubscribe/{token}')
    def unsubscribe_page(token: str, session: Session = Depends(get_session)):
        if not session.scalar(select(CampaignJob.id).where(CampaignJob.unsubscribe_token == token)):
            raise HTTPException(404, 'Link not found')
        return HTMLResponse('<!doctype html><html lang="es"><meta name="viewport" content="width=device-width"><title>Dejar de recibir promociones</title><h1>Dejar de recibir promociones</h1><p>Retira tu permiso para este negocio y canal.</p><form method="post"><button>Confirmar baja</button></form></html>')

    @app.post('/campaign-unsubscribe/{token}')
    def unsubscribe_post(token: str, session: Session = Depends(get_session)):
        c.unsubscribe(session, token, now())
        return HTMLResponse('<h1>Tu baja quedó registrada</h1><p>No recibirás promociones pendientes de este negocio y canal.</p>')

    @app.post('/api/campaign-hooks/{integration_id}')
    async def campaign_hook(integration_id: str, request: Request, session: Session = Depends(get_session)):
        integration = integrations.get(integration_id)
        if not integration: raise HTTPException(404, 'Integration not configured')
        if integration['scope'] == 'test' and not demo_mode: raise HTTPException(403, 'Simulation disabled')
        body = await request.body()
        try:
            event = integration['adapter'].verify_event(body, request.headers.get('X-Campaign-Signature'))
            # Normalize/validate before changes. Original signed body fingerprint retained.
            for key in ('id','key','message_id','kind','at'):
                if not isinstance(event[key],str) or not 1 <= len(event[key]) <= 256: raise ValueError('Invalid event')
            c.date(event['at'])
            event['raw_sha256'] = __import__('hashlib').sha256(body).hexdigest()
        except Exception:
            raise HTTPException(401, 'Invalid provider event') from None
        return c.ingest_event(session, integration, event, now())

    if demo_mode:
        @app.post(root + '/simulate/dispatch', dependencies=[Depends(write)])
        def simulate_dispatch(business_id: str, session: Session = Depends(get_session)):
            if c.settings(session, business_id).scope != 'test': raise HTTPException(409, 'Test scope required')
            session.commit()
            return c.dispatch(app.state.session_factory, integrations, now=now(), base_url=base_url, business=business_id, include_replies=False)

        @app.post(root + '/{campaign_id}/simulate-receipt', dependencies=[Depends(write)])
        def simulate_receipt(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
            import hmac, hashlib
            c.scoped_campaign(session, business_id, campaign_id)
            revisions = select(CampaignRevision.id).where(CampaignRevision.campaign_id == campaign_id)
            count = 0
            for job in list(session.scalars(select(CampaignJob).where(CampaignJob.business_id == business_id,
                CampaignJob.revision_id.in_(revisions), CampaignJob.scope == 'test', CampaignJob.state == 'accepted'))):
                integration = next(v for v in integrations.values() if v['business_id'] == business_id and v['scope'] == 'test' and v['adapter'].name == job.provider)
                adapter = integration['adapter']
                if adapter.capabilities.get('network'): raise HTTPException(409, 'Fake transport required')
                body = c.canonical({'id':'demo-delivery:'+job.id,'key':job.id,'message_id':job.provider_id,
                    'kind':'delivered','at':now().isoformat()}).encode()
                signature = hmac.new(adapter.secret.encode(), body, hashlib.sha256).hexdigest()
                event = adapter.verify_event(body, signature)
                event['raw_sha256'] = hashlib.sha256(body).hexdigest()
                c.ingest_event(session, integration, event, now())
                count += 1
            return {'simulated_delivery_events':count}
