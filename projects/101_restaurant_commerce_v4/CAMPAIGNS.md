# 101 campaigns — integration map and local milestone

Implementation owner: this existing commerce application. Base revision `eff0812`.
Local campaign branch `work/101-029-campaigns`; no production activation authorized.

| Reuse | Actual path under src/world_model/restaurant_commerce | Evidence / gap |
|---|---|---|
| Application and browser | api.py, web/staff.js, web/shared.js | FastAPI and static JS; named staff cookie sessions, CSRF, membership isolation implemented |
| Customer authority | models.py:Customer, service.py:_upsert_customer | Existing business-scoped contacts; generic flags are not email marketing consent |
| Orders and payment | service.py:create_order/apply_payment_status, payment_workflow.py, wompi_workflow.py | Durable checkout, signed simulated notifications, verified Wompi sandbox path; no real provider calls in this campaign milestone |
| Refunds | financial_workflow.py, financial_providers.py | Existing full-refund authority; partial refund observations need canonical extension |
| Jobs and schema | recovery.py, db.py, migrations.py, maintenance.py | SQLAlchemy, SQLite/PostgreSQL, explicit offline migrations and durable worker claims |
| Marketing / analytics | growth.py, notifications.py, operations.py | Manual WhatsApp handoff exists; actual email delivery absent; canonical totals are COP whole pesos despite `_minor` names |
| New campaign boundary | campaign_models.py, campaigns.py, campaign_routes.py, campaign_delivery.py, campaign_email.py | Permissions/revisions/approval/outbox/events; delivery only delegated to adapters |

First tasks: additive campaign schema; channel-specific permissions referencing existing contacts; exact-revision approval and durable simulator; staff Campaigns UI; tracked context into canonical checkout; payment/refund-backed reporting; SES adapter and failure tests. WhatsApp/SMS remain visibly unconfigured and reject dispatch. Human copy is the normal path. Honorato pilot fixtures and products are explicitly synthetic, not publication-approved business facts.

Provider guidance checked 2026-11-02 reference: [SES SendEmail](https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_SendEmail.html), [SES sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html), [SNS signatures](https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message-verify-message-signature.html), [Gmail sender guidelines](https://support.google.com/mail/answer/81126), [Ley 2300](https://normograma.crcom.gov.co/crc/compilacion/docs/ley_2300_2023.htm), [CRC RNE](https://www.crcom.gov.co/es/micrositios/comunicados-como-es/registro-numeros-excluidos). RNE includes email; missing/current-review evidence blocks live. Ordinary windows use America/Bogota, weekdays 07–19, Saturday 08–15, no Sunday/holiday. Legal exceptions are not inferred. Current legal review is an activation requirement.

## Run the local application

From `projects/101_restaurant_commerce_v4` in this checkout:

```bash
python3.12 -m venv .venv-campaign
.venv-campaign/bin/pip install -e '.[test,browser,campaign-email]'
CAMPAIGN_PYTHON=.venv-campaign/bin/python scripts/run_campaign_demo.sh \
  --db /tmp/honorato-campaign-fresh.db --port 8799
```

Open `http://127.0.0.1:8799/campaigns`. Synthetic login: `campaign.manager`,
passphrase `synthetic campaign demonstration only`. The other fictitious business
has its own `other.manager` account with the same test passphrase. Each account
has access only to its own business. Use a fresh database for each clean rehearsal;
the command preserves existing databases and never resets permissions or history.

1. Load the business, edit human copy, select contacts and save the preview.
2. Review two eligible and five excluded synthetic recipients, the sender, terms,
   Bogotá schedule, expiry, US$0 simulation cost and revision digest.
3. Approve this version for simulation and schedule it. Editing creates a new
   immutable revision. Later permission grants cannot expand the approved audience.
4. Withdraw one eligible recipient's permission using its pending unsubscribe link.
5. Run simulated dispatch and then receive a simulated delivery receipt.
6. Open the other recipient's tracked link, add the fictitious product and use the
   existing checkout. Its existing simulated payment path establishes the paid order.
7. Refresh the campaign report. A signed test refund event changes the canonical
   payment refund ledger and both campaign and daily-finance reporting.

For the complete repeatable HTTP rehearsal (including replayed delivery/refund
callbacks, a COP5,000 partial refund and tenant/tampered-link negatives):

```bash
.venv-campaign/bin/python scripts/campaign_rehearsal.py \
  --url http://127.0.0.1:8799 --output /tmp/honorato-campaign-result.json
```

The demo uses a **fixed campaign-policy clock of 2026-11-03 10:00 Bogotá**, shown
on screen. Canonical payment/order timestamps remain actual timestamps. This
avoids pretending that a nighttime or holiday demonstration is a lawful live
send. The synthetic holiday/RNE fixtures are never live clearance. Pass `--worker`
to use the application's existing automatic recovery thread; otherwise the screen
runs the same durable dispatcher on demand. The deployment rehearsal runtime's
separate worker remains provider-disabled; no production worker was activated.

## Persistence, authority and limitations

- New campaign records reference `Customer`, `RestaurantCommerceProfile` and
  `Order`. They do not replace those authorities. `CampaignOrderCredit` is a
  unique primary attribution association, with no copied monetary totals.
- The checkout API discards public `source_channel`/`external_source_ref` claims.
  An opaque tracked visit cookie can supply validated, business-bound context.
  The canonical order and attribution association are committed together before
  checkout provider submission. Tracking does not authenticate the buyer.
- A real existing reserved/redeemed promotion code linked to an approved campaign
  takes precedence over the last eligible tracked visit in seven days. The primary
  association is frozen at order creation and survives edits/refunds. Other visits
  remain non-additive evidence. No discount engine was added.
- Reports read canonical confirmed `Payment` state and `Order.total_minor`. In
  this commerce application, COP `_minor` values are **whole pesos**, not cents.
  Totals already include discounts and delivery fees. Refunds are counted once;
  there is no profit estimate or claim of incremental sales.
- `refunds.py:PaymentRefund` extends the **commerce** payment authority with
  confirmed partial-refund evidence. The existing authenticated notification inbox
  deduplicates callbacks; provider/reference/amount/currency and refund cap are
  checked. Only the explicitly simulated adapter currently accepts partial-refund
  observations. Full-refund behavior remains canonical. Real Wompi partial refunds
  require provider-specific qualification; this change does not enable refund writes.
- Job keys bind business, revision, existing contact and channel. Scheduling and
  outbox creation share one transaction. Atomic business-scoped locking serializes
  claims and contact limits on SQLite/PostgreSQL. Each transmission is persisted
  before the provider call. A crash or ambiguous timeout becomes **unknown** and
  cannot be blindly resent. Authenticated receipts can reconcile it.
- Cancellation and pause stop work not yet claimed for transmission. They cannot
  recall a provider submission. Interrupted claims retain their unknown state.
- Consent is business/channel/marketing-purpose scoped, destination-bound and
  append-evidenced. Generic CRM consent and a completed purchase are insufficient.
  Permission, suppression, current registry evidence, sending hours, holidays,
  contact limits, sender, revision, expiry, budget and mode are checked at dispatch.
- Unsubscribe GET shows a confirmation; POST withdraws permission, including the
  one-click email POST mechanism. Bounces and complaints suppress promptly. Events
  retain provider/receipt timestamps, normalized facts and signed-body fingerprints.
- Test/live/provider-test scopes are explicit in state and reports. The current
  campaign routes **refuse live and provider-test approvals and dispatch**. They
  never substitute a simulator for missing SMS, WhatsApp or SES configuration.
- No email open/read claims are made. Known scanner user agents are flagged and
  excluded from attribution. Unrecognized scanners, forwarded links, missing
  cookies, offline and cross-device purchases remain coverage limitations.

## Brand and email boundary

`campaign_email.py` renders escaped HTML and plain text with fallback names,
live text, offer terms, expiry and a visible unsubscribe link. The retained source
logo is packaged under its content hash; provenance is in
`campaign-brand-source.json`. It is the saved website raster, not a newly invented
logo or a publication approval. Synthetic product/copy content is visibly labelled.
Tone, examples, source facts/images and render inputs live in the approved brand
snapshot. Preview and transport consume the same renderer.

The browser proof inspects desktop/mobile HTML and the real checkout. It does
**not** certify Outlook/Gmail/Apple Mail rendering or deliverability. Those checks
remain part of an explicitly authorized provider test.

## Schema and verification

Existing populated databases require a backup, stopped writers and an explicit
additive upgrade. Startup refuses the old schema instead of guessing consent or
retroactively attributing orders:

```bash
COMMERCE_DATABASE_URL='sqlite:////absolute/path/test.db' \
  .venv-campaign/bin/python -m world_model.restaurant_commerce.maintenance \
  upgrade-campaigns --offline
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src \
  .venv-campaign/bin/python -m pytest tests/test_campaigns.py \
  tests/test_campaign_email_adapter.py tests/test_campaign_browser.py
```

The tests use the existing `test_payment_durability_m3.factory`; set
`COMMERCE_PAYMENT_TEST_DATABASE_URL` to a disposable UTF-8 loopback PostgreSQL
instance to exercise the same contracts there. Browser evidence defaults to
`/tmp/101-campaign-browser`; override with `CAMPAIGN_BROWSER_EVIDENCE`.
The existing `security/run.py`/`security/check.py` release gate applies to the
installed artifact. Earlier `eff0812` qualification does not cover this extension.
The enlarged full suite exceeded the previous ten-minute runner limit without
finishing. The runner now defaults to a bounded 30-minute test allowance; use
`--test-timeout-seconds` (60–3600) when needed. A timeout still fails qualification
and never substitutes partial results for completed tests.

## Activation and next milestone

The SES adapter uses the AWS credential chain, one recipient per call, delivery-key
message tags, HTML/plain text, and RFC8058 unsubscribe headers. SDK retries are
explicitly disabled in its environment factory: SES SendEmail provides no
application idempotency key. Supported definite throttles get bounded local retry;
timeout/5xx/lost-response outcomes remain unknown. SNS verification requires an
expected topic, sender, HTTPS region-bound Amazon certificate URL, valid certificate
and signature version2. Subscription confirmation is deliberately not auto-followed;
configure the topic separately. Tests use SDK stubs and synthetic signing keys.

Before an authorized provider test, supply a concrete business-owned sender,
region/configuration set/topic, named authorized recipient, exact content, scope,
schedule and spend cap. Review SES domain verification, DKIM/SPF/DMARC, account
sending/production-access status, topic routing, public HTTPS tracking/unsubscribe
origin and mail-client rendering. No DNS or account configuration was changed.
Before live activation, connect audited current RNE review/integration, current
legal interpretation and official holiday evidence, actual channel consent, contact
limits, scoped configuration and an explicitly reviewed activation switch. Current
routes intentionally remain disabled even if AWS credentials exist.

**Next: official WhatsApp work package.** Add business-authorized Cloud API sender
configuration and approved marketing-template snapshots behind `Transport`, verify
Meta callbacks on raw bodies, normalize errors/receipts/replies, and show account,
template and allowance readiness. Derive the 24-hour service window only from
actual inbound messages; route replies to named staff and persist opt-outs. Reuse
campaign approval, jobs, permissions and order credit. Paused/rejected templates
must block. A real recipient test remains separately authorized. SMS then adds a
provider/Colombia route review, E.164 and segment encoding/cost rules, receipts and
opt-outs through the same lifecycle. Sequences/holdouts follow these working paths.

The existing manual WhatsApp composer outbox still represents a human handoff,
not verified delivery. It has no reliable transmission timestamp. Before live
multi-channel activation, connect that operational history to contact-limit review
or disable the legacy marketing handoff path; do not count it as a provider receipt.
The present shared frequency check spans the new campaign channel contracts.


## WhatsApp extension

The official WhatsApp transport, template snapshots, authenticated callback/inbox
and opt-out path now reuse this lifecycle. See [WHATSAPP.md](WHATSAPP.md) for
configuration, supported template shapes, synthetic browser proof and activation
limits. SMS remains unconfigured; real sending remains disabled.
