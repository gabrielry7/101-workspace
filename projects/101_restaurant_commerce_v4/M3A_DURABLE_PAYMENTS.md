# M3a — durable checkout and payment reconciliation (0.6.0)

Real-money use remains gated. These changes establish durable local intent and
recovery against controlled providers; they do not implement Wompi, refunds,
scoped staff login or production deployment/restore.

## Transaction and recovery contract

Checkout validates the customer, cart, price, discounts and delivery quote before
committing anything. One transaction then stores the immutable order/items/contact,
reserved benefits/quote, completed idempotency binding and `PaymentIntent`. Only
then may the provider be called. Invalid local requests still roll back completely.
A malformed or missing provider reply no longer deletes the order.

Every attempt uses the original order ID, amount, currency, contact input and
provider idempotency key. A conditional database lease with a random ownership
token coordinates request handlers and recovery workers. Provider IO happens
outside the database transaction. Only the current token may finalize local state;
a late earlier worker cannot overwrite a recovered payment.

Unknown outcomes can be replayed automatically **only** when the adapter explicitly
sets `supports_idempotent_checkout=True`. This is a required provider contract, not
proof that an arbitrary provider implements it. Simulated and cash providers are
deterministic; Wompi remains fail-closed and declares no replay guarantee. Multiple
HTTP attempts may occur; monetary deduplication depends on that provider contract.
Unsupported replay or malformed output becomes `review_required`, with a durable
operator obligation and no fabricated trusted payment. Cancellation does not
prevent an already in-flight remote effect; any resulting paid/cancelled state
remains visible and requires reconciliation.

Each API process starts a small recovery thread through its lifespan. It uses fresh
sessions, due-time ordering and database leases, so multiple Uvicorn workers safely
share the queue. Defaults: one-second polling,25 intents per cycle,30-second lease,
two-second retry delay. Provider adapters must enforce bounded network timeouts;
the controlled test adapter uses four seconds. Recovery can be disabled explicitly
with `create_app(payment_recovery_enabled=False)` for deterministic offline tests.
`POST /api/operator/payments/recover` runs a bounded authorized recovery cycle.
No new database, service bus or distributed framework is required.

Authenticated payment notifications first enter a durable inbox. An early callback
whose payment reference is not yet bound receives202 and remains pending. Binding
or background recovery processes it later. Unknown references do not monopolize
the recovery batch. Existing signature, provider, amount, currency, event-ID and
fingerprint checks remain authoritative. Contradictory signed evidence is retained
for reconciliation; it cannot silently rewind a paid state. Replaying an old paid
event after a refund is effect-free.

`GET /api/operator/restaurants/{business_id}/payment-reconciliation` exposes unique
open obligations. The staff page shows them and suppresses normal fulfillment
actions while review is required; the server also refuses advancement. This is
an unresolved-work queue, not a refund executor or an assertion that money moved.
A future audited resolution/refund workflow remains necessary.

## Browser recovery

The browser creates a cryptographically random intent key and separate recovery
secret before submission. It stores only those random values, business scope and
a timestamp in guarded local storage: no contact, address or cart data. The server
stores only the secret hash. `POST /api/restaurants/{business_id}/orders/recover`
checks the key, secret, business,24-hour recovery window and access revocation,
then returns the original order with its existing bounded capability expiry.
Knowing an idempotency key alone grants no recovery access.

Reload consults that endpoint before any new submission. Unknown/network errors
preserve the intent; a confirmed404 lets the user reenter details with the same
key/secret. Expiry requires an explicit distinct-purchase confirmation. Blocked
storage preserves current-page retries with an honest recovery warning. Missing
secure randomness fails closed. Payment uncertainty/reconciliation is never shown
as a confirmed successful order. Old/low-memory physical devices remain unqualified.

## Explicit offline upgrade

Existing0.5.x databases need this upgrade before the new application starts:

```sh
# COMMERCE_DATABASE_URL must already point to the backed-up database.
# Stop ALL API/recovery writers first; never run this beside a live old version.
python -m world_model.restaurant_commerce.maintenance upgrade-payments --offline
```

The command requires the URL through the environment and never prints it. It
creates three tables: `restaurant_payment_intents`,
`restaurant_payment_reconciliations`, and `restaurant_payment_notification_inbox`.
The migration is transactional and idempotent on SQLite/PostgreSQL, checks the
M2 schema first, preserves old order/payment IDs, and invents no historical intent.
M2 columns must already exist; the older SQLite customer-safety upgrade remains
separate. Partial/unknown schemas fail closed. Existing incomplete databases are
not silently upgraded by `init_schema`; an empty development DB may initialize.
Readiness verifies required tables/columns, not every possible constraint drift.

Keep the additive tables on rollback. Do not run old checkout writers alongside
M3a: they lack the durable-intent contract. Historical uncertain provider effects
require evidence-based review; no blind deletion/replay/backfill is provided.

## Acceptance and reproducibility

Use `./adversarial/run.sh` to rebuild the disposable PostgreSQL environment and
execute the retained suite. The fault cases now require a committed pre-provider
order with the same ID after timeout/restart; the worker-kill case requires recovery
**without a customer retry**. The paid/cancelled property now requires truthful
states plus exactly one durable surfaced obligation instead of hiding either fact.
The reload case requires automatic recovery and exactly one order POST.

`tests/test_payment_durability_m3.py` additionally covers lease takeover/stale-owner
fencing, early notifications, queue fairness, malformed provider values, replay
without an adapter guarantee, invalid input rollback, secret scope/expiry/revocation
and restart recovery. Set `COMMERCE_PAYMENT_TEST_DATABASE_URL` to a disposable
loopback PostgreSQL database to run its financial cases in isolated owned schemas.
`COMMERCE_MIGRATION_TEST_DATABASE_URL` adds PostgreSQL migration cases.

The global operator-token isolation test remains red by design until scoped staff
authorization is implemented. Complete customer authentication, real provider
contracts, financial compensation, production restore and device qualification
remain separate release gates. See the shared commerce audit's M3 implementation
report for actual run counts, artifact identities and remaining failures.
