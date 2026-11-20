"""Bind an explicitly authenticated phone membership to ordinary public checkout.

A submitted phone/email is never proof of identity. Guest quoting and secret-bound
recovery remain usable without login; email verification does not verify a phone.
"""

import hmac

from fastapi import HTTPException

from . import customer_signup as signup
from .customer_signup_models import CustomerMembership
from .models import utcnow


def verified_checkout_customer(request, session, options, *, production=False):
    business = request.path_params.get("business_id")
    if not business or request.method != "POST" or not options or not options.get("adapters"):
        return None
    prefix = "/api/restaurants/" + business + "/orders"
    if request.url.path not in {prefix, prefix + "/quote"}:
        return None  # Recovery keeps its independent original-secret contract.
    token = request.cookies.get("__Host-commerce_customer" if production else "commerce_customer")
    if not token:
        return None
    try:
        account, _ = signup.authenticate(session, token, options, options.get("clock", utcnow)())
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise
    if account.channel != "phone":
        return None
    membership = session.get(CustomerMembership, (account.id, business))
    if not membership:
        return None
    csrf = request.headers.get("X-101-Customer-CSRF", "")
    if not csrf and request.url.path.endswith("/quote"):
        return None  # Public base-price quotes don't claim identity or redeem rewards.
    if request.headers.get("Sec-Fetch-Site") == "cross-site" or not hmac.compare_digest(
        csrf, signup.csrf(token)
    ):
        raise HTTPException(403, "customer_session_changed")
    return membership.customer_id
