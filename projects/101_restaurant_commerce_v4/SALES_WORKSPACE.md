# Sales and readability iteration — 0.24.0

`/workspace/sales` adds orders to the same merchant shell as Customers. Search a
code or historical customer name, filter order/payment status, open an order,
accept/prepare/mark ready/hand over, or cancel
an unpaid order with a reason. Normal transitions take one click. Cash handover
requires explicit confirmation that the money was received; it uses the existing
cash payment authority. A read-only staff role can inspect without operation buttons.

Customers now uses 15px names/navigation, 14px contact text, darker secondary copy
and a shorter header. The shared template remains deliberately restrained, with
violet selection and useful status colors. No additional UI library was introduced.

## Run and review

```bash
npm ci --prefix frontend
npm run build --prefix frontend
PYTHONPATH=src python -m world_model.restaurant_commerce.sales_workspace_demo \
  --db /tmp/101-sales-review-new.db --port 8808
```

Open http://127.0.0.1:8808/workspace/sales. User `campaign.manager`, password
`synthetic campaign demonstration only`. Read-only user `sales.viewer` uses the
same explicitly fictitious password. This loopback launcher creates 80 customers,
30 demonstration orders and the existing example payment/refund. It sends no
messages and calls no delivery/payment provider. Use a fresh database to repeat
initial conditions; restarting preserves prior actions.

- Search `DEMO-201`: paid, discounted pickup. Accept → prepare → ready → handover.
- Search `DEMO-209`: cash pickup. Confirm amount, cash received and handover.
- Search `DEMO-205`: awaiting payment; cancel with a reason.
- `DEMO-213`: payment review blocks advancement.
- `DEMO-221`: courier delivery confirmation is required before completion.
- In Customers, search Mateo and inspect the retained 24,900 captured /5,000
  refunded /19,900 net example. Sales → Todos includes the same canonical order.
- Move between Customers/Sales, inspect details, use browser back, search and
  pagination. Phone layouts retain both payment and fulfillment information.

## Existing producer → contract → new consumer

| Owner reused | Consumer / minimum addition |
| --- | --- |
| `staff_routes.py`, `staff.py`: session, tenant membership, roles, CSRF | Existing shared shell; Sales reads require `operations.read`; writes use existing `operations.write`. |
| `models.py:Order`, `OrderItem`, `Payment`; `refunds.py` | `sales_workspace.py` projects paginated order list, counts, canonical detail and captured/refunded totals. No new schema, customer store, payment authority or order total. |
| `service.py:transition_order` | Its existing read-only validation is extracted into `validate_order_transition`, used by preview and rechecked by the existing locked mutation. Preview cannot change state. Quoted-delivery cancellation side effects remain only in the mutation. |
| Existing `PATCH /api/operator/orders/{id}` | `sales.tsx` preflights current state, sends expected version, preserves role/CSRF/business guards, and pauses after an ambiguous reply until explicit refresh. No blind mutation retry. |
| `customer_workspace.py`, existing asset middleware | `/workspace/sales` serves the same built application and CSP/cache policy. |
| Canonical historical contact snapshot | Conservative missing-name/phone defaults allow partial snapshots to render without inventing contact evidence or rewriting history. |

Read API: `GET /api/operator/restaurants/{business}/sales` accepts literal `q`
(order code or displayed historical contact name, max80),
`status=active|all|<order status>`, `payment_status=all|<order payment status>`,
`offset`, `limit`1–100. Search/filter run before count/pagination. A present contact
snapshot with no name does not borrow a current Customer name. SQLite/PostgreSQL
JSON extraction preserves that distinction.
Counts are for the business; list count is for the filter. Detail appends
`/{order_id}` and checks both IDs. Audience/customer data are not duplicated.
Paid/refunded money is grouped by currency and test/cash/provider source. The
order's discounted total is displayed once; captured payment minus confirmed
refunds is separate. COP retains the app's whole-peso accounting convention.
A provider label alone does not certify a live transaction or settlement.

## Native reservations and contact handoff — 18 November 2026

Sales now has Pedidos / Reservas views in the same shell. The reservation queue is
paginated, filters by state and uses the merchant timezone. Explicit date filters
apply to `starts_at`, not creation time; changing between order/reservation views
clears inherited dates. Detail supports the existing allowed transitions, with
confirmation for cancellation/no-show and an explicit state check after a lost
response. Viewer/finance roles cannot mutate or prepare contact messages.

`reservation_workspace.py` supplies `GET .../sales-reservations` and `/{id}` read
projections with counts, timezone, source fields and allowed actions. Existing
`PATCH /api/operator/reservations/{id}` remains the write owner. Its optional
`expected_version` checks a refreshed/locked current row before same-state handling;
the response exposes the existing ORM version. Legacy status-only callers remain
compatible. No schema change or cancellation-reason field was added.

`contact-handoff.tsx` reuses the existing order/reservation WhatsApp APIs under
`contact.read`. Omitting the destination uses the canonical contact snapshot;
existing explicit destinations are still accepted after phone validation. The UI
prepares a message, then offers a separate link to the WhatsApp composer. It sends
no message and creates no delivery claim. These were API-only capabilities at the
baseline, so the new controls are intentional additions.

The main Admin fallback remains: deliveries, settings, stock and financial
resolution are not replaced by this slice. Their absence must remain in the
consolidation ledger, not be hidden by removing the old page.

## Reused and extracted interface pieces (bones)

| Logical piece | Owner / editable boundary |
| --- | --- |
| Shell, business navigation, detail, table, search, filters, buttons, badges | Reused `frontend/src/main.tsx` / `style.css`; shared roles in `readability.css`. |
| API errors, cancellable reads, date/money formatters, avatar, empty/loading feedback | Extracted existing helpers to `frontend/src/ui.tsx`; no second client/auth system. Currency formatters are reused per currency. |
| Order summary, row/status, content/totals, next action, confirmation | New `sales.tsx` composition, with `sales.css` geometry and surfaces. It consumes canonical data/action eligibility. |
| Dialog semantics/focus, icons | Existing Base UI and Lucide, retaining notices. |

Geometry (`--workspace-width`, control height), type roles (`--text-body`, label,
caption), secondary color, surfaces and action placement can be changed without
altering evidence. The browser check changes the shared body role to18px, measures
actual navigation font size, and confirms identical API data. This is CSS-level
editability, not a new visual theme editor. The separate Astro review-parts owner
is not imported into this React app.

## Visual iteration contract

On **every** iteration: reopen the relevant saved references, render the actual
app, inspect desktop/mobile, identify a concrete issue, refine and inspect again.
References remain in the world-model `docs/product-design/references/2026-11-05`:
2/3 for navigation/shell,4 for metrics,5 for mobile. Reference1 remains the QR
invitation's character; this working order queue does not need decorative tiles.
Screenshots and measured roles are retained in the companion world-model review.

Pass1 revealed missing mobile payment context and needless confirmation of normal
order progress. Pass2 restores context and reserves dialogs for cash/cancellation.
Narrow-phone inspection then aligned summary numbers when labels wrap. Automated
axe/layout checks supplement actual visual inspection; they are not a taste score
or comprehensive accessibility certification.

## Checks

```bash
PYTHONPATH=src python -m pytest tests/test_sales_workspace.py \
  tests/test_operations_m5.py tests/test_customer_safety_m2.py \
  tests/test_financial_resolution_m3b.py tests/test_staff_m4.py \
  tests/test_customer_workspace.py
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=src python -m pytest \
  tests/test_sales_workspace_browser.py tests/test_customer_workspace_browser.py
# Existing fixture creates an isolated schema per test on a disposable local DB:
COMMERCE_PAYMENT_TEST_DATABASE_URL=postgresql+psycopg://USER@127.0.0.1:55446/postgres \
  PYTHONPATH=src python -m pytest tests/test_sales_workspace.py tests/test_customer_workspace.py
```

The browser suite tests normal transitions, cash confirmation, cancellation,
version conflict, a server-accepted PATCH whose response is lost, read-only role,
pagination/deep links/back/scroll, business switching,320/390/768/1440/1920px
layouts, and automatic WCAG A/AA checks. Existing Customers tests still exercise
signup QR, real signup, keyboard/error paths and stale business responses.

For repeatable visual evidence, run `python scripts/audit_sales_workspace.py
--url http://127.0.0.1:8808 --out /tmp/101-sales-visual`. It captures real desktop,
phone, detail and cash-confirmation states, checks axe violations, and records
computed type sizes and solid-background contrast. Inspect the resulting images
against the reference pack; the script cannot judge appearance.

The existing mobile lab supports Sales with `python scripts/measure_customer_workspace.py
--area sales --url http://127.0.0.1:8808 --out /tmp/101-sales-speed.json`.
It reports three cold runs, first painted row, LCP, click feedback, real detail
completion and back restoration. See CUSTOMER_WORKSPACE.md for the profile;
Sales uses the 31-order fixture, Customers uses 10,000 synthetic contacts.

## Next boundary

Campaigns is the next shared-interface workflow. The existing `/campaigns`,
`/admin` operations and finance capabilities remain available. This first Sales
slice does not replace courier configuration, dispatch or financial resolution;
blocked actions explain the relevant condition, with an operations link for the
existing workflow. No deployment, live sender activation or provider test is
implied by the local demonstration.
