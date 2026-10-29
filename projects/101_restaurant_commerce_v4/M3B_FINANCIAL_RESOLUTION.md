# M3b — controlled payment lookup and full-refund resolution

This milestone uses controlled providers only. Wompi remains unimplemented and
real-money operation remains gated. `create_app` refuses financial-provider
configuration in production. The global operator token grants no authority on
`/api/finance/` routes.

The host supplies `financial_authenticator(token) -> FinancialPrincipal | None`.
A principal has a server-derived actor ID, business scopes, explicit permissions
(`finance.read`, `finance.lookup`, `finance.refund`, `finance.resolve`) and aware
expiry. Resolve revocation on each request. No default financial principal exists.
The disposable harness supplies synthetic credentials; this is not staff login,
credential provisioning, membership management or a production session system.

Financial adapters declare `controlled=True` and implement lookup by original
checkout key/reference, refund lookup, and full refund. Provider IO must have bounded
timeouts. A missing lookup means unknown, never proof of failure. Observations must
match the order, full amount, currency and reference and contain bounded evidence
identifiers. Adapters must independently enforce a full-payment refund ceiling;
a local preflight cannot prevent an external refund racing a remote request.

One durable full-refund intent per order is committed before provider IO, together
with the authorizing actor/reason and a financial hold. Repeated clicks recover that
intent. Database leases and ownership tokens fence completion. Recovery queries the
refund before reissuing a write; replay requires an explicit idempotency guarantee.
Unknown outcomes remain held. A signed external refund blocks further dispatch.
Fulfillment and courier dispatch cannot proceed while an active refund intent exists.

Confirmed settlement, operation state, benefit compensation and financial audit
commit together. Applied reward points are restored, promotion usage is released,
and completed-order earnings are reversed from their original ledger entries.
Already-spent earnings create explicit loyalty debt and block further redemptions;
future earned/released credits settle debt with ledger provenance. Completed order
fulfillment history remains intact. This also applies to authenticated refund
notifications, not just operator actions. Partial refunds are outside this contract.

Resolution requires the matching order, current financial authority, a reason and
confirmed provider evidence. A paid lookup cannot clear an uncertain refund. A
provider query started before a newer contradiction cannot resolve that episode.
Distinct contradictions reopen/update obligations and retain prior evidence in audit.
A definitive failed refund can be explicitly withdrawn with its no-effect evidence,
allowing fulfillment again. That original refund intent is retained and not reissued;
a second refund authorization after withdrawal is not implemented in this milestone.

The staff page uses a separate password input for financial credentials, kept only
in memory. It offers lookup, full refund, history and evidence-bound resolution.
It displays pending/unknown states honestly and instructs staff to inspect history
when a response is lost. Reload requires re-entering authority; no financial token
is persisted in browser storage.

## Offline upgrade

Stop all writers, take a backup, and set `COMMERCE_DATABASE_URL` privately. A database
already upgraded through M3a needs:

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-finance --offline
```

Three additive tables store financial operations, append-only application audit and
loyalty refund debts. No historical refund or staff authority is fabricated. Partial
schemas are refused; application startup does not silently upgrade existing data.
The audit is application-append-only, not tamper-proof against a database administrator.
Existing user databases were not changed by this implementation.

## Repeatable execution

```sh
./adversarial/run.sh --run-dir /tmp/101-commerce-runs/m3b-replay --layers baseline,financial
```

The runner builds/installs the actual package, starts owned PostgreSQL and controlled
HTTP providers, runs the baseline and financial API/browser/process-interruption
scenarios, retains evidence, then stops its owned services. Use a fresh directory.
Use a persistent run directory and `COMMERCE_TOOLCHAIN` for runs that must survive a
host restart. The broader default suite still retains the known global staff-scope
failure. Full authorization, live provider protocols, deployment/restore, broad
security scanning and physical old/slow-phone qualification remain release gates.
