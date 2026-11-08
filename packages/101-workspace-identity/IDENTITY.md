# 101 Workspace — living product identity

Version 0.1.0 · Owner: this package. Applies to 101 operating dashboards, including
merchant and appropriate internal tools. It does not replace Honorato's public
brand, customer-facing website or other businesses' identities.

## Character and voice

Precise, calm, quick, approachable. The interface helps someone do the next thing.
It should feel like a sharp tool: readable data, obvious actions, little ceremony.
Use plain Spanish in the merchant product. Labels name tasks: Inicio, Clientes,
Ventas, Campañas, Analítica web. Actions use verbs: Crear campaña, Revisar,
Programar, Cancelar. Say “3 pedidos por aceptar”, not “Optimiza tu ecosistema”.
Avoid business jargon, inflated claims, motivational filler, invented success,
excessive warnings and decorative explanations of internal implementation.
Explain consequences when a decision needs them (receiving cash, sending, cancelling).

## Visual source of truth

`tokens.css` is the reusable framework-independent implementation. Import it once
in each dashboard, then map existing semantic variables to it. Do not paste a
second color/type palette. `decisions.json` retains dated user direction. The
actual commerce consumer imports these tokens into its production build.

- Typeface: locally served Manrope Variable, regular500/body,600–650 emphasis.
  Arial/system fallback. Retain OFL notice from the frontend font distribution.
- Names and navigation15px, labels/contact14px, secondary details12px. Mobile
  primary text14px minimum; narrow ancillary badges may be11px. Main title30px,
  mobile27px. Data uses tabular numerals. Never shrink all text to fit a design.
- **Current color direction (2026-11-05, clarified): gray + white is welcome;
  gray-on-gray is not.** Avoid muddy surface layering and faint text on similar
  backgrounds. Use distinct white working surfaces, deliberate accent roles and
  readable secondary text. This supersedes the earlier overbroad “no gray canvas”.
  `pairings.css` contains seven review candidates, including gray + white. The actual
  demo workspace exposes a local “Vista de color” selector across its existing
  workflows. None is the permanent default yet; “Actual · comparar” restores the
  original tokens. Public merchant branding stays separate.
- Green/amber/red express statuses with written labels; color alone is insufficient.
  White surfaces and existing measured role colors target WCAG AA. Recheck actual
  computed contrast after changes; inherited screenshots are not fresh evidence.
- 12px surface corners, quiet1px borders, minimal shadows except floating overlays.
  Geometry uses4/8px increments with24px major gaps. Controls44px; visible focus.
- Simple Lucide line icons with consistent stroke; use accompanying text for tasks.
  The101 text wordmark is the working application mark, not a new trademark/logo.
  No purchased illustrations, new mascot or copied third-party brand assets.

## Composition recipes

Shell: persistent desktop sidebar, business identity, ordinary navigation, utilities
at the bottom; phone drawer with keyboard/focus support. Single business needs no
switcher. Main content max1560px,24–32px padding,16px on phones. Current reference
implementation is `projects/101_restaurant_commerce_v4/frontend/src/main.tsx`.

Working list: short title, one primary action, optional compact real summary,
filters/search, bounded table/list, selected item detail. Keep selected row, query,
scroll, dates and back behavior. Facts remain readable when columns collapse.
Detail panel420px desktop,370px medium, full-width phone. Avoid repeated card nesting.

Inicio: compact results, list of current work needing attention, timestamped recent
activity. Each figure or task goes to its actual underlying workflow. No invented
revenue or “101 completed” event without an existing record. No fake percentage
comparison when a baseline is missing. Revenue accounting and period must be clear.

Charts: small legible SVGs using the three chart roles, visible date context,
accessible text/tables, clear units. Values are inspectable; animation is optional.
Demo analytics must say “Datos de ejemplo” and never enter real summaries/reports.
Use channel/status color consistently; no gradients needed to make a table useful.

## Interaction and speed

Acknowledge actions promptly; never display unconfirmed money/provider effects as
success. Reuse established permissions and immutable approval contracts. Preserve
error/retry states; don't blindly repeat an uncertain mutation. Keyboard focus,
back/deep links and touch targets are part of the design. Respect reduced motion.
Animations typically140ms and must not delay the next action.

Budgets: ≤180KiB gzipJS,35KiB gzipCSS,80KiB fonts for ordinary shell/route; target
100ms acknowledgment,150ms cached return,2.5s meaningful cold content andCLS≤0.1
under the documented local mobile profile. These are targets, not universal speed
claims. Record device/network/dataset/cache/finish condition and all samples.

## Reuse map and component boundaries

- Reused shell, table, button, tabs, search, badge, detail: commerce `main.tsx`,
  `style.css`, `readability.css`; behavioral helpers in `ui.tsx`.
- Reused dialog/focus: Base UI. Icons: Lucide. React/TypeScript/Vite consumes them;
  the Python application serves the output. No new production Node service.
- New portable identity: this package, with independent geometry/type/color roles.
- New view compositions must use those roles and shared controls. Record their
  actual owner; do not call a copied component shared. Don't import the separate
  Astro customer-review runtime into React just to share a label.

This package is a reusable token/identity layer, not yet a published universal
React component library. Other stacks can import CSS directly. React dashboards
should extract existing working primitives when needed, retaining their contracts.
Source data, brand facts, action behavior and visual tokens remain separate.

## References, examples and decisions

All seven originals are retained in the shared101repository at
`docs/product-design/references/2026-11-05/`, with hashes and a reference board:
1 character/color accents;2 precise navigation;3 quiet workspace shell;4 compact
metrics;5 mobile clarity;6 optional assistance;7 dense useful analytics. They are
private references, not shipped assets or permission to copy another brand.
Working before/after evidence: shared `docs/product-design/sales-workspace-review.md`.

## Required update loop — every design request

1. Read this identity and the user's latest direction. Reopen relevant originals.
2. Apply the requested change to the existing source tokens/components. Update this
   file and append a concise decision to `decisions.json` when direction changes;
   record component additions or implementation-only changes without pretending
   they were separately approved brand decisions. Version meaningful identity changes.
3. Render actual populated, empty/error, desktop and phone states. Look at them
   beside the original references. Refine observed problems, render and look again.
4. Verify source behavior, contrast, geometry, keyboard and relevant speed budgets.
   Record screenshots/measurements in the shared design review and101log.
5. Keep one current identity. Supersede prior choices explicitly; do not fork a new
   visual language for each feature. Other dashboards adopt updates deliberately,
   with their own consumer checks; do not silently restyle unrelated public sites.

## Current consumers and extracted compositions (2026-11-05)

The live sample sheet is `/workspace/identity`. It uses the same CSS loaded by
Customers, Sales, Inicio, Campaigns and the analytics example. No separate mock theme.

| Logical piece | Reuse / owner | Editable presentation, retained behavior |
| --- | --- | --- |
| Navigation, business context, button/input/badge | Reused: `frontend/src/main.tsx`, `style.css`, `readability.css`, `ui.tsx` | Token type/color/geometry; session and business access remain authoritative |
| Heading and period picker | New extracted: `workspace-views.tsx` (`PageHeading`, `PeriodPicker`) | Typography/spacing; one inclusive Bogotá date contract, carried into working lists |
| Working surfaces, metric strip, attention/activity rows | New compositions: `workspace-views.tsx`, `workspace-views.css` | Surface radius/fill, typography and spacing independent of read-only canonical projections |
| Chart, sources and daily table | New: `AnalyticsView` | Chart role colors and geometry; explicit deterministic fixture, never reported as business activity |
| Campaign copy/review/audience/results | New composition: `campaign-workspace.tsx` over existing `campaign_routes.py` | Shared surfaces/controls; existing immutable revision, permission, outbox and payment attribution contracts |
| Email content preview | Reused: existing email renderer and authenticated preview endpoint | Separate merchant brand; shared workspace identity does not rewrite the email brand |

Inicio shows at most six recent records; current attention is explicitly separate
from the selected results period. Campaign results cover the entire campaign and
say so. Post-scheduling eligibility is labelled current, distinct from approval
and historical delivery. Working lists use creation dates. Historical customer totals and current
payment-review counts retain those explicit meanings under a list date filter.
Charts have visible scale/date labels and an accessible daily table. Simulation
acceptance is labelled as acceptance by the simulator; delivery remains separate.

Browser verification changes `--wm-accent` and `--wm-radius` in the actual analytics
consumer, checks computed paint/geometry, and verifies its numbers stay unchanged.
This is a concrete reuse proof, not a claim that every legacy style is tokenized.
Rendered review and measurements: shared `docs/product-design/workspace-views-review.md`.


## Loyalty configuration adoption

Clientes → Fidelización reuses the shell, scoped navigation, buttons, badges,
resource reads and Base UI dialog behavior. New compositions live in commerce
`frontend/src/loyalty*.tsx` and `loyalty.css`; they consume this package's colors,
caption/label/body type and surface geometry. No separate loyalty palette exists.

Reusable form bones are owned by `loyalty-shared.tsx`: field, exact-money input,
percentage/integer controls and pending-command feedback. Program, experiment and
economics forms are their actual consumers. Geometry remains in the composition
CSS, identity roles in these tokens, and action authority in existing server APIs.

Working tables preserve every meaningful column; directory-specific icon-column
widths and mobile hiding rules must not leak into financial tables. Constrained
tables scroll within their own focusable region. Read-only financial copy separates
recorded balances, historical cost estimates, unknown cost and general review.
Simulations retain explicit assumptions; a hypothetical lift is never a success
claim. Publication review shows named participants/products and pinned versions.

Rendered iterations and measured roles: shared
`docs/product-design/loyalty-workspace-review.md`. Shared data tables retain all
financial columns on phones through internal scrolling rather than directory
column-hiding rules.


## Loyalty results adoption

`loyalty-results.tsx` composes the existing scoped shell, resource/command helpers,
Base UI dialogs, exact money controls and table surfaces. Its new comparison bone
keeps effect and confidence interval together in a responsive definition list;
the primary uncertainty must remain visible on phones. Wider financial tables
retain every column in their own scroll region. New geometry lives in
`loyalty.css`; colors/type/surfaces consume this same package. No palette is chosen
by this analytics release; the existing color-review candidates remain available.

Nonbuyers are counted explicitly; missing cost is not zero. Provisional results,
measured/simulated receipts, estimated cost and suppressed intervals are named in
ordinary language. Financial retry feedback uses the existing persistent-command
guard and preserves uncertain requests. Rendered review/measurements are in shared
`docs/product-design/loyalty-analytics-review.md`.

## Actual-app color review (2026-11-05)

`frontend/src/color-preview.tsx` is a new demo-only review control. Existing shell,
customer list/detail/QR, campaign editor/report, sales and loyalty components remain
owned by their existing modules. `frontend/src/color-preview.css` maps their visual
roles into shared `pairings.css`; geometry, evidence and actions are unchanged.
Candidates are browser-local, not business configuration. The explicit demo policy
controls mounting; the query string/local storage cannot enable it in ordinary
mode. Storage failures fall back to the current rendering. Use `?pairing=cobalt`
or `?pairing=gray-white` for direct review links. Other pairings: ink, violet,
forest, lime. The control does not change public checkout or branded email previews.

Comparison delivery: show several actual-app renders together with direct links.
Name surface order explicitly: white panels on gray (`gray-white`) and gray panels
on white (`white-gray`). A hidden selector or one example alone is insufficient
for comparing options. This is a review preference, not selection of a default.

## Provisioned analytics (2026-11-07)

Canonical UUID businesses use the authorized reporting API with real/pending/error
states. Reuse the shared PageHeading, PeriodPicker, result strip, tables and
Failure/Loading components. Keep financial scope and order-cohort/refund timing
visible; browser events never become financial records. Existing named demo
businesses retain explicitly labeled sample charts. No new palette or chart tokens.

## Internal business onboarding (2026-11-08)

`frontend/src/onboarding.tsx` and `onboarding.css` add the internal Negocios
composition. Reuse the existing shell, typography, working surfaces, buttons,
resource states, Lucide icons and Base UI dialog/focus behavior. Reference2 informs
navigation precision; reference7 informs compact operational grouping. No new theme.
Directory rows, stage details and CSV intake are new compositions owned by that
module. Their geometry remains editable separately from account/provisioning facts.

Platform administrators can open this view without merchant memberships. That
permission does not grant access to merchant orders, customers or analytics.
Persist each submitted payload and request key before sending; uncertain requests
stay visible and can be retried unchanged. Ready, pending external setup and
suspended remain distinct written states. Show requested DNS records beside the
pending domain. Suspension conserves existing records/resources. Phone layouts
retain full names, domain instructions and44px controls without horizontal overflow.
Actual render/measurement evidence lives in the shared provisioning demo review.
