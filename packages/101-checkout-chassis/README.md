# Customer checkout chassis

Owner: `@101/checkout-chassis`; normal consumer:
`restaurant_commerce/web/index.html` + its existing `index.js` controller.
The same component serves the original checkout, a neutral coat and a clearly
fictional warm example. The example is not an approved Honorato identity.

`/workspace/website` is the authenticated editor in the existing workspace.
It previews the actual public checkout, edits independent design properties,
imports/exports JSON and applies a versioned business-scoped appearance.
The preview blocks order/reservation/delivery/payment writes, does not touch
customer draft/recovery storage and suppresses controller analytics events.
It retains normal quoting and existing form behavior for visual inspection.

## Separation and reuse

| Layer | Owner / contract |
|---|---|
| Products, quoted totals, availability, pickup/delivery, customer fields and consents | Existing commerce API, `index.js`, services and records. No duplicate cart, order, customer or payment implementation. |
| Checkout structure | Existing real DOM/IDs and handlers; extracted totals, fulfillment/contact/extras wrappers. `checkout-anatomy.js` labels reused/new pieces, parents, text hierarchy, fields, actions and state surfaces. |
| Layout and geometry | `contract.json`: sidebar/stacked, page maximum, form width, column gap and insets. Responsive collapse remains automatic. |
| Color roles | Explicit text, secondary text, field/card/background/border, primary action/label, secondary fill, focus and feedback roles. |
| Typography | Independent heading/body families and heading/body/label/action sizes. Neutral Inter resolves from the shared typography source; actual font file and license already ship with the workspace. New brand fonts require an explicitly registered, licensed/self-hosted family. Arbitrary CSS/font URLs are not accepted. |
| Surfaces | Shared `boneProfile` and `applyBoneProfile`: independent container/product/fulfillment/contact/extras/button/confirmation/dialog radius, padding, border, fill, margins and shadow. The checkout projection excludes arbitrary CSS and opacity. |
| Actions | Original handlers, enabled/disabled state, idempotency, live quote, recovery and provider URLs. Appearance can style controls; it cannot change their destination, price, consent or behavior. |
| Measurement | Existing `component-preview/measure.js` and `content-bounds.js`, pinned in `vendor/`. Editor only: actual visible DOM/CSS geometry and bounded solid-color contrast. Export labels the viewport/scope and limitations. No universal quality score. |

Each logical and leaf part is in `checkout-anatomy.js`. Source evidence and control
values remain their original owners. The editor inventory includes hidden dialog
and confirmation roles; visible measurements do not claim those are open or measured.

## Contract and reproduction

`contract.json` is authored. `build.py` resolves the shared neutral family, emits
`checkout-contract.js`, and copies browser modules/styles/validators into the Python
wheel's `web/` directory. Only relative vendor import paths are rewritten. The
frontend imports the authored package; the public page imports that same built
browser module. Python validates the same packaged contract and a constrained
projection of shared surface properties. Run:

```sh
python packages/101-checkout-chassis/build.py
python packages/101-checkout-chassis/build.py --check
node packages/101-checkout-chassis/test.mjs
```

Pinned upstream owner files live in the World Model repository:
`packages/site-runtime/src/bones/{contract.js,types.js,typography.json}` and
`packages/component-preview/{measure.js,content-bounds.js}`. See `vendor/manifest.json`
for exact hashes. Do not fork these primitives to add checkout facts or logic.
The current reference source is commerce `d230f7d`; no third-party design or new
font/media/dependency/license was imported.

A profile has only `schema_version`, `layout`, `geometry`, `typography`, `colors`
and `bones.surfaces`. No copy, products, asset URLs, business/customer IDs, offer
values, payment settings, consent defaults or executable strings belong in it.
`checkoutProfile()` validates before changing an existing DOM, so invalid imports
preserve the current draft. Geometry and surface values have bounded ranges.
A valid profile still needs inspection for text wrapping and brand fit.

The editor export envelope is `101-checkout-export-v1`, containing `profile` and
optional visible `measurements`. Import applies only the validated profile to a
draft. Applying to customers is a separate explicit save. A stale revision returns
409 rather than overwriting another editor's changes. Unsaved editor state is
local to that mounted business view; reload/business change discards it.

## Storage, migration and rollback

One additive table: `restaurant_checkout_designs`, keyed by the existing business
foreign key, with current revision, design JSON and private last-actor ID. Existing
staff audit records authorization/commit. Public projection contains only business,
revision and visual profile. No new canonical business or brand/facts database.

Fresh databases include it. Existing installations require an explicit offline
`checkout_design.upgrade_checkout_design(engine)` after backup; startup does not
silently install it. Before installation, public checkout retains its source coat;
the editor reports unavailable storage and save returns503. The upgrade is
idempotent and changes no existing rows. SQLite and disposable PostgreSQL have
executable migration/save/conflict proof.

Rollback: disable new appearance writes or restore retained source/assets while
keeping the new table for forward recovery. Do not drop it or replace newer user
records just to roll back presentation. There is no financial-data migration.

## Boundaries

This milestone covers the cart, fulfillment/contact/payment controls, product
options dialog, mobile cart action and existing confirmation/recovery display.
It does not reskin the rest of the storefront, signup, reservations, unsubscribe,
tracking pages or merchant dashboard, and does not automate brand synthesis.
Original controller and server security continue governing actual payments.
Software tests use synthetic businesses/orders; no real order, send, provider
activation, payment or merchant acceptance is established by this work.

## Source-catalog test adoption

`catalog_connection.py` connects explicitly enrolled, simulated COP test merchants
into the existing Menu/MenuCategory/MenuItem, quote, order and operator owners.
It retains the source amount and multiplier separately from currentness. The
public context never marks archived prices or stock as currently confirmed.
Existing databases need the explicit additive
`upgrade_catalog_connection(engine)` migration. Fresh databases include the
`restaurant_catalog_connections` table. Repeated enrollment preserves operator
price/stock edits; a changed mapping or new source stops for reconciliation.
Only demo-mode, scoped `settings.write` may import. A catalog cannot enable live
payments. Original bound retries still reconcile before new-write guards.

The checkout and a connected website share the existing `101:selection-cart:<business>:v1`
selection contract from World Model `packages/site-runtime/src/commerce/selection-cart.js`.
The copied browser asset is pinned byte-for-byte; it stores product references
and quantities, never authoritative prices. Quotes and fulfillment remain here.
The controller also accepts a server-bound `data-commerce-business` for scoped
same-origin routes; query parameters remain compatible. Preview mode never writes
that selection. The optional simulated-payment `business_id` is verified through
the existing payment/order join before changing state.

Rollback: stop new test imports/orders, retain the new table and transactional
records, and return to the previous source/controller. Do not drop menus, orders,
customers, or restore an old backup over newer orders. No provider, dependency,
font or music license was introduced. This is local test integration, not current
merchant authorization, real payments, inventory assurance or production hosting.
