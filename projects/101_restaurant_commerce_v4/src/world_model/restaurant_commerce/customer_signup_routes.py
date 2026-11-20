"""One signup page for direct links and QR; owner downloads stay staff-scoped."""
import io
import re
import hmac
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import Field, field_validator
from sqlalchemy import delete, inspect
from sqlalchemy.orm import Session
from . import customer_signup as signup
from .customer_signup_models import CustomerLoginSession, CustomerMembership
from .customer_signup_migrations import ready
from .models import Customer, utcnow
from .schemas import StrictModel


class Start(StrictModel):
    channel: Literal['phone', 'email']
    destination: str = Field(min_length=3, max_length=254)
    source: Literal['qr', 'website', 'direct'] = 'direct'


class Check(StrictModel):
    challenge_id: str = Field(min_length=36, max_length=36)
    code: str = Field(pattern=r'^[0-9]{6}$')


class Source(StrictModel):
    source: Literal['qr', 'website', 'direct'] = 'direct'


class Email(StrictModel):
    email: str | None = Field(default=None, max_length=254)

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        if value and not re.fullmatch(r"[^\s<>@]+@[^\s<>@.]+(?:\.[^\s<>@.]+)+", value):
            raise ValueError('email_invalid')
        return value or None


def register(app, get_session, scoped_staff, options, demo_mode, production):
    options = options or {}
    adapters = options.get('adapters', {})
    for adapter in adapters.values():
        if adapter.network is False and (production or not demo_mode or signup.scope(options) != 'test'):
            raise RuntimeError('Fake signup verification requires an explicit test environment')
        if adapter.network is True and signup.scope(options) != 'live':
            raise RuntimeError('Real signup verification cannot run in simulation')
    public_origin = signup.origin(options['public_origin'], production) if options.get('public_origin') else None
    if options and not ready(app.state.engine):
        raise RuntimeError('Signup requires the explicit offline upgrade-signup migration')
    app.state.signup_options = options
    clock = options.get('clock', utcnow)
    cookie = '__Host-commerce_customer' if production else 'commerce_customer'
    challenge_cookie = '__Host-signup_challenge' if production else 'signup_challenge'
    root = '/api/customer/signup/{business_id}'
    web = Path(__file__).parent / 'web'

    def configured(channel=None):
        if not public_origin or not any(signup.available(options, c) for c in ([channel] if channel else ['phone', 'email'])):
            raise HTTPException(503, 'verification_unconfigured')

    def request_origin(request):
        if request.headers.get('X-101-Signup') != '1' or request.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise HTTPException(403, 'same_site_required')
        if request.headers.get('Origin') and request.headers['Origin'] != public_origin:
            raise HTTPException(403, 'same_site_required')

    def current(request, session, mutate=False):
        token = request.cookies.get(cookie)
        account, login = signup.authenticate(session, token, options, clock())
        if mutate:
            request_origin(request)
            if not hmac.compare_digest(request.headers.get('X-101-Customer-CSRF', ''), signup.csrf(token)):
                raise HTTPException(403, 'session_changed')
        return account, login

    def read(business_id: str, request: Request, session: Session = Depends(get_session)):
        return scoped_staff(request, session, business_id, 'growth.read')

    @app.get('/join/{business_id}')
    def signup_page(business_id: str, session: Session = Depends(get_session)):
        signup.profile(session, business_id)
        return FileResponse(web / 'signup.html')

    @app.get('/customers/signup')
    def owner_page():
        return RedirectResponse("/workspace/customers?view=signup", status_code=307)

    @app.get(root)
    def metadata(business_id: str, request: Request, session: Session = Depends(get_session)):
        business = signup.profile(session, business_id)
        channels = {c: bool(public_origin and signup.available(options, c)) for c in ['phone', 'email']}
        ready = any(channels.values())
        me = None
        if ready:
            try:
                account, _ = current(request, session)
                me = {**signup.account_view(session, account, business_id), 'csrf': signup.csrf(request.cookies[cookie])}
            except HTTPException as exc:
                if exc.status_code != 401:
                    raise
        return {'business_id': business_id, 'business_name': business.display_name, 'available': ready,
                'mode': signup.scope(options) if ready else 'unconfigured', 'account': me, 'channels': channels,
                'countries': options.get('allowed_regions', ['CO']),
                'storefront_url': getattr(app.state, 'merchant_workspaces', {}).get(business_id, {}).get('store_url') or '/r/' + quote(business.slug, safe='')}

    @app.post(root + '/opened')
    def opened(business_id: str, payload: Source, request: Request, session: Session = Depends(get_session)):
        configured(); request_origin(request); signup.profile(session, business_id)
        client = request.client.host if request.client else 'unknown'
        signup.reserve(session, f'views:{signup.scope(options)}:{client}:{int(clock().timestamp()) // 3600}', 100)
        signup.event(session, business_id, signup.scope(options), payload.source, 'page_opened', clock())
        session.commit()
        return {'recorded': True}

    @app.post(root + '/start')
    def start(business_id: str, payload: Start, request: Request, response: Response, session: Session = Depends(get_session)):
        configured(payload.channel); request_origin(request)
        result, binding = signup.begin(session, business_id, payload.channel, payload.destination, payload.source,
            request.client.host if request.client else 'unknown', options, clock())
        response.set_cookie(challenge_cookie, binding, max_age=600, httponly=True, secure=production, samesite='lax')
        return result

    @app.post(root + '/verify')
    def verify(business_id: str, payload: Check, request: Request, response: Response, session: Session = Depends(get_session)):
        configured(); request_origin(request)
        token = signup.finish(session, business_id, payload.challenge_id, request.cookies.get(challenge_cookie), payload.code, options, clock())
        old = request.cookies.get(cookie)
        if old:
            session.execute(delete(CustomerLoginSession).where(CustomerLoginSession.token_hash == signup.digest(old)))
            session.commit()
        response.set_cookie(cookie, token, max_age=30 * 86400, httponly=True, secure=production, samesite='lax')
        response.delete_cookie(challenge_cookie, secure=production, httponly=True, samesite='lax')
        return {'verified': True}

    @app.post(root + '/join')
    def join(business_id: str, payload: Source, request: Request, session: Session = Depends(get_session)):
        configured()
        account, _ = current(request, session, True)
        account = signup.lock_account(session, account.id, clock())
        signup.membership(session, account, business_id, payload.source, clock())
        session.commit()
        return signup.account_view(session, account, business_id)

    @app.put(root + '/email')
    def email(business_id: str, payload: Email, request: Request, session: Session = Depends(get_session)):
        configured()
        account, _ = current(request, session, True)
        signup.lock_account(session, account.id, clock())
        link = session.get(CustomerMembership, (account.id, business_id))
        if not link:
            raise HTTPException(404, 'membership_required')
        customer = session.get(Customer, link.customer_id)
        if account.channel == 'email':
            raise HTTPException(409, 'verified_email_change_requires_verification')
        customer.email = signup.email_address(payload.email) if payload.email else None
        session.commit()
        return {'saved': True, 'email_verified': False}

    @app.post(root + '/logout')
    def logout(business_id: str, request: Request, response: Response, session: Session = Depends(get_session)):
        configured()
        _, login = current(request, session, True)
        session.delete(login); session.commit()
        response.delete_cookie(cookie, secure=production, httponly=True, samesite='lax')
        return {'signed_out': True}

    owner_root = '/api/operator/restaurants/{business_id}/signup'

    @app.get(owner_root, dependencies=[Depends(read)])
    def owner(business_id: str, session: Session = Depends(get_session)):
        business = signup.profile(session, business_id)
        path = '/join/' + quote(business_id, safe='')
        return {'business_name': business.display_name, 'available': bool(public_origin and any(signup.available(options, c) for c in ['phone', 'email'])),
                'mode': signup.scope(options) if adapters else 'unconfigured',
                'signup_url': public_origin + path + '?source=website' if public_origin else None,
                'qr_url': public_origin + path + '?source=qr' if public_origin else None,
                'funnel': signup.funnel(session, business_id, signup.scope(options)) if options else []}

    @app.get(owner_root + '/qr.{format}', dependencies=[Depends(read)])
    def qr(business_id: str, format: str, session: Session = Depends(get_session)):
        signup.profile(session, business_id)
        if not public_origin:
            raise HTTPException(409, 'signup_origin_unconfigured')
        if format not in {'png', 'svg'}:
            raise HTTPException(404, 'format_unavailable')
        import segno
        value = public_origin + '/join/' + quote(business_id, safe='') + '?source=qr'
        output = io.BytesIO()
        segno.make_qr(value, error='m').save(output, kind=format, scale=10, border=4, dark='#000000', light='#ffffff')
        return Response(output.getvalue(), media_type='image/png' if format == 'png' else 'image/svg+xml',
                        headers={'Content-Disposition': f'attachment; filename="101-signup.{format}"', 'Cache-Control': 'no-store'})
