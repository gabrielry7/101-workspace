# Wompi sandbox integration (0.9.0)

Only `wompi_sandbox` is implemented. The old `wompi` production adapter stays
fail-closed. Production app startup rejects sandbox providers. No remote refund
execution or M3b financial-provider eligibility is enabled by this change.

## Start a private test storefront

Install the project with its normal dependencies, then run:

```bash
python -m world_model.restaurant_commerce.wompi_sandbox_demo \
  --run-dir /tmp/101-wompi-demo --port 8876
```

Open `http://127.0.0.1:8876/`. This creates synthetic restaurant data in a **new**
private directory. It loads test keys from
`~/.config/101-world-model/wompi-sandbox/credentials.json`. Use a fresh directory
for a separate run; add `--resume` with the original directory/port to test restart.
It binds loopback only, provides no default staff accounts, sends no application
messages, and never modifies an existing commerce database. Keep the same browser
origin for recovery. Use only Wompi's documented fake cards and synthetic contacts.

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

Requires completed M4 schema. The upgrade adds only
`restaurant_wompi_sandbox_lookups`; it does not provision staff or change payments.
Fresh disposable databases include the table. Existing production databases were
not upgraded during implementation.

## Remaining qualification

Public HTTPS callback delivery and actual events-secret verification, hosted card
submission/return across supported devices, provider duplicate-reference behavior,
refund lookup/idempotency and staff financial resolution for this remote adapter
remain separate work. Broad scanners, production restore and physical old-device
qualification remain open. Passing sandbox tests does not authorize real money.

Protocol sources: [keys/environments](https://docs.wompi.co/docs/colombia/ambientes-y-llaves/),
[hosted checkout](https://docs.wompi.co/docs/colombia/widget-checkout-web/),
[native events](https://docs.wompi.co/docs/colombia/eventos/),
[transactions](https://docs.wompi.co/docs/colombia/transacciones/),
[test fixtures](https://docs.wompi.co/docs/colombia/datos-de-prueba-en-sandbox/).
