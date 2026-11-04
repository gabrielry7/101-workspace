# Loyalty experimentation — stages 1–3

Implemented: a staff-authorized configuration foundation for multiple loyalty
strategies, immutable published versions and separately versioned experiments.
Stage 2 adds deterministic points/fixed-value rule previews against published versions.
Stage 3 adds controlled versioned execution through the existing checkout, wallet and
financial workflows. Ordinary baseline benefits remain; new orders can add an exact
published strategy under the synthetic execution gate described below.

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
| GET `/capabilities` | Explicitly reports configuration-only capability |
| GET/POST `/programs` or `/experiments` | List or create a draft |
| GET/PUT `/{kind}/{id}` | Inspect history or edit draft with expected revision |
| POST `/{kind}/{id}/publish` | Publish the exact reviewed revision and SHA256 digest |
| POST `/{kind}/{id}/state` | Pause a published definition or archive it |
| POST `/programs/{id}/versions/{version_id}/preview` | Evaluate a hypothetical cart using that exact published version |

Create bodies contain `request_key` and `document`. Retrying the same creation key
with the same initial document returns its existing resource; a different document
conflicts. Concurrent first creation can return 409; retry the same request key.
Edit bodies contain `expected_revision` and `document`. Publish bodies contain
`expected_revision` and the `digest` returned by GET. A successful publish increments
the working revision and creates a distinct permanent version ID. Retrying the
original publish returns that same version, including after subsequent draft edits.
A stale revision or digest conflicts. Concurrent writes cannot silently overwrite
one another. Editing creates a new draft while retaining all published versions.
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
algorithm version for later enrollment; it does not assign customers yet.

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

Version-pinned order earning/redemption and partial refunds;
persistent randomized enrollment; simulator; staff configuration screens; and
intent-to-treat contribution-profit reporting remain pending. Customer authentication,
cost provenance and statistical analysis details are prerequisites for a pilot.
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
real economics, assignment and the remaining release stages are still pilot gates.

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

Existing-order writers acquire Payment → Order → execution state → account →
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
Stages 4–7 (assignment, simulator, staff configuration UI and ITT profit reporting)
remain separate delivery stages. No winner or behavioral lift is claimed.
