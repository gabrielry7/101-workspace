"""Owner UI and business-scoped connector routes."""
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from . import connections as c, staff
from .connection_models import schema_ready


class AuthorizationResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    state: str = Field(min_length=1, max_length=256)
    code: str | None = Field(default=None, max_length=4096)
    error: str | None = Field(default=None, max_length=256)


class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    location: str = Field(pattern=r'^accounts/[0-9]+/locations/[0-9]+$', max_length=160)


def register_connections(app, get_session, scoped_staff, runtime, staff_cookie, production):
    if runtime:
        if runtime.mode not in {'test', 'live'} or (production and runtime.mode == 'test'):
            raise RuntimeError('Simulated connections cannot run in production')
        if runtime.mode == 'test' and not app.state.demo_mode:
            raise RuntimeError('Simulated connections require demo mode')
        if not schema_ready(app.state.engine):
            raise RuntimeError('Run explicit offline upgrade-connections before enabling Connections')
    app.state.connections = runtime
    web = Path(__file__).parent / 'web'

    @app.get('/connections', include_in_schema=False)
    def connections_page():
        return FileResponse(web / 'connections.html', headers={'Cache-Control': 'no-store'})

    @app.get('/connections/demo-authorize', include_in_schema=False)
    def simulated_consent(request: Request, session: Session = Depends(get_session)):
        if not runtime or runtime.mode != 'test':
            raise HTTPException(404, 'Unavailable')
        staff.authenticate(session, request.cookies.get(staff_cookie))
        return FileResponse(web / 'connections-consent.html', headers={'Cache-Control': 'no-store'})

    def require_runtime():
        if runtime is None:
            raise HTTPException(409, 'Google connection is not configured')

    root = '/api/operator/restaurants/{business_id}/connections'

    @app.get(root)
    def connection_status(business_id: str, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, 'growth.read')
        from .instagram_routes import status as instagram_status
        return {'google': c.document(session, business_id, runtime), 'instagram': instagram_status(session,business_id,getattr(app.state,'instagram',None)), 'others': [
            {'provider': name, 'state': 'not_implemented'} for name in ['facebook', 'search_console', 'ga4', 'tiktok']],
            'whatsapp': {'state': 'configured_separately', 'url': '/campaigns'}}

    @app.post(root + '/google/authorize')
    def authorize(business_id: str, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, 'settings.write')
        require_runtime()
        _, auth_session = staff.authenticate(session, request.cookies.get(staff_cookie))
        return {'url': c.start_authorization(session, business_id, auth_session.token_hash, runtime)}

    @app.get('/connections/google/callback', include_in_schema=False)
    def callback_page(request: Request):
        require_runtime()
        if any(len(request.query_params.getlist(key)) > 1 for key in ['state', 'code', 'error']):
            raise HTTPException(400, 'Duplicate authorization parameters')
        # Staff cookies are SameSite=Strict. A cross-site OAuth return therefore
        # lands on a same-origin bridge before an authenticated, CSRF-bound POST.
        return FileResponse(web / 'connections-callback.html', headers={'Cache-Control': 'no-store'})

    @app.post('/connections/google/complete', include_in_schema=False)
    def callback(body: AuthorizationResponse, request: Request):
        require_runtime()
        if bool(body.code) == bool(body.error):
            raise HTTPException(400, 'Invalid authorization response')
        with app.state.session_factory() as session:
            _, auth_session = staff.authenticate(session, request.cookies.get(staff_cookie))
            staff.csrf_check(request, auth_session)
            session_hash = auth_session.token_hash
        def permission(session, business):
            scoped_staff(request, session, business, 'settings.write')
        c.complete_authorization(app.state.session_factory, body.state, session_hash, runtime,
                                 permission, code=body.code, denied=bool(body.error))
        return {'completed': True}

    @app.post(root + '/google/select')
    def select(business_id: str, body: Selection, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, 'settings.write'); require_runtime()
        c.select_location(session, business_id, body.location, runtime)
        return {'scheduled': True}

    @app.post(root + '/google/refresh')
    def refresh(business_id: str, request: Request, discover: bool = False, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, 'settings.write'); require_runtime()
        c.refresh(session, business_id, runtime, discover=discover)
        return {'scheduled': True}

    @app.post(root + '/google/disconnect')
    def disconnect(business_id: str, request: Request, session: Session = Depends(get_session)):
        scoped_staff(request, session, business_id, 'settings.write'); require_runtime()
        c.disconnect(session, business_id, runtime)
        return {'disconnected_locally': True}
