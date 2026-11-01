# M5 customer and staff frontend — 0.10.0

M5 builds on the existing M1–M4 service, payment ledger, scoped staff sessions and safe DOM rendering. The package ships its own small HTML/CSS/JavaScript bundle; it needs no frontend build service, remote font, component CDN or framework migration.

## Customer experience

- Searchable categorized menu, modifier dialog, quantities, item availability and server totals.
- Per-business two-hour cart draft containing only public item/modifier IDs and quantities. Contact information is not persisted in browser drafts.
- Signed two-minute quote binding and total confirmation before checkout. A changed cart or price requires a new confirmation; accepted retries recover the original order even after the quote expires or ordering is paused.
- Pickup times in the restaurant's timezone, with manager-maintained weekdays, hours, closed dates, lead time and capacity. No configured schedule means **time to be confirmed**, not an invented promise.
- Existing durable checkout recovery, receipt, paid/pending/declined/review states, polling, reload and return recovery. Same-origin tabs coordinate with Web Locks and the original persisted intent. Storage or required API failures stop submission with an explanation.
- Reservation requests retain their idempotency key across reloads. After an unknown result the customer reenters the same details to retrieve the same request. No contact PII is persisted. Exact replay survives policy changes and passage of the appointment time. A reservation still requires staff confirmation.
- Explicit `/r/{slug}` merchant link resolves the existing commerce profile; the capability API returns that link. This is an integration seam, not publication into the separate Honorato site.

## Staff experience

Named M4 login and per-business roles continue to govern every operator API. Queue reads are bounded to50 orders per page, with active/status/payment filters and search within that page. Detail includes contact, items/modifiers, notes, pickup time and current version. State changes carry the expected version and actor/reason; cash handoff requires explicit collection confirmation. Failed/unknown actions are not automatically resubmitted.

Managers can pause new orders, configure pickup and adjust stock/sold-out flags. Changes are versioned and audited. Last-slot and last-unit allocation is transactional; authoritative validation happens before the durable order commits and before provider IO. Persisted pickup timestamps normalize to UTC, including equivalent-offset requests on SQLite.

Stock is an **allocated order budget**, not a complete warehouse system. Pending and uncertain orders consume units. Cancellations/failed payments do not automatically restock: a manager verifies and adjusts with an audit reason. Automated reservation expiry/abuse controls and physical inventory reconciliation remain release work.

The daily financial view sums current local payment states for orders **created on the selected restaurant-local day**. It shows confirmed gross/full refunds/known balance, unconfirmed payments and all-date open reviews. Provider fees and settled net remain explicitly unknown. It is not a settlement ledger or bank close. The existing audited financial interface remains available, and unqualified Wompi refund submission stays disabled.

## Resilience and compatibility

Reads and response bodies have15-second deadlines. Polls are single-flight, completion-driven, back off to60 seconds, and pause while hidden/offline/unauthenticated. Mixed-resource errors retain a stale warning; success from another endpoint cannot certify a failed queue. Mutation uncertainty stays visible. Connection-state layout reserves space to avoid page jumps.

Checkout needs a secure context, Web Locks, cryptographic randomness and writable browser storage. Unsupported configurations fail before submission. The ES5 boot guard/static notice covers missing APIs/scripts and disabled JavaScript. Compatibility is demonstrated in the recorded current Chromium build only; exact historical Chromium/Firefox/Safari versions, real low-end phones, OS/browser zoom and screen-reader behavior still need qualification. CSS zoom and CPU/network throttling are emulations, not physical-device proof.

Delivery, loyalty, marketing and messaging retain their existing capability/authority gates. This release does not invent a courier, verified customer login, allergens, media, fees or completed refunds. Real-money use remains disabled.

## Offline database upgrade

Existing databases are not changed automatically. After the previous M2/M3/M4/Wompi upgrades, stop every writer, take and verify a backup, and run against the intended database:

```bash
python -m world_model.restaurant_commerce.maintenance upgrade-operations --offline
```

`COMMERCE_DATABASE_URL` supplies the private target. This adds empty pickup-policy and stock tables; no business schedule or stock is inferred. Startup refuses an old or partial schema. Provision named staff using the existing M4 procedure. A rollback uses the previous compatible artifact and preserved backup; do not drop history to downgrade.

## Repeatable local qualification

Prerequisites: project test/browser dependencies, psycopg, PostgreSQL `initdb`/`pg_ctl`/`createdb`, Chromium, and a local axe-core4.10.2 distribution. Point `COMMERCE_AXE_PATH` to its `axe.min.js`; the test fails if unavailable rather than reporting a skipped accessibility pass. No provider credentials are needed.

```bash
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium \
COMMERCE_AXE_PATH=/path/to/axe-core/axe.min.js \
python scripts/qualify_wompi_sandbox.py \
  --run-dir /tmp/commerce-m5-unique-run \
  --layers tests,postgres --financial --operations
```

Use a fresh run directory. The command builds and installs a wheel in that directory, tests that installed artifact, starts its own loopback PostgreSQL cluster with separate per-test schemas, records commands/times/exits/JUnit/hash manifests and browser artifacts, and stops its own PostgreSQL cluster in `finally`. HTTP browser fixtures stop their own local servers. It does not contact Wompi or provision cloud resources. Generated data/evidence remain for inspection; cleanup never targets another run.

`tests/test_frontend_m5.py` exercises actual HTTP and synthetic backend records, including complete order/staff lifecycle, two tabs/lost response/pause/reload, reservation replay, offline cart, storage/lock fallback, polling deadlines, deterministic1-of20 read loss, unknown staff mutation, keyboard/dialog focus, 200% CSS zoom,320–1440px layouts, axe and6xCPU/400kbps-down/100kbps-up/800ms-latency measurements. Existing browser security/adversarial suites retain XSS, scope, delayed responses and payment-recovery checks. Operations tests run against SQLite and PostgreSQL; PostgreSQL-layer counts include some endpoint tests that deliberately use their own SQLite database, as documented in the qualification report.

## Recorded qualification (2026-11-01)

Full installed-wheel suite:368pass,0fail,0skip, including52browser cases and21operations cases. Final PostgreSQL layer:173pass,0fail,0skip;147cases route through PostgreSQL fixtures,7explicit SQLite cases and19database-free adapter/parser cases. The stronger populated-upgrade check also passed separately on SQLite. All49package files match the installed artifacts. Two earlier application failures, one clock-sensitive throttle test and a disk-full PostgreSQL initialization are retained in the shared audit evidence; none are counted as passes. Current Chromium/axe emulation does not certify real devices.

## Deployment boundary

Honorato's approved menu/identity/media, actual hours/capacity, stock process and publication adapter must be reviewed with its owner before customer publication. The separate Honorato website was not changed. Broad security scanning, rate limits/abuse defenses, backup/restore/rollback drills, operational alerts, production staff provisioning and independent financial review remain M6/launch gates. No amount of frontend testing certifies every phone or real-money readiness.
