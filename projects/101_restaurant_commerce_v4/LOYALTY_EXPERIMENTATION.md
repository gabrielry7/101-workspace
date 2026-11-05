# Loyalty experimentation — stages 1–7

Implemented: a staff-authorized configuration foundation for multiple loyalty
strategies, immutable published versions and separately versioned experiments.
Stage 2 adds deterministic points/fixed-value rule previews against published versions.
Stage 3 adds controlled versioned execution through the existing checkout, wallet and
financial workflows. Ordinary baseline benefits remain; new orders can add an exact
published strategy under the synthetic execution gate described below.
Stage 4 independently enrolls verified customers into permanent randomized cohorts
and routes synthetic checkout through those assignments.
Stage 5 adds a read-only financial simulator with explicit assumptions and sensitivity.
Stage 6 adds the scoped operator workspace for programs, experiments, publication
review, economics and passive balance/cost monitoring.
Stage 7 adds original-assignment profit reports, source-bound cost evidence,
customer-level uncertainty, measurement warnings and CSV exports.

The complete design and staged acceptance criteria live in the shared repository:
`/home/t/101-world-model/docs/commerce-audit/LOYALTY_EXPERIMENTATION_PLAN.md`.

## Enable configuration

Configuration routes are off by default. On an existing installation, stop all
writers, back up the database and run:

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-loyalty-config --offline
```

`COMMERCE_DATABASE_URL` selects the backed-up database, as for existing maintenance
commands. SQLite and PostgreSQL are supported. No live database was upgraded during
implementation. Repeating a completed upgrade is safe; partial schemas fail closed.
The upgrade adds six tables and immutable-history triggers. It does not convert
legacy wallet balances or invent historical program versions. Fresh test/development
schemas include these tables. Existing schemas do not acquire them on startup.

Then set `COMMERCE_LOYALTY_CONFIGURATION_ENABLED=1` before starting the existing
application, or pass `loyalty_configuration_enabled=True` to `create_app`.
The same flag controls the Stage-2 preview endpoint; no new database upgrade is
needed for installations that already completed Stage 1.
Only `0` and `1` are valid environment values. An explicit factory argument overrides
the environment. Enabled startup/readiness requires the complete configuration
schema. Disable the flag to remove the configuration routes without deleting history.
Partial or damaged schemas still fail readiness; disabling the flag is not a repair.

**Public reward execution, experimental enrollment and analytics activation remain
disabled.** Attempts to enter `active` fail. Publishing only records reviewed rules.
Public capabilities continue to report `execution_enabled: false`; the Stage-3
transaction adapter is deliberately available only to trusted synthetic callers.

## Staff API

Base: `/api/operator/restaurants/{business_id}/loyalty-config`.
Use existing named staff sessions and CSRF headers. Reads require `growth.read`;
mutations require `growth.write` (currently manager-only). No public route grants
customer identity, enrollment or rewards. Existing staff audit records authorization
and transaction commits; an additional append-only audit retains configuration
resource, revision, digest and actor in the same mutation transaction.

| Method and suffix | Action |
| --- | --- |
| GET `/capabilities` | Reports optional configuration/preview and controlled adapter availability; public execution stays off |
| POST `/simulator` | Calculate hypothetical economics without saving or activating a program |
| GET `/experiments/{id}/enrollment` | Descriptive assignment, exposure and ledger diagnostics; requires the offline assignment upgrade |
| GET/POST `/programs` or `/experiments` | List or create a draft |
| GET/PUT `/{kind}/{id}` | Inspect history or edit draft with expected revision |
| POST `/{kind}/{id}/publish` | Publish the exact reviewed revision and SHA256 digest |
| POST `/{kind}/{id}/state` | Pause a definition with published history or archive it |
| POST `/programs/{id}/versions/{version_id}/preview` | Evaluate a hypothetical cart using that exact published version |

Create bodies contain `request_key` and `document`. Retrying the same creation key
with the same initial document returns its existing resource; a different document
conflicts. Concurrent first creation can return 409; retry the same request key.
Edit bodies contain `expected_revision` and `document`. Publish bodies contain
`expected_revision` and the `digest` returned by GET. A successful publish increments
the working revision and creates a distinct permanent version ID. Retrying the
original publish returns that same version, including after subsequent draft edits.
A stale revision or digest conflicts. Concurrent writes cannot silently overwrite
one another. Editing retains all published versions and creates a new proposal;
an existing operational pause is preserved.
Archived definitions cannot be edited; archiving does not delete published history.

Example points document (illustrative amounts only):

```json
{
  "name": "Incremental points hypothesis",
  "currency": "COP",
  "earning": {"type": "points", "spend_minor_per_point": 1000},
  "maximum_reward_minor": 10000,
  "per_customer_budget_minor": 50000,
  "campaign_budget_minor": 1000000
}
```

All amounts are integer minor units, never decimal currency floats. Schemas also
support descriptions, timezone-qualified dates, eligibility and exclusions,
expiration, minimum redemption, cost assumptions and promotion stacking policy.
Eligibility product/customer references must belong to the business. They do not
establish authentication or consent. Points and fixed-value schemas are first-release
execution candidates; cashback/frequency/milestone/tier/percentage/product types are
configuration-only extension points. Only points earning and fixed-value redemption
can be previewed; no type issues or redeems a real reward at this stage.

An experiment document names a currency, enrollment start/end, observation window,
eligibility, exclusion group, written analysis plan and 2–20 named variants whose
integer basis-point allocations total 10,000. Exactly one control has a null
`strategy_version_id`; treatment variants pin existing published strategy versions
in the same business/currency. Existing benefits must be preserved. Explicit overlap
requires a reason. The published experiment stores a random salt and assignment
algorithm version. Publishing does not enroll customers; the controlled Stage-4
adapter below is the separate enrollment boundary.

Published rule documents, experiment versions, variants and configuration audit
rows reject UPDATE/DELETE at the database level, including raw SQL. Foreign keys
prevent ordinary parent deletion from erasing history. Database owners who can
alter/drop triggers remain privileged; this is not administrator-tamper-proof storage.
Readiness checks column/key structure, check-constraint names and canonical enabled
history triggers; it does not prove equivalence of arbitrary check-constraint SQL.

## Stage-2 rule preview contract

The staff preview endpoint requires `growth.read` plus the existing session and CSRF
protection. It accepts **hypothetical prices, identity and balances**; these assumptions
never authenticate a customer or authorize a discount. Product/customer IDs must
belong to the requested business. A version must belong to both that business and
program. Draft IDs, foreign versions and unsupported reward types cannot silently
produce valid reward calculations.

Example body (replace IDs with this business's IDs):

```json
{
  "currency": "COP",
  "at": "2026-11-04T12:00:00Z",
  "customer_id": "customer-id",
  "assume_verified_identity": true,
  "assumed_available_points": 100,
  "assumed_refund_debt_points": 0,
  "redeem_reward": true,
  "lines": [
    {
      "line_id": "cart-line-1",
      "product_id": "menu-item-id",
      "subtotal_minor": 10000,
      "promotion_discount_minor": 0
    }
  ],
  "tax_minor": 1900,
  "delivery_fee_minor": 7000
}
```

Each line subtotal is the **extended item amount before discounts, excluding tax and
delivery** (quantity/modifiers already priced). Existing promotion discounts must be
allocated to their actual lines by the caller. The preview does not infer tax or
promotion allocation from the current checkout. Stage 3 must supply authoritative
order snapshots and enforce budgets, identity, account locking and refund state.

Calculation version `points-fixed-v1` defines these choices:

- Product/customer exclusions and currency apply before earning/redemption.
  Dates are start-inclusive and end-exclusive at the explicit scenario time.
- Minimum purchase uses eligible item spending after existing promotions, before
  the new loyalty discount. Excluded products, tax and delivery cannot meet it.
- With stacking disabled, any existing promotion discount in the cart blocks this
  program's earning and redemption, even on an otherwise excluded product.
- Fixed-value discounts are capped by `maximum_reward_minor` and eligible item
  spending. A capped reward still costs its configured full points price; zero
  value consumes no points. No tax/delivery discount is inferred.
- Required available balance is the greater of `minimum_redeem_points` and the
  reward's `points_cost`; only `points_cost` is spent. Outstanding refund debt blocks
  redemption. Points from this purchase are not available for its redemption.
- The discount is allocated proportionally across eligible net lines using integer
  largest remainders, with stable line-ID ties. Allocations conserve the exact total.
- Points = floor(eligible item spending after both discounts / spend per unit)
  × points per unit. Floor once per order, not per line. Unsuccessful redemption
  leaves ordinary eligible earning intact. Expiration, when configured, derives
  from the explicit scenario time using elapsed 24-hour UTC days (including across
  daylight-saving changes); no system clock is consulted.
- `maximum_reward_minor` caps the monetary discount. It does not invent a currency
  valuation for points. Campaign/customer budgets and redemption probability are
  **not** interpreted as authorization, spend caps or expected-value discounts here.
  Atomic budget checks and liability accounting belong to Stage 3.
- Money uses integer minor units bounded by the safe JSON integer range. Points
  are bounded by the existing signed 32-bit account range. Invalid input, calculation
  overflow and impossible expiration dates fail explicitly rather than clamp.

Responses include the program/version IDs, immutable version digest, scenario digest,
calculation version, per-line allocation, qualifying spend/units/remainder, points,
expiration, discount and reason codes. `eligible_by_rules` describes only the supplied
scenario; inspect the separate earning/redemption results. Unsupported configurations
return `supported: false`, a reason and zero effects. Budget/activation checks are
explicitly `not_performed`; `execution_enabled` remains false.

The adapter never reads today's program draft or substitutes current menu prices
or wallet balances. Previewing the same version/scenario stays identical after a
new draft/version or archive. This is a historical/hypothetical rules replay, not a
claim that an archived program can issue new benefits. Normal staff authorization
attempts are audited, but previews do not change orders, wallets, ledger, redemptions,
refund debt or configuration history. No new dependency or schema migration is added.

## Remaining stages

Stage 7 intent-to-treat contribution-profit reporting is implemented below. Version-pinned
execution/refunds, persistent assignment, simulator and staff configuration screens
are implemented under the staged gates documented below. Customer authentication,
cost provenance and statistical analysis details remain prerequisites for a pilot.
Existing real-money gates remain in effect. No optimal reward or business uplift is
claimed by configuration tests.

## Verification commands

Use the project's existing Python test environment:

```sh
PYTHONPATH=src python -m pytest tests/test_loyalty_configuration.py -q
```

The fixture uses SQLite by default. With `COMMERCE_PAYMENT_TEST_DATABASE_URL` pointing
to a disposable loopback PostgreSQL database, each test creates and cleans its own
schema. Never use a customer database. Tests cover raw-SQL immutability, lifecycle,
stale review, cross-business references, staff permissions/CSRF, feature flags,
populated repeated upgrades, partial-schema rejection and concurrent edits/publish.

The restricted execution environment stalled even a bare FastAPI TestClient request;
the same probe returned normally outside that restriction. HTTP qualification uses
that functioning environment, without changing application behavior to hide the stall.

Stage-1 installed-package qualification (2026-11-04 UTC): **147 tests passed**,
zero failures/skips: 36 foundation cases on disposable PostgreSQL, the same 36 on
SQLite, plus 75 existing growth, customer-safety, financial-resolution and capacity
consumer cases using their actual mixed fixtures. All 67 packaged source/asset files
matched the checkout; installed import path was independently checked. Targeted Ruff
and whitespace checks passed. Evidence is retained in the shared workspace at
`data/loyalty-verification/installed-{postgresql,sqlite}.{txt,xml}` and
`wheel-manifest.json`. No production-performance claim follows from these tests.

Stage-2 installed-package qualification (2026-11-04 UTC): **126 checks passed** with
zero skips in the final run: 46 new rule/preview cases, 36 configuration regressions,
11 existing growth cases and 17 customer-safety cases on SQLite; three preview
consumer cases and 13 bounded-readiness cases on disposable PostgreSQL. Property
checks exercise allocation conservation, permutation invariance, monotonic earning
and split-line equivalence. All 70 packaged source/asset files match the checkout;
targeted Ruff and whitespace checks pass. Evidence is retained separately at
`data/loyalty-verification/stage2-20261104/final/` in the shared workspace.

An earlier combined candidate run returned one unexpected 503 in the existing
SQLite schema-freshness readiness test. Isolated candidate and unchanged canonical
reruns both passed; the final PostgreSQL readiness suite passed. The original failure
is retained in the parent evidence directory, with no timeout/assertion changes.
Its cause is not established, and these results do not establish production latency.


## Stage 3: controlled execution and financial history

Installation is explicit, including for fresh databases. After the configuration
upgrade, stop writers, back up the database and run:

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-loyalty-execution --offline
```

This adds seven execution tables and retention triggers on snapshots, lot movements,
execution events, refund allocations, the existing points ledger and confirmed refund
observations. Lot origin, cost and expiry cannot change; balances remain projections.
Partial schemas or altered/missing guards fail readiness and repeat upgrade. No old
points are converted into invented versioned lots. `reconcile` reports any existing
ledger discrepancy and the unattributed legacy balance separately.

A trusted service caller may pass `loyalty_execution=ExecutionSelection(version_id,
redeem_reward=False, enabled=True, price_basis="synthetic_tax_exclusive")` to
`RestaurantCommerceService`, alongside a verified customer ID. The enable switch
is false by default. Only simulated payment checkout is admitted. Neither request
JSON, contact matching, configuration publication nor a staff cookie selects an
execution version. Current order prices have no tax decomposition: the explicit
synthetic price assertion is **not** a production tax adapter. Customer authentication,
real economics and the remaining release stages are still pilot gates.

The server prices the cart, checks eligibility and currency, allocates existing
promotion discounts by largest remainder with stable line-index ties, and evaluates
the frozen strategy. Checkout rechecks the wallet and strategy status under locks,
then atomically stores the result and original order-item IDs, reserves cost budgets,
debits any reward, and creates the existing payment intent. A changed selection
conflicts with the original idempotency binding. New reservations cannot use paused
programs; already-pinned orders continue their original terms. Version edits never
change old orders or reset strategy budgets. A disabled internal RewardDefinition
connects versioned fixed rewards to existing RewardRedemption records; ordinary
checkout cannot select that bridge as an enabled legacy reward.

All points share the existing business/customer wallet. New incremental earning is
attributed to versioned lots; ordinary baseline earning is retained and its actual
checkout-time settings are captured separately. Point lots are consumed by earliest
expiry, then lot ID, before unattributed legacy points. Legacy reward reservations,
releases, refunds and debt repayments also consume/restore these lots. There is no
second spendable balance. Completion works through the payment, cash-pickup legacy,
and delivery consumers. The controlled new-version selector itself remains limited
to simulated payments.

Existing verified-order writers acquire Payment → Order → Customer → execution state → account →
strategy/budget → lots/debt as needed. Newly inserted checkout rows precede the account
lock. Locked projection reads refresh SQLAlchemy's identity map; retaining an old
Python object does not retain an old spendable balance. The account and budget
revision columns additionally fence conflicting SQLite writers. Callers own commits;
no loyalty helper sends providers a request. Existing optimistic contact conflicts
may require a full transaction retry with the same checkout idempotency key.

### Cost budgets, expiration and reconciliation

Campaign and customer caps apply across all versions of one strategy. Reservation
uses conservative **gross issuance cost** (points × explicit positive cost estimate)
plus the current fixed discount. Payment applies the discount cost; fulfillment
commits the actual issued-point estimate and releases unused reservation. Cancellation
releases uncommitted cost. Refunds and expiration do not replenish committed campaign
budgets. This deliberately conservative cap is not an accounting profit calculation;
analytics must not subtract a discount again after using already-discounted revenue.
All amounts use integer minor units, with bounded points and basis points.

`loyalty_wallet.expire_due_accounts(session, at=..., limit=...)` is the bounded,
idempotent maintenance consumer; the caller commits. Reserved points are already
outside available lots and do not expire underneath an unresolved payment. Returns
preserve original expiry: already-expired returns create paired restoration/expiry
history rather than new usable points. Refunds count already-expired source points
as retired, so a customer is not charged twice. `reconcile(session, account)` checks
wallet versus ledger, lot movements versus lot balances, unattributed legacy points,
and outstanding lot cost (gross and probability-weighted estimates). It reports
unknown legacy valuation, rather than estimating it from today's rules. Outstanding
budget reservations must be monitored alongside available-lot liability.

### Partial refunds and review

The existing authenticated simulated-provider notification accepts
`status="partially_refunded"`, a unique `refund_reference`, `refund_amount_minor`,
and optional `loyalty_allocation={"lines": {"ORDER_ITEM_ID": MINOR_UNITS},
"delivery_fee_minor": MINOR_UNITS}`. Allocation is **paid consideration**, not a
claim of physical product return. It must sum exactly to the confirmed amount;
cumulative line and delivery allocations cannot exceed original paid amounts.
Foreign lines, negative/fractional amounts and conflicting allocation retries fail.
Real-provider partial-refund normalization remains unqualified.

An unallocated confirmed partial refund remains durable and visible. It holds that
order's new earnings and blocks further reward redemption for the customer; it does
not invent a product allocation. Existing financial-role/CSRF authorization protects
`POST /api/finance/restaurants/{business_id}/loyalty-refunds/{refund_id}/allocation`.
The body is the allocation above. The actor, allocation and committed-action audit
are retained. Repeating the same resolution is safe; changing an allocation requires
a future correction contract, not editing history. A full confirmed refund is
unambiguous and compensates even if previous partial allocations remain unknown.

Entitlement is recomputed cumulatively from original rules and remaining paid eligible
spending. Minimum qualification uses retained **pre-reward** spending; each line's
reward discount is retired proportionally using cumulative integer floor. Points
restore proportionally to eligible refunded paid consideration, with full-refund
remainder correction. Monotone prefixes of original lot consumption avoid rounding
changes across refund chunks and preserve each returned point's original expiry.
Spent earning reversals create the existing refund debt; later credits repay it.
Gross issued, reversed, restored and retired counters remain distinct. Missing
allocation resolved after completion can release held earnings exactly once.

### Stage 3 acceptance

`tests/test_loyalty_execution.py` exercises the real checkout/fulfillment/refund
consumers, version edits and shared caps, SQL retention, populated upgrade, partial
refund allocation and financial authorization, spent-point debt, expired returns,
projection refresh, and PostgreSQL races for redemption, campaign exhaustion,
completion versus refund, and expiration versus cancellation. Run against disposable
SQLite and PostgreSQL using the existing `COMMERCE_PAYMENT_TEST_DATABASE_URL` fixture.
Ordinary growth, identity, finance, delivery, payment/capacity and readiness tests
remain required consumers. Test fixtures use synthetic customers and local providers.
Stages 6–7 (staff configuration UI and ITT profit reporting)
remain separate delivery stages. No winner or behavioral lift is claimed.


## Stage 4: controlled randomized assignment

After the configuration and execution upgrades, stop writers and back up the
selected database before the optional offline upgrade:

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-loyalty-assignment --offline
```

The six new tables retain eligibility decisions, one experiment run, assignments,
allowed-overlap evidence, exposure receipts and order bindings. All reject
UPDATE/DELETE, with scope guards for run/version, customer, variant and order links.
Fresh startup does not silently install these tables. Repeating a completed upgrade
is safe; missing/altered guards and partial schemas require repair. Old orders,
customers, wallet balances and cohorts are not backfilled or fabricated.

A trusted adapter constructs `LoyaltyAssignmentService(session, actor_id,
enabled=True, mode="synthetic")` and calls `enroll(business_id, version_id,
verified_customer_id=..., identity_evidence_ref=..., request_key=...)`. The caller
commits or rolls back the whole transaction. Enrollment needs no order or wallet.
The identity reference records the trusted verification source; submitted telephone
numbers, public JSON and staff cookies do not authenticate a customer. Missing
verified identity produces a retained ineligible decision. Foreign-customer IDs fail.
Customer allowlists are supported; order/product-dependent enrollment eligibility
is explicitly unsupported, so buying cannot silently become a condition of randomization.
Cart eligibility is evaluated later by the assigned program.

The first successful enrollment freezes one published experiment version for the
run. Its salt, published variant order and integer basis-point allocations determine
SHA256 assignment (`sha256-v1`): hash UTF-8 compact JSON
`["101-loyalty-assignment","sha256-v1",salt,experiment_version_id,business_id,customer_id]`,
interpret the full digest as a big-endian integer, take modulo 10,000, then select
its cumulative allocation interval. The assignment is persisted and unique per
business/experiment/customer. Independent repeated enrollment returns the original
eligibility decision and assignment, even after a configuration edit, pause or end.
Another version cannot replace the run for newly enrolled customers; create a new
experiment for a new allocation protocol. Allocations are probabilities, not quotas.

Customer → Experiment locks serialize enrollment, checkout selection and overlap
checks. Time is assessed after lock waits; reward reservation rechecks the offer
window after wallet/budget waits. Each customer has an assignment-relative observation
window plus carryover protection. Control assignments hold the same exclusion lease.
Within an exclusion group, overlapping experiments require **both** frozen policies
to allow overlap; retained pairs surface a contamination warning. Different exclusion
groups intentionally do not exclude each other, so operators must group interfering
offers consistently. Pausing does not release an exclusion lease or erase a cohort.

A controlled checkout caller supplies `loyalty_experiment=AssignmentCheckout(
experiment_id, redeem_reward=False, enabled=True,
price_basis="synthetic_tax_exclusive")` alongside trusted `verified_customer_id`.
Manual version selection and assignment selection are mutually exclusive. Only
simulated payments are qualified; no public enrollment/selection/activation API is
added. Checkout never enrolls or rerandomizes. Every contextual order retains its
assignment or an explicit unverified/not-enrolled outcome, including control orders.
Treatment execution pins the original strategy version and the existing Stage-3
snapshot, ledger, financial compensation and liability history.

Baseline earning and requested existing rewards remain available. An existing reward
request takes priority over experimental redemption. Paused/archived programs or
experiments, expired windows, ineligible carts and already-exhausted budgets fall
back to ordinary checkout and record the reason. Insufficient experimental redemption
can still allow eligible earning. Corruption fails rather than silently relabeling a
customer as control. A budget/offer change while waiting for authoritative reservation
locks may reject the transaction and require a refreshed quote; it cannot overdraw.
Draft edits do not deactivate a previously assigned published version; pause/archive
is the explicit operational stop. Original order retries resolve before current
assignment lookup, preserving their original financial terms after later enrollment,
pause or edits. Expected-total/quote-token protections remain in force.

Exposure is separate: after actually rendering an assigned surface, a trusted
adapter calls `record_exposure(..., verified_customer_id=..., request_key=...,
kind="offer_surface_rendered" | "control_surface_rendered", surface=...,
source_ref=...)`. Source receipts are idempotent; the kind must match the assignment.
Late or paused exposures remain observable with warnings. Enrollment, quoting and
purchasing never invent exposure. Actual issuance, reservation, application and refund
usage stay in the existing ledger, joined through immutable order bindings.

The staff enrollment endpoint requires existing `growth.read`, tenant scope and the
configuration feature flag. It reports assigned counts (including nonbuyers), exact
expected-allocation fractions, explicit exposures, bound orders, ledger activity and
allowed-overlap warnings. These are descriptive diagnostics, not a sample-ratio
significance test, profit estimate or winner declaration. Future ITT reporting must
use **all original assignments** and all verified outcomes in the chosen window,
including ordinary orders without this checkout context. Contact-only orders cannot
be attributed to randomized identities. Identity coverage, contribution-cost coverage,
observation maturity and confidence intervals remain Stage-7 responsibilities.

`tests/test_loyalty_assignment.py` retains replay/restart, no-purchase enrollment,
control/baseline/refund, fixed redemption, version edits, explicit exposure, bilateral
overlap/carryover, raw-SQL scope/immutability, HTTP authorization/flag and PostgreSQL
race regressions. The lock-wait time regression and quote-to-reservation isolation
case preserve concrete review findings. No live customer enrollment, provider call,
production migration or experimentally established behavioral lift is claimed.

Stage-4 installed-wheel qualification (2026-11-04 UTC): **316 checks passed**:
199 SQLite cases and 117 PostgreSQL cases, no failures or skips. The SQLite run
explicitly deselects ten PostgreSQL-oriented cases; assignment/ledger races and
installed-schema query bounds execute on PostgreSQL. All 80 packaged source/asset
files match the tested checkout. Coverage includes existing identity, financial,
delivery, payment, capacity and bounded-readiness consumers. Full Ruff on new files,
focused undefined-name checks on affected modules and whitespace checks pass.
Evidence: shared `data/loyalty-verification/stage4-20261104/release/`, including the
wheel/hash manifest and `final/installed-{sqlite,postgresql}.{txt,xml}`. The existing
Starlette/httpx deprecation warning remains; no dependency was added or changed.


## Stage 5: financial simulator API

`POST /api/operator/restaurants/{business_id}/loyalty-config/simulator` uses the
existing configuration flag, tenant-scoped `growth.read` permission and staff CSRF
protection. It is available to authorized viewers as a nonpersistent calculation.
No new schema, execution enablement, enrollment, wallet operation or provider call
is involved. The staff console that will call this API remains Stage 6.

Example request (illustrative minor-unit amounts, not recommended reward rates):

```json
{
  "currency": "COP",
  "horizon_days": 90,
  "average_order_value_minor": 10000,
  "purchases_per_customer": "2",
  "customer_count": 1000,
  "contribution": {"type": "margin", "contribution_margin_bps": 3000},
  "reward": {
    "type": "proportional",
    "reward_value_bps": 200,
    "fulfillment_cost_bps": 200
  },
  "expected_redemption_bps": 5000,
  "operating_cost_minor": 100000,
  "assumed_purchase_lift_bps": 1000,
  "sensitivity": {"redemption_bps": [2500, 5000, 10000], "lift_bps": [0, 500, 1000]}
}
```

Basis points are integers: 1000 means 10%. Frequencies accept decimal strings
with at most six decimal places, or integer JSON values; floating-point JSON values,
booleans, scientific notation, nonfinite values and unknown fields are rejected.
The horizon is a declaration, not an instruction to multiply or annualize inputs.
All amounts use the same declared currency. AOV must be net of tax, refunds and
existing benefits, **before** the incremental experimental reward. Contribution
must likewise be before the new reward and program operating costs.

Contribution can alternatively be supplied as
`{"type":"order_contributions","source_reference":"cost-sheet-v1","orders":[
{"revenue_minor":10000,"contribution_minor":3000}]}`.
The calculator derives the revenue-weighted rate, sum(contribution)/sum(revenue),
and explicitly labels its extrapolation. Negative contributions are supported;
aggregate revenue must be positive and order contribution cannot exceed revenue.
These are caller-supplied observations, not authenticated outcome data or a causal
estimate. No customer/order identifiers are looked up or implicitly linked.

Three distinct reward models are supported:

- `proportional`: face value and fulfillment cost as basis points of sales.
- `per_purchase`: `reward_value_minor`, `fulfillment_cost_minor` and decimal-string
  `rewards_per_purchase`. For example `"0.2"` models an expected one reward per five
  purchases; it does not implement a customer-level buy-five eligibility counter.
- `fixed_issuance`: `reward_value_minor`, `fulfillment_cost_minor` and integer
  `issued_rewards`. This count stays fixed even if purchase frequency changes.

Fulfillment cost is the full economic cost when a reward is redeemed; a discount or
credit normally costs its face value. A product's supplied cost can differ from its
face value. Zero-cost assumptions for positive reward value produce a warning.
Redemption probability applies to eventual reward use. Expected reward cost is
neither immediate cash outflow nor accounting liability. Operating cost is fixed
for the supplied horizon. Only incremental costs belong in this input; baseline
costs already included in contribution must not be subtracted again.

With baseline orders O = customers × frequency, sales S = O × AOV, contribution
rate m, assumed purchase lift L, expected variable reward-cost rate c and expected
fixed reward cost F, the model calculates:

```text
projected sales = S × (1 + L)
expected reward cost = S × (1 + L) × c + F
incremental contribution profit = S × L × m − expected reward cost − operating cost
break-even extra sales = (S × c + F + operating cost) / (m − c)
```

The last expression applies when baseline sales and the effective incremental
margin are positive. A fixed issuance pool has c = 0; a per-purchase model derives
c from cost per purchase / AOV. Zero baseline sales give an undefined percentage
lift, and nonpositive effective margin with positive costs gives no finite
break-even. If costs at zero lift are zero, the scenario is already at break-even;
that does not mean it earns positive profit. Negative lift down to -100% is supported.
AOV, customer count and marginal contribution rate remain constant as frequency
changes. Budget caps, eligibility, per-order rounding/floors and behavior are not
inferred from published program configuration.

The example above yields baseline sales 20,000,000, projected sales 22,000,000,
expected reward cost 220,000 and estimated incremental profit 280,000 minor units.
At zero lift the program costs 300,000 including operations; extra sales contribute
29% after variable rewards. Break-even is therefore 1,034,483 extra minor units
(rounded upward), requiring 5.172414% lift (rounded upward). This is an algebraic
scenario, not observed improvement.

The pure `loyalty_simulator.simulate` function uses exact rational arithmetic.
Outputs round only once: monetary aggregates use integer minor-unit **strings**
so large totals survive JSON/browser parsing exactly; percentages and expected
order counts use six-place decimal strings. Half values round away from zero.
Break-even sales and lift round upward; profitability is evaluated before rounding.
Inputs retain safe-integer bounds, observed-order lists are capped at 1,000 and
sensitivity axes at nine values each (81 cells). Each cell includes full costs,
profit, break-even status and warnings under its declared lift/redemption pair.

Responses retain the input scenario, SHA256 scenario digest, calculation version
`loyalty-economics-v1`, rounding/assumption statements, `lift_is_assumed: true` and
`causal_effect_estimated: false`. No experiment winner or optimal reward is selected.
The result can inform an experiment design; Stage 7 must establish realized effects
using the original randomized cohorts and complete contribution-cost coverage.

Stage-5 installed-wheel qualification (2026-11-04 UTC): **152 checks passed**
(150 SQLite and two PostgreSQL consumers), with no failures or skips. This includes
39 simulator cases, hand-calculated examples, exact break-even/property checks,
fixed versus variable issuance, zero/negative margins, zero sales, no lift, full
redemption, large-integer serialization, sensitivity equivalence and strict inputs.
The actual staff endpoint proves flag/tenant/role/CSRF behavior and no order,
wallet, ledger or configuration-audit writes; existing configuration, rule previews,
growth, customer protection and assignment diagnostics remain compatible. All 81
packaged source/asset files match the tested checkout. New-file Ruff, affected-module
undefined-name checks and whitespace pass. Evidence is retained in shared
`data/loyalty-verification/stage5-20261104/final-release/` (wheel manifest and final JUnit/logs).
The earlier candidate is retained under `release/`. Final zero-sales review adds an
explicit regression: zero costs can already cover break-even, but percentage lift
remains undefined when baseline sales are zero.

## Reliability and refund contract (101-033)

Operational pause survives draft edits and publication. A definition with published
history can be paused even while its current proposal is a draft. Neither editing
nor publishing resumes execution; activation remains gated.

Verified ordinary/control orders now capture `baseline-paid-food-v1` in their
existing customer snapshot. This freezes the baseline enabled flag and earning
rate at checkout. Cumulative refunds constrain both future earning and previously
issued points, using compensating entries in the existing ledger. Reward-point
restoration uses cumulative paid-food proportions, with the full-refund remainder
returned exactly once. The original policy and mutable `baseline_refund_state`
are separate fields; the whole customer snapshot is **not database-immutable**.
Order locking/version fencing protects this projection. No new schema is required.

Pickup refunds reduce paid food directly. Partial delivery refunds require an
explicit food/fee allocation. The existing finance-authorized allocation endpoint
also accepts baseline orders without installing the experimental schema. Its line
IDs must belong to the order; baseline earning uses total paid food, so it does not
invent line-level tax or promotion allocations. Allocation evidence is retained
with its actor and cannot be revised through the service. Missing historical earning
policy or unknown delivery allocation holds redemption; the system does not borrow
today's rate. A historical order with no refund may establish its policy at first
completion, explicitly marked as such. Historical partial-refund policy gaps require
financial investigation or full-refund compensation rather than fabricated backfill.

Expire due lots under the account lock before recovering or repaying refund debt.
Returning a grant from an already-refunded order retires that source's assessed
clawback, whether the returned points have expired yet or not. It first reduces
that source's outstanding debt, then restores previously recovered value newest-first
with its original lot provenance/expiry. Cross-order retirement uses immutable
execution events; it does not acquire another order/state lock after the account.
Later compensation distinguishes retired expired points from retired valid returns.

Older hashed debt repayments without attributable execution events cannot be
safely reconstructed. Such a callback retains its authenticated payload in the
payment inbox; draining marks it for financial review and leaves canonical refund
compensation unapplied. This is a documented historical-data limitation, not an
automatically resolved refund. Current writers attach repayment provenance.

The review findings, reproduction conditions and verification limits are retained
in [the reliability audit](LOYALTY_RELIABILITY_AUDIT.md). Stage 6 and live activation
remain outside these repairs.

## Stage 6 — operator configuration and economics

The shared101workspace adds **Clientes → Fidelización**, at
`/workspace/customers?view=loyalty`. It uses the existing login, business context
and permissions. Programs, experiments, calculator and balances/costs are scoped
child views. Hidden views do not load their data. The current configuration flag
still controls the API; the console explains an unavailable deployment.

Operators can create/edit points earning and fixed-value discounts, dates,
eligibility, product exclusions, expiration, redemption limits, cost assumptions,
campaign/customer budgets and promotion stacking. Existing future reward types
retain their documents and historical versions. Publication retains the exact
reviewed revision/digest; editing a proposal never reassigns customers or resumes
a paused definition. Archiving retains history and is confirmed explicitly.

Experiment forms select immutable published versions, exactly one control and
allocations totaling100%, enrollment dates, observation/carryover windows, selected
customers, exclusion groups, overlap rationale and an analysis plan. Existing
benefits remain preserved. Available enrollment diagnostics remain descriptive;
configuration publication does not activate offers or enroll real customers.
Stage7 contribution-profit inference remains a separate release.

The calculator consumes the existing exact simulator, including percentage,
per-purchase and fixed-issuance costs, contribution margin or supplied order-level
contribution, operating cost, explicit redemption/lift assumptions and sensitivity.
Monetary strings are formatted through BigInt; inputs convert decimal text to
integer units without binary-float currency calculations. Changed assumptions mark
old output stale. No assumed lift is labeled as a measured effect.

New read endpoints, under the same `loyalty-config` root:

- `GET /overview`: committed read snapshot of account totals, historical lot cost
  grouped by currency, due expiration, unattributed balances, campaign budget usage,
  recent ledger, allocation holds and a separate general financial-review queue.
- `GET /{programs|experiments}/{id}/eligibility`: scoped participant/product names
  for the saved revision or immutable `version_id`; stale revision and foreign IDs
  cannot silently become a different review.

Neither endpoint creates accounts, expires points, reconciles or writes rewards.
The overview uses a separate read transaction: repeatable-read/read-only on
PostgreSQL and explicit BEGIN on SQLite, so concurrent earning cannot mix totals
from different commits. Lifetime/account point aggregates and money use integer
strings. Due lots are shown separately rather than silently expired by a GET.
Unattributed cost stays unknown. Only campaign `'*'` budget buckets are summed;
committed issuance cost is not added to outstanding lot cost as a second total.
Multi-currency program budget history is explicitly unvalued when ambiguous.

The hold list scans at most100recent partially-refunded orders and labels truncation;
it is not an exhaustive financial total. Open general financial reconciliations are
shown separately without inventing confirmed refund amounts. Recent ledger is
limited20entries. No new schema or dependency is introduced.

Mutation guards preserve creation keys and exact pending payloads after lost
responses, reconcile matching saved edits, honor optimistic revisions and prevent
late responses from navigating a different business. Read-only roles can inspect
and calculate; publication/editing/pause/archive require existing `growth.write`.

A loopback-only synthetic fixture is available via
`python -m world_model.restaurant_commerce.loyalty_workspace_demo --db PATH --port 8816`.
It reuses canonical services, creates no provider calls, and preserves operator
changes on restart. All example contacts, orders and values are fictitious.

The installed 0.26.0 artifact is qualified independently of the source tree; source,
wheel and installed-file parity is retained with the release evidence. Existing
Customers, Sales and Campaigns browser consumers are included. Rendered iterations,
role measurements and timing limits live in shared
`docs/product-design/loyalty-workspace-review.md`.

## Stage 7 — original-assignment contribution profit

The **Resultados** view under Clientes → Fidelización consumes the frozen experiment
run, original assignments and verified order identity snapshots. It includes every
assigned customer, including people with no orders, exposure or redemption. The
run's original version/window/protocol remain unchanged after new publications.
Verified ordinary purchases without a reward/assignment checkout binding count.
Guest contact matches do not establish identity; their coverage is reported separately.
An unverified contact match to an assigned customer's ID also makes that person's
contribution unknown; it cannot certify a missing outcome as zero. “Nonbuyer” means
no verified qualifying purchase observed, not proof of no purchases elsewhere.

Primary follow-up is `[assigned_at, evaluation_ends_at)`. Qualifying completed
purchases must be initiated after assignment and completed within that interval.
Completed purchases remain in frequency after later refunds; current confirmed
refunds reduce their net receipts and invalidate old cost evidence. Canceled orders
also require cost evidence, including unpaid cash orders with preparation/waste.
Unresolved accepted/paid orders and open financial reviews (including pending
checkouts without a confirmed capture) make contribution unavailable. Pre-assignment
checkouts cannot become new outcomes simply by completing after randomization.

Each arm uses its entire original randomized denominator. Missing/stale costs make
its profit unknown, rather than deleting the customer/order or replacing the cost
with zero. 30/60/90-day second-purchase rates mean at least two post-assignment
completed purchases. Their denominators explicitly include all assignments mature
for that particular period, including nonbuyers. They are descriptive secondary
measures, separate from the fixed primary window.

### Explicit deployment

Core checkout does not require SciPy. The optional analytics engine and test extra
declare `scipy>=1.14,<2`; the statistics library supplies Student-t quantiles and
allocation diagnostics rather than a bespoke distribution implementation. Install
`.[loyalty-analytics]`, stop writers, back up the database and explicitly run:

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-loyalty-measurement --offline
```

This one-table upgrade requires the prior configuration, execution and assignment
upgrades. It is repeatable, preserves populated commerce and installs scope/revision
and UPDATE/DELETE/replacement guards. Startup does not invent cost records or add
the optional table. Readiness verifies its complete protections when present.

Set both `COMMERCE_LOYALTY_CONFIGURATION_ENABLED=1` and
`COMMERCE_LOYALTY_ANALYTICS_ENABLED=1` (strict0/1 flags). Analytics defaults off;
enabling it requires the schema and optional dependency. It does not enable order
execution, enrollment, public customer authentication or real-provider rewards.

### Financial evidence, not inferred margins

The current order schema has no authoritative ingredient/fulfillment/fee accounting.
The new append-only `restaurant_loyalty_financial_evidence` is an observation history,
not a parallel customer/order/accounting authority. It records source reference,
actor, time, request digest, financial digest, revision and superseded observation.

Order costs explicitly supply signed integer `variable_cost_minor` (ingredients,
preparation, delivery, fees and pass-through tax deductions, net of recoveries) and
`additional_reward_cost_minor`. The latter covers actual non-discount fulfillment
plus recognized expected outstanding costs of habitual and additional rewards,
net of corrections. Discounts are already in captured net receipts and are not
subtracted again. A required `includes_estimate` declaration distinguishes estimated
costs; the source remains a financial staff assertion, not independently verified truth.

Per-customer contribution is the sum of canonical confirmed net receipts minus those
two cost inputs, less an equal share of the arm's declared full-experiment operating
cost. Operating evidence is required even for explicit zero and covers the original
variant population; new enrollment invalidates the old population digest. The full
operating amount is allocated over every assigned person, including nonbuyers.
Orderless reward activity without attributable cost makes affected profit unknown.

Financial fingerprints include the canonical order, captured/refunded payments,
confirmed partial refunds, open reconciliations and cost-relevant ledger/lot state.
Because baseline points have no origin lots, customer redemption/restoration
activity also reopens prior cost reviews conservatively; ordinary earning alone
does not. This lets finance release an earlier accrual rather than count its future
reward cost again after the actual discount is realized. Signed additional costs
can record these reversals. No historical baseline provenance is invented.
Changes require a new cost review. A concurrent stale correction conflicts; identical
requests replay one observation. UTC normalization makes SQLite/PostgreSQL replay
responses and fingerprints independent of session timezone. Historical observations
are never edited/deleted; a correction supersedes the prior version.

Expected pending cost from experimental order lots is shown separately. It excludes
unvalued baseline history and is not added to declared accrual cost a second time.
Budget commitments likewise are not additional profit costs. Monetary sums and
variances use integers/Fraction/Decimal; API money and fractional means are strings.
The browser uses BigInt for monetary display/rounding. No float-money aggregation.

### Protocol, uncertainty and warnings

New experiment documents may freeze `analysis_protocol`: method
`welch_bonferroni_v1`, family confidence90/95/99%, minimum customers per arm (at
least30), a sample-size/power rationale and a readout after enrollment plus full
follow-up. The declared minimum is not a guarantee of statistical power. An existing
version without this structure remains descriptive; later publication cannot add
a protocol retroactively to the frozen run.

The effect is treatment minus control mean contribution profit per original customer.
Welch variance/degrees of freedom use exact customer-level rational quantities;
SciPy supplies the dimensionless t critical value. Bounds round outward to integer
minor units. Bonferroni covers every planned treatment/control contrast, not repeated
looks or all pairwise treatment comparisons. Intervals are approximate and conditional
on supplied costs; they do not model uncertainty of estimated costs, untracked channels
or nonrandom assignment. See the primary [NIST Welch reference](https://www.itl.nist.gov/div898/handbook/prc/section3/prc312.htm)
and [SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html).

Intervals are suppressed for incomplete follow-up/open enrollment/early readout,
insufficient arm sizes, missing/late protocol, missing/stale financial evidence,
unresolved payments/orders, mixed currencies/payment simulation modes, incomplete
identity coverage, contamination or allocation imbalance/unavailable diagnostic.
Allocation checks require expected cells of at least5 and flag p<0.001. A zero
observed variance does not produce a misleading zero-width population interval.
No customer is dropped for any warning and no winner is automatically declared.

Contamination inspects other customer assignments across exclusion groups and
protection windows, plus off-protocol order rewards; it does not rely solely on
recorded overlap rows. Exposure counts use original follow-up; late receipts and
their warnings remain separate. Issuance and actual applied redemption are descriptive.
Report duration, original window, maturity and provider simulation mode are explicit.

### API and exports

Under the existing `loyalty-config` root, with analytics enabled:

- `GET /experiments/{id}/report` and `/report.csv`: scoped `growth.read`, coherent
  committed read snapshots, as-of/configuration/data revision stamps, aggregate CSV
  with formula-safe variant names. A CSV is a newly generated current reading.
- `GET /analytics/orders/{id}` and `/analytics/variants/{id}`: current financial
  fingerprint, latest evidence and at most20 historical revisions.
- `POST` to the same two evidence routes: `finance.resolve` and CSRF; body includes
  request key, expected revision, financial digest, source, estimate declaration and
  costs. Author identity comes from the staff session, never the request body.

GET/CSV never enrolls, earns, redeems, expires, reconciles or creates accounts. Cost
evidence changes only measurement history and staff audit, not payment/order/wallet
state. Report math uses all eligible data; the actionable order-cost list is bounded
to100 and labels truncation. Existing configuration lists remain unpaginated.
The API's `net_revenue_minor` fields currently mean confirmed receipts after refunds;
the UI labels them net receipts. Orders have no tax decomposition. Pass-through
deductions must be covered by supplied costs for contribution; no accounting revenue
or tax breakdown is inferred from gross receipts.

`PaymentRefund` has no universal historical event timestamp. Reports therefore use
current confirmed refunds for original-window orders and expose
`historical_financial_cutoff_available: false`; no historical financial as-of API
fabricates earlier knowledge. Preserve each CSV with its actual as-of/data revision.

The separate loopback fixture `python -m world_model.restaurant_commerce.loyalty_analytics_demo
--db PATH --port 8831` uses the combined workspace, simulated commerce and clearly
synthetic cost assumptions. Its real-time follow-up is incomplete. Matured/known-effect
cohorts and later refunds are exercised by tests with explicit synthetic clocks.
Demo restart preserves operator cost corrections. No provider spending or activation.

Rendered proof and final qualification live in shared
`docs/product-design/loyalty-analytics-review.md`.
