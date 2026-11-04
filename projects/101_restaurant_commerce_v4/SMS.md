# SMS and provider readiness integration

Base `8d4da8c`. Reuse `campaigns.py` lifecycle/outbox/permissions/attribution,
`campaign_routes.py` staff/CSRF/business isolation, `campaign_models.py` additive
campaign migration and canonical checkout/payment/refund modules. No separate CRM,
order ledger, worker or payment authority. WhatsApp already has a real Cloud API
adapter and explicit metadata sync; actual account credentials are not configured.

Minimum additions: `sms_delivery.py` Twilio transport, official signature validator
and encoding estimates; `sms.py` business route configuration and event projection;
`sms_routes.py` scoped configuration/callbacks; shared campaign UI plus SMS setup.
`provider_readiness.py` prepares immutable single-recipient test review packets and
shows specific blockers; it does not authorize messages. Real provider verification
requires configured credentials/account and an expressly identified recipient,
message and spending limit. Test and live scopes remain separate.

Sources checked 2026-11-04: https://www.twilio.com/docs/usage/security ,
https://www.twilio.com/docs/messaging/api/message-resource ,
https://www.twilio.com/docs/glossary/what-sms-character-limit ,
https://www.twilio.com/en-us/guidelines/co/sms ,
https://www.twilio.com/en-us/sms/pricing/co . Rates are configured evidence, not a
hard-coded country price. Colombia sender/route capabilities require actual review;
country-level two-way support does not establish that a particular route supports
replies. Unsupported alphanumeric/domestic long-code routes stay blocked. Meta's
current developer reference returned429; activation requires revalidation.

## Repeatable local demonstration

From this project directory, using Python 3.12 and Chromium:

```bash
python3 -m venv .venv-campaign
.venv-campaign/bin/pip install -e '.[test,browser,campaign-sms]'
CAMPAIGN_PYTHON=$PWD/.venv-campaign/bin/python \
  scripts/run_campaign_demo.sh --sms --whatsapp --db /tmp/101-sms-demo.db --port 8802
# In another terminal; creates one more synthetic campaign/order per run:
.venv-campaign/bin/python scripts/campaign_rehearsal.py --channel sms \
  --url http://127.0.0.1:8802 --output /tmp/101-sms-rehearsal.json
```

Open `http://127.0.0.1:8802/campaigns` or `/sms`. The console prints the synthetic
staff login. Select SMS, write copy, preview personalized segments and exclusions,
approve and schedule. In `/sms`, simulate BAJA before dispatch; return to campaigns,
dispatch and simulate receipts. Follow an eligible delivery's ordering link through
the existing simulated checkout. The HTTP rehearsal also verifies cross-business
403, tampered link404, signed form callback replay/reordering, duplicate refund and
zero live totals. Expected order24900COP, refund5000COP, net19900COP. These integer
amounts use the canonical commerce COP accounting convention, not a second total.
Fixtures, including Honorato branding, products, contacts, route, RNE and prices,
are labelled synthetic. No real delivery or provider connection is established.
The rehearsal's preserved database must not be overwritten when restarting.

```bash
TMPDIR=/tmp/101-sms-ui COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src \
  .venv-campaign/bin/python -m pytest tests/test_sms_campaigns.py \
  tests/test_provider_readiness.py tests/test_sms_browser.py \
  tests/test_campaigns.py tests/test_whatsapp_campaigns.py \
  tests/test_campaign_email_adapter.py tests/test_campaign_preview_security.py
```

Create that short TMPDIR before browser tests. Set
`COMMERCE_PAYMENT_TEST_DATABASE_URL` to a disposable loopback PostgreSQL database
to run the existing database fixture against PostgreSQL. For an existing database,
back it up, stop writers and run `maintenance upgrade-campaigns --offline` using
`COMMERCE_DATABASE_URL`; this creates the four additive campaign tables. It neither
copies customers nor changes existing paid-order authority.

## Provider boundary and limitations

Install `.[campaign-sms]`. Configure `TwilioTransport.from_environment` with
`secret_prefix='TWILIO_HONORATO'`, account SID, sender, public HTTPS callback and
inbound URLs; load `TWILIO_HONORATO_AUTH_TOKEN` through the existing private secret
mechanism. Register the instance in `create_app(campaign_options={'integrations':
{integration_id: {'business_id': ..., 'scope': 'provider_test', 'adapter': adapter}}})`.
Do not put secrets in the sender form. This is the same injection boundary as
email/WhatsApp; deployment does not infer integrations from secret presence.

Callbacks use `/api/sms-hooks/{integration_id}/status?key={local_delivery_key}` and
`/incoming`. The official Twilio validator checks the original form values and
configured external URL with AuthToken HMAC-SHA1. Shared-key SHA256 settings are
explicitly unsupported and rejected. Integration, account, sender, destination,
callback path and local job must agree; callers cannot choose the business.
History stores normalized minimum evidence plus the raw request hash. Standard
SMS callbacks omit a provider timestamp, so receipt time is explicitly marked;
no provider timestamp is invented. Parameter order and duplicate deliveries do
not increase totals. Inbound replies appear in the staff inbox, return empty
TwiML and never cause an automatic reply or new customer record. STOP/BAJA creates
business/channel/destination suppression; a greeting does not grant consent.

Submission acceptance, provider delivery/failure and unavailable receipt coverage
remain distinct. There are no SMS read receipts. Timeout,5xx and malformed response
outcomes stay unknown, with no blind retry or claimed provider idempotency.
Route-specific receipt capability is reported separately from actual received
receipts. Billing is an estimate based on frozen text, personalized name, complete
links, encoding and configured per-segment rate; actual billing remains unknown
until integrated with provider billing evidence. Simulation costs zero. No profit
is inferred. Delivery, clicks and replies cannot mark an order paid.

Encoding follows Twilio's published calculator: GSM160/153 and UTF-16-unit70/67,
with indivisible encoded graphemes, GSM extension escapes and surrogate pairs.
CR/LF count separately; no smart encoding/transliteration is applied. Regression
cases include153carets and67emoji, both three segments, plus family emoji and
combining marks. Reference implementation:
https://github.com/TwilioDevEd/message-segment-calculator/tree/main/src/libs .
The first route supports Colombian mobile destinations only. Alphanumeric and
Colombia domestic long-code senders are blocked. International long-code and short
code records require current actual route/registration/price review; a country
capability page is insufficient. Inbound is only offered when the route supports it;
every message also carries an unsubscribe link. Non-test configuration is forced
UNVERIFIED, without price or assumed inbound/delivery support.

## Recommended real test and activation dependencies

1. Finish the local rehearsal and inspect the exact rendered message, recipient,
   exclusion, schedule, segment estimate and cost. Simulator callbacks prove the
   application contract only.
2. Configure the authorized Meta account and sender privately. Explicitly probe
   current phone/WABA membership and approved marketing templates. Verify current
   Graph version/access scopes, catalogue completeness, allowance and price, then
   public HTTPS callback authenticity and signature handling. Verify recipient
   consent, RNE evidence and Colombia hours/holiday rules before activation.
3. Use one explicitly consenting owner-controlled phone, one exact approved
   WhatsApp template and a separately approved small budget (suggestedUS$1maximum,
   not authorization). Prepare the immutable one-recipient review packet in the
   campaign screen. Review its blockers and separately authorize activation of
   provider-test dispatch. Present code deliberately cannot send it.
4. Once SMS account/route/registration/rate and inbound/receipt support are verified,
   repeat with one SMS to the same consenting phone and its own approved cap.
   Check provider acceptance, physical receipt, authenticated callback, tracked
   checkout and withdrawal independently. A callback does not prove a human read.
5. Test STOP/BAJA with a still-pending recipient and verify suppression. Stop after
   the agreed message count; no retries after ambiguous acceptance. Keep all real
   test records in provider_test scope, outside simulation and live reports.

No real Meta/Twilio credentials were found in this machine's documented private
sources during implementation; no real test recipient/account/template was
identified. Those are external verification blockers, not simulated successes.
Meta's developer site returned429 during this review, so current account contracts
must be reconfirmed before activation. Test-review preparation, including a claimed
consent source, never changes permissions or authorizes sending. Global live and
provider-test dispatch remain disabled. Current route, pricing, legal and public
callback checks cannot yet be cleared by a manual READY toggle. Enabling either
requires a separate reviewed activation implementation and the concrete inputs.

After real channel qualification, the next product milestone is purchase-stopped
welcome/returning-customer sequences and randomized holdouts using the same consent,
contact limits and canonical order events; attributed sales are not incremental lift.
