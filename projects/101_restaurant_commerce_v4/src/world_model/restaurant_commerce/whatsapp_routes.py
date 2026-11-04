"""Staff setup/inbox and raw-body authenticated Meta callbacks."""
import hashlib
import hmac
import json
from datetime import timedelta
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import Field
from . import whatsapp as w
from .campaign_models import WhatsAppConversation, WhatsAppEvidence, WhatsAppReply
from .models import Customer, StaffAccount
from .staff import aware


class SimulateInput(w.Input):
    customer_id: str = Field(max_length=36)
    text: str = Field(min_length=1,max_length=2000)
    request_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,100}$')


def register(app,get_session,read,write,integrations,now,demo_mode):
    root='/api/operator/restaurants/{business_id}/whatsapp'

    @app.get('/whatsapp')
    def page(): return FileResponse(Path(__file__).parent/'web/whatsapp.html')

    @app.get(root,dependencies=[Depends(read)])
    def configuration(business_id:str,session:Session=Depends(get_session)):
        result=w.readiness(session,business_id,now())
        result['customers']=[{'id':c.id,'name':c.name,'phone':c.phone} for c in session.scalars(select(Customer).where(Customer.business_id==business_id).limit(500))]
        return result

    @app.put(root+'/sender',dependencies=[Depends(write)])
    def sender(business_id:str,payload:w.SenderInput,session:Session=Depends(get_session)):
        if not demo_mode and w.c.settings(session,business_id).scope=='test': raise HTTPException(409,'simulation_requires_test_environment')
        return w.configure(session,business_id,payload,now())

    @app.post(root+'/sync',dependencies=[Depends(write)])
    def sync(business_id:str,session:Session=Depends(get_session)):
        integration=next((v for v in integrations.values() if v['business_id']==business_id and v['scope']==w.c.settings(session,business_id).scope and v['adapter'].name=='whatsapp_cloud'),None)
        if not integration: raise HTTPException(409,'official_provider_unconfigured')
        return w.sync_provider(session,business_id,integration['adapter'],now())

    @app.post(root+'/templates',dependencies=[Depends(write)])
    def template(business_id:str,payload:w.TemplateInput,session:Session=Depends(get_session)):
        if not demo_mode: raise HTTPException(409,'manual_templates_require_test_environment')
        return w.put_template(session,business_id,payload,now())

    @app.get(root+'/conversations',dependencies=[Depends(read)])
    def inbox(business_id:str,session:Session=Depends(get_session)):
        rows=list(session.scalars(select(WhatsAppConversation).where(WhatsAppConversation.business_id==business_id).limit(100)))
        return {'conversations':[{'id':r.id,'destination':r.destination,'scope':r.scope,'state':r.state,
            'assigned_to':r.assigned_to,'assigned_name':(session.get(StaffAccount,r.assigned_to).username if r.assigned_to and session.get(StaffAccount,r.assigned_to) else None),'opted_out':r.opted_out,'last_inbound_at':r.last_inbound_at,
            'service_window_open':bool(r.last_inbound_at and aware(r.last_inbound_at)<=now()<aware(r.last_inbound_at)+timedelta(hours=24)),
            'messages':[json.loads(e.document) for e in session.scalars(select(WhatsAppEvidence).where(WhatsAppEvidence.conversation_id==r.id,WhatsAppEvidence.kind=='inbound').order_by(WhatsAppEvidence.provider_at).limit(100))],
            'replies':[{'id':p.id,'body':p.body,'state':p.state,'reason':p.reason,'actor':p.actor} for p in session.scalars(select(WhatsAppReply).where(WhatsAppReply.conversation_id==r.id).limit(100))]} for r in rows]}

    @app.post(root+'/conversations/{conversation_id}/reply')
    def reply(business_id:str,conversation_id:str,payload:w.ReplyInput,principal=Depends(write),session:Session=Depends(get_session)):
        if not demo_mode: raise HTTPException(409,'live_reply_disabled')
        return w.queue_reply(session,business_id,conversation_id,payload,principal.actor_id,now())

    @app.get('/api/whatsapp-hooks/{integration_id}')
    def challenge(integration_id:str,request:Request):
        integration=integrations.get(integration_id)
        if not integration or not hasattr(integration['adapter'],'challenge'): raise HTTPException(404,'Integration not configured')
        if integration['scope']=='test' and not demo_mode: raise HTTPException(403,'Simulation disabled')
        try: value=integration['adapter'].challenge(request.query_params.get('hub.mode'),request.query_params.get('hub.verify_token'),request.query_params.get('hub.challenge'))
        except ValueError: raise HTTPException(403,'Invalid verification') from None
        return PlainTextResponse(value)

    @app.post('/api/whatsapp-hooks/{integration_id}')
    async def callback(integration_id:str,request:Request,session:Session=Depends(get_session)):
        integration=integrations.get(integration_id)
        if not integration or not hasattr(integration['adapter'],'verify_events'): raise HTTPException(404,'Integration not configured')
        if integration['scope']=='test' and not demo_mode: raise HTTPException(403,'Simulation disabled')
        body=await request.body()
        try: events=integration['adapter'].verify_events(body,request.headers.get('X-Hub-Signature-256'))
        except Exception: raise HTTPException(401,'Invalid WhatsApp callback') from None
        return w.ingest(session,integration,events,hashlib.sha256(body).hexdigest(),now())

    if demo_mode:
        @app.post(root+'/simulate-inbound',dependencies=[Depends(write)])
        def simulate(business_id:str,payload:SimulateInput,session:Session=Depends(get_session)):
            customer=session.get(Customer,payload.customer_id)
            if not customer or customer.business_id!=business_id: raise HTTPException(404,'Customer not found')
            integration=next((v for v in integrations.values() if v['business_id']==business_id and v['scope']=='test' and v['adapter'].name=='simulated_whatsapp'),None)
            if not integration or integration['adapter'].capabilities.get('network') is not False: raise HTTPException(409,'Fake WhatsApp transport required')
            adapter=integration['adapter']
            event={'object':'whatsapp_business_account','entry':[{'id':adapter.waba_id,'changes':[{'field':'messages','value':{
                'messaging_product':'whatsapp','metadata':{'phone_number_id':adapter.phone_id},
                'messages':[{'id':'wamid.simulated.inbound.'+payload.request_key,'from':customer.phone.lstrip('+'),
                    'timestamp':str(int(now().timestamp())),'type':'text','text':{'body':payload.text}}]}}]}]}
            body=json.dumps(event).encode(); signature='sha256='+hmac.new(adapter.app_secret.encode(),body,hashlib.sha256).hexdigest()
            return w.ingest(session,integration,adapter.verify_events(body,signature),hashlib.sha256(body).hexdigest(),now())
