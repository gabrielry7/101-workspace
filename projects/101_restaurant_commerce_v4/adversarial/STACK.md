# Executed adversarial stack

Use the current application revision. All targets are disposable loopback PostgreSQL,
synthetic accounts and controlled providers. No customer data, remote payment keys,
cloud provisioning or model calls are needed. Keep the run directory private: native
traces can contain synthetic session and order capabilities.

One command (Linux, PostgreSQL tools, uv, Node/npm and Chromium installed):

```sh
COMMERCE_TOOLCHAIN=/path/to/test-tools \
  /path/to/test-tools/venv/bin/python adversarial/full_stack.py \
  --output /path/to/new-private-run \
  --cache /path/to/security-tool-cache \
  --native-tools /path/to/native-tools
```

Run `adversarial/run.sh` once to bootstrap that Python tool environment if absent.
`security/check.py` prepares pinned native security tools, rules and runtime wheels.
The combined command runs the existing adversarial journeys, then the deployment
security gate sequentially. Each runner stops only its owned services and retains
evidence. Failed layers do not prevent the independent security deployment from
running. Exit2 means executed suites passed but the requested Strix layer was not
run; exit1 means at least one suite failed/incomplete. Neither means full qualification.

The two deployments deliberately remain explicit: journeys exercise an installed
wheel with two Uvicorn workers and a separate installed recovery runner; the security gate exercises
the hash-locked deployment artifact with separate recovery worker and monitor.
Faults kill API and recovery together after provider acceptance and restart both.
The deployment gate separately verifies its release lifecycle and monitor. Do not claim
those runtime boundaries are interchangeable or production qualified.

## Load and fault budgets

Default sequential Locust phases are smoke2users/15s, baseline10/30s,
normal30/60s, spike100/45s, recovery5/30s and sustained20/300s.
This is a five-minute local sustained test, not a long-duration production soak.
`load_profiles` in the private run config can set explicit bounded
`[name,users,spawn_per_second,seconds]` rows; maximum1000users and1700seconds
including shutdown allowances. The pasted original schedule was unreadable;
these are chosen local budgets, not a reconstruction of it.

Native CSV/HTML, per-operation p50/p95/p99, request/error rates, actual peak users,
completed checkouts, process RSS/CPU counters and host load samples are retained.
Every phase has a unique database/provider key prefix. PASS requires positive
completed checkouts, achieved concurrency, zero request failures, no duplicate
intents, and equal completed/paid-order/payment/provider-effect counts.
Profiles cannot be empty, target remote services, or overwrite old evidence.

Toxiproxy exercises500ms database/provider latency, connection resets and a5000ms
provider TCP timeout, plus provider acceptance with lost reply and process death.
Application client timeout can fire before the injected5000ms timeout; the receipt
records actual latency. Database and persistent provider ledger are checked.

Finite stock and pickup capacity have existing PostgreSQL race regressions.
The load profile uses unlimited seeded stock; it is not an inventory-exhaustion test. Full customer
login is absent: customer authorization uses protected order capabilities.

## Costs

Locust, Playwright, Schemathesis, Toxiproxy, OWASP ZAP, Semgrep Community Edition
and Trivy can all run locally without license/subscription fees. Hosted services,
commercial editions, cloud machines and AI agents can cost separately.
Strix is open-source/free software but requires a Docker runtime and a configured
model backend. Model API use or hosted Strix is not implicitly free. This suite
records Strix NOT RUN under the existing USD0 constraint rather than using saved
credentials or pretending a scanner probe was a penetration test.

Official sources: https://github.com/locustio/locust,
https://github.com/microsoft/playwright, https://github.com/schemathesis/schemathesis,
https://github.com/Shopify/toxiproxy, https://www.zaproxy.org/,
https://docs.semgrep.dev/semgrep-ce-languages, https://github.com/aquasecurity/trivy,
https://github.com/usestrix/strix.
