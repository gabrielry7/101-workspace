# Owner Connections — first milestone

Google Business Profile is the first connector. The app owns business selection,
authorization binding, selected location, connection state and synchronization.
It reads Google listing data, the latest review page (up to 50), and daily website
clicks, call-button clicks and direction requests. No Google writes or replies are
implemented. Call clicks are not calls or sales. Missing metrics are unavailable,
not zero. Other platforms are visibly pending; WhatsApp remains configured in the
existing campaign subsystem.

## Integration map

| Producer → boundary → consumer | Reused / added |
| --- | --- |
| Named staff → `api.py::scoped_staff`, `staff.py` → business connection routes | Existing authority; `settings.write` for changes, `growth.read` for dashboard |
| Owner consent → `connection_routes.py` → `connections.py` | New session-bound state, PKCE, single-use exchange and location selection |
| Google OAuth and APIs → `connection_google.py` → connection worker | New real read adapter and explicit no-network fake adapter |
| Durable jobs → existing SQLAlchemy engine / in-process worker pattern → cached dashboard | Three additive tables in `connection_models.py`; no separate service |
| `web/growth.html` → `/connections` → listing/reviews/daily-value UI | Existing staff UI scripts; new responsive page |
| Existing Customer, orders, payments, campaigns | Unchanged authorities; Google interactions never create paid sales |
| World-model `local_search/workbench_records.py` | Existing metric vocabulary informed labels; no claim of live data ingestion into its CSV workbench |
| World-model Instagram evidence archive | Separate acquisition subsystem; no official owner OAuth connection is claimed |

Google API content is deliberately **not exported to the permanent evidence
archive, Truth or the metric-import workbench**. The existing business ID is used;
provider accounts and locations keep their external IDs. Explicit owner selection
is an association for this connection, not a canonical business identity merge.

## Repeatable local demo

From `projects/101_restaurant_commerce_v4`, with package test/browser dependencies:

```sh
PYTHONPATH=src python -m world_model.restaurant_commerce.connections_demo \
  --db /tmp/101-connections-demo.db --port 8804
```

Open `http://127.0.0.1:8804/connections`. Sign in with fixture username
`campaign.manager`, passphrase `synthetic campaign demonstration only`.

1. Connect Google; the next screen explicitly says it is a local simulator.
2. Allow the simulation, select Honorato's fictitious location, confirm.
3. The durable worker retrieves a fictitious listing, one review/reply and daily
   values 12 website clicks, 4 call clicks, 7 direction requests.
4. Reload: the selected connection and cached data survive.
5. Disconnect: local cached content disappears immediately; the worker revokes
   access, then the status becomes disconnected.
6. Reconnect and choose the second fictitious location; or cancel consent.

The adjacent `.demo-key` is generated once with mode0600; retain it with the demo
DB for restart tests. It is not a production secret and must not be committed.
The demo sends no Google requests, SMS, email or other external messages.

## Existing database migration

Stop writers, take a backup, then run:

```sh
COMMERCE_DATABASE_URL=sqlite:////absolute/path/commerce.db \
  PYTHONPATH=src python -m world_model.restaurant_commerce.maintenance \
  upgrade-connections --offline
```

PostgreSQL URLs are also supported. The migration creates only the three new
connection tables and is idempotent. New databases include them; existing databases
are not migrated on startup. Enabling a connector against an old schema fails with
a specific migration instruction. Unconfigured apps continue to serve a truthful
unconfigured Connections page.

## State and worker contract

`disconnected → authorizing → exchanging → discovering → choose_location → syncing
→ connected/partial`.

Denial, reconnect-required, sync-error and disconnecting are separate outcomes.
OAuth state is hashed, PKCE material encrypted, expires after ten minutes, and is
bound to the staff session and connection generation. The browser callback uses a
same-origin completion POST because existing staff cookies are SameSite=Strict.
It clears code/state from browser history before submission. Staff authentication
commits its heartbeat: authenticate **before** acquiring the connection lock;
consume the grant with an atomic conditional DELETE. Concurrent callbacks cannot
exchange the same authorization twice.

There is one durable job per connection, saved in the same transaction as state
changes. Workers claim with a write lock, five-minute lease, generation and random
lease identifier. Network calls happen outside the database lock. Stale workers
cannot overwrite a newer selection or restore disconnected data. Expired claims
repeat bounded read operations from the beginning, not resumable per-page cursors;
there are no additive metric writes. Discovery pages are bounded, cycle checked,
and capped at20accounts/500locations. Oversized accounts receive an explicit error.

Network/429/5xx read failures get at most three attempts with30/60second backoff.
An uncertain code exchange is never automatically repeated: reconnect is required.
An exchange already in flight briefly rejects reconnect/disconnect (409), preventing
an acquired token from being orphaned by a simultaneous local disconnect. A process
crash after Google accepted a code can still require a new authorization; unknown
remote grants should be removed in Google's account permissions.

Live synchronization runs approximately every12hours while the app/worker runs.
Manual refresh has a60second cooldown after a successful sync. An unavailable
section produces a partial snapshot with an explicit reason; unrelated successful
sections remain visible. No listing mutations, review replies or messaging exist
in this adapter.

## Storage and disconnect

Fernet encrypts access/refresh tokens and PKCE material. A persistent key comes
from the existing environment-based secret-loading mechanism; never put it in Git.
The first version has one active encryption key; rotation requires a planned
re-encryption migration, not replacing the key and losing access.

Cache original response objects for at most24hours, replacing them on sync. Do not
store historical aggregates. Reads hide expired data even when the worker is down;
the worker removes it physically on its next cycle. Keep the worker operational
for retention; backups require the same deletion/expiry policy before activation.
External resource IDs remain as connection configuration. Google's current content
policy, including its30day maximum for permitted temporary content, governs reuse.

Disconnect deletes cached content, selected resource and active connection tokens
immediately, cancels prior work, and enqueues revocation with encrypted material.
Failed revocation remains visibly pending; no data sync resumes. After seven days,
remaining revocation material is removed and the UI instructs the owner to revoke
101 in Google account settings. Successful/already-invalid revocation clears it
immediately. Google revocation can affect the Google user's grant to this app,
including other links using the same grant; do not describe it as location-only.

## Real Google activation — not exercised by this milestone

The adapter exists, but local fixtures and HTTP mocks are not a verified Google
connection. No provider account was connected, deployed or modified here.

Configure an approved Google project and OAuth web client; enable Account
Management, Business Information, legacy review and Performance APIs as applicable.
Configure the exact HTTPS callback, consent-screen/app verification requirements,
privacy/deletion disclosures and authorized pilot owner. Requesting project access
and the owner authorizing a location are separate steps.

Inject these server-side values using the existing secret mechanism:

- `COMMERCE_GOOGLE_CONNECTION_ENABLED=1` — explicit real-adapter activation.
- `COMMERCE_GOOGLE_CLIENT_ID`, `COMMERCE_GOOGLE_CLIENT_SECRET`.
- `COMMERCE_GOOGLE_REDIRECT_URI=https://YOUR_HOST/connections/google/callback`.
- `COMMERCE_CONNECTION_KEY` — persistent Fernet key (32random bytes, urlsafe base64).

The default is unconfigured, never a simulator fallback. Google currently uses
`https://www.googleapis.com/auth/business.manage`; it is broader than this app's
read-only feature set. Explain the scope to the owner. Tokens never enter browser
responses. Configure proxy logs to omit OAuth query strings; the demo disables
access logging. Do not substitute the workspace's Google Places API key for OAuth.
A configured client is not proof of app approval, location access or provider health.

Before release, exercise one authorized real read-only owner flow and verify exact
location/account binding, token refresh, field availability, revocation behavior,
retention in backups and operational quotas. No live account test is claimed here.

## Verification commands

```sh
PYTHONPATH=src python -m pytest tests/test_connections.py
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src \
  python -m pytest tests/test_connections_browser.py
COMMERCE_PAYMENT_TEST_DATABASE_URL=postgresql+psycopg://USER@127.0.0.1:55446/connections_test \
  PYTHONPATH=src python -m pytest tests/test_connections.py
```

The optional PostgreSQL fixture creates isolated schemas. Browser tests serve the
real app over HTTP. The cross-site-return case intercepts a fake Google hostname
inside Chromium and makes no external HTTP call. Installed-package qualification
also runs existing signup and campaign consumers; native receipts record outcomes.

## Next milestone

Official Instagram/Facebook owner onboarding using this lifecycle, with an exact
login-route/scope/capability matrix, provider callbacks where required, revocation
and deletion handling, and fixture/live proof kept distinct. Search Console and
website measurement follow. WhatsApp's existing adapter remains the sending owner;
its business onboarding can later consume the connection boundary without copying
campaign or customer logic. TikTok and advertising/POS remain later connectors.

## Provider references checked 2026-11-05 UTC

- https://developers.google.com/identity/protocols/oauth2/web-server
- https://developers.google.com/my-business/content/prereqs
- https://developers.google.com/my-business/content/policies
- https://developers.google.com/my-business/reference/businessinformation/rest/v1/accounts.locations/list
- https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list
- https://developers.google.com/my-business/reference/performance/rest/v1/locations/fetchMultiDailyMetricsTimeSeries
