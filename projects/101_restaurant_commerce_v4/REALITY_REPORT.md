# Restaurant Commerce V4 reality report

V4 is a hardening release, not a feature demo.

## Regression + adversarial suite

- 79 tests collected/passed
- 32 V4-focused adversarial/reliability tests
- Python `compileall`: pass
- browser UI inline-JavaScript syntax: pass for storefront/admin/growth/delivery
- coverage run: 86% package-wide line coverage in this execution environment
- wheel build/install/import canary: pass
- live Uvicorn health/readiness/storefront canary: pass
- installer-to-mock-101 canary: pass
- V2/V3 regression reality flows + V4 reality flow: pass
- Ruff/Bandit/pip-audit were not installed in this runtime, so no claims are made for those tools

### Adversarial cases exercised

- weak/missing production secrets
- accidental production demo mode
- unauthorized order/tracking reads
- oversized request bodies
- request-rate flood boundary
- unknown input fields
- idempotent request replay
- same idempotency key with changed payload
- 8 concurrent identical order submissions
- malicious payment-provider identity/amount/currency/reference/status output
- selective retry behavior
- circuit-breaker opening
- event-sink outage and replay drain
- payment-state regression
- paid cancellation without refund
- deferred cash settlement
- terminal reservation escape
- webhook forgery/replay/conflicting replay
- stale delivery callback rewind
- delivery-completion replay
- SQLite FK/WAL/busy timeout
- database money constraint violation
- storefront cache query elimination
- bounded quote query count
- protected observability endpoint

## Concurrency canary

Eight concurrent requests submitted the exact same order/idempotency key while the payment provider was deliberately slowed.

```text
successful order creators:       1
in-progress conflicts:           7
payment checkout calls:          1
persisted order for key:         1
```

The invariant tested is the important one: duplicate client retries cannot multiply the external checkout side effect.

## Local microbenchmark

See `V4_PERFORMANCE.json` for raw output.

On this container, single-process, local SQLite, no network:

```text
warm cached storefront:
  20,000 iterations
  ~2.0M function calls/sec
  p99 ~0.0005 ms

server-authoritative quote:
  2,000 iterations
  ~549 quotes/sec
  mean ~1.82 ms
  p95 ~2.18 ms
  p99 ~2.87 ms
```

The storefront figure is intentionally a cache microbenchmark and **not** an HTTP/server capacity forecast. The quote number is also local-only; production PostgreSQL/network/provider latency will differ.

## Network/provider activity

External provider calls during this hardening/reality run:

```text
Wompi:              0
Uber Direct:        0
Mensajeros Urbanos: 0
WhatsApp/Meta:      0
other paid API:     0
```

Real provider adapters remain fail-closed.

## Reliability boundary still remaining

V4 materially improves the application core but does not justify claiming a certified high-availability production system. Before live money/fulfillment:

- integrate the schema through 101's actual Alembic chain
- run PostgreSQL concurrency/load/failure testing
- implement real provider adapters with official webhook verification + strict HTTP timeouts
- run backup/restore and worker-crash drills
- use distributed/edge rate limiting for multi-worker deployments
- add CI dependency/security scanners and external review
- establish monitoring alerts and an incident/SLO process

Those are deployment/provider obligations, not hidden behind a “military grade” label.
