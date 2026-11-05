# Customer workspace — first shared UI slice

`/workspace/customers` is the working merchant directory. Version 0.23.0 adds
custom typography, warm neutral surfaces, violet selection, a compact table,
customer details and signup tools. Base UI supplies dialog/focus behavior; it is
not the visual theme. The frontend is React/TypeScript, built with Vite and served
by the existing FastAPI application. There is no production Node service.

The standing reference pack remains in the world-model checkout at
`docs/product-design/references/2026-11-05/`. References 2/3 guide the shell and
navigation; 1 guides the QR invitation's character; 5 guides the phone layout.
The original screenshots are private design references, not shipped app assets.

## Run locally

```bash
# From projects/101_restaurant_commerce_v4; use Python with project test/browser extras.
python -m pip install --no-build-isolation -e '.[test,browser]'
npm ci --prefix frontend
npm run build --prefix frontend
PYTHONPATH=src python -m world_model.restaurant_commerce.customer_workspace_demo \
  --db /tmp/101-customers-review-new.db --port 8806 --customers 80
```

Open `http://127.0.0.1:8806/workspace/customers`.
User: `campaign.manager`. Password: `synthetic campaign demonstration only`.
All contacts, memberships and money in this launcher are fictitious. Codes are
shown locally; no messages, provider requests, subscriptions or deployment occur.
QRs contain the configured origin. A loopback QR is for this computer's local
review, not a public signup link usable from someone else's phone.
Use a fresh database to choose another fixture size; restarting preserves it.

Review: search `Mateo`, open the first result, inspect COP24,900 captured /5,000
refunded /19,900 net, then go back. Search and scroll survive. Open **Invitar
clientes**, download PNG/SVG or copy the link. Follow the link, use email signup,
and search for that address in the directory. Phone signup remains available.

## Integration map

| Producer / owner | New consumer |
| --- | --- |
| `staff_routes.py` session, role/business membership, CSRF | `frontend/src/main.tsx`; one login; switcher only for multiple authorized businesses. `slug` is added to the existing identity response for correct storefront links. |
| `models.py:Customer` | `customer_workspace.py` bounded search/list/detail, existing IDs, no new contact store. |
| `customer_signup_models.py` account + membership | Registration/source details; missing optional tables stay unavailable. No signup-derived marketing permission. |
| `campaign_models.py:ContactPermission` | Read-only marketing permission state, channel, scope and timestamp. A grant is not dispatch eligibility. |
| Canonical `Order`, `Payment`, `refunds.py:PaymentRefund` | Confirmed captured/refunded sums by currency and test/provider scope; at most one paid-order count per group. Full refunds are not subtracted again as partial refunds. No writes or duplicate totals. |
| `customer_signup_routes.py` | Existing scoped metadata, PNG/SVG downloads and public phone OR email signup. |
| `api.py` CSP/assets/GZip | Built hashed `/workspace-assets/assets/*` with immutable caching; HTML/API no-store. Existing strict CSP preserved using Base UI `CSPProvider.disableStyleElements`. Middleware now tolerates mounted ASGI endpoints. |
| Existing `/admin`, `/campaigns`, `/connections`, storefront | Working navigation preserves selected business through `staff.js`; existing interfaces remain during migration. |

There is **no new database schema/migration**: all new data access is a read
projection. Existing optional signup/connection schema upgrades still apply to
older installations. The fixture uses the existing application initializer.

`GET /api/operator/restaurants/{business}/customers` accepts literal `q` (max120),
`kind=all|registered|email|phone`, `offset` and `limit` (1–100). Stable order is
creation descending then canonical ID. Percent and underscore are literal search
characters. `GET .../customers/{id}` checks both business and ID, returns the most
recent20orders plus all-time confirmed payment totals. APIs enforce `growth.read`
under existing role policy; browser state is not authorization.

Purchase totals mean **associated canonical payments**, not verified personal
spending, settled funds or profit. Guest-order contact matching does not prove
who purchased; each recent order shows retained identity verification. Simulated
payments are separated. Other provider observations are labeled as such, not
assumed live (a provider may itself be in sandbox). COP uses this application's
whole-peso accounting; other currencies retain their canonical minor units.

The new screen is read-only except existing session/signup workflows. Permission
editing, customer merging and bulk marketing actions are outside this slice.

## Verification

```bash
PYTHONPATH=src python -m pytest tests/test_customer_workspace.py \
  tests/test_staff_m4.py tests/test_customer_safety_m2.py
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src python -m pytest \
  tests/test_customer_workspace_browser.py tests/test_signup_browser.py
# Optional disposable PostgreSQL, isolated test schema per existing fixture:
COMMERCE_PAYMENT_TEST_DATABASE_URL=postgresql+psycopg://USER@127.0.0.1:55446/postgres \
  PYTHONPATH=src python -m pytest tests/test_customer_workspace.py
```

With frontend dev dependencies installed, run
`python scripts/audit_customer_workspace.py --url http://127.0.0.1:8806 --out /tmp/101-customer-accessibility`
for the actual directory, detail, QR and mobile WCAG A/AA automated checks.
This supplements keyboard and visual review; it is not a complete accessibility certification.

The browser suite exercises real HTTP, deep links/reload, query/scroll/focus
restoration, phone-sized layout, keyboard entry/escape, empty/error/retry,
PNG/SVG downloads, email signup returning to the same directory, multiple
businesses and a deliberately delayed old-business response. The existing signup
suite verifies the phone path. No mock screenshots substitute for these journeys.

Build outputs and notices ship in the Python wheel; consuming installations need
no Node toolchain. Rebuild before packaging after frontend edits. Pinned package
versions and lockfile are in `frontend/`; runtime licenses are retained in
`frontend/licenses` and included with the built assets. `frontend/public` carries
the distribution notices, not user reference screenshots.

## Repeatable speed measurement

```bash
PYTHONPATH=src python -m world_model.restaurant_commerce.customer_workspace_demo \
  --db /tmp/101-customers-speed-new.db --port 8807 --customers 10000
# In another terminal:
python scripts/measure_customer_workspace.py --url http://127.0.0.1:8807 \
  --out /tmp/101-customer-performance.json
```

The script records browser/OS, dataset count and three fresh-cache runs:390×844,
4× CPU slowdown,150ms latency,1.6Mbit/s down,750Kbit/s up. Login is established
before the run; this is a returning authenticated user's first workspace visit.
Useful content means the first customer row painted. LCP is separately observed.
Feedback is two animation frames after the click; detail completion waits for
real detail content. Back restoration is recorded separately. These are local lab
measurements, not real-device or field-p75/INP claims. Bundle budgets use gzip;
fonts are counted separately. The baseline before formatter reuse is retained in
the world-model review evidence alongside the optimized run.

## Remaining product work

The user reviewed this slice and requested better readability. Version0.24.0
implements that iteration and the shared [Sales workflow](SALES_WORKSPACE.md).
Campaigns is next; its existing route remains operational. Home and cross-functional
Reports are deferred; we do not relabel the legacy growth page as the new Reports.
Campaign results stay with campaigns and sales with Sales. Presence has explicit
Website and Google destinations; Social is marked upcoming. No command palette,
forced assistant, fake overview metrics or additional provider dashboard is added.
Existing signup verification and Google/Meta provider activation requirements are
unchanged; the local UI does not prove live provider readiness.
