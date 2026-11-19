"""Scoped SMS setup and authenticated form callbacks; never trust request Host."""
import hashlib
import json
import secrets
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from fastapi import Depends,HTTPException,Request
from fastapi.responses import RedirectResponse, FileResponse,Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import sms
from .campaign_models import SmsEvidence
from .models import Customer
from .schemas import StrictModel
from pydantic import Field


class InboundInput(StrictModel):
    customer_id:str=Field(max_length=36)
    text:str=Field(min_length=1,max_length=1600)


def register(app,get_session,read,write,integrations,now,demo_mode):
    root='/api/operator/restaurants/{business_id}/sms'

    @app.get('/sms')
    def page():return RedirectResponse("/workspace/connections?provider=sms", status_code=307)

    @app.get(root,dependencies=[Depends(read)])
    def config(business_id:str,session:Session=Depends(get_session)):
        result=sms.readiness(session,business_id)
        result['customers']=[{'id':c.id,'name':c.name,'phone':c.phone} for c in session.scalars(select(Customer).where(Customer.business_id==business_id).limit(500))]
        result['inbound']=[json.loads(e.document) for e in session.scalars(select(SmsEvidence).where(SmsEvidence.business_id==business_id,SmsEvidence.scope==result['scope'],SmsEvidence.kind=='inbound').order_by(SmsEvidence.received_at.desc()).limit(50))]
        return result

    @app.put(root+'/sender',dependencies=[Depends(write)])
    def configure(business_id:str,payload:sms.SenderInput,session:Session=Depends(get_session)):
        if sms.c.settings(session,business_id).scope=='test' and not demo_mode:raise HTTPException(409,'simulation_requires_test_environment')
        return sms.configure(session,business_id,payload,now())

    async def callback(integration_id,request,session,inbound):
        integration=integrations.get(integration_id)
        if not integration or integration['adapter'].name not in {'twilio_sms','simulated_sms'}:raise HTTPException(404,'SMS integration not configured')
        if integration['scope']=='test' and not demo_mode:raise HTTPException(403,'Simulation disabled')
        if request.headers.get('content-type','').split(';')[0]!='application/x-www-form-urlencoded':raise HTTPException(415,'Form callback required')
        if request.headers.get('X-Twilio-Webhooks-Signature-Settings'):raise HTTPException(401,'Shared-key signature mode not configured')
        query=list(request.query_params.multi_items())
        if (inbound and query) or (not inbound and (len(query)!=1 or query[0][0]!='key')):raise HTTPException(401,'Unexpected callback URL')
        expected_url=integration['adapter'].inbound_url if inbound else integration['adapter'].callback_url
        if request.url.path!=urlsplit(expected_url).path:raise HTTPException(401,'Callback path not bound')
        body=await request.body()
        try:event=integration['adapter'].verify_callback(body,request.headers.get('X-Twilio-Signature'),key=request.query_params.get('key'),inbound=inbound)
        except Exception:raise HTTPException(401,'Invalid SMS callback') from None
        result=sms.ingest(session,integration,event,hashlib.sha256(body).hexdigest(),now())
        return Response('<?xml version="1.0" encoding="UTF-8"?><Response/>',media_type='application/xml') if inbound else result

    @app.post('/api/sms-hooks/{integration_id}/status')
    async def status(integration_id:str,request:Request,session:Session=Depends(get_session)):
        return await callback(integration_id,request,session,False)

    @app.post('/api/sms-hooks/{integration_id}/incoming')
    async def incoming(integration_id:str,request:Request,session:Session=Depends(get_session)):
        return await callback(integration_id,request,session,True)

    if demo_mode:
        @app.post(root+'/simulate-inbound',dependencies=[Depends(write)])
        def simulate(business_id:str,payload:InboundInput,session:Session=Depends(get_session)):
            from twilio.request_validator import RequestValidator
            customer=session.get(Customer,payload.customer_id)
            if not customer or customer.business_id!=business_id:raise HTTPException(404,'Customer not found')
            integration=next((v for v in integrations.values() if v['business_id']==business_id and v['scope']=='test' and v['adapter'].name=='simulated_sms'),None)
            if not integration or integration['adapter'].capabilities.get('network') is not False:raise HTTPException(409,'Fake SMS adapter required')
            adapter=integration['adapter'];params={'AccountSid':adapter.account_sid,'MessageSid':'SM'+secrets.token_hex(16),'From':customer.phone,'To':adapter.sender,'Body':payload.text}
            body=urlencode(params).encode();signature=RequestValidator(adapter.auth_token).compute_signature(adapter.inbound_url,params)
            event=adapter.verify_callback(body,signature,inbound=True)
            return sms.ingest(session,integration,event,hashlib.sha256(body).hexdigest(),now())
