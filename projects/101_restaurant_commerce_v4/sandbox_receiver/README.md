# Wompi sandbox receipt receiver

Built and tested locally; not deployed. Creating persistent resources requires
confirmed Cloudflare Workers Free plan and the user's $0 ceiling. No account,
plan, domain, production Worker or existing database should be changed implicitly.

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
Actual Wompi→HTTPS→D1→commerce delivery remains unverified until deployment and
manual Events URL configuration.
