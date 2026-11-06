"""Scoped connection lifecycle and durable, fenced read synchronization."""
import json
import os
import secrets
from datetime import timedelta
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import delete, or_, select, update
from .models import utcnow
from .staff import aware, digest
from .connection_models import BusinessConnection as Connection, ConnectionAuthorization as Authorization, ConnectionJob as Job
from .connection_google import GoogleBusinessAdapter, ConnectionFailure

PROVIDER = 'google_business'
CACHE_TTL = timedelta(days=1)


class ConnectionRuntime:
    def __init__(self, adapter, key, *, clock=utcnow, worker=True):
        self.adapter, self.mode, self.clock, self.worker = adapter, adapter.mode, clock, worker
        self.provider = getattr(adapter, "provider", PROVIDER)
        self.cipher = Fernet(key)

    def seal(self, value):
        return self.cipher.encrypt(json.dumps(value).encode()).decode()

    def open(self, value):
        try:
            return json.loads(self.cipher.decrypt(value.encode()))
        except (InvalidToken, ValueError, AttributeError) as exc:
            raise ConnectionFailure('credential_key_unavailable') from exc


def from_environment():
    if os.getenv('COMMERCE_GOOGLE_CONNECTION_ENABLED', '0') != '1':
        return None
    required = ['COMMERCE_GOOGLE_CLIENT_ID', 'COMMERCE_GOOGLE_CLIENT_SECRET',
                'COMMERCE_GOOGLE_REDIRECT_URI', 'COMMERCE_CONNECTION_KEY']
    if any(not os.getenv(k) for k in required):
        raise RuntimeError('Enabled Google connection requires client ID, secret, exact redirect URI and encryption key')
    uri = os.environ[required[2]]
    parsed = urlsplit(uri)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path != '/connections/google/callback' or parsed.query or parsed.fragment):
        raise RuntimeError('Google redirect must be HTTPS with the exact Connections callback path')
    return ConnectionRuntime(GoogleBusinessAdapter(*(os.environ[k] for k in required[:3])), os.environ[required[3]])


def find(session, business, runtime):
    return session.scalar(select(Connection).where(Connection.business_id == business,
        Connection.provider == runtime.provider, Connection.mode == runtime.mode))


def lock(session, connection_id):
    # An actual write serializes SQLite as well as PostgreSQL. Network calls never
    # run while this short lock is held.
    session.execute(update(Connection).where(Connection.id == connection_id).values(generation=Connection.generation))
    return session.get(Connection, connection_id, populate_existing=True)


def ensure(session, business, runtime):
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    insert = pg_insert if session.bind.dialect.name == 'postgresql' else sqlite_insert
    session.execute(insert(Connection).values(business_id=business, provider=runtime.provider, mode=runtime.mode,
        state='disconnected', generation=0).on_conflict_do_nothing(index_elements=['business_id', 'provider', 'mode']))
    row = find(session, business, runtime)
    return lock(session, row.id)


def enqueue(session, row, operation, now, *, secret=None):
    job = session.get(Job, row.id)
    if job is None:
        job = Job(connection_id=row.id)
        session.add(job)
    job.generation, job.operation, job.state = row.generation, operation, 'pending'
    job.lease, job.lease_until, job.attempts, job.available_at = None, None, 0, now
    job.secret = secret
    job.expires_at = now + timedelta(days=7) if secret else None


def start_authorization(session, business, session_hash, runtime):
    now = runtime.clock()
    row = ensure(session, business, runtime)
    if row.state == 'exchanging':
        raise HTTPException(409, 'Authorization is completing; retry shortly')
    if row.state == 'disconnecting':
        raise HTTPException(409, 'Revocation is pending; reconnect after it completes')
    row.generation += 1
    row.state, row.error, row.next_sync = 'authorizing', None, None
    session.execute(delete(Authorization).where(Authorization.connection_id == row.id))
    session.execute(delete(Job).where(Job.connection_id == row.id))
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    session.add(Authorization(state_hash=digest(state), connection_id=row.id,
        session_hash=session_hash, generation=row.generation,
        verifier=runtime.seal({'verifier': verifier}), expires_at=now + timedelta(minutes=10)))
    session.commit()
    return runtime.adapter.authorize_url(state, verifier)


def complete_authorization(factory, state, session_hash, runtime, authorize, *, code=None, denied=False):
    now = runtime.clock()
    with factory() as session:
        grant = session.get(Authorization, digest(state))
        if not grant or grant.session_hash != session_hash or aware(grant.expires_at) <= now:
            raise HTTPException(400, 'Authorization expired, already used or belongs to another session')
        row = session.get(Connection, grant.connection_id)
        authorize(session, row.business_id)  # Existing staff authentication commits its heartbeat.
        row = lock(session, grant.connection_id)
        if row.generation != grant.generation or row.mode != runtime.mode or row.provider != runtime.provider or row.state != 'authorizing':
            raise HTTPException(409, 'Authorization superseded')
        connection_id, generation = row.id, row.generation
        verifier = runtime.open(grant.verifier)['verifier']
        consumed = session.execute(delete(Authorization).where(Authorization.state_hash == digest(state),
            Authorization.session_hash == session_hash, Authorization.generation == row.generation))
        if consumed.rowcount != 1:
            raise HTTPException(400, 'Authorization already used')
        row.state = 'access_denied' if denied else 'exchanging'
        row.next_sync = now + timedelta(minutes=10)
        session.commit()  # Consume before the single-use exchange; no blind retry.
    if denied:
        return
    try:
        tokens = runtime.adapter.exchange(code, verifier, now)
        error = None
    except ConnectionFailure as exc:
        tokens, error = None, exc.reason
    with factory() as session:
        row = lock(session, connection_id)
        if row.generation != generation or row.state != 'exchanging':
            # A concurrent disconnect must never restore a connection.
            return
        if tokens is None:
            row.state, row.error = 'reconnect_required', error
        else:
            row.secret = runtime.seal(tokens)
            row.state, row.error = 'discovering', None
            row.assets = row.snapshot = row.selected = None
            row.assets_until = row.snapshot_until = row.last_success = None
            enqueue(session, row, 'discover', now)
        session.commit()


def select_location(session, business, selected, runtime):
    row = find(session, business, runtime)
    if not row:
        raise HTTPException(409, 'Connect an account first')
    row = lock(session, row.id)
    if row.state not in {'choose_location', 'connected', 'partial', 'sync_error'} or not row.secret:
        raise HTTPException(409, 'Account is not ready for location selection')
    if not row.assets_until or aware(row.assets_until) <= runtime.clock():
        raise HTTPException(409, 'Location selection expired; rediscover accounts')
    if selected not in {a['key'] for a in json.loads(row.assets or '[]')}:
        raise HTTPException(403, 'Location was not authorized on this connection')
    row.generation += 1
    row.selected, row.state, row.error = selected, 'syncing', None
    row.snapshot = row.snapshot_until = row.last_success = None
    enqueue(session, row, 'sync', runtime.clock())
    session.commit()


def refresh(session, business, runtime, *, discover=False):
    row = find(session, business, runtime)
    if not row:
        raise HTTPException(409, 'Connect an account first')
    row = lock(session, row.id)
    if not row.secret or row.state in {'authorizing', 'exchanging', 'disconnecting', 'reconnect_required', 'access_denied'}:
        raise HTTPException(409, 'Reconnect this account')
    job = session.get(Job, row.id)
    if job and job.state in {'pending', 'running'}:
        return
    now = runtime.clock()
    if row.last_success and now < aware(row.last_success) + timedelta(seconds=60):
        raise HTTPException(429, 'Wait one minute before refreshing')
    row.generation += 1
    operation = 'discover' if discover or not row.selected else 'sync'
    row.state, row.error = ('discovering' if operation == 'discover' else 'syncing'), None
    enqueue(session, row, operation, now)
    session.commit()


def disconnect(session, business, runtime):
    row = find(session, business, runtime)
    if not row:
        return
    row = lock(session, row.id)
    if row.state == 'exchanging':
        raise HTTPException(409, 'Authorization is completing; retry disconnect shortly')
    if row.state == 'disconnecting':
        return
    row.generation += 1
    secret = row.secret
    row.secret = row.assets = row.snapshot = row.selected = None
    row.assets_until = row.snapshot_until = row.last_success = row.next_sync = None
    local_only=getattr(runtime.adapter, 'local_disconnect_only', False)
    if local_only:
        secret=None
    row.error = 'revoke_in_instagram_settings' if local_only else None
    row.state = 'disconnecting' if secret else 'disconnected'
    session.execute(delete(Authorization).where(Authorization.connection_id == row.id))
    if secret:
        enqueue(session, row, 'revoke', runtime.clock(), secret=secret)
    else:
        session.execute(delete(Job).where(Job.connection_id == row.id))
    session.commit()


def document(session, business, runtime):
    if runtime is None:
        return {'provider': PROVIDER, 'mode': None, 'state': 'unconfigured', 'assets': [], 'snapshot': None}
    row = find(session, business, runtime)
    if not row:
        return {'provider': runtime.provider, 'mode': runtime.mode, 'state': 'disconnected', 'assets': [], 'snapshot': None}
    now = runtime.clock()
    # Expired content is never served even if the maintenance worker is stopped.
    assets = json.loads(row.assets) if row.assets and row.assets_until and aware(row.assets_until) > now else []
    snapshot = json.loads(row.snapshot) if row.snapshot and row.snapshot_until and aware(row.snapshot_until) > now else None
    job = session.get(Job, row.id)
    return {'provider': runtime.provider, 'mode': row.mode, 'state': row.state, 'error': row.error,
            'selected': row.selected, 'assets': assets, 'snapshot': snapshot,
            'last_success': row.last_success, 'cache_expires_at': row.snapshot_until,
            'job': {'state': job.state, 'attempts': job.attempts} if job else None,
            'capabilities': getattr(runtime.adapter, 'capabilities', {'read_listing': True, 'read_reviews': True, 'read_metrics': True,
                             'write_listing': False, 'reply_reviews': False})}


def maintenance(session, runtime):
    now = runtime.clock()
    scope = (Connection.provider == runtime.provider) & (Connection.mode == runtime.mode)
    ids = select(Connection.id).where(scope)
    session.execute(delete(Authorization).where(Authorization.connection_id.in_(ids), Authorization.expires_at <= now))
    session.execute(update(Connection).where(scope, Connection.assets_until <= now).values(assets=None, assets_until=None))
    session.execute(update(Connection).where(scope, Connection.snapshot_until <= now).values(snapshot=None, snapshot_until=None))
    session.execute(update(Connection).where(scope, Connection.state == 'authorizing',
        ~Connection.id.in_(select(Authorization.connection_id))).values(state='reconnect_required'))
    session.execute(update(Connection).where(scope, Connection.state == 'exchanging', Connection.next_sync <= now).values(state='reconnect_required'))
    # Expiring revocation material cannot live indefinitely after an outage.
    for job in session.scalars(select(Job).where(Job.connection_id.in_(ids), Job.operation == 'revoke', Job.expires_at <= now)):
        row = lock(session, job.connection_id)
        if row.generation == job.generation and row.state == 'disconnecting':
            row.state, row.error = 'disconnected', 'revoke_in_provider_account' if runtime.provider != PROVIDER else 'revoke_in_google_account'
        session.delete(job)
    for row in session.scalars(select(Connection).where(Connection.mode == runtime.mode, Connection.provider == runtime.provider,
            Connection.state.in_(['connected', 'partial']), Connection.next_sync <= now)):
        row = lock(session, row.id)
        if row.state not in {'connected', 'partial'} or not row.next_sync or aware(row.next_sync) > now:
            continue
        row.generation += 1
        row.state = 'syncing'
        enqueue(session, row, 'sync', now)
    session.commit()


def dispatch_one(factory, runtime):
    now = runtime.clock()
    with factory() as session:
        maintenance(session, runtime)
        candidate = session.scalar(select(Job.connection_id).join(Connection).where(Connection.mode == runtime.mode, Connection.provider == runtime.provider,
            Job.available_at <= now, or_(Job.state == 'pending', (Job.state == 'running') & (Job.lease_until <= now)))
            .order_by(Job.available_at).limit(1))
        if not candidate:
            return False
        row = lock(session, candidate)
        job = session.get(Job, candidate, populate_existing=True)
        if (not job or job.generation != row.generation or job.state not in {'pending', 'running'}
                or aware(job.available_at) > now or (job.state == 'running' and aware(job.lease_until) > now)):
            session.rollback()
            return False
        lease = secrets.token_hex(24)
        job.state, job.lease, job.lease_until = 'running', lease, now + timedelta(minutes=5)
        job.attempts += 1
        generation, operation, selected = row.generation, job.operation, row.selected
        secret = job.secret if operation == 'revoke' else row.secret
        session.commit()
    result, failure = None, None
    try:
        tokens = runtime.open(secret)
        if operation == 'revoke':
            runtime.adapter.revoke(tokens)
        else:
            tokens = runtime.adapter.refresh(tokens, now)
            # Save refreshed credentials before further network operations.
            with factory() as session:
                row = lock(session, candidate)
                job = session.get(Job, candidate)
                if row.generation != generation or not job or job.lease != lease:
                    return True
                row.secret = runtime.seal(tokens)
                session.commit()
            result = runtime.adapter.discover(tokens) if operation == 'discover' else runtime.adapter.snapshot(tokens, selected, now)
    except ConnectionFailure as exc:
        failure = exc
    except Exception:
        # Do not leak tokens or provider response text into logs or the UI.
        failure = ConnectionFailure('invalid_provider_response')
    with factory() as session:
        row = lock(session, candidate)
        job = session.get(Job, candidate)
        if row.generation != generation or not job or job.lease != lease:
            return True
        job.lease = job.lease_until = None
        if failure:
            row.error = failure.reason
            if failure.retry and job.attempts < 3:
                job.state, job.available_at = 'pending', now + timedelta(seconds=30 * 2 ** (job.attempts - 1))
            else:
                job.state = 'failed'
                row.state = ('disconnecting' if operation == 'revoke' else
                             'reconnect_required' if failure.reason in {'reconnect_required', 'credential_key_unavailable'} else 'sync_error')
        else:
            job.state = 'done'
            row.error = None
            if operation == 'revoke':
                row.state = 'disconnected'
                job.secret = None
            elif operation == 'discover':
                row.assets, row.assets_until = json.dumps(result), now + CACHE_TTL
                row.state = 'choose_location'
            else:
                row.snapshot, row.snapshot_until = json.dumps(result), now + CACHE_TTL
                row.last_success, row.next_sync = now, (now + timedelta(hours=12) if getattr(runtime.adapter, 'automatic_sync', True) else None)
                row.state = 'partial' if result['errors'] else 'connected'
        session.commit()
    return True


def start_worker(factory, runtime):
    import logging
    from threading import Event, Thread
    stop = Event()
    def run():
        while not stop.wait(1):
            try:
                dispatch_one(factory, runtime)
            except Exception:
                logging.getLogger(__name__).warning('Connection worker deferred; next cycle will recover')
    thread = Thread(target=run, name='commerce-connections', daemon=True)
    thread.start()
    return stop, thread
