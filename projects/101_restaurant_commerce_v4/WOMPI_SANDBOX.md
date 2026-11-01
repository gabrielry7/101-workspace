# Wompi sandbox integration (0.9.1)

Only `wompi_sandbox` is implemented. The old `wompi` production adapter stays
fail-closed. Production app startup rejects sandbox providers. No remote refund
execution or M3b financial-provider eligibility is enabled by this change.

## Start a private test storefront

Wompi's hosted page returned HTTP403 with loopback return URLs during execution;
the same signed checkout loaded with a public return URL. Do not use localhost as
the hosted return URL. For a disposable test, start an official Cloudflare Quick
Tunnel (no account needed), then use its HTTPS origin:

```bash
cloudflared tunnel --url http://127.0.0.1:8876
python -m world_model.restaurant_commerce.wompi_sandbox_demo \
  --run-dir /tmp/101-wompi-demo --port 8876 \
  --return-url https://YOUR-TEMPORARY-HOST.trycloudflare.com/
```

Open that **same HTTPS origin**, so browser recovery remains on the same origin
through checkout and return. Anyone with the temporary URL can access this
synthetic test app; stop its tunnel and app after testing. No real customer data.
The demo requires a new private directory and loads test keys from
`~/.config/101-world-model/wompi-sandbox/credentials.json`. It provisions no staff
accounts and modifies no existing database. `--resume` with the original directory
and port retains the fixed return URL; it does not change an old payment URL when
a tunnel hostname changes. Use a new run for a new hostname.

`--api-only` permits loopback return URLs solely for the bounded protocol smoke;
it does not qualify hosted navigation. [Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

The normal storefront submits an immutable local order, then follows a signed
hosted checkout URL. Card entry belongs to Wompi. Local contact data, recovery
secrets and private keys are absent from that URL. Despite legacy `_minor` names,
the existing commerce ledger/UI uses whole COP pesos: outbound amounts are
multiplied by100; inbound cent values must divide exactly by100.

## Run the bounded remote contract smoke

```bash
python scripts/check_wompi_sandbox.py \
  --run-dir /tmp/101-wompi-check --execute-sandbox
```

Run using the installed wheel's Python environment. This starts/stops its own
loopback app, uses a new synthetic database and official approved/declined cards,
allows at most four provider POSTs, and verifies server lookup plus repeated
recovery of the original order. No uncertain POST is retried. `evidence.json`
contains safe financial results and the package code digest. Private recovery
files stay mode0600 in the mode0700 run directory; do not publish them. Native
provider responses, card tokens, contact data and keys are not written to reports.
An incomplete scenario fails the command; a rerun uses a fresh directory.

## Callback and recovery contract

Configure `/api/webhooks/payments/wompi_sandbox` only after exposing the intended
test application through a suitable HTTPS URL. **Do not enter localhost as Wompi's
Events URL.** The local demo does not establish public webhook reachability.

Native events require the test events secret and signed transaction ID, status
and amount. Only a durable receipt earns HTTP200. The worker independently looks
up the transaction using the private key, checks merchant public key, order,
business, reference, amount and currency, then feeds the existing payment inbox.
Unsigned event reference/currency and browser `status` parameters never settle a
payment. Browser return IDs require the original expiring/revocable recovery
credential. Unknown IDs, lookup failure or missing recovery never mean paid.

Lookup jobs survive restart, use a fenced60-second lease and exponential backoff,
and stop after12 attempts. Genuine bound adverse states/long-pending results open
reconciliation; VOIDED never fabricates a refund. Distinct approved transactions
for one reference trigger review. A pure replayable checkout URL does **not** prove
provider-side charge uniqueness. Real duplicate-reference/concurrent-payment
qualification remains a release gate.

The browser blocks payment navigation when recovery cannot be persisted and
blocks a new checkout after a return with missing recovery. A deliberate new
purchase after a terminal outcome clears the old transaction hint.

## Existing databases

Sandbox storage is optional. Ordinary startup does not add its table to an
existing database. Stop writers, back up, and explicitly run:

```bash
COMMERCE_DATABASE_URL=... python -m world_model.restaurant_commerce.maintenance \
  upgrade-wompi-sandbox --offline
```

Requires completed M4 schema. The upgrade creates `restaurant_wompi_sandbox_discovery` and adds the
`single_attempt` column to earlier sandbox lookup tables. It preserves existing
lookup jobs and payment data; running it twice is safe. Fresh disposable databases
include both sandbox tables. Existing production databases were
not upgraded during implementation.

## Remaining qualification

Public HTTPS callback delivery and actual events-secret verification, hosted card
submission/return across supported devices, concurrent provider duplicate-reference behavior,
refund lookup/idempotency and staff financial resolution for this remote adapter
remain separate work. Broad scanners, production restore and physical old-device
qualification remain open. Passing sandbox tests does not authorize real money.

Protocol sources: [keys/environments](https://docs.wompi.co/docs/colombia/ambientes-y-llaves/),
[hosted checkout](https://docs.wompi.co/docs/colombia/widget-checkout-web/),
[native events](https://docs.wompi.co/docs/colombia/eventos/),
[transactions](https://docs.wompi.co/docs/colombia/transacciones/),
[test fixtures](https://docs.wompi.co/docs/colombia/datos-de-prueba-en-sandbox/).


## No-return recovery and repeatable qualification

The existing recovery worker now discovers transactions by the immutable order
reference after a 60-second grace period. A list result only supplies IDs: each
ID receives an independent authenticated lookup that checks merchant, business,
order, amount and currency before using the existing payment inbox. Empty lists
never mean declined. Discovery continues across pending, failed and paid local
states for up to 48 hours/60 bounded passes, with backoff capped at one hour.
This is a sandbox safety net, not a production reconciliation schedule or proof
of complete provider pagination. Saturated lists (20 or more) or unknown metadata
fail closed. New observations preserve old failed/exhausted jobs for audit.

Each discovery pass retains transaction hints atomically, then the bounded normal
lookup queue handles them. A discovery observation has one lookup attempt; the
next discovery pass can refresh it. Native events/customer returns retain the
12-attempt lookup policy. Expired/stolen leases cannot apply stale results.
Exhausted bound jobs, immutable amount conflicts, contradictory final statuses,
multiple approvals and externally observed refunds create visible reconciliation
holds. An observed refund never invents local refund accounting or loyalty
compensation. Resolving Wompi financial holds still needs the qualified remote
financial adapter; legacy controlled-provider resolution is not enabled for it.

Install test dependencies in an isolated Python environment and local receiver
runtime (`npm install --prefix sandbox_receiver`). PostgreSQL tools and Chromium
must be on PATH. The workspace's retained toolchain already contains these.

```bash
python scripts/qualify_wompi_sandbox.py --run-dir /tmp/wompi-qualification-NEW
```

This one command builds/installs a wheel, runs the complete tests, Wompi cases on
a fresh local PostgreSQL cluster, and receiver tests in real Workers/Miniflare
with D1. It retains native logs, JUnit, command receipts, versions and wheel hash;
it stops only its own database. Use a short workspace run path for evidence that
must survive reboot. A fresh run directory is mandatory. No zero-test or skipped
suite is reported as passed.

Remote opt-in, bounded to 12 direct Wompi POSTs per protocol run:

```bash
python scripts/qualify_wompi_sandbox.py --run-dir /tmp/wompi-remote-NEW \
  --layers tests,postgres,receiver,remote,hosted --execute-sandbox \
  --cloudflared /path/to/verified/cloudflared
```

The hosted test uses a temporary accountless tunnel, never the permanent Events
URL, and stops it afterward. It caps transaction submissions at one and tests the
provider's actual return button, narrow viewport, CPU throttling, reload and
reconnection. This does not certify physical older phones or all browsers.

The protocol edge test kills the app before the fake payment and verifies
background recovery without delivering a transaction ID or callback. Its tamper
probe uses a fresh unused reference so duplicate-reference validation cannot mask
signature validation. Refund probes are separate provider-contract checks and do
not enable refunds in commerce. `--payment-edges-only` on
`scripts/check_wompi_sandbox.py --edge-cases` explicitly omits those refund writes
and records PARTIAL coverage, rather than silently passing them.

**Known remote refund failure:** on 2026-10-30, `test_scenario: "declined"` yielded
PENDING and later APPROVED. A 2026-11-01 sandbox GET confirmed APPROVED with
`is_sandbox: false` and `sandbox_test_scenario: null`. Requests used test keys,
the fixed sandbox host and a fake-card transaction. No production endpoint was
called; the contradictory flag does not establish a real-money movement. Do not
trust the simulator's requested outcome or enable remote refunds until this
contract is resolved. Retain failing results when rerunning; do not substitute a
mocked pass. [Documented refund scenarios](https://docs.wompi.co/docs/colombia/reembolsos-sandbox/).

## Optional durable HTTPS receiver

`sandbox_receiver/` contains a sandbox-only Workers/D1 receiver and executable
runtime tests. **Deployed 2026-11-01 on the confirmed Workers Free plan ($0).**
The user supplied the Current plan screenshot and explicitly authorized storing
the sandbox Events secret and separate reader token in encrypted Worker secrets.
No private payment key was uploaded; no account upgrade or existing-site change.

The receiver verifies the native signature, rejects production/stale/malformed
events, persists only signed financial fields, and acknowledges only after the
D1 insert. Consumption/ack require a separate 256-bit reader token. Replayed
receipts cannot resurrect an acknowledged event. The Python consumer verifies
the event again and commits its local lookup job before acknowledging remotely;
lost acknowledgements replay safely. It keeps independent reference recovery
working while the receiver is unavailable.

After this verified deployment, a private mode0600 JSON file with `url` (HTTPS
origin) and `token` (64 hexadecimal characters) can be passed to the demo as
`--receiver-config /private/path.json` on each start/resume. Secrets belong in
Worker secret bindings, never repository config. This machine's configuration is
`/home/t/.config/101-world-model/wompi-sandbox/receiver.json`.

Set the **sandbox** URL de Eventos to
`https://101-wompi-sandbox-receiver.reader-101.workers.dev/events` and save it.
The deployed receiver's signed-fixture checks pass. Actual Wompi-native delivery
was qualified on2026-11-01: an approved callback arrived with commerce terminated
in7.02seconds, and restart recovered the same paid order in15.43seconds with one
payment. A declined callback retained across shutdown was consumed on a second
restart without duplicating the payment. These are measured individual sandbox
scenarios, not production/load certification. Repeat the bounded receiver checks with:

```sh
python scripts/check_wompi_receiver.py --run-dir /tmp/receiver-NEW --execute-sandbox
```

After saving the sandbox dashboard URL, qualify native delivery during a process
outage with the existing payment probe (refund writes remain excluded):

```sh
python scripts/check_wompi_sandbox.py --run-dir /tmp/native-webhook-NEW \
  --execute-sandbox --edge-cases --payment-edges-only \
  --receiver-config /home/t/.config/101-world-model/wompi-sandbox/receiver.json
```

This mode waits for an actual approved native event while commerce is terminated,
restarts the app, and requires the checksum-bound job to be processed and remotely
acknowledged with one payment record. Reference polling alone cannot pass this
acceptance check. Empty inbox required at startup; no invented callbacks. The
probe retains private runtime evidence and stops only its own application.
A late callback may arrive after the test process stops: resume that same
disposable demo with its original port, `--resume`, and `--receiver-config` to
drain it before the next isolated probe. Do not delete or manually acknowledge
unconsumed receipts to make the empty-inbox precondition pass. Keep the real-money
and refund gates closed; the prior refund-simulator contradiction remains open.
