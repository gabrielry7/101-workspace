"""Business signup, durable verification challenges and persistent customer sessions."""
import hashlib
import hmac
import secrets
import re
from datetime import UTC, timedelta
from urllib.parse import urlsplit
import phonenumbers
from fastapi import HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from .models import Customer, RestaurantCommerceProfile
from .staff import aware
from .customer_signup_models import (
    CustomerAccount, CustomerMembership, CustomerLoginSession,
    SignupChallenge, SignupThrottle, SignupEvent,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def phone_number(value):
    try:
        if not value.startswith('+') or len(value) > 40:
            raise ValueError()
        if any(c not in '+0123456789 ()-.' for c in value):
            raise ValueError()
        phone = phonenumbers.parse(value, None)
        if not phonenumbers.is_valid_number(phone):
            raise ValueError()
        return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
    except (ValueError, phonenumbers.NumberParseException):
        raise HTTPException(422, 'phone_invalid') from None


def profile(session, business):
    row = session.get(RestaurantCommerceProfile, business)
    if not row:
        raise HTTPException(404, 'business_not_found')
    return row


def origin(value, production):
    p = urlsplit(value)
    if (p.scheme not in {'https', 'http'} or not p.hostname or p.username or p.password
            or p.path or p.query or p.fragment or '\\' in value or any(ord(c) <= 32 for c in value)
            or (p.scheme == 'http' and (production or p.hostname not in {'localhost', '127.0.0.1', '::1'}))):
        raise ValueError('Signup requires a configured HTTPS origin (loopback HTTP in development)')
    _ = p.port
    return value


def event(session, business, scope, source, stage, now):
    session.add(SignupEvent(business_id=business, scope=scope, source=source, stage=stage, created_at=now))


def reserve(session, key, limit):
    """Atomic durable counters, shared by all workers; no provider call on denial."""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    insert = sqlite_insert if session.get_bind().dialect.name == 'sqlite' else pg_insert
    session.execute(insert(SignupThrottle).values(key=digest(key), count=0).on_conflict_do_nothing())
    result = session.execute(update(SignupThrottle).where(SignupThrottle.key == digest(key), SignupThrottle.count < limit)
                             .values(count=SignupThrottle.count + 1))
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(429, 'verification_limit', headers={'Retry-After': '60'})


def scope(options):
    return options.get('mode', 'live')


def email_address(value):
    # Case-insensitive account identifiers; never remove dots or plus tags.
    value = value.strip().lower()
    if (len(value) > 254 or not value.isascii() or not re.fullmatch(
            r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value)
            or '..' in value or value.startswith('.') or '.@' in value or len(value.split('@')[0]) > 64):
        raise HTTPException(422, 'email_invalid')
    return value


def available(options, channel):
    adapter = options.get('adapters', {}).get(channel)
    if not adapter or adapter.validate():
        return False
    if adapter.network:
        return (scope(options) == 'live' and options.get('live_enabled') is True
                and options.get('max_cost_per_request_microusd', 0) > 0
                and options.get('daily_budget_microusd', 0) >= options['max_cost_per_request_microusd'])
    return scope(options) == 'test'


def begin(session, business, channel, destination, source, client_key, options, now):
    profile(session, business)
    if not available(options, channel):
        raise HTTPException(503, 'verification_unconfigured')
    destination = phone_number(destination) if channel == 'phone' else email_address(destination)
    if channel == 'phone':
        region = phonenumbers.region_code_for_number(phonenumbers.parse(destination))
        if region not in options.get('allowed_regions', ['CO']):
            raise HTTPException(422, 'country_unavailable')
    adapter = options['adapters'][channel]
    mode = scope(options)
    hour = int(now.timestamp()) // 3600
    minute = int(now.timestamp()) // 60
    limit = options.get('daily_request_limit', 100)
    if adapter.network:
        limit = min(limit, options['daily_budget_microusd'] // options['max_cost_per_request_microusd'])
    reserve(session, f'{mode}:day:{now.date()}', limit)
    reserve(session, f'{mode}:{channel}:{destination}:{hour}', 5)
    reserve(session, f'{mode}:cooldown:{channel}:{destination}:{minute}', 1)
    reserve(session, f'{mode}:client:{client_key}:{hour}', 20)
    last = session.scalar(select(SignupChallenge).where(SignupChallenge.scope == mode,
        SignupChallenge.channel == channel, SignupChallenge.destination == destination)
        .order_by(SignupChallenge.created_at.desc()).limit(1))
    if last and (now - aware(last.created_at)).total_seconds() < 60:
        session.rollback()
        raise HTTPException(429, 'verification_cooldown', headers={'Retry-After': '60'})
    binding = secrets.token_urlsafe(32)
    challenge = SignupChallenge(business_id=business, channel=channel, destination=destination,
        scope=mode, binding_hash=digest(binding), source=source,
        created_at=now, expires_at=now + timedelta(minutes=10))
    session.add(challenge)
    session.commit()
    try:
        result = adapter.start(destination, challenge.id)
        challenge.state = result.state if result.state in {'pending', 'rejected'} else 'unknown'
        challenge.provider_id = result.provider_id
    except Exception:
        challenge.state = 'unknown'
    if challenge.state == 'pending':
        event(session, business, mode, source, 'code_requested', now)
    session.commit()
    if challenge.state != 'pending':
        raise HTTPException(503, 'verification_unavailable')
    result = {'challenge_id': challenge.id, 'destination': destination, 'channel': channel,
              'expires_in': 600, 'resend_after': 60, 'mode': mode}
    if adapter.network is False:
        result['demo_code'] = adapter.code(challenge.provider_id)
    return result, binding


def membership(session, account, business, source, now):
    profile(session, business)
    row = session.get(CustomerMembership, (account.id, business))
    if row:
        return row
    customer = session.scalar(select(Customer).where(Customer.business_id == business, Customer.phone == account.identifier)) if account.channel == 'phone' else None
    # The canonical table's exact normalized phone key remains the authority. Do not
    # silently merge legacy local-format contacts without a country/identity review.
    if customer is None:
        candidate = Customer(business_id=business, phone=account.identifier if account.channel == 'phone' else None,
                             email=account.identifier if account.channel == 'email' else None)
        try:
            with session.begin_nested():
                session.add(candidate)
                session.flush()
            customer = candidate
        except IntegrityError:
            customer = session.scalar(select(Customer).where(Customer.business_id == business, Customer.phone == account.identifier)) if account.channel == 'phone' else None
    existing = session.scalar(select(CustomerMembership).where(CustomerMembership.customer_id == customer.id))
    if existing and existing.account_id != account.id:
        raise HTTPException(409, 'membership_scope_conflict')
    row = CustomerMembership(account_id=account.id, business_id=business, customer_id=customer.id, source=source, created_at=now)
    session.add(row)
    event(session, business, account.scope, source, 'membership_created', now)
    session.flush()
    return row


def lock_account(session, account_id, now):
    session.execute(update(CustomerAccount).where(CustomerAccount.id == account_id).values(verified_at=CustomerAccount.verified_at))
    return session.get(CustomerAccount, account_id)


def finish(session, business, challenge_id, binding, code, options, now):
    challenge = session.get(SignupChallenge, challenge_id)
    if (not challenge or challenge.business_id != business or challenge.scope != scope(options)
            or not binding or not hmac.compare_digest(challenge.binding_hash, digest(binding))):
        raise HTTPException(401, 'verification_invalid')
    if aware(challenge.expires_at) <= now or challenge.state != 'pending' or challenge.attempts >= 5:
        raise HTTPException(409, 'verification_expired_or_used')
    claimed = session.execute(update(SignupChallenge).where(SignupChallenge.id == challenge.id,
        SignupChallenge.state == 'pending', SignupChallenge.attempts < 5)
        .values(state='checking', attempts=SignupChallenge.attempts + 1))
    session.commit()
    if claimed.rowcount != 1:
        raise HTTPException(409, 'verification_in_progress')
    try:
        result = options['adapters'][challenge.channel].check(challenge.destination, challenge.provider_id, code)
        state = result.state
    except Exception:
        state = 'unknown'
    if state != 'approved':
        challenge.state = 'pending' if state == 'denied' and challenge.attempts < 5 else 'unknown' if state == 'unknown' else 'rejected'
        session.commit()
        raise HTTPException(503 if state == 'unknown' else 422, 'verification_unavailable' if state == 'unknown' else 'code_incorrect')
    query = select(CustomerAccount).where(CustomerAccount.scope == challenge.scope, CustomerAccount.channel == challenge.channel, CustomerAccount.identifier == challenge.destination)
    account = session.scalar(query)
    if account is None:
        candidate = CustomerAccount(channel=challenge.channel, identifier=challenge.destination, scope=challenge.scope, verified_at=now)
        try:
            with session.begin_nested():
                session.add(candidate)
                session.flush()
            account = candidate
        except IntegrityError:
            account = session.scalar(query)
    account = lock_account(session, account.id, now)
    membership(session, account, business, challenge.source, now)
    token = secrets.token_urlsafe(32)
    session.add(CustomerLoginSession(token_hash=digest(token), account_id=account.id, expires_at=now + timedelta(days=30)))
    challenge.state = 'consumed'
    event(session, business, account.scope, challenge.source, 'identifier_verified', now)
    session.commit()
    return token


def authenticate(session, token, options, now):
    row = session.get(CustomerLoginSession, digest(token)) if token else None
    if not row or aware(row.expires_at) <= now:
        raise HTTPException(401, 'sign_in_required')
    account = session.get(CustomerAccount, row.account_id)
    if not account or account.scope != scope(options):
        raise HTTPException(401, 'sign_in_required')
    return account, row


def csrf(token):
    return digest('customer-session-csrf:' + token)


def account_view(session, account, business):
    link = session.get(CustomerMembership, (account.id, business))
    customer = session.get(Customer, link.customer_id) if link else None
    return {'identifier': account.identifier, 'login_method': account.channel, 'member': link is not None,
            'email': customer.email if customer else None,
            'email_verified': bool(customer and account.channel == 'email' and customer.email == account.identifier),
            'business_id': business}


def funnel(session, business, mode):
    rows = session.execute(select(SignupEvent.source, SignupEvent.stage, func.count()).where(
        SignupEvent.business_id == business, SignupEvent.scope == mode).group_by(SignupEvent.source, SignupEvent.stage))
    return [{'source': source, 'stage': stage, 'count': count} for source, stage, count in rows]
