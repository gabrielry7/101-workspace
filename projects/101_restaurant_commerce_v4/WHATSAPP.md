# Official WhatsApp campaign milestone

Integration map (base a770603): `campaigns.py` owns immutable audience/content
approval, permissions, dispatch and canonical order credit; `campaign_delivery.py`
is the delivery contract; `campaign_routes.py` shares staff/CSRF/business isolation;
`campaign_models.py` registers durable campaign records. `recovery.py` invokes the
same dispatcher. `api.py` and `service.py` already carry validated visits into
canonical checkout. Reuse all of these; no new customer/payment authority.

Minimum additions: business sender readiness and template snapshots; official
Cloud API transport; authenticated batch callbacks; inbound-only service windows,
destination opt-outs and staff reply outbox; channel selection and inbox UI.
`upgrade-campaigns --offline` creates the additive campaign-prefixed tables.
Live dispatch remains disabled; simulator fixtures cannot verify Meta readiness.

Provider references checked 2026-11-04: Meta's official collection
https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api
and template request https://www.postman.com/meta/whatsapp-business-platform/request/o65u5m5/send-message-template-text ;
https://whatsappbusiness.com/products/platform-pricing/ describes inbound-reset
service windows. Official SDK webhook reference:
https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/ .
The SDK is archived; no SDK dependency is introduced. Current developer reference
requests returned HTTP429; recheck current Graph version, error codes, template
and account restrictions before real activation. Prices are configuration with
source/time, never universal constants. No provider calls authorized by this file.

## Run and inspect

From this project, install the existing test/browser extras or reuse an existing
Python3.12 test environment. All examples use synthetic contacts and payment:

```bash
CAMPAIGN_PYTHON=.venv/bin/python scripts/run_campaign_demo.sh \
  --whatsapp --db /tmp/101-whatsapp-fresh.db --port 8801
```

For the complete repeatable HTTP rehearsal against that fresh database:

```bash
python scripts/campaign_rehearsal.py --channel whatsapp --url http://127.0.0.1:8801 \
  --output /tmp/101-whatsapp-rehearsal.json
```

This asserts duplicate/reordered receipts, withdrawal blocking both pending jobs,
cross-business denial, tampered links and the canonical partial refund.

Open `/campaigns` for channel selection and `/whatsapp` for sender configuration,
template status and staff replies. Test login: `campaign.manager`; passphrase:
`synthetic campaign demonstration only`. The existing email demo remains the
same without `--whatsapp`. Use a fresh DB; existing histories are not reset.
The simulation clock is 2026-11-03 10:00 America/Bogota, visible in Campaigns.

Select WhatsApp and `honorato_demo/es`, review the exact text parameters (including
`{name}` fallback), approve and schedule. In the inbox, simulate an inbound message,
queue a staff response, then simulate BAJA before dispatch. Pending marketing and
reply jobs are skipped. Another eligible recipient's ordering link uses the same
checkout and canonical paid-order/refund report. No inferred permission from a
purchase, inbound greeting or template approval. Replies are human-authored,
explicit support simulations; there is no automated bot to escalate from.

```bash
PYTHONPATH=src COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium python -m pytest \
  tests/test_whatsapp_campaigns.py tests/test_whatsapp_browser.py \
  tests/test_campaigns.py tests/test_campaign_browser.py tests/test_campaign_email_adapter.py
```

Set `COMMERCE_PAYMENT_TEST_DATABASE_URL` to an isolated loopback UTF-8 PostgreSQL
instance for the existing per-test-schema fixture. `WHATSAPP_BROWSER_EVIDENCE`
selects the browser capture directory. `upgrade-campaigns --offline` creates the
five additive `restaurant_campaign_whatsapp_*` tables; readiness rejects an old
installation until this explicit migration. No existing database was upgraded.

## Delivery, evidence and activation boundaries

- Shared approvals contain the sender/account binding, approved template identifier,
  language, exact supported definition/digest and positional parameters. Parameters
  and personalized names are frozen with the audience. Campaign sending always
  uses a MARKETING template, even inside an open service window.
- Supported templates are text BODY with contiguous numeric parameters (up to5),
  text FOOTER, ordering URL button0 and opt-out quick-reply button1. The approved
  URL must exactly equal the configured origin plus `/campaign-link/{{1}}`.
  Media, utility/authentication templates and other layouts are visibly unsupported;
  they are never silently rewritten. Editing content invalidates campaign approval.
- The real adapter POSTs to a configured version of official `graph.facebook.com`,
  one recipient at a time, with `biz_opaque_callback_data` for reconciliation.
  Its capability contract advertises no idempotency. Timeout/5xx/malformed success
  stays unknown; quality/recipient/throughput/template rejections are terminal and
  require deliberate review rather than repeated sends to defeat a restriction.
- POST `/api/whatsapp-hooks/{integration_id}` verifies the original bytes with
  X-Hub-Signature-256 and the app secret, then validates WABA and phone-number ID.
  The integration selects the business and scope. GET verifies the separate
  subscription token. Raw-body hashes and minimal normalized event history are
  retained; batched events are transactional, replay-safe and order-tolerant.
  Provider approval callbacks require a definition refresh before pending work
  resumes; a status callback cannot prove that the content remained unchanged.
- Inbound-only windows use the provider timestamp (reject implausibly future events),
  never receipt time or outbound/read/delivery events. Old events cannot rewind or
  extend the latest genuine inbound timestamp. System notices do not open a window.
  Unknown inbound senders become transport conversations, not new CRM customers.
- STOP/BAJA and supported equivalents, quick replies and provider opt-out errors
  suppress the destination/business/channel. New greetings never restore permission.
  Shared contact limits and Colombia controls still apply to marketing. Staff
  support replies have their own durable outbox and recheck window, sender, pause,
  scope and withdrawal; they cannot use an old number's window for a new sender.
- The existing recovery worker runs both campaign and support-reply dispatch.
  Cancellation cannot recall an already submitted message. Delivery/read receipts
  are distinct from acceptance and trusted payment; receipt states do not create
  sales or reset service windows. Terminal failure receipts count as receipt
  coverage, not successful delivery. Primary attribution remains one credit/order.
- Manual account/template readiness is clearly synthetic. Non-test sender metadata
  can be prepared, but is forced UNVERIFIED with unknown price and zero allowance.
  The explicit authenticated `/whatsapp/sync` boundary uses a configured real
  adapter to fetch provider metadata; it refuses test records and incomplete
  catalogues, marks unsupported templates, preserves observations and never infers
  a current sending allowance or enables live sends. No sync was called against Meta.

Server integration configuration uses `WhatsAppCloudTransport.from_environment`
with business-bound `phone_id`, `waba_id`, selected `version`, and a secret prefix
such as `WHATSAPP_HONORATO`. Load `_TOKEN`, `_APP_SECRET`, `_VERIFY_TOKEN` through the
existing private environment mechanism. Put the adapter in `campaign_options`
`integrations` with the explicit business and `provider_test`/`live` scope. Secrets
never enter sender/template JSON or the browser. Configure Meta subscriptions for
messages and message_template_status_update; GET challenge alone is not webhook
signature or sender readiness proof. Do not automatically subscribe/configure an
external account from a UI load.

Before a separately authorized real recipient test: verify the current Graph
version/contracts, authorized business sender and account, complete current template
catalogue, access scopes, public HTTPS callback/tracking origin, current pricing and
account allowance evidence, recipient marketing permission and legal/RNE/holiday
controls. Check actual provider callbacks and native delivery separately from the
synthetic tests. Global live/provider-test dispatch remains disabled in this
milestone, including staff replies. No fallback to SMS/email is configured.


The SMS milestone adds an explicit account-readiness probe at
`POST /api/operator/restaurants/{business}/campaigns/provider-readiness/whatsapp/probe`.
It checks phone membership in the configured WABA and completeness of the phone
and template catalogues before retaining the observation. Page loads do not probe.
This observation cannot establish allowance, pricing or live callback readiness.
The shared one-recipient provider-test review packet freezes the proposed test,
but is never a campaign approval or a permission to send. See [SMS.md](SMS.md).
