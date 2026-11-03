# Checkout timing experiment

Run from the commerce project using the existing free local toolchain:

```sh
COMMERCE_TOOLCHAIN=/home/t/101-world-model/data/commerce-adversarial-tools/toolchain \
/home/t/101-world-model/data/commerce-adversarial-tools/toolchain/venv/bin/python \
  adversarial/measure.py --output /tmp/101-commerce-timing-new
python3 adversarial/analyze_timing.py /tmp/101-commerce-timing-new
```

The output must not exist. This builds/installs the actual wheel, creates owned
loopback PostgreSQL and controlled providers, proves a positive ordering journey,
then executes six blocks in reversed condition order: shared customer with tracing,
distinct customers with tracing, distinct customers without tracing, then reverse.
Each block restarts API/recovery workers and runs 2 users/10 seconds warmup,
30 users/30 seconds and 100 users/45 seconds. The two API workers and database
settings remain fixed. Cleanup stops only owned services, preserving evidence.
The database grows across blocks; reversed order only partly controls this.

Every phase retains native Locust output, exact command/timestamps/exit status,
p50/p95/p99 by operation, per-process resources and financial database audit.
PostgreSQL is sampled every 250 ms (plus query time) for activity and blocking.
Relation names of waiting statements are retained; SQL values/text are discarded.
The initial November 3 run added relation-name sampling partway through as a
separate observer; its coverage is explicitly shorter than the primary sampler.

Tracing is opt-in via private disposable config `timing_enabled`; production
application source and schema are unchanged. Per-process JSONL captures request
UTC start, monotonic duration, route templates, status and spans. No bodies,
headers, query parameters, customer identifiers or SQL statements are retained.
FastAPI copies request context into handler threads. The probe is installed once
per API worker process; restart rather than installing repeatedly in one process.

Interpretation:

- `request_ms`: application ASGI lifetime, excluding the final trace file append;
  client Locust latency includes that overhead as well as network/scheduling costs.
- `endpoint_dispatch_wait`: scheduling delay for the route handler; dependency
  execution/scheduling before the route is outside this span.
- `connection_acquire`: QueuePool acquisition, including new connection creation;
  excludes pre-ping outside `_do_get`. It is not pure pool queue wait.
- `sql_execute`: driver execute duration including network/database lock waits;
  excludes result consumption and Python ORM work.
- `commit_including_flush`: Session.commit including ORM flush and overlapping SQL.
- `provider_executor`: full ProviderExecutor call, including retries/backoff;
  direct event-sink calls outside this executor remain unattributed.
- `unattributed_endpoint_ms`: endpoint less SQL, acquisition and provider spans.
  Includes Python/ORM work, commit overhead and other IO; do not call it CPU time.
- Request spans can overlap. Never sum commit + SQL or add percentile values.
- New checkouts with provider execution are reported separately from all order POSTs
  because exact retries share the same route. Pending/recovery-owned intents may
  have no request-local provider span; Locust checkout statistics cover all calls.

Two repetitions are descriptive evidence, not a confidence interval or production
SLA. Shared-host resource contention, database growth and randomized user behavior
remain confounders. Shared/individual customer workloads still use one business
and cart. Fixed-arrival-rate traffic, mixed businesses, hours-long soak, physical
mobile devices and remote providers are outside this experiment.
