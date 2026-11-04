# Customer signup: phone or email, with a shareable business QR

Implemented in the existing commerce owner from canonical `c60e517`. One public
page offers **phone OR email**, each verified by a six-digit code. Neither requires
the other, a password, or a second factor. Signup and return login share the flow;
verified sessions persist for30days. A signed-in customer explicitly joins another
business without requesting another code. Signing up never grants marketing consent.

## Integration map

| Boundary | Actual paths / reused authority |
|---|---|
| Public/signup and scoped owner routes | `customer_signup_routes.py`, registered through existing `api.py` staff permissions |
| Verification, sessions and membership | `customer_signup.py`, six tables in `customer_signup_models.py`; memberships reference canonical `models.Customer` |
| Phone verification | `customer_signup_delivery.TwilioPhoneVerifier`, official Verify SMS REST endpoints |
| Email verification | `customer_signup_delivery.SesEmailVerifier`, transactional SESv2 codes using the existing AWS environment/credential mechanism |
| Business name and normal website entry | Existing `RestaurantCommerceProfile`; `web/index.html` / `index.js` show Únete when signup is configured |
| Customer and owner UI | `web/signup.*`, `web/signup-owner.*`; existing `web/growth.html` links to the QR screen |
| Migration | `customer_signup_migrations.py`, existing `maintenance.py` command; nullable canonical phone for email-only customers |
| Demo / proof | `signup_demo.py`, `test_customer_signup.py`, `test_signup_migration.py`, `test_signup_browser.py` |

No new CRM, order or payment authority. Phone signups reuse exact canonical
business/phone records. Email signups create real email-only contacts with NULL
phone, never a fake number. Existing customer summaries allow a missing phone;
legacy phone-message planning suppresses those contacts explicitly. Campaign
permission remains absent until independently granted. Guest checkout remains
available; signup does not expose old orders or automatically grant wallet spending.

A verified login identifier can join multiple businesses. Phone and email are
separate identifiers until an explicit account-linking flow is implemented. Never
auto-merge on an unverified CRM email, nor infer that unrelated phone/email logins
are the same person. Legacy local-format phone records need a country/identity
review before linking; this flow uses normalized E.164. Email identity comparison
is case-insensitive, preserves dots/plus tags, and currently supports ASCII email.
The optional profile-email endpoint does not make that email a login credential;
changing an email login requires verification and is not implemented here.

## Run locally

```bash
python3 -m venv .venv-signup
.venv-signup/bin/pip install -e '.[test,browser,campaign-email]'
PYTHONPATH=src .venv-signup/bin/python -m world_model.restaurant_commerce.signup_demo \
  --db /tmp/101-signup-demo.db --port 8803
```

Open `/join/honorato-campaign-test` or `/customers/signup`. Owner fixture login:
`campaign.manager`, passphrase `synthetic campaign demonstration only`. Both
verification channels are explicit simulators; the code appears on screen and no
message is sent. Honorato business records here are labelled demonstration data.
A localhost QR works on this machine only. Configure a real public origin before
printing/sharing outside the demo; no production domain or deployment was changed.

The owner can download PNG or SVG and copy a normal website link. QR encodes the
configured business URL with `source=qr`; website entry uses `source=website`.
There is no customer-facing QR on the website. Page opened, code requested,
identifier verified and membership created events are scoped by business and mode.
Apertures/requests are event counts, not distinct humans; memberships count once.

For an existing database: back it up, stop writers, then explicitly run:

```bash
COMMERCE_DATABASE_URL='sqlite:////absolute/path/database.db' \
  .venv-signup/bin/python -m world_model.restaurant_commerce.maintenance upgrade-signup --offline
```

Fresh databases include the schema. Existing databases are not silently upgraded.
PostgreSQL drops only the phone NOT NULL restriction; SQLite rebuilds the customer
table offline while preserving original columns, data, indexes, triggers and
inbound foreign-key targets. Tests preserve a real existing order/customer and
run foreign-key checks. No historical verification or consent is backfilled.

## Verification and provider configuration

```bash
mkdir -p /tmp/101-signup-ui
TMPDIR=/tmp/101-signup-ui COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src \
  .venv-signup/bin/python -m pytest tests/test_customer_signup.py \
  tests/test_signup_migration.py tests/test_signup_browser.py \
  tests/test_customer_safety_m2.py tests/test_growth_v2.py
```

Set `COMMERCE_PAYMENT_TEST_DATABASE_URL` to a disposable loopback PostgreSQL
instance to exercise the same fixture there. The browser uses actual HTTP, verifies
both methods, persistence and a second business, and downloads a QR. The recorded
PNG was independently decoded with OpenCV to the exact business URL. This is local
application proof; no real SMS/email deliverability or account verification occurred.

Inject `signup_options` into the existing `create_app` with `public_origin`,
`mode` (`test` or `live`) and `adapters` keyed by `phone` and `email`. An absent
adapter disables that choice. Simulation cannot call a network adapter and fake
adapters are forbidden in production. No live sending is enabled by default.
For a separately authorized activation, configure `live_enabled=True`, allowed
phone regions, a daily request ceiling, a conservative maximum total provider cost
per request and a daily budget in integer microdollars USD. The cap includes SMS
and successful-verification fees where applicable; it is a configured ceiling,
not a measured invoice. Durable counters reserve before transmission and stop
new requests at the limit. Rates must be reviewed before enabling the switch.

Twilio uses `SIGNUP_TWILIO_ACCOUNT_SID`, `SIGNUP_TWILIO_AUTH_TOKEN`, and
`SIGNUP_TWILIO_SERVICE_SID` through its environment factory. SES uses the existing
AWS credential chain plus configured sender/configuration set and an independent
high-entropy `SIGNUP_EMAIL_CODE_SECRET` (at least32characters). Verify sender/domain,
account access, current rates and the actual owner-authorized recipient before
real tests. Secrets never enter URLs, forms or business profile JSON.

Codes expire after10minutes, permit at most five checks and are single-use, bound
to the initiating browser/business/channel. Resends require60seconds and are
limited per identifier/client/day across workers. Ambiguous submission/check
outcomes never grant access or trigger automatic resend. Sessions use durable
hashed tokens in HTTP-only cookies. Restart preserves memberships and sessions.
Verification is transactional: it contains no offer and does not use campaign
marketing approval, unsubscribe headers or promotional permissions.

Provider references checked2026-11-04: [Twilio verification](https://www.twilio.com/docs/verify/api/verification),
[Twilio checks](https://www.twilio.com/docs/verify/api/verification-check),
[SES SendEmail](https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_SendEmail.html),
[Segno serialization](https://segno.readthedocs.io/en/latest/serializers.html).
