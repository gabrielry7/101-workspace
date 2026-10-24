# Restaurant Commerce V3 schema delta

V3 adds delivery fulfillment without changing Business Genome / Truth semantics.

## Existing table changes

### `restaurant_commerce_profiles`

Add:

- `delivery_enabled` boolean
- `delivery_provider` string
- `delivery_origin_address` text nullable
- `delivery_origin_latitude` numeric/float nullable
- `delivery_origin_longitude` numeric/float nullable
- `delivery_max_distance_meters` integer nullable

### `restaurant_orders`

Add:

- `delivery_fee_minor` integer, default 0

`total_minor` remains the amount charged to the customer and now equals food net + delivery fee for delivery orders.

## New tables

### `restaurant_delivery_quotes`

Immutable-ish quote snapshot used before checkout:

- business/provider identity
- provider quote reference
- currency / fee
- distance
- origin snapshot
- destination snapshot
- instructions
- pickup/dropoff estimates
- expiry
- consumed timestamp
- raw provider quote payload/provenance

Provider quote reference is unique.

### `restaurant_deliveries`

One operational fulfillment row per delivery order:

- `order_id` unique FK
- `quote_id` unique FK
- provider
- provider delivery reference
- normalized status
- fee/currency
- immutable origin/destination snapshots
- tracking URL
- courier display metadata
- ETAs
- dispatch / pickup / delivery / cancellation timestamps
- raw status payload

### `restaurant_delivery_events`

Append-only-ish normalized provider/status events:

- delivery FK
- provider status
- normalized status
- occurred timestamp
- unique dedupe key
- raw event payload

## Migration guidance for live 101

Do not use `Base.metadata.create_all()` in production.

Create a proper Alembic migration using 101's real Base and Business FK policy. Existing pickup orders must backfill:

```text
restaurant_orders.delivery_fee_minor = 0
```

Existing restaurant profiles should default:

```text
delivery_enabled = false
```

so V3 does not silently turn on delivery for current businesses.

Provider webhook raw payloads may contain operational/customer data and should follow 101's data-retention policy.
