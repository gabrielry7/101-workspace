# Changelog

## 0.4.0

Reliability / adversarial hardening release. V4 intentionally prioritizes correctness and failure containment over new product features.

- DB-backed request idempotency fingerprints
- concurrent duplicate checkout suppression
- optimistic locking on mutable commerce state
- explicit payment + reservation state machines
- refund-before-cancel invariant for paid orders
- authoritative cash-at-pickup settlement behavior
- signed/replay-safe provider webhooks
- webhook receipt ledger
- provider response validation
- selective retries + provider circuit breakers
- transactional durable event outbox with recoverable publisher leases
- SQLite foreign keys/WAL/FULL sync/busy timeout
- server-side DB constraints for money/quantity/config invariants
- strict bounded API inputs + request-body cap
- production fail-closed secrets/demo behavior
- public order/tracking capability tokens
- security headers + no-store sensitive responses
- mutation rate limiting
- readiness + metrics surfaces
- shared storefront cache
- batch cart pricing queries
- N+1 removal from delivery listing
- SQL-based growth analytics
- paid/completed-only LTV and revenue semantics
- profile-level payment provider allowlist
- production defaults exclude simulated providers
- 32 focused V4 adversarial tests, including an 8-way concurrent idempotency race

## 0.3.0

Delivery orchestration: quotes, dispatch, tracking, courier state machine and fail-closed provider boundaries.

## 0.2.0

Loyalty, rewards, promotions, consent-gated automations and growth analytics.

## 0.1.0

Menu, cart, pickup ordering, customers, payments, reservations and operator surface.
