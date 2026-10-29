"""Named local staff sessions. No legacy token or implicit business authority."""

import hashlib
import hmac
import re
import secrets
import time
from datetime import UTC, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select, update

from .financial_auth import FinancialPrincipal
from .models import (
    StaffAccount,
    StaffAudit,
    StaffLoginWindow,
    StaffMembership,
    StaffSession,
    utcnow,
)

COOKIE = "commerce_staff"
READ = frozenset({"operations.read", "growth.read", "finance.read"})
OPERATE = frozenset({"operations.write", "contact.read"})
FINANCE = frozenset({"finance.lookup", "finance.refund", "finance.resolve"})
ROLES = {
    "viewer": READ,
    "operator": READ | OPERATE,
    "finance": READ | FINANCE,
    "manager": READ | OPERATE | FINANCE | {"growth.write"},
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def username(value):
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._@+-]{2,119}", value):
        raise ValueError(
            "Staff username must contain 3–120 ASCII letters, digits or ._@+-"
        )
    return value


def password_hash(password, salt=None):
    if not 15 <= len(password) <= 128 or any(
        0xD800 <= ord(c) <= 0xDFFF for c in password
    ):
        raise ValueError("Use a passphrase of 15–128 characters")
    salt = salt or secrets.token_hex(16)
    key = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=32768,
        r=8,
        p=3,
        maxmem=64 * 1024 * 1024,
    )
    return "scrypt32m3$" + salt + "$" + key.hex()


def verify_password(password, encoded):
    # Same expensive operation for missing/disabled accounts; no account oracle.
    parts = encoded.split("$") if encoded else []
    salt = parts[1] if len(parts) == 3 and parts[0] == "scrypt32m3" else "00" * 16
    candidate = password_hash(password, salt)
    return hmac.compare_digest(candidate, encoded or "")


def provision(
    session, login, password, business_id, role, *, actor, platform_admin=False
):
    if role not in ROLES or not actor:
        raise ValueError("Explicit role and provisioning actor required")
    name = username(login)
    account = session.scalar(select(StaffAccount).where(StaffAccount.username == name))
    if account:
        raise ValueError("Account exists; use explicit reset or membership maintenance")
    account = StaffAccount(
        username=name,
        password_hash=password_hash(password),
        platform_admin=platform_admin,
    )
    session.add(account)
    session.flush()
    session.add(
        StaffMembership(account_id=account.id, business_id=business_id, role=role)
    )
    session.add(
        StaffAudit(
            actor_id=actor,
            business_id=business_id,
            action="staff.provision",
            resource=account.id,
        )
    )
    session.commit()
    return account


def throttle(session, name, ip):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    now = utcnow()
    minute = int(time.time() // 60)
    # Bound expensive password work across workers and unknown-account guesses.
    for subject, limit in (("global", 100), ("ip:" + ip, 20), ("user:" + name, 5)):
        key = digest(f"{subject}:{minute}")
        statement = insert(StaffLoginWindow).values(
            key=key, attempts=1, expires_at=now + timedelta(minutes=2)
        )
        count = session.scalar(
            statement.on_conflict_do_update(
                index_elements=["key"], set_={"attempts": StaffLoginWindow.attempts + 1}
            ).returning(StaffLoginWindow.attempts)
        )
        if count > limit:
            session.commit()
            raise HTTPException(
                429, "Too many login attempts", headers={"Retry-After": "60"}
            )
    session.execute(delete(StaffLoginWindow).where(StaffLoginWindow.expires_at < now))
    session.commit()


def login(session, name, password, ip, previous=None):
    try:
        name = username(name)
    except ValueError:
        name = "!invalid-username"
    throttle(session, name, ip)
    account = session.scalar(select(StaffAccount).where(StaffAccount.username == name))
    try:
        valid = verify_password(password, account.password_hash if account else None)
    except ValueError:
        valid = False
    if not valid or not account or not account.active:
        raise HTTPException(401, "Invalid staff credentials")
    if previous:
        session.execute(
            update(StaffSession)
            .where(StaffSession.token_hash == digest(previous))
            .values(revoked=True)
        )
    raw = secrets.token_urlsafe(32)
    row = StaffSession(
        token_hash=digest(raw),
        account_id=account.id,
        auth_version=account.auth_version,
        csrf=secrets.token_urlsafe(32),
        expires_at=utcnow() + timedelta(hours=8),
    )
    session.add(row)
    session.add(
        StaffAudit(actor_id=account.id, action="staff.login", resource=account.id)
    )
    session.commit()
    return raw


def authenticate(session, raw):
    if not raw or len(raw) > 128:
        raise HTTPException(401, "Staff login required")
    row = session.get(StaffSession, digest(raw))
    account = session.get(StaffAccount, row.account_id) if row else None
    now = utcnow()
    if (
        not row
        or not account
        or row.revoked
        or not account.active
        or row.auth_version != account.auth_version
        or aware(row.expires_at) <= now
        or aware(row.last_seen_at) + timedelta(minutes=30) <= now
    ):
        raise HTTPException(401, "Staff session expired or revoked")
    row.last_seen_at = now
    session.commit()
    return account, row


def same_origin(request):
    origin = request.headers.get("origin")
    expected = str(request.base_url).rstrip("/")
    if (origin is not None and origin != expected) or request.headers.get(
        "sec-fetch-site"
    ) == "cross-site":
        raise HTTPException(403, "Same-origin staff request required")


def csrf_check(request, row):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        same_origin(request)
        supplied = request.headers.get("x-101-csrf", "")
        if not supplied.isascii() or not hmac.compare_digest(row.csrf, supplied):
            raise HTTPException(403, "Valid CSRF token required")


def authority(session, account, row, business_id, permission):
    member = (
        session.get(StaffMembership, (account.id, business_id)) if business_id else None
    )
    permissions = ROLES.get(member.role, frozenset()) if member else frozenset()
    if not business_id:
        if not account.platform_admin:
            raise HTTPException(403, "Platform administrator required")
    elif permission not in permissions:
        raise HTTPException(403, "Staff permission for this business required")
    return FinancialPrincipal(
        actor_id=account.id,
        business_ids=frozenset({business_id}) if business_id else frozenset(),
        permissions=permissions,
        expires_at=aware(row.expires_at),
    )
