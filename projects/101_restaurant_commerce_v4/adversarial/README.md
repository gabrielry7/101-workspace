> Current combined stack, load budgets and runtime limitations: [STACK.md](STACK.md).
> Historical budgets and release-gap statements below describe the earlier harness.

# Repeatable local adversarial execution

From the commerce project directory:

```sh
./adversarial/run.sh
```

This builds a wheel, installs it outside the source tree, initializes a new real
PostgreSQL cluster on random loopback ports, seeds two businesses and separate
customers, starts two Uvicorn workers and an inspectable synthetic provider, runs
the baseline, then browser, generated API, property, load, fault and scanner layers.
It retains native reports and stops only processes belonging to the run. A red
result is expected while release gaps remain. Read `assessment.json` and native
receipts: an exit code alone is not a security verdict.

## Prerequisites and scope

Linux x86_64, `uv`, PostgreSQL executables (`initdb`, `pg_ctl`, `createdb`), Node/npm,
and Chromium must be installed. Run as an ordinary non-root user. Public package
and scanner-rule/database downloads need network access and several GB of disk.
The launcher installs pinned Python packages in a task-local environment;
Playwright uses its locked npm dependencies. Toxiproxy, Java, ZAP and Trivy binary
downloads are pinned and checksum checked. Semgrep rules and Trivy advisory data
are fetched at execution time; native reports record the coverage actually used.
Set `COMMERCE_TOOLCHAIN` to a writable disk directory if `/tmp` is small.

The app and attack targets are loopback only. Do not point this suite at production.
No provider credentials, real messages, purchases or model calls are needed.
`config.json` contains ephemeral synthetic secrets and is mode0600; do not publish
it. Native raw reports can also contain synthetic data. Commit curated/redacted
summaries, not run directories or caches.

The application has named staff accounts, business memberships and HTTP-issued
sessions. The harness seeds separate single- and dual-business identities and runs
two workers with durable recovery loops. Customer login remains absent. WhatsApp is a consent-checked handoff, not a messaging adapter. Email
sending is absent. Payment/delivery/event seams use controlled network services
whose SQLite ledger survives application restarts. Demo mode is intentionally
on, rate limiting raised for load tests; this is not production-configuration
qualification. Production guards are covered by the existing regression suite.

## Layers, bounds and expected gaps

- Baseline: all existing tests, seven runner-safety cases, plus real HTTP checkout, simulated payment, staff
  fulfillment and customer status through the installed wheel and PostgreSQL.
- Browser: 13 real-backend scenarios plus official Playwright planner/generator/
  healer tool attempts. Duplicate submissions, tabs, lost replies, reload,
  reconnect, stale quotes/address changes, unavailable storage and business
  switching. Traces retained. Healer diagnoses; it cannot skip assertions.
- Hypothesis: seed101027, up to30 examples/property, action sequences up to10
  transitions; money totals, replay, authority, consent and malformed notifications.
- Schemathesis: seed101, 15 examples/operation, examples+fuzzing phases, separate
  public/customer/staff contexts. Server-error and response-schema checks, actual
  live OpenAPI; hooks bind real opaque IDs and credentials. Per-profile process
  budgets90/120/60s. Budget exhaustion means PARTIAL, never PASS.
- Locust: smoke2users/10s; normal10/20s; spike30/15s; recovery3/15s; sustained10/60s.
  Browse/quote/checkout/exact replay/payment/status; CSV, HTML, actual peak users,
  latency per operation and PostgreSQL/provider invariant audit. This short local
  run measures a host-local envelope, not production capacity or long endurance.
- Toxiproxy: DB latency/reset/recovery, provider latency/reset, acceptance followed
  by lost reply, and killing both application workers after simulated payment
  success before local completion. Provider ledger compared with real DB rows.
- ZAP: bounded active API/web HTTP scan, real customer-capability/staff-session
  contexts, protected200 reach proof, OpenAPI import, native active request counts.
  External-callback and unsupported browser rules excluded and listed. Scan budget
  exhaustion/unsupported rules/export failure remain PARTIAL.
- Semgrep CE source rules and Trivy dependencies/secrets/configuration. The optional
  `Dockerfile` is a proposed disposable harness image, not a built release artifact.
  Built-container scanning is BLOCKED without a usable container engine/image.
- Strix is BLOCKED without explicit paid-model enablement/hard budget and a usable
  runtime. Existing provider key presence is not authorization. No model calls.
- Five Trail of Bits skill procedures were applied manually; native plugin
  workflow execution remains PARTIAL. See `skill_review.md` for actual evidence.

The referenced downloadable brief was unavailable in this workspace. These are
explicit conservative local budgets chosen from the pasted requirements, not a
claim to have executed unknown attachment budgets. Physical old/slow phones and
old browser engines remain unqualified; network simulations cannot prove them.

## Inspect, resume and clean up

```sh
# Keep the owned services for investigation.
./adversarial/run.sh --run-dir /tmp/my-commerce-run --keep
# Resume selected layers on that same disposable target (fresh output paths needed).
./adversarial/run.sh --config /tmp/my-commerce-run/config.json --layers locust,faults --keep
# Stop only owned services. Evidence and database files are retained.
./adversarial/run.sh --config /tmp/my-commerce-run/config.json --cleanup
```

Use a fresh run for independent full assessments. Browser output refuses overwrite;
command logs also refuse overwrite; give other direct layer invocations fresh output directories.
Do not reuse consumed identifiers, stock, or old reports to infer a new pass.
Normal cleanup checks an ownership marker and process start times. A machine crash
can leave PostgreSQL running; the explicit cleanup command uses the recorded owned
cluster. It never removes unrelated resources or deletes run data.

Real-money release stays gated on durable financial intent/reconciliation, scoped
staff/customer authentication, durable browser retry recovery, migrations and
recovery qualification. A successful scanner does not override these contracts.

M4 focused acceptance: `./adversarial/run.sh --run-dir /tmp/101-commerce-runs/m4 --layers baseline,financial,browser,properties`. The retained staff-isolation test now exercises a real single-business session and must pass. `config.json` also contains synthetic staff passwords/session headers; never publish it or raw login traces.
