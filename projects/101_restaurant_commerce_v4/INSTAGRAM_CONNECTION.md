# Instagram connection and resumable photo intake — 6 November 2026

Working software with mock-transport qualification. **No live Instagram account has
been connected or imported.** No public deployment or DNS changes were performed.

## Shared 101 address

User confirmed ownership of `unocerouno.co`. Target workspace: `app.unocerouno.co`.
Register one exact redirect URI for the 101 app:

`https://app.unocerouno.co/connections/instagram/callback`

Every tenant uses that same callback. A one-use OAuth state binds the originating
staff session, business connection, provider and generation; it does not trust a
business ID from a returned URL. Owners authorize their own professional accounts.
Instagram Login authorizes one account per grant, so the confirmation screen shows
that account; it does not invent a multi-account Facebook Page picker.

Read-only DNS check: Porkbun authoritative nameservers; `app.unocerouno.co` CNAME
`pixie.porkbun.com`. The connected Cloudflare account returned no matching zone.
No Porkbun credentials were present in the documented environment/files; plugin
lookup found no matching available connector. This is a parking destination, not
proof of a deployed workspace. Public HTTPS requests did not establish a working app.
Do not route public traffic to the local101/101 synthetic demo.

## Configuration path

Deploy the existing FastAPI application and its persistent database behind HTTPS
with real staff authentication; disable demo aliases and protect credentials. Point
only the app subdomain at that chosen deployment. Existing root DNS/email remains
outside this change. Hosting destination/access is still needed; no paid hosting
was provisioned and no nameserver migration is implied.

In Meta's app settings, register the exact callback above and enable the intended
Instagram Login access. Verify the professional account/tester or app-review path.
Use the read permission `instagram_business_basic`; no publishing or messaging
permission is requested here. Exact fields must be confirmed by actual account reads.

Run `python scripts/configure_social_instagram.py` locally to enter the app secret
hidden from output. It writes a new0600 private config, refuses overwrite, and creates
an Instagram-specific Fernet key without replacing the Google connector's key:
`~/.config/101-world-model/instagram-social.env`. Never commit or paste it into chat.
Required settings:

- COMMERCE_INSTAGRAM_CONNECTION_ENABLED=1
- COMMERCE_INSTAGRAM_CLIENT_ID
- COMMERCE_INSTAGRAM_CLIENT_SECRET
- COMMERCE_INSTAGRAM_REDIRECT_URI
- COMMERCE_INSTAGRAM_API_VERSION (explicit supported version from Meta app)
- COMMERCE_INSTAGRAM_CONNECTION_KEY

Load that file server-side into the hosted service, never the frontend. Do not enable
until the exact HTTPS callback works. Disable callback query-string access logging;
the callback bridge immediately removes its code/state from browser history. Connect
from the intended business workspace, confirm the returned username, then import.

## Actual implementation and limits

Reuses `connections.py`, encrypted credentials, authorization records, generation
fencing, durable jobs, staff CSRF/permissions and tenant IDs. Generalized provider
selection and scoped worker/maintenance queries prevent Google and Instagram jobs
from consuming each other's records. Google policy/cache behavior remains separate.

New adapter: `connection_instagram.py`; routes: `instagram_routes.py`; UI:
`frontend/src/social-instagram.tsx`. Existing Connections and sidebar link to it.
One read import has at most2pages×20posts and5count probes (7requests); existing
worker retries at most3attempts. It reconstructs fixed Graph paths from validated
IDs/cursors rather than following provider next URLs. Automatic periodic sync is off.

Native timestamps and precision, normalized UTC, original offset, observation time,
format, caption, metric definition and missing reason are retained. Day-only values
do not invent minutes; business-local timezone and capture time remain unconfirmed.
Likes/comments are optional field probes; missing/denied values stay null, real zero
stays zero. These are current lifetime counts, not historical24h outcomes. Reach,
saves, shares, watch time, search analytics and orders are **not implemented here**.
No claim that a timestamp or visual treatment caused a result. Partial reads remain
visible. Normal social listing now consumes the actual scoped cached baseline.

This first adapter conservatively uses short-lived grants (at most1hour) and reports
expiry/reconnect. Long-lived exchange/refresh still needs implementation and live
qualification before claiming ongoing unattended sync. No remote revocation is
claimed: disconnect immediately removes local token/data/jobs, with an instruction
to remove provider access in Instagram settings. Retained snapshots expire after1day.

## Uploads

`social_uploads.py` adds one additive table, `social_uploads`. Bounded12MiB JPEG/PNG
files,256KiB sequential chunks, offsets/hashes, safe retry/resume, one final asset per
completed upload,3pending uploads per tenant,1day expiry, cancel and an existing-asset
selector. Preserves originals; no client-side downsize required. Unfinished expired
uploads are cleaned on the next intake for that tenant; scheduled global cleanup is
still needed for abandoned tenants. Video files remain unsupported.

Fresh databases register the table. Existing databases require offline
`social_uploads.upgrade(engine)` and `connection_models.upgrade_connections(engine)`
after backup/stopping writers. The isolated local demo was stopped/backed up using
SQLite's backup API, migrated and restarted. Rollback: prior application build with
new tables retained, or restore the pre-upgrade backup offline. No canonical production
DB migration or PostgreSQL qualification. Private demo backup:
`/tmp/social-production-before-connection-upgrade.db`.

## Evidence

New tests: `test_instagram_connections.py`, `test_social_uploads.py`; existing Google
connection/social production regressions. Cover provider/tenant/session fencing,
denial/replay, encrypted token/non-leakage, selected-account mismatch, bounded hostile
pagination, real zero versus unavailable metric, source timestamp, expiry/disconnect,
large-file interrupted upload/retry, offsets, partial completion and duplicate finalization.
Providers are mocked; this does not establish real Meta permissions or field support.

Actual browser test uploads a roughly1.55MB synthetic photo, intentionally interrupts
the second chunk, resumes using the retry button, edits/approves/downloads the rendered
package. Saved evidence: World Model `artifacts/social-connections-20261106/`.
Desktop1440/mobile390 inspected; final390px document width equals viewport.
Existing identity/shell/buttons reused; choice/action and missing-data states remain explicit.

No paid generation, publication, customer messages or live provider probes. Remaining
master-plan work includes real authorization, approved Honorato facts/material,
layered designs, learned voice/examples/pairwise judgment, durable render economics,
full source retention/deletion and video. Nothing here declares Stage1 finished.

## Documentation consulted

Meta's official collection:
https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
It distinguishes Instagram Login/professional accounts and permissions. Direct Meta
business-login documentation returned429 and insights documentation was inaccessible
on this run. Adapter requests are therefore explicitly not live-validated; broad
collection documentation is not evidence for every metric or permission.
