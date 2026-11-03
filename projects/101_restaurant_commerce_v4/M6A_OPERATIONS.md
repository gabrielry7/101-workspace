# M6a: repeatable local deployment and recovery

This is a **loopback, simulated-payment rehearsal**, not a production deployment.
Real money, remote provider recovery, real messages and unqualified Wompi refunds
remain disabled. No existing business database is upgraded by these tools.

## What is connected

`deployment/runtime.py` passes an explicit PostgreSQL engine into the existing
`create_app`, with schema initialization and the embedded recovery thread disabled.
A separate process calls the existing payment, financial and event-outbox owners;
SQL leases, order identity, financial audit and staff authorization remain theirs.
No second order store or migration framework is introduced.

The outbox consumer now fsyncs a private, immutable event-ID receipt before
acknowledging publication. Duplicate delivery checks identical content. A write
failure leaves the outbox pending; it never claims a WhatsApp/email delivery.
These local receipts need their own retention/backup policy before a real deployment.

The monitor reads existing database queues and private worker/backup receipts. It
retains opened/resolved alert receipts without customer payloads. This proves local
alert generation, **not delivery to an on-call person**. A failed monitor or full
host disk requires an external supervisor/monitor; this tool cannot page from a dead
machine. Remote Wompi receiver health is explicitly unassessed here.

## Reproduce the qualification

Requirements: Linux x86_64, CPython **3.12.14**, host libpq and PostgreSQL tools
(`initdb`, `pg_ctl`, `createdb`, `pg_dump`, `pg_restore`); a Python test environment
with pytest and Hypothesis; the retained M6a Git revision. The checked runtime lock
pins the actual Linux/CPython wheels, including psycopg. OS packages and interpreter
are external prerequisites, not a container image or hermetic OS build.

If the wheel cache is absent, prepare it using the checked hashes (free package
repository downloads; no merchant/provider credentials):

```bash
python -m pip download --only-binary=:all: --require-hashes \
  -r deployment/requirements.lock -d /tmp/commerce-m6-wheelhouse
```

From this project, the complete test/cleanup command on the current machine is:

```bash
/home/t/101-world-model/data/commerce-adversarial-tools/toolchain/venv/bin/python -B \
  scripts/qualify_operations_m6.py \
  --run-dir /tmp/commerce-m6-new-run \
  --wheelhouse /tmp/commerce-m6-wheelhouse
```

The run directory **must not exist**. It builds both current and retained M6a wheels,
installs clean offline hash-locked environments, launches its own PostgreSQL and
HTTP/worker/monitor processes, executes positive and failure scenarios, runs
retained PostgreSQL tests, saves native evidence and stops only its own processes.
It does not delete retained evidence or private data. `evidence/` contains commands,
times, results and hashes. Database archives, configs, cookies and event payloads
remain private elsewhere in the run directory; do not publish the whole directory.
`--previous-wheel` can select a retained wheel compatible with `--previous-revision`.
The older application is paired with that revision's deployment modules, not the
new runtime API. Both rebuilt bundles use the current hash-locked installer; this
rehearses application rollback, not a downgrade of the security-patched installer.

The test cluster uses local trust authentication and synthetic records. It is not
suitable for a shared host with untrusted local users. Run as an ordinary dedicated
user; `initdb` refuses root. The tools never contact Wompi or provision cloud resources.

## Deployment contract

- Configuration is a private regular JSON file (0600); state/site roots are 0700.
- `mode` must be exactly `rehearsal`, PostgreSQL must be explicitly loopback, and
  its database name must be a bounded simple identifier. URL query overrides,
  SQLite, unknown options and production mode fail closed.
- `public_access_secret` is a stable private signing secret, at least32 characters.
  Preserve the original secret for restore; generating another breaks order access.
- `state_dir` is outside the release. `allow_writes` defaults to **false**.
- Defaults: recovery/monitor interval1s, stale worker15s, due backlog60s,
  backup freshness86400s. These are configuration thresholds, not agreed SLAs.

Minimal config fields, with values obtained from private local configuration:

```json
{
  "mode": "rehearsal",
  "database_url": "postgresql+psycopg://LOCAL_ROLE@127.0.0.1:5432/FRESH_DATABASE",
  "public_access_secret": "REPLACE_WITH_THE_EXISTING_PRIVATE_SIGNING_SECRET",
  "state_dir": "/absolute/private/state",
  "allow_writes": false
}
```

Build a wheel, then `scripts/commerce_release.py pack --wheel PATH --wheelhouse PATH
--output NEW_DIRECTORY --revision COMMIT` emits a manifest SHA256. Keep that digest
in the trusted release record. `install --bundle PATH --manifest-sha256 HASH --site
PRIVATE_SITE` verifies exact bundle contents and performs an offline pip install
with all hashes required. It records the installed tree in a trusted receipt
**outside** the release. Added files, changed code, altered symlinks and unlisted
bundle content are rejected. The controller/receipt directory and host interpreter
must themselves remain trusted; this does not defend against a compromised owner/root.

`activate --site PRIVATE_SITE --release ID --config PRIVATE_JSON --port PORT`:

1. Verifies the installed tree and configuration under an exclusive deployment lock.
2. Reconciles a retained pending ownership journal and snapshots the effective
   private config for rollback, so edits to the input file cannot change fallback.
3. Stops the previous owned process groups (PID plus process start time).
4. Starts API, recovery worker and monitor separately. A child waits on a pipe until
   its ownership journal is fsynced; controller death before release causes exit.
5. Checks actual serving PID/release, database readiness, a successful worker cycle
   and a monitor cycle before publishing the current release pointer.
6. On candidate failure, relaunches the previous artifact with its saved config.

This has a short planned outage; it is not zero-downtime deployment. A dead
controller does not autonomously finish deployment: rerun activate or stop to
reconcile the journal. The CLI is a local controller, not a long-lived process
supervisor. Production requires a qualified supervisor, TLS, network policy,
separate least-privilege roles and a protected operator surface.

`rollback --site PRIVATE_SITE --config PRIVATE_JSON --port PORT` selects the recorded
previous compatible release. **Keep the current database**. Never restore yesterday's
backup or perform destructive down-migrations just to roll back application code.
`stop --site PRIVATE_SITE` stops only journaled owned processes; it does not drop data.
Do not run two independent controllers against the same site/state directories.

## Backup and restore procedure

Use the selected release's interpreter/runtime so the artifact is explicit:

```bash
RELEASE/venv/bin/python -I -B RELEASE/database.py backup \
  --config PRIVATE_JSON --directory NEW_PRIVATE_BACKUP_DIRECTORY
```

`pg_dump --format=custom --no-owner --no-privileges` produces a consistent snapshot
of **one database**. The archive and manifest are fsynced before the fresh-backup
receipt is published. Preserve the returned manifest SHA256 separately. The archive
is private, but it is **not encrypted**. Keep signing secrets and deployment config
in their separate secure backup. Role definitions, event receipt spool, provider
history and changes after the snapshot are outside this dump.

For recovery: stop writers and recovery processes, create a **different empty
PostgreSQL database**, and use a private config pointing at it with
`allow_writes:false` and the original signing secret. Then:

```bash
RELEASE/venv/bin/python -I -B RELEASE/database.py restore \
  --config QUARANTINE_JSON --directory PRIVATE_BACKUP_DIRECTORY \
  --manifest-sha256 TRUSTED_MANIFEST_HASH --expected-database EXACT_TARGET_NAME --offline
```

Restore rejects the source database, nonempty targets, wrong signing configuration,
unsafe target names and altered backup files. It holds a cooperating advisory lock
and uses `pg_restore --single-transaction --exit-on-error`; there is no `--clean`.
The operator must exclude other noncooperating writers; `--offline` is an explicit
operator assertion, not a host-wide lock or access-control mechanism.

Schema readiness is recorded after restore. If an older supported schema was
restored, run the existing explicit offline migration from the chosen artifact
before serving it. The runner tests a populated pre-M5 fixture with the existing
`upgrade_operations` function; it does not infer arbitrary legacy compatibility.
M6a adds no tables. A failed or incomplete schema cannot start the API/worker.

In quarantine, business writes and recovery workers are disabled. Staff authentication
and read-only order recovery remain available for verification; provider transaction
recovery requests are rejected. Check original order/payment references and totals,
recovery expiration, signing capabilities, staff scopes and revoked sessions.

Before reopening, reconcile **all post-snapshot writes and external effects**.
A database snapshot can predate staff revocations, payments, refunds and fulfillment.
The drill deliberately proves that a later order is absent after snapshot restore;
that is a recovery gap, not a successful rollback of the external world. Revoke
restored sessions conservatively if the revocation gap cannot be established.
Reopening writes requires an explicit reviewed config change after that reconciliation.

The measured small synthetic restore is not a production RPO/RTO commitment. Offsite
encrypted retention, WAL/PITR, backup scheduling, storage loss, representative data
volume and actual provider reconciliation remain release gates.

## Alert interpretation

`state/status.json` contains bounded aggregate queue counts and oldest due ages.
`state/alerts/` stores alert transitions; each is a local durable receipt only.

| Signal | Meaning / operator response |
|---|---|
| database_unavailable | Counts are **unknown/null**, never zero. Inspect DB, pause writes, recover safely. |
| worker_missing/stale/wrong_database/cycle_failed | Check owned worker and configured DB; restart through controller. |
| payments/financial/events_backlog | Due, unleased work exceeds threshold; inspect retained records, not blind retries of money. |
| financial_review | Open reconciliation requires authorized financial review. |
| backup_missing/stale/wrong_database | No fresh completion receipt for this DB. Verify actual backup and schedule a restore drill. |

A fresh backup receipt is evidence of completed backup at that time, not continuous
archive availability or a new restore test. An active lease/future retry isn't counted
as immediately due. Heartbeats and queue ages are both needed: a live worker can fail
to make progress. Remote receiver and human paging status remain unassessed.

## Technical references

[PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html),
[pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html), and
[pip hash-checking installs](https://pip.pypa.io/en/stable/topics/secure-installs/)
describe the guarantees and limits used here. M6a qualification results and native
evidence live in the shared `docs/commerce-audit/M6A_IMPLEMENTATION.md` report.
