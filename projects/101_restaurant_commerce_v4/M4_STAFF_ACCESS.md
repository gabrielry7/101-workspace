# M4 staff access

Staff now authenticate with named accounts and server-backed sessions. Neither
`COMMERCE_OPERATOR_TOKEN` nor `X-101-Financial-Token` grants access. The former
`financial_authenticator` injection is rejected; financial principals come from
current staff membership. Customer order capabilities remain separate.

## Offline upgrade and account lifecycle

Stop all writers and back up the existing database, set `COMMERCE_DATABASE_URL`
privately, then run `python -m world_model.restaurant_commerce.maintenance upgrade-staff --offline`.
This adds five tables and no accounts. Existing runtime databases are never upgraded
implicitly; partial schemas fail readiness. Fresh disposable databases include them.

The trusted host administrator provisions accounts with an interactive password
prompt (never a password argument):

```sh
python -m world_model.restaurant_commerce.staff_admin create --username alice --business BUSINESS_ID --role manager --actor LOCAL_ADMIN_ID
python -m world_model.restaurant_commerce.staff_admin membership --username alice --business BUSINESS_ID --role operator --actor LOCAL_ADMIN_ID
python -m world_model.restaurant_commerce.staff_admin remove-membership --username alice --business BUSINESS_ID --actor LOCAL_ADMIN_ID
python -m world_model.restaurant_commerce.staff_admin reset-password --username alice --actor LOCAL_ADMIN_ID
python -m world_model.restaurant_commerce.staff_admin disable --username alice --actor LOCAL_ADMIN_ID
```

This is a trusted local administrator boundary, not a self-service invitation API.
Password resets and disabling invalidate sessions; membership changes apply to the
next authorization check. An already-authorized in-flight action may finish.
`--platform-admin` at creation explicitly permits global maintenance endpoints;
it does not grant access to businesses without membership. Never grant it to ordinary staff.

| Role | Read operations/growth/financial history | Fulfillment, contact, access revoke | Financial lookup/refund/resolve | Growth changes |
|---|---|---|---|---|
| viewer | yes | no | no | no |
| operator | yes | yes | no | no |
| finance | yes | no | yes | no |
| manager | yes | yes | yes | yes |

All 27 existing operator handlers have an explicit policy; unmapped routes deny.
Bare order, reservation, delivery and message IDs resolve their business from stored
records. Global metrics, event drain and payment recovery require platform authority.
Service-owned commits append actor/business/action audit in the same transaction;
a separate authorization record is an attempt, not proof of a completed effect.
Background recovery remains a system action; financial intents retain their initiator.

## Sessions and interface

`/admin`, `/delivery` and `/growth` share a login interface. A business selector lists
memberships; typed alternate IDs are still checked server-side. Financial actions use
the same session. The browser stores no password or credential in local/session storage.
An HttpOnly SameSite=Strict cookie persists reloads; production uses a Secure
`__Host-` cookie. Deploy production behind correctly configured HTTPS/reverse proxy.

Sessions expire after eight hours or 30 minutes idle. Every protected request checks
account state, auth version, session revocation and current membership. Logout revokes
the current session; logout-all revokes all and atomically advances the account version.
Mutations require a session-bound CSRF header and reject foreign Origin/Fetch-Site.
Login requires a custom header and same-origin request. Passwords use salted scrypt
(N=32768,r=8,p=3,32MiB), with 15–128-character passphrases. Login throttles persist in
the database: 5/account,20/client IP,100/global per fixed minute across workers. A
reverse proxy must supply trustworthy client addressing; shared-IP throttling may
require tuning. No default staff or default password is created, even in demo mode.

Late browser responses are fenced by business/session generation; logout clears
protected content. Requests time out visibly; uncertain financial effects must be
checked in history. Revocation is authoritative at the server. Another open tab may
show old data until its next poll, visibility refresh or protected request.

Remaining: MFA/SSO and self-service recovery/invitations, broader security scanner
qualification, production backup/restore and old/low-memory device verification.
Real-money use and production financial providers remain gated.
