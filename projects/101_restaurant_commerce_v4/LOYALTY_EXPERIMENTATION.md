# Loyalty experimentation — stage 1

Implemented: a staff-authorized configuration foundation for multiple loyalty
strategies, immutable published versions and separately versioned experiments.
Existing points, checkout, refunds, promotions and baseline benefits are unchanged.

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
Only `0` and `1` are valid environment values. An explicit factory argument overrides
the environment. Enabled startup/readiness requires the complete configuration
schema. Disable the flag to remove the configuration routes without deleting history.
Partial or damaged schemas still fail readiness; disabling the flag is not a repair.

**There is no reward execution, experimental enrollment or analytics activation in
this stage.** Attempts to enter `active` fail. Publishing only records reviewed
rules. All capabilities report `execution_enabled: false`.

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
configuration-only extension points. No type executes at this stage.

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

## Remaining stages

Pure rule evaluation; version-pinned order earning/redemption and partial refunds;
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
