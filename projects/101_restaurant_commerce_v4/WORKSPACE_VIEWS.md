# 101 Workspace: identity, Inicio, Campaigns and analytics example

## Shared staff entry — 18 November 2026

`workspace_access.py` supplies one `/workspace/login` entry for the eight legacy
staff pages and normal `/workspace` routes. It runs inside the existing security/
reliability middleware; redirects retain its CSP/referrer/cache headers. Public
customer/token/OAuth/webhook paths and JSON APIs retain their separate policies.

`GET /api/staff/entry` resolves an allowlisted local return destination under the
existing staff session. It maps legacy `business_id` to workspace `business`,
requires explicit selection for multiple memberships, and never silently substitutes
another business for an inaccessible one. Known selection/filter/date query state
survives login; external URLs, recursive `next`, secrets, fragments and duplicate
parameters do not. No credentials enter return state or local storage.

The existing cookie, password policy, development-only 101 alias, roles, CSRF and
API 401/403 contracts are unchanged. Logout broadcasts a credential-free notice
across tabs; refresh generations prevent old identity replies restoring a logged-out
view. Legacy navigation links carry the selected business while those tools remain
in service. Unmigrated pages are not redirected to incomplete replacements.

Native Sales reservations/order-filter/contact changes are described in
`SALES_WORKSPACE.md`; native finance/delivery/settings and daily reports are described there too.
Growth/channel moves remain open; legacy retirement retains its separate gate.

The shared identity lives in `../../packages/101-workspace-identity/`:
`IDENTITY.md`, `tokens.css`, and `decisions.json`. The frontend imports the actual
CSS package. `/workspace/identity` is its running sample sheet. Every requested
change to dashboard design updates this same identity and is reviewed against the
seven retained originals in the shared101repository. Merchant public brands remain
separate. See `docs/product-design/workspace-views-review.md` there for rendered evidence.

## Run locally

From this project, with its Python dependencies and frontend dependencies installed:

```sh
npm --prefix frontend run build
PYTHONPATH=src python -m world_model.restaurant_commerce.workspace_demo --db /tmp/101-workspace-demo.db --port 8809
```

Open `/workspace/home`. Temporary shortcut: **101 / 101**. This aliases the
existing demo manager session only in `workspace_demo.app_for_demo`; remove its
`workspace_demo_login` assignment to retire the shortcut. No account is added and
normal application startup does not enable it. Original demo-only login: `campaign.manager` /
`synthetic campaign demonstration only`. `sales.viewer` uses the same fictitious
password and cannot change campaigns. All customers, orders and payments here are
fixtures. The campaign clock is fixed to November3,2026,10:00 in Bogotá; the calendar
picker uses today's Bogotá date. For reproducible fixture results choose Nov3.
No credentials, paid calls or real sends are used. Reusing a database preserves
edits, withdrawals, cancelled campaigns and orders; choose a new path to restart.

Routes: `/workspace/home`, `/workspace/campaigns`, `/workspace/analytics`,
`/workspace/identity`, existing `/workspace/customers` and `/workspace/sales`.
Legacy operational/channel configuration routes remain available.

## Integration map

| Entry / piece | Existing producer → consumer | New responsibility |
| --- | --- | --- |
| Shared shell | `staff.py`, existing session/CSRF/business scopes → `frontend/src/main.tsx` | Navigation, retained creation-date filters, clear selected objects on business switch |
| Inicio | Canonical Customer/Order/Payment/PaymentRefund, CampaignRevision, BusinessConnection → `workspace_overview.py` → `HomeView` | Scoped read projection; no new canonical records |
| Campaigns | `campaign_routes.py` → `campaigns.py`, permissions/outbox/adapters/renderer/tracking/payment attribution → `campaign-workspace.tsx` | Bounded list projection, human email editor, saved preview, fixed approval/scheduling/cancellation/report UI |
| Date filter | `workspace_period.py` → overview, customer and Sales list queries | Inclusive Bogotá calendar dates, exclusive next-day UTC bound, maximum366days |
| Analytics | Deterministic local fixture → `AnalyticsView` | Explicit example, no provider/API collector, persistence or revenue writes |
| Identity | `packages/101-workspace-identity/tokens.css` → existing styles and new compositions | Portable roles and living guide; actual sample sheet and token-consumption proof |
| Local rehearsal | Existing campaign/customer/Sales seeders, fake transport and phone/email verifier → `workspace_demo.py` | Explicit composition, fixed campaign clock and existing signed simulated payment authority |

No migration, second customer list, order-total store, queue or payment authority
was introduced. The analytics example is not connected to Google Analytics or a
website tracker. Counts are fictional and never enter Inicio or campaign reports.

## Accounting and limits

Inicio counts customers/orders by creation date. Its money row sums captured
payments less accumulated refunds for those orders, separately by currency and
simulation/cash/provider scope. It is a cohort view, not bank settlement or profit.
COP follows the existing whole-peso contract. Fully refunded payments are counted
once; partial refunds use existing refund records. Attention items are current,
regardless of the selected period; recent activity shows at most six recorded
customer/order/current-revision entries. It does not invent publication events.

The campaign list filters by creation date; a campaign report explicitly covers
the entire campaign. Simulation approvals cannot authorize real messages. Provider
acceptance, delivery, missing receipts, unknown outcomes, visits and attributed
sales remain distinct. The demo dispatch button processes due work for the selected
business, as labelled; other campaigns may share its contact-frequency limit.

Email editing is the migrated path. Existing WhatsApp/SMS adapters and setup remain
in their existing advanced screens. Unconfigured status is visible. A campaign's
customer picker uses the existing metadata cap of500contacts; larger audience
selection is a subsequent API/UI improvement. Browser image loading is not read
proof. Read-only roles can inspect but cannot approve or schedule.

## Repeatable browser rehearsal

Create a campaign, choose the synthetic persona0 and persona1 contacts, write copy and terms,
save and inspect the HTML/plain-text preview. Check the exact-version review box,
approve, then schedule at the displayed test clock. Use a pending delivery's
unsubscribe link before dispatch; process pending work and simulate a receipt.
Follow the remaining recipient's tracked link into the real test storefront,
place a test order and inspect the attributed report. Tests additionally submit
a signed partial refund twice and assert one refund adjustment.

```sh
PYTHONPATH=src python -m pytest -q tests/test_workspace_overview.py tests/test_customer_workspace.py tests/test_sales_workspace.py tests/test_campaigns.py
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src python -m pytest -q tests/test_workspace_views_browser.py tests/test_customer_workspace_browser.py tests/test_sales_workspace_browser.py
python scripts/measure_workspace_views.py --url http://127.0.0.1:8809
```

The browser suite runs real local HTTP and built assets, performs checkout and
refund verification, tests permission withdrawal and revision invalidation, checks
business switching/date drill-through, and checks12desktop/mobile accessibility
states. It also changes real CSS tokens and verifies appearance changes without
changing data. Build the frontend before running it. No full historical-suite
claim is implied. Installed-wheel and disposable PostgreSQL qualification use the
existing `security/qualification_plugin.py`.

Next: review the visible compositions with the owner; replace the analytics fixture
with an explicitly scoped website-measurement source when authorized. Keep channel
readiness/live provider tests separate from this dashboard delivery.

## Combined loyalty preview

For all implemented areas together, use the existing loyalty fixture as an extension
of the shared app (same temporary101/101login, Campaigns transport, signup and Sales):

```sh
PYTHONPATH=src python -m world_model.restaurant_commerce.loyalty_workspace_demo --db /tmp/101-workspace-demo.db --port 8806
```

Open Inicio or `/workspace/customers?view=loyalty`. This applies existing loyalty
migrations to the local fixture and seeds synthetic examples once; restarts preserve
operator edits. Configuration is enabled here; execution, assignment and Stage7
analytics remain disabled. The normal production startup is unchanged.
