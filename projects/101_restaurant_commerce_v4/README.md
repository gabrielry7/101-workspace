# Staff access update (0.8.0)

See [M4 staff setup and authorization](M4_STAFF_ACCESS.md). Legacy operator and financial tokens no longer authorize requests. Upgrade existing databases offline and provision named staff before using operator pages. Real money remains gated.

Previous controlled financial milestone: version **0.7.0**, [M3b contracts and offline upgrade](M3B_FINANCIAL_RESOLUTION.md). Real-money operation remains gated.

# 101 Restaurant Commerce V4 — Reliability Release

**Current release0.6.0:** [M3a durable payments, recovery, reconciliation and offline upgrade](M3A_DURABLE_PAYMENTS.md). Real-money use remains gated. The V4/M1/M2 sections below retain historical context.

V4 is the V1/V2/V3 restaurant-commerce stack after a dedicated adversarial hardening pass.
It deliberately adds very little product surface. The work is concentrated on **correctness under retries, concurrency, malformed input, provider failure, webhook replay, state corruption, event-sink failure, abusive traffic, and hot-path latency**.

```text
V1  menu → cart → pickup → payment → reservations → operations
V2  loyalty → promos → CRM → review/win-back automations → analytics
V3  delivery quote → courier dispatch → tracking → delivered
V4  break it → make failure explicit → make retries safe → make reads fast
```

## V4 reliability properties

### Money and state integrity

- integer minor-unit money only
- DB checks enforce non-negative prices/fees and order-total arithmetic
- explicit order, payment, reservation and delivery state machines
- paid orders require a refund state before cancellation
- delivery orders cannot complete before courier delivery
- cash-at-pickup is an explicit deferred-payment path and settles when fulfillment completes
- growth/LTV analytics count paid + completed commerce, not abandoned/failed attempts

### Idempotency and concurrency

- DB-backed request idempotency ledger with canonical request fingerprints
- same key + same request safely replays the existing resource
- same key + different request is a conflict
- concurrent duplicate submissions share one durable order/intent; supported provider retries retain the same immutable idempotency key
- deterministic provider idempotency keys are passed to payment/courier boundaries
- optimistic version columns protect mutable commerce rows from lost updates
- customer/account/message creation converges through DB uniqueness rather than check-then-insert assumptions

### External provider containment

- explicit retry only for errors the adapter marks retryable
- unknown provider exceptions are **not** blindly retried around payment/courier side effects
- circuit breaker isolates repeatedly failing provider operations
- provider responses are treated as untrusted and validated for identity, reference, currency, amount and legal state
- Wompi, Uber Direct and Mensajeros Urbanos remain fail-closed boundaries until real adapters are configured
- simulated payment/delivery providers are excluded from production defaults

### Webhook safety

- HMAC-authenticated provider webhook boundary
- required stable provider event IDs
- persistent webhook receipt ledger
- replay-safe duplicate events
- event-ID reuse with different canonical content is rejected
- payment callbacks verify amount + currency + provider ownership
- older delivery events cannot rewind newer fulfillment state

### Durable events

Commerce events use a **transactional DB outbox**:

```text
commerce mutation
     +
outbox row
     ↓ one DB commit
post-commit publish attempt
     ↓
published OR pending retry
```

A failed event sink cannot roll back an accepted order. Outbox workers use a database lease so a crashed publisher can be recovered. Delivery is intentionally **at-least-once**; events carry stable `event_id` / `dedupe_key` for consumer deduplication.

### API security envelope

Production startup fails closed without strong secrets.

- named staff sessions check current business membership, role and revocation
- public order/tracking reads require an HMAC capability token
- production cannot enable demo mode or seed demo data
- demo payment-completion endpoint is absent in production
- strict Pydantic input models reject unknown fields
- bounded cart/modifier/string/body sizes
- per-process mutation rate limit
- CSP, HSTS (production), no-sniff, frame denial, referrer and permissions headers
- sensitive responses are `Cache-Control: no-store`
- request IDs and latency headers on responses

The in-process rate limiter is defense-in-depth; a multi-worker production deployment still needs an edge/distributed limiter.

### Database durability

SQLite development/runtime configuration enables:

- foreign keys
- WAL
- `synchronous=FULL`
- 30-second busy timeout
- connection pre-ping

The standalone bundle also includes constraints and indexes that must be translated into 101's real Alembic migration before live deployment.

### Performance

- shared bounded TTL cache for storefront payloads
- warm storefront reads require zero SQL queries until TTL expiry
- cart quote path batch-loads menu items/modifiers rather than issuing per-line queries
- order list uses eager loading
- delivery list no longer has an N+1 serializer query pattern
- growth analytics use SQL aggregation instead of loading the whole order corpus into Python
- gzip for larger responses

See `V4_PERFORMANCE.json` and `HARDENING_REPORT.md` for measured local results and limits.

## Run the deterministic demo

```bash
python -m pip install --no-build-isolation -e .
python -m world_model.restaurant_commerce.demo \
  --db /tmp/101-restaurant-commerce-v4.db \
  --port 8787
```

Then:

```text
Storefront       http://127.0.0.1:8787/demo
Orders           http://127.0.0.1:8787/admin
Growth           http://127.0.0.1:8787/growth
Delivery         http://127.0.0.1:8787/delivery
API docs         http://127.0.0.1:8787/docs
Health           http://127.0.0.1:8787/health
Readiness        http://127.0.0.1:8787/ready
```

Staff pages require a provisioned named account in development and production. Follow [M4 setup](M4_STAFF_ACCESS.md); no default staff password exists.

## Run verification

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m compileall -q src scripts
PYTHONPATH=src python scripts/stress-v4.py
```

## Production boundary

V4 is substantially harder to break than V3, but the phrase “military reliable” should not be interpreted as a certification. Before real restaurant money/fulfillment goes live, 101 still needs:

- the V4 schema translated into and exercised through the live 101 Alembic chain
- PostgreSQL production replay/load/failover testing
- actual Wompi/Uber Direct/Mensajeros adapters with strict connect/read timeouts and their official signature schemes
- distributed rate limiting when using multiple workers
- secret-manager integration and rotation procedure
- backup/restore and disaster-recovery drills
- production monitoring/alerting/SLOs
- external security review / dependency scanning in CI

No external provider call is required to run or test this bundle.

## Frontend security boundary (M1)

The four pages use packaged external JavaScript, explicit event listeners and DOM
text nodes for API values. Do not reintroduce `innerHTML`, interpolated event
attributes, or executable string handlers. Scripts are served by a fixed asset
allowlist with a strict script CSP; inline styles remain permitted for the
existing design. The request-body limiter preserves the ASGI disconnect channel
once its buffered body is consumed, including when serving files.

Checkout and tracking destinations fail closed by default. Configure exact HTTPS
origins through `create_app(checkout_url_origins=(...), tracking_url_origins=(...))`
only after verifying the provider contract. `/api/browser-policy` exposes this
non-secret policy; do not derive it from customer/API response data. Only the
specific simulator paths are allowed locally in demo mode. Real provider adapters
remain unimplemented. These settings do not certify an integration or bypass
server-side payment verification.

Run browser regressions as a required release check (they are an optional install
extra so backend-only environments can still run unit tests):

```sh
python -m pip install -e '.[test,browser]'
python -m playwright install chromium
PYTHONPATH=src python -m pytest -q
```

For an installed system browser, set `COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium`.
Set `COMMERCE_BROWSER_ARTIFACTS` to a temporary folder for layout screenshots.
Tests intercept all browser traffic and use isolated SQLite and simulated
providers. Repeat the new tests against a built wheel installed in a clean target
with that target on `PYTHONPATH`; this checks JS package inclusion and actual
asset serving. The historical79 tests alone did not exercise the browser boundary.

This milestone does not fix the remaining audited financial, customer identity,
consent, staff-login or recovery flaws. M2 below supersedes the identity, consent and message-handoff portion of this historical caveat. Checkout still needs stable intent/reload recovery. Do not enable public real-money use on the basis of these milestones.

## M2 customer safety (0.5.0)

Public orders/reservations are guest requests. A phone number identifies a contact
claim, not authority over a customer account. Guests cannot change an existing
profile or its consent, redeem loyalty, consume customer-limited promotions, earn
account loyalty or trigger account automations. Order/reservation responses and
courier dispatch use immutable submitted contact snapshots, not a mutable account
name. General promotion quotes do not consult another customer's usage history.

The service's `verified_customer_id` constructor argument is an **internal trusted
adapter boundary**, not a new login mechanism. An authenticated adapter must prove
the customer's identity before passing it. The service checks business and phone
scope. No public API accepts or derives this authority from request data. Existing
unit/reality-demo fixtures explicitly construct verified identities; those are
not phone-verification integration evidence. Actual customer login/verification
remains future work.

Consent requests retain source, policy version, server timestamp and verification
state in the contact snapshot. Guest requests do not authorize account marketing.
Reservation WhatsApp selection starts unchecked; public marketing is disabled
until account verification. Historical consent flags remain intact but cannot
permit queued messages without explicit verified-consent timestamps. Verified
server callers may record consent/revocation; guest input cannot do so.

The outbox `/handoff` action rechecks current verified consent, recipient, channel,
status and due time before preparing a WhatsApp composer. It records `handed_off`,
never `sent` or `delivered`. Popup blocking/closing cannot create send evidence.
The old `/sent` endpoint and service method fail closed until a genuine send-receipt
adapter exists. This is not a WhatsApp sending integration.

Order capabilities are versioned, expire seven days from original order creation,
and are invalidated by the operator-only `/api/operator/orders/{id}/access/revoke`
action. Exact checkout replay cannot extend the expiry or undo revocation. Old
unexpiring tokens and unbound historical replays are rejected. Staff must assist
with expired/legacy orders; no self-service identity recovery is claimed yet.

### Existing database upgrade

Startup/readiness detects missing M2 columns. It does **not** infer historical
consent or run the upgrade automatically. Stop writers and verify a backup first.
For an offline SQLite copy, use the explicit idempotent function:

```python
from world_model.restaurant_commerce.db import make_engine, database_ready
from world_model.restaurant_commerce.migrations import upgrade_customer_safety
engine = make_engine("sqlite:////absolute/path/to/offline-copy.db")
upgrade_customer_safety(engine)
assert database_ready(engine)
```

This adds nullable order/reservation contact snapshots, a zero-default order-access
version, and nullable WhatsApp/marketing verification timestamps. Existing rows
are preserved; historical snapshots/verification remain unknown. Keep the additive
columns on rollback. Do not roll back publicly to code accepting the old unsafe
customer/replay flows. PostgreSQL migration/concurrency proof remains M3; this
upgrade deliberately refuses other database dialects. No existing runtime database
was upgraded during implementation.

## M1/M2 adversarial corrections (0.5.1, historical checkpoint)

The reload/payment/PostgreSQL gaps below are the pre-M3a state; see the current M3a contract above.

Offline attack tests reproduced and corrected stale food/delivery quotes, duplicate
checkout/reservation submissions, lost-response retries within an open page,
stalled policy startup, and staff responses surviving a business/token change.
Pending submissions retain their exact body/key and freeze edits until resolved;
confirmed rejections release the form. UUID creation has a cryptographic fallback.
**Reload/closed-tab recovery is still absent and remains a real-money release gate.**

Malformed validation inputs now return safe422 responses without echoing input.
Phone input accepts ASCII digits, an optional leading plus, spaces, parentheses,
periods and hyphens; canonical output contains5–15digits. Ambiguous Unicode digits,
letters and extensions are rejected. Historical noncanonical outbox recipients
and unsupported message purposes fail closed instead of changing the destination.

SQLite's savepoint hook now starts a real outer transaction when the driver has
not done so, so rejected requests cannot commit guest profiles or orphaned retry
claims. Previously orphaned claims are not automatically deleted: staff must inspect
provider and database evidence before recovery. There are no schema changes in0.5.1;
the explicit0.5.0 upgrade remains required for older databases. PostgreSQL and
provider-commit crash recovery remain unproven. Tests are synthetic and do not
establish low-end-device or older-browser support.
