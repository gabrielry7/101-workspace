# V4 schema delta

V4 must be represented as a real migration when integrating into `/home/t/101-world-model`.
`Base.metadata.create_all()` is for a fresh standalone database and **does not upgrade an existing V3 database**.

## New tables

### `restaurant_idempotency_records`

Persists `(scope, key)` request ownership, canonical request fingerprint, in-progress/completed state and resulting entity ID.

### `restaurant_event_outbox`

Transactional domain-event outbox with:

- stable ID / optional dedupe key
- pending/publishing/published lifecycle
- publish attempts / last error
- publisher lease expiration
- published timestamp

### `restaurant_webhook_receipts`

Unique `(provider, event_id)` replay ledger with canonical payload fingerprint and processed timestamp.

## New/changed columns

### `restaurant_commerce_profiles`

- `payment_provider`
- `cash_at_pickup_enabled`

### optimistic version columns

Added to mutable rows where lost updates materially matter:

- customers
- orders
- payments
- deliveries
- reservations
- loyalty accounts
- outbound messages

## Constraints added

V4 adds DB-level checks for:

- non-negative item/payment/delivery/reward/promotion values
- modifier min/max selection consistency
- order quantity bounds
- discount range and discount component identity
- exact order total arithmetic
- prep/reservation/configuration ranges
- loyalty balances/lifetime counters
- promotion redemption-limit configuration

## Indexes added

Notable hot-path indexes include:

- `(business_id, status, created_at)` orders
- `(business_id, last_order_at)` customers
- `(order_id, status)` payments
- `(provider, status)` deliveries
- `(business_id, starts_at)` reservations
- `(status, scheduled_at)` outbound messages
- `(status, occurred_at)` event outbox

## Integration requirement

Do not copy this standalone SQLAlchemy Base into live 101. Translate this delta into the existing 101 Base/Alembic conventions and test both:

1. upgrade from the current live revision with representative data;
2. clean database bootstrap to head.

Migration rollback/destructive semantics should be decided against the real 101 persistence contract rather than inferred from this bundle.
