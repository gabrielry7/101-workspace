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

- Typeface: locally served Inter Variable, regular500/body,600–650 emphasis.
  Arial/system fallback. Retain INTER-LICENSE.txt from the pinned Fontsource distribution.
- Names and navigation15px, labels/contact14px, secondary details12px. Mobile
  primary text14px minimum; narrow ancillary badges may be11px. Main title30px,
  mobile27px. Data uses tabular numerals. Never shrink all text to fit a design.
- **Current color direction (2026-11-05, clarified): gray + white is welcome;
  gray-on-gray is not.** Avoid muddy surface layering and faint text on similar
  backgrounds. Use distinct white working surfaces, deliberate accent roles and
  readable secondary text. This supersedes the earlier overbroad “no gray canvas”.
  `pairings.css` contains seven review candidates, including gray + white. The actual
  explicitly internal workspace exposes a local “Vista de color” selector across its existing
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

Shell: persistent desktop sidebar starting with business identity, ordinary navigation, utilities
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

`frontend/src/color-preview.tsx` is an internal review control. Existing shell,
customer list/detail/QR, campaign editor/report, sales and loyalty components remain
owned by their existing modules. `frontend/src/color-preview.css` maps their visual
roles into shared `pairings.css`; geometry, evidence and actions are unchanged.
Candidates are browser-local, not business configuration. The server environment `COMMERCE_ENV=internal` controls mounting, independently
of the fictional-data `demo_mode` disclosure; the query string/local storage cannot enable it in ordinary
mode. Storage failures fall back to the current rendering. Use `?pairing=cobalt`
or `?pairing=gray-white` for direct review links. Other pairings: ink, violet,
forest, lime. The control does not change public checkout or branded email previews.

Merchant copy must inform, guide or explain. Remove generic or repetitive slogans;
retain useful explanations, permissions, safety information and fictional-data disclosures.
The merchant Home does not promote the internal Identity specimen. Its navigation
and direct route are available only in the explicitly internal environment.

Comparison delivery: show several actual-app renders together with direct links.
Name surface order explicitly: white panels on gray (`gray-white`) and gray panels
on white (`white-gray`). A hidden selector or one example alone is insufficient
for comparing options. This is a review preference, not selection of a default.

## Social production slice · 2026-11-06

`frontend/src/social.tsx` composes the existing workspace shell with a source/fact form and rendered-photo review. Geometry is owned by `social.css`; brand media remains separate from workspace styling. Preserve explicit missing-metric states, source permission, saved-version approval and visible deterministic-copy limits. Current slice is provisional pending real Honorato material and broader production controls.

Social connection/intake extension: the same content workspace now presents explicit
Instagram setup/authorization/import states and source-post coverage. Photo intake
shows progress and an explicit retry action, with a scoped reusable asset selector.
It retains the existing shell, buttons and white working surfaces; no new theme.

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

Review refinement: onboarding icon targets are44px on phones, including close and
pagination. The provisioned-analytics consumer resets inherited directory column
widths/hiding with scoped table selectors; all financial columns remain table cells
at every width, with a focusable internal scroll region when necessary. Do not let
customer-directory geometry decide whether a financial value is visible.

## Inter across 101 interfaces (2026-11-08)

User-selected default: Inter for all 101 product and internal UI text, including
headings, controls, navigation, dialogs, onboarding and legacy staff tools. Use
`--wm-font` and the locally served variable font; no third-party font requests.
Preserve monospace for code where functional. Merchant websites and customer creative
outputs retain their separately approved brand typography. `typography.css` and its
font asset here are the source; generated legacy/internal distributions retain the OFL.

Sidebar direction (2026-11-08): remove the standalone “101 | workspace” branding
row from desktop navigation and the phone drawer. Business identity comes first;
keep the existing Inicio navigation action.

## Monthly reports

Reportes reuses the workspace shell, controls, white surfaces and Inter. New monthly
summary and PDF composition belong to commerce monthly-reports.tsx and
monthly_report_pdf.py. Three primary figures, previous values and short source states;
no generated headlines/advice. Saved snapshots supply both views. Unknown is an em
placeholder, measured zero is numeric. Legacy sample charts never enter these reports.

### Social business information and stale drafts — 2026-11-12

Reuse the current business shell, Inter, white working surfaces and compact form
controls (standing reference03). Keep reusable business information in one collapsible
section above the post editor. Show unknown capacity/margin explicitly; don't prefill
unconfirmed business claims. Fact rows separate value, source, dates and correction.
A stale draft stays readable beside its form; explain why review is needed, retain
permitted photography, and require fresh confirmation/approval after correction.
Use existing border/surface roles with fallback values for the adopted shell; controls
remain at least44px, with a single-column phone form. Merchant creative fonts remain
independent. Test synthetic material is labeled in the preview.

### Social references and questions — 2026-11-12

Reuse the business-information panel and shared Inter/white surfaces from the N02
recipe and standing reference03. A collapsible board keeps reference cards, voice
rules and questions separate. Show the judgment AND why a reference matters; keep
its comparison group distinct from whether the owner likes it. Cards never imply
measured commercial success. Questions show their origin and unknown demand clearly.
Use existing44px controls, a wrapping three-button switcher and stacked phone fields.
Post review retains a compact expandable source-context receipt. A factual correction
must not become a style preference, and research examples must not become output
photography by default. Source and permission fields remain explicit owner inputs.

Social guided setup (2026-11-13): reuse the existing white context panel, shared
Inter and native radio/checkbox controls. Five steps cover priority, buying routes,
first content idea, available material and review. Choices start unselected;
custom answers and explicit unknowns are first-class. Only relevant details open.
Choice rows use visible borders and at least44px touch targets, two columns on
wide screens and one on phones. Review offers per-answer edits and explicit save;
loading does not expose an empty editable context. Voice examples live in the
existing brand board and remain editable before separate confirmation.

Sidebar visibility (2026-11-13): a44px panel toggle sits beside the business name
in the desktop sidebar header, replacing its decorative bag icon to preserve space.
Hiding the sidebar releases its full width; the header exposes a matching reopen
button next to the page label. Focus moves between the two controls and visibility
is remembered locally, independent of business data. The existing phone drawer,
close button and Escape behavior remain separate. No branding row is reintroduced.

Social production activity (N04,2026-11-14): reuse the shared white working panel,
Inter, normal action buttons and44px controls. A compact list shows queued/running/
failed/needs-review/completed status; activity and manual effort open on demand.
Retry names the failed step; completed work opens its actual saved result. Unknown
machine costs are explicitly uncalculated. Photo review/approval remains a separate
working surface. Phone actions wrap; no status is conveyed solely by color.

Company header (2026-11-15): following the supplied Modsley reference, the company
name/business selector and panel toggle occupy one flat full-width sidebar header.
Remove the rounded business card, decorative icon and subtitle. Its64px desktop
height aligns exactly with the page header; the phone drawer uses60px with the same
name/close arrangement. Names remain one line with ellipsis/full-name tooltip;
selection,44px toggle, saved collapse preference and keyboard focus remain active.
This updates the business header itself; no separate101branding row is introduced.

Social proposal review (N05,15 November2026): keep facts, references and proposal
review in the shared white/Inter panels. Inputs collapse after preparation so the
owner can compare two copy approaches, inspect claim sources, edit the chosen text
and record a factual/style/strategy reason. The model/template route stays explicit;
no universal quality score or invented search volume. Reuse shell, form controls,
buttons and responsive two-column layout; the proposal comparison is a local bone
owned by Social, separate from the final publication approval.44px actions and
phone wrapping are checked against reference03. Copy choice buttons align at the
bottom of each option, and whole-copy review remains distinct from claim citations.

Social static editor (N06,15 November2026): the existing photo form gains a
collapsible design panel, shared Inter controls and separate title/information/
price fields. Photo-only, photo-first and information presets share the same
version/review surface. Color and typography controls stay separate from source
facts; geometry is behind focused advanced disclosures. Changing a price writes
the current fact through the existing confirmed-context writer and stales affected
work; the photograph and layer geometry survive correction.44px actions, wrapping
controls and readable fact sources are checked on phones. The review panel now
sizes to its content; anchors join editing and prepared review without a new page.
Historical images are clearly historical and never substitute for current approval.
Creative output typography currently uses the existing licensed Inter Regular
face;101UI typography stays governed by this identity, separately from merchant
content choices. No default serif, font substitution or universal taste score.

Social guided video (N10 first recipe,16 November2026): reuse the Social pack,
shared Inter/white panels,44px controls, N04 activity and N07 review/approval.
The shot guide, take selector and bounded trim/crop/audio editor are new Social
pieces; framing diagrams are neutral guidance and never merchant content. Saved
video views collapse the photo editor, show one playable preview and link directly
to the guide. Permission, source time and material remain separate from geometry.
Phone fields stack; replace one take without losing the other choices. Full-video
watch/listen acknowledgment is independent of final approval. Comparisons based
only on a cover never stand in for temporal/video review. Before/refined desktop
and390px evidence lives in docs/social/n10-evidence in the World Model repository.

Social speech correction (N12,2026-11-16): extend the existing Video panel with source-timed word fields, explicit meaning review and correction history. Reuse Inter, white panels and44px controls; fields wrap on phones. Subtitle size is a bounded creative setting, separate from UI typography. Voice-service availability, machine transcript, owner corrections and exact approval remain distinct. Desktop/mobile evidence is recorded in the World Model Social N12 report.

Owner-entered subtitles (2026-11-17): when voice recognition is unavailable, keep
the answer clip playable and offer a focused disclosure for short captions with
explicit source start/end times. Start with blank times; never imply automatic
alignment or confidence. Label saved text as supplied by the business, retain the
original and correction history, and permit time corrections only for this source.
Use the same Inter, white panels and44px controls; time fields stay in two readable
columns on phones. Text/time changes require a new render, review and approval.

Campaign email designs (2026-11-18): reuse CampaignDetail and its existing shared
Inter form/select/action/review bones. One compact design strip previews alternatives
without writing a revision; unsaved comparisons clear review and disable approval
and scheduling. A saved choice creates a new exact-version review. Keep the101UI
font separate from the creative fonts of the six email layouts. The new local strip
is owned by campaign-workspace.tsx; React Email owns email-compatible primitives,
while101owns content/brand bindings and each adapted layout. Verified44px controls,
desktop/390px layouts and explicit unavailable-render states. Original family source,
licensed fonts and adaptation notes remain in email-renderer; this adds no gallery
or visual builder.

Email chassis (2026-11-18): extend the same campaign form with one collapsed
**Huesos y chasis** group. Source/neutral styles, bounded fields and JSON export/
import use existing Inter, 44px controls, white surfaces and wrapping actions.
Creative text geometry and fonts remain separate from the 101 UI. The style
configuration contains no campaign facts or recipient/action data. Saving changes
requires a fresh exact-version review; resetting restores the selected recipe.
Keep professional family structures distinct. Actual email geometry and solid
contrast are measured with the existing component-preview instrument, without
shipping that inspector into recipient emails or calling a ratio a taste score.


### Shared entry and Sales reservations — 18 November 2026

Reuse the existing login, business identity, list/detail, tab, confirmation and
status bones from references02/03. `workspace-entry.tsx` resolves an authorized
return destination; its business choices are explicit. `reservations.tsx` composes
a compact queue and detail, with merchant-local times. `contact-handoff.tsx`
separates preparing a message from opening its external composer. Account identity
contains session options; a standalone logout icon remains available. New
reservation and view-switch buttons have44px minimum targets. Spacing and select
borders were refined after actual phone inspection. Keep all merchant fonts and
source facts separate from these UI choices.

### Native operations and finance — 18 November 2026

U04–U06 reuse references02/03 and the current Sales list/detail, shared tabs,
Base UI confirmation, Inter and white surface bones. New composition owners:
`deliveries.tsx`, `operation-settings.tsx`, `financial-review.tsx`,
`daily-finance.tsx`; their scoped styling is `operations-workspace.css`.
`operations-ui.tsx` shares bounded errors and single-command/unknown states.
Delivery and finance details reuse the fixed `detail sale-detail` bone; on phones
that pane becomes the focused full-width view. Settings use two-column desktop
forms and single-column phone rows; each inventory item keeps its own edits/version.
New targets are at least44px. Technical statuses, confirmed money and unknowns
remain distinct. Inspect actual1440/390/320px screens; screenshots do not establish
live provider qualification. Public storefront and email creative keep their brands.

Growth/channel consolidation (18 November 2026): native catalogues, original-growth
report, manual outbox, WhatsApp/SMS campaigns, sender/template configuration and
bounded conversation detail reuse references02/03, Inter, white working surfaces,
existing tabs/list-detail/confirmation and operations-ui controls. New compositions
are owned by growth-workspace.tsx, channel-config.tsx, channel-inbox.tsx and
campaign-channel-controls.tsx; growth-channels.css owns their editable geometry.
No new theme or merchant brand is introduced. Responsive refinements retain44px
tab/actions, visible refresh controls, wrapping suppression explanations and a
one-column phone form. Operating-panel expansion survives state refresh; Back
restores provider choice. Source/scope, unknown price, manual handoff, simulation
and provider evidence remain distinct. Actual1440/390/320px captures and their
measurements are retained in the shared consolidation U07–U09 report. Live provider
capability remains separate.

Workspace completion (18 November2026): Google/Instagram account panels and native
signup/funnel reuse the existing white surfaces, Inter, review dialogs and tabs from
references02/03. `ProviderTabs` and `SignupContent` are extracted existing bones;
`account-connections.tsx` and `signup-tools.tsx` compose those without embedding facts
in styling. Native entry mapping retains the company header and business context.
Observed phone refinements explicitly keep metric names and signup stages visible
against old directory-column rules; bounded three-column tables wrap at320px.
Spacing and source/error labels were refined after inspecting actual desktop/phone
renders, then rendered and inspected again. Current sources, simulation, expiration
and missing values remain visibly distinct. This does not alter merchant creative
identity or authorize live connections/sends.

Customer checkout editor (2026-11-19): `/workspace/website` reuses the existing
Inter/white working panels,44px actions and compact two-column layout from
references02/03. The editor changes the merchant checkout's separately owned
chassis; it does not impose staff tokens on public merchant output. At390px the
Open site action keeps a visible label and a preview jump avoids long backtracking.
The embedded preview uses a static header so it cannot cover the checkout title.
Desktop/phone captures were inspected, refined and inspected again. Reused shared
bones validators, typed anatomy and geometry/contrast measurements are owned by
`@101/checkout-chassis`; original commerce handlers retain prices and actions.
Neutral/fictional warm coats are examples, not selected merchant identities.

## Connected merchant operating demo (2026-11-20)

Home keeps actual current-work and result records, with a compact store entry and
an optional tool directory (collapsed on phones). Unsigned Social packs join the
same review queue and open their exact saved revision in Contenido. Website groups
Mi tienda, Productos and the existing checkout editor. Test-price edits have
revision checks and preserve prior order totals. Reuse shared Inter, white surfaces,
44px controls and the existing semantic tokens; public merchant branding remains
separate. The explicit banner reads Modo demo · sin cobros ni envíos.

Demo transactions, test clocks/calendars and synthetic contact permissions stay
labeled. Available navigation never implies live authorization or web analytics.
Analytics routing uses the actual platform enrollment capability, not UUID shape.
The readiness details identify actual activation gates without a universal score.
Full desktop/phone proof and bounds live in World Model
`docs/product-design/honorato-workspace/README.md`.
