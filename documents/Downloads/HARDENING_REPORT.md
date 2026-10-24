# V4 hardening report

## Method

V4 started from the verified V3 bundle. The hardening pass attacked the system from six directions:

1. duplicate/retried requests;
2. concurrent mutation races;
3. malformed and adversarial API input;
4. lying/failing payment and courier providers;
5. replayed/out-of-order callbacks and event-sink failure;
6. hot-path query/latency behavior.

The original V1/V2/V3 regression tests were retained, and a dedicated V4 adversarial suite was added.

## Failure modes found and fortified

### Public object reads

V3 order IDs were sufficient to fetch order/tracking data. V4 places those reads behind an HMAC capability token and reduces the tracking DTO to public-safe fields.

### Idempotency

V3's order idempotency key could replay by key without proving that the second payload was identical. V4 persists a canonical SHA-256 fingerprint. A changed request under the same key is now a conflict.

An explicit 8-way concurrent test proves only one payment checkout call occurs for an identical order submission.

### Provider output trust

V4 assumes external providers can return corrupt/inconsistent values. Checkout/quote/dispatch responses are checked before commit for provider identity, references, currency, amounts/fees and valid state.

### Blind retries

Unknown failures around money/courier side effects are not retried. Only `RetryableProviderError` is eligible, and repeated failures open a circuit breaker.

### Webhook replay and forgery

Webhooks require HMAC authentication plus a persistent provider event ID. Replay is idempotent. Event-ID reuse with conflicting content is rejected. Payment callbacks must match the stored amount/currency/provider.

### State regression

Payment and reservation transitions are explicit. Older delivery events are ignored instead of rewinding courier state. Delivery completion drives order completion once; replay cannot double-award loyalty.

### Paid-order cancellation

V3 allowed a paid order to reach cancellation without a refund state. V4 requires refund first.

### Event sink failure

V3 could lose the distinction between committed commerce state and downstream event delivery. V4 stores the event in the same transaction and publishes after commit. Publisher failures leave durable retry state.

### DB invariants

V4 pushes critical arithmetic and non-negativity assumptions into database constraints so service bugs cannot silently persist impossible order totals.

### Revenue semantics

Customer LTV/growth analytics now use paid + completed orders rather than treating incomplete attempts as realized revenue.

### Query amplification

Cart pricing now batch-fetches items/modifiers. Order/delivery listing removes serializer-driven N+1 paths. Storefronts use a bounded TTL cache.

## Concurrency model

Mutable high-value rows use SQLAlchemy optimistic version columns. Unique constraints remain the final authority for idempotency, customer identity, provider references and dedupe keys.

SQLite is hardened for standalone/demo use, but PostgreSQL remains the expected production database for high write concurrency. V4 does not pretend SQLite is a horizontally scalable production queue.

## Event delivery guarantee

The outbox is **at-least-once**, not exactly-once. A worker can crash after a sink accepts an event but before `published` is persisted. Every event therefore carries a stable outbox `event_id` / `dedupe_key`, and consumers must be idempotent.

## Provider timeout requirement

The generic synchronous provider executor deliberately does not kill a hung side-effecting thread; doing so would leave ambiguous remote state. Real HTTP adapters must configure bounded connect/read/write timeouts in their HTTP clients. This is a provider-adapter acceptance requirement for V5/live integration.

## Security scope

This pass adds substantial application-layer controls but is not a penetration-test certification. Edge WAF/rate limiting, dependency auditing, secrets management and external security review belong to the deployment layer.
