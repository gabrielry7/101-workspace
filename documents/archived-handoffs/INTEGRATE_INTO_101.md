# Integrating Restaurant Commerce V4 into 101

Target checkout:

```text
/home/t/101-world-model
```

V4 should be integrated as an operational subsystem under the existing 101 conventions, not copied blindly over current work.

## Safe sequence

1. Diff the live `src/world_model/restaurant_commerce/` (if present) against this bundle.
2. Preserve unrelated WhatsApp/world-model/site work.
3. Reuse 101's existing SQLAlchemy Base/session and Alembic infrastructure.
4. Translate `V4_SCHEMA_DELTA.md` into a real migration; test upgrade from current head and clean bootstrap.
5. Preserve the separation between operational commerce state and Business Genome/Claims.
6. Replace demo/dev authentication with the real 101 authorization model while retaining resource-level access control.
7. Configure production secrets through 101's secret/deployment system.
8. Keep simulated payment/delivery providers disabled in production.
9. Wire real Wompi/Uber/Mensajeros adapters only after adapter contract tests, official callback signatures and bounded HTTP timeouts are implemented.
10. Run V1–V4 tests plus the broader 101 regression suite.
11. Run a PostgreSQL concurrency/restart canary before enabling a restaurant.

## V4 invariants that must survive integration

- request idempotency keys are fingerprinted; conflicting reuse is rejected
- one duplicate request cannot cause multiple payment/courier side effects
- payment/courier responses are validated before persistence
- payment and fulfillment state cannot regress
- paid cancellation requires refund first
- delivery completion is required for delivery-order completion
- durable outbox mutation and commerce state commit atomically
- event publishing is at-least-once with stable consumer dedupe identity
- provider callback event IDs are persistent and replay-safe
- public order/tracking data is capability-protected
- production cannot expose demo payment/status mutation paths
- realized revenue/LTV means paid + completed commerce
- truth/Genome does not ingest operational orders as external-business Claims

## Production DB note

Do not rely on `Base.metadata.create_all()` to upgrade an existing V3 database. V4 introduces new tables, columns, constraints and indexes. The live upgrade must be an Alembic migration aligned with the current 101 revision graph.

## Rate limiting

The bundle's limiter is local process defense-in-depth. Deployments with multiple application workers must use a shared edge/distributed rate limit.

## Provider calls

No external Wompi/Uber/Mensajeros/Meta call was performed in the standalone V4 build.
