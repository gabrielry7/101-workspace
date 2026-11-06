"""Instagram authorization reuses existing staff, tenant and durable connection contracts."""
from pathlib import Path
from datetime import datetime
from .staff import aware
from .connection_google import ConnectionFailure
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from . import connections as c, staff
from .connection_instagram import configuration
from .connection_models import schema_ready
from .connection_routes import AuthorizationResponse


class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    account_id:str=Field(pattern=r'^[0-9]{1,40}$')


def status(session,business,runtime):
    if runtime is None:
        cfg=configuration()
        return {'provider':'instagram','state':'unconfigured','assets':[],'snapshot':None,
                'configured':False,'missing_configuration':cfg['missing'], 'enabled':cfg['enabled'],
                'capabilities':{'posts':'blocked','counts':'blocked','insights':'not_enabled','publish':False}}
    result=c.document(session,business,runtime)
    result['configured']=True
    row=c.find(session,business,runtime)
    if row and row.secret and row.state in {'connected','partial','choose_location','sync_error'}:
        try:
            expiry=aware(datetime.fromisoformat(runtime.open(row.secret)['expires_at']))
            if expiry<=runtime.clock():
                result['state']='reconnect_required'
                result['error']='authorization_expired'
        except (ConnectionFailure,ValueError,KeyError):
            result['state']='reconnect_required'
            result['error']='credential_key_unavailable'
    result['verification']='fixture' if runtime.mode=='test' else ('live_read' if result.get('snapshot') else 'not_live_verified')
    result['token_policy']='short_lived_reconnect_required_after_expiry'
    snapshot=result.get('snapshot')
    if snapshot:
        result['capabilities']={**result['capabilities'],'read_posts':'fixture' if runtime.mode=='test' else 'live_verified',
                                'post_counts':'partial' if snapshot['errors'] else ('fixture' if runtime.mode=='test' else 'live_verified')}
    result['remote_revocation']='remove_access_in_instagram_settings'
    return result


def register(app,get_session,scoped_staff,runtime,staff_cookie,production):
    if runtime:
        if runtime.provider!='instagram' or (runtime.mode=='test' and (production or not app.state.demo_mode)):
            raise RuntimeError('Invalid Instagram runtime scope')
        if not schema_ready(app.state.engine):raise RuntimeError('Run offline upgrade-connections first')
    app.state.instagram=runtime
    root='/api/operator/restaurants/{business_id}/social/instagram'
    def configured():
        if runtime is None:raise HTTPException(409,'instagram_not_configured')
    def write(business_id:str,request:Request,session=Depends(get_session)):
        return scoped_staff(request,session,business_id,'settings.write')

    @app.get(root)
    def read(business_id:str,request:Request,session=Depends(get_session)):
        scoped_staff(request,session,business_id,'growth.read')
        return status(session,business_id,runtime)
    @app.post(root+'/authorize',dependencies=[Depends(write)])
    def authorize(business_id:str,request:Request,session=Depends(get_session)):
        configured()
        _,auth=staff.authenticate(session,request.cookies.get(staff_cookie))
        return {'url':c.start_authorization(session,business_id,auth.token_hash,runtime)}
    @app.get('/connections/instagram/callback',include_in_schema=False)
    def bridge(request:Request):
        configured()
        if any(len(request.query_params.getlist(k))>1 for k in ['state','code','error']):
            raise HTTPException(400,'duplicate_authorization_parameters')
        return FileResponse(Path(__file__).parent/'web/workspace/index.html',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    @app.post('/connections/instagram/complete',include_in_schema=False)
    def complete(body:AuthorizationResponse,request:Request):
        configured()
        if bool(body.code)==bool(body.error):raise HTTPException(400,'invalid_authorization_response')
        with app.state.session_factory() as session:
            _,auth=staff.authenticate(session,request.cookies.get(staff_cookie))
            staff.csrf_check(request,auth)
            session_hash=auth.token_hash
        def permission(session,business):scoped_staff(request,session,business,'settings.write')
        c.complete_authorization(app.state.session_factory,body.state,session_hash,runtime,permission,code=body.code,denied=bool(body.error))
        return {'completed':True}
    @app.post(root+'/select',dependencies=[Depends(write)])
    def select(business_id:str,body:Selection,session=Depends(get_session)):
        configured();c.select_location(session,business_id,body.account_id,runtime)
        return {'scheduled':True}
    @app.post(root+'/refresh',dependencies=[Depends(write)])
    def refresh(business_id:str,session=Depends(get_session)):
        configured();c.refresh(session,business_id,runtime)
        return {'scheduled':True}
    @app.post(root+'/disconnect',dependencies=[Depends(write)])
    def disconnect(business_id:str,session=Depends(get_session)):
        configured();c.disconnect(session,business_id,runtime)
        return {'disconnected_locally':True,'provider_revocation':'remove_access_in_instagram_settings'}
