# 101 Restaurant Commerce V4 — Reliability Release

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
- concurrent duplicate order submissions produce only one external payment checkout
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

- operator bearer token uses constant-time comparison
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

Development operator token defaults to `dev-operator`. Production refuses that token.

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
