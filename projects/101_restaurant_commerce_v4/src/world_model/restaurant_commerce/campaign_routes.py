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

    root = '/api/operator/restaurants/{business_id}/campaigns'

    @app.get('/campaigns')
    def campaign_page():
        return FileResponse(Path(__file__).parent / 'web/campaigns.html')

    @app.get(root, dependencies=[Depends(read)])
    def campaign_list(business_id: str, session: Session = Depends(get_session)):
        cfg = c.settings(session, business_id)
        return {'campaigns':[{'id':row.id,'state':row.state} for row in session.scalars(select(Campaign).where(Campaign.business_id == business_id))],
                'channels':{'email':'simulation_only','whatsapp':'unconfigured','sms':'unconfigured'},
                'live_send_enabled':False,'scope':cfg.scope,'paused':cfg.paused,'clock':now().isoformat(),
                'sender':json.loads(cfg.config_json).get('sender'),
                'customers':[{'id':x.id,'name':x.name,'email':x.email} for x in session.scalars(select(Customer).where(Customer.business_id == business_id).limit(500))]}

    @app.post(root, dependencies=[Depends(write)])
    def campaign_create(business_id: str, payload: c.Draft, session: Session = Depends(get_session)):
        return c.save_draft(session, business_id, payload, now())

    @app.post(root + '/pause', dependencies=[Depends(write)])
    def campaign_pause(business_id: str, payload: PauseInput, session: Session = Depends(get_session)):
        session.execute(update(CampaignSettings).where(CampaignSettings.business_id == business_id).values(paused=payload.paused))
        session.commit()
        return {'paused':payload.paused}

    @app.get(root + '/{campaign_id}', dependencies=[Depends(read)])
    def campaign_preview(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
        return c.preview(session, business_id, campaign_id, now())

    @app.get(root + '/{campaign_id}/email', dependencies=[Depends(read)])
    def campaign_email_preview(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
        return HTMLResponse(c.preview(session, business_id, campaign_id, now())['email']['html'])

    @app.put(root + '/{campaign_id}', dependencies=[Depends(write)])
    def campaign_edit(business_id: str, campaign_id: str, payload: c.Draft, session: Session = Depends(get_session)):
        return c.save_draft(session, business_id, payload, now(), campaign_id)

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
            return c.dispatch(app.state.session_factory, integrations, now=now(), base_url=base_url, business=business_id)

        @app.post(root + '/{campaign_id}/simulate-receipt', dependencies=[Depends(write)])
        def simulate_receipt(business_id: str, campaign_id: str, session: Session = Depends(get_session)):
            import hmac, hashlib
            c.scoped_campaign(session, business_id, campaign_id)
            revisions = select(CampaignRevision.id).where(CampaignRevision.campaign_id == campaign_id)
            count = 0
            for job in list(session.scalars(select(CampaignJob).where(CampaignJob.business_id == business_id,
                CampaignJob.revision_id.in_(revisions), CampaignJob.scope == 'test', CampaignJob.state == 'accepted'))):
                integration = next(v for v in integrations.values() if v['business_id'] == business_id and v['scope'] == 'test')
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
