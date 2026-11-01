# Wompi sandbox receipt receiver

Deployed 2026-11-01 after the user confirmed Workers Free ($0 current plan) and
explicitly authorized the two sandbox secret uploads. The dedicated endpoint is
`https://101-wompi-sandbox-receiver.reader-101.workers.dev/events` and D1 database
is `101-wompi-sandbox-receipts`. Existing account plan and reader-101 resources
were not changed. Stay on Free; quota exhaustion must fail, never trigger an upgrade.

`worker.mjs` is an ES module with D1 binding `DB`, secret bindings `EVENTS_SECRET`
(test-events key only) and `READER_TOKEN` (random 64-hex capability). Use a dedicated
sandbox Worker/database, apply `schema.sql`, enable workers.dev HTTPS and current
compatibility date, and enable sampled logs/traces without bodies/headers. No
Wompi private payment key is required by the receiver.

Routes:
- `POST /events`: native transaction.updated test event; 32KiB streaming body cap,
  48h past/5min future timestamp bounds, financial signature fields only. Durable
  insertion before 200; unavailable D1 returns 503, never a false acknowledgement.
- `GET /private/events`: authenticated bounded batch of 20 pending receipts.
- `POST /private/ack`: authenticated list of at most 20 receipt checksums.
- `GET /health`: database reachability and service version. Separately verify
  secret provisioning with a controlled signed fixture before sharing Events URL.

Only signed ID/status/amount and optional signed reference/currency are retained.
Card/contact fields are dropped. No provider transactions/refunds or outbound
messages are issued. Backend independently verifies financial truth with Wompi.
Acknowledged receipts remain for replay suppression; retention/alerting and
refund-event support are explicit future operational requirements. This is not
production deployment certification.

```sh
npm install
npm test
```

Pinned Miniflare 5 uses its exported V4 option conversion utility. Runtime tests
exercise actual Workers crypto and D1: receipt persistence, replay, privacy,
authentication, forged/production/stale/oversized events and storage failure.
No failure is repaired by skipping a test. Python consumer tests exercise commit
before remote acknowledgement, lost acknowledgements and independent discovery.
Deployed checks also pass for eight concurrent duplicate receipts, signature and
auth rejection, privacy, durable local enqueue, lost acknowledgement and replay.
Run `python scripts/check_wompi_receiver.py --run-dir /tmp/receiver-NEW
--execute-sandbox` from the project root with its dependencies installed. This is
a signed synthetic fixture. On2026-11-01 the native callback test also passed
after the user saved the sandbox Events URL: approval persisted while commerce
was stopped and settled after restart; a late declined receipt also survived
shutdown and was consumed on the next start. Real-money and refund release gates
remain closed. See `WOMPI_SANDBOX.md` for the bounded native rerun command.

The local pinned runtime tests retain compatibility date 2026-10-29. An attempt
to run the deployed 2026-11-01 date locally was rejected before tests started:
installed workerd supports only through 2026-10-30. The real deployed tests pass
on 2026-11-01; do not describe the local suite as the same runtime configuration.
