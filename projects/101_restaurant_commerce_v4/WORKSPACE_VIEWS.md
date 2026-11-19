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

Email, WhatsApp and SMS editing now share Campañas. Existing sender/template
configuration is native in Conexiones; bounded conversation history and test-only
human replies are in Campañas → Conversaciones. Unconfigured status is visible. A campaign's
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


## U07–U09: growth and channels in the shared workspace

Existing records/services remain authoritative; no schema, canonical business,
customer, campaign, queue or credential store was added.

- Clientes → Promociones/Recompensas reads the original catalogues. Creation
  remains the existing manager-only API; there was no old catalogue creation UI.
- Reportes → Comercio y clientes retains the original all-history currently-paid,
  completed-order arithmetic. It does not subtract partial refunds and is not the
  newer refund-adjusted report. Mixed-currency money is withheld rather than summed.
- Campañas → Mensajes manuales explicitly plans win-back through the original
  rule/planner, displays bounded old-outbox history and prepares the original
  WhatsApp handoff. Neither planning nor handoff means delivery. Current campaign
  WhatsApp withdrawal also blocks this older handoff; missing new permission rows
  retain the old verified-flag policy. The legacy outbox still is not automatic
  provider/frequency history (see CAMPAIGNS.md before live activation).
- Campañas now edits existing WhatsApp template/parameter and SMS campaigns,
  retaining promotion links, immutable revisions, exact approvals, schedule/expiry,
  cancellation, current eligibility and unknown outcomes. SMS segmentation/cost
  uses the full server-rendered message, including tracked links. Email's React
  Email templates/chassis and v1/v2 rendering paths remain unchanged.
- The collapsible operating panel shows local readiness and explicit business
  pause/resume. A pause can cause processed due jobs to be skipped; resuming does
  not revive them. A provider-test review freezes one recipient/version/cost limit
  but always has send_authorized=false. Saving or inspecting it never sends.
- Conexiones → WhatsApp/SMS uses explicit allowed sender fields (no secrets),
  templates, readiness and individually reviewed probes/imports. A saved sender
  digest detects stale edits; imported provider metadata is not resubmitted as
  editable fields. Non-test declarations remain unverified. Google/Instagram stay
  with their existing owner until U10; no fake native connection is claimed.
- Campañas → Conversaciones paginates original WhatsApp transport conversations
  and SMS inbound evidence. Transport identity is not a new customer match.
  Source/provider and acquisition times remain distinct. Test-only WhatsApp replies
  retain actor assignment, request-key dedupe, current sender/scope, 24-hour window,
  pause and opt-out checks. SMS has history and STOP/HELP tests, not invented replies.
- Demo campaign dispatch and demo reply dispatch are separate. Each processes only
  its selected business; stale-send cleanup no longer modifies another business.
  No mutation retries automatically after an ambiguous response. A separate GET
  checks saved state; browser Back restores provider selection.

New composition owners: frontend growth-workspace, channel-config, channel-inbox
and campaign-channel-controls; existing shell/tabs/list-detail/Base UI dialogs and
operations-ui command controls are reused bones. Geometry, surfaces, type and
status roles stay in growth-channels.css and the shared identity. New backend
modules provide bounded scoped projections, not a replacement execution engine.

Native workflow tests: test_growth_channels_workspace.py and
 test_growth_channels_workspace_browser.py. Existing campaign/WhatsApp/SMS,
React Email and shared workspace consumers remain release gates. Synthetic media,
contacts and transports qualify software only; real sending stays disabled.
No old staff entry page is retired by this slice. U10–U13 remain separate work.
