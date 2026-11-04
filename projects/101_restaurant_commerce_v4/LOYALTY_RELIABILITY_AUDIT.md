# Loyalty stages 1–5: reliability and code-quality audit

Review baseline: `c743dc9cc9a1a9af7f76c925b81a766c7ca6b6cf` (0.18.1),
2026-11-04. Task 101-033. Application code remained unchanged during investigation.
The user authorized review first, then small repair batches with regression proof.
Stage 6 is not part of this change. Severity reflects customer/money consequences,
not stylistic preference. Line references below identify the frozen baseline.

## Confirmed findings

### A1 — High: editing silently defeats a pause

- Files: `src/world_model/restaurant_commerce/loyalty_config.py:214,282`;
  consumers `loyalty_assignment_checkout.py:106,130`, `loyalty_execution.py:135,196`.
- Trigger: pause a published program or experiment that has assigned customers,
  then edit a proposal. Editing sets the parent to draft; historical assignment
  execution accepts draft parents. Conversely, edit an executing parent first,
  then try to pause it: the API permits pausing only a published parent.
- Expected: operational pause survives drafting/publication; running historical
  rules can always be paused. Actual: the next quote selects the incentive again,
  and the next pause request is rejected.
- Impact: operators unintentionally resume costs while editing and cannot stop
  some running historical offers through the configuration lifecycle.
- Proof: actual SQLite configuration → enrollment → quote probes reproduced both
  program and experiment paths. Existing tests often directly mutate ORM state,
  bypassing the defective public lifecycle.
- Smallest fix: preserve paused state across edits/publication; allow pause for a
  draft with retained published history. Keep activation unavailable and require
  an explicit reviewed resume contract rather than inferring resume from an edit.
- Regression: both kinds × pause-before-edit/edit-before-pause, publication while
  paused, and actual checkout records no incremental snapshot while paused.

### A2 — High: ordinary/control points ignore partial refunds

- Files: `refunds.py:68`, `loyalty_execution.py:563`, `growth.py:275–303`.
- Trigger: a verified ordinary/control order is partially refunded, before or
  after completion. The partial-refund caller invokes experimental compensation,
  which returns false for unmarked orders; no baseline compensation follows.
- Expected: retain only earned points supported by remaining eligible paid spend,
  using the original policy; no double reversal after retries or full refund.
  Actual: a completed 11,900 pickup order earns 11 points, then a confirmed 5,000
  refund leaves all 11 instead of 6 at the original 1,000 earning rate. A partial
  refund before completion also leaves earning based on the original total.
- Impact: rewards remain spendable on refunded purchases; control and treatment
  arms handle the same financial event differently.
- Proof: actual synthetic checkout/payment/completion/refund consumers in SQLite.
- Smallest sound fix: freeze new-order baseline policy, retain cumulative assessed
  reversal separately from recovered balance/debt, and post compensating entries
  to the existing ledger under the existing Order/account locks. Missing historical
  policy and ambiguous delivery allocation must be held for review rather than
  borrowing today's rate or inventing returned products.
- Regression: before/after-completion refunds, chunking/replay, spent-point debt,
  partial→full, rate edits, delivery ambiguity and missing policy provenance.

### A3 — High: expiration scheduling changes refund debt

- Files: `loyalty_execution.py:569–618`, `growth.py:308–324,332–361`.
- Trigger: A earns 11 nonexpiring points; another order reserves all 11; C earns
  11 points expiring tomorrow. Advance two days and refund A.
- Expected: expired C points cannot pay A's clawback. Actual: without expiration
  maintenance first, debt is 0; with maintenance first, debt is 11.
- Impact: maintenance scheduling changes financial entitlement and permits expired
  value to erase valid debt. Both paths can still reconcile the nominal ledger.
- Proof: two actual SQLite execution/refund paths differing only in prior expire().
- Fix: expire due lots under the account lock before refund recovery and debt
  settlement, including ordinary earning/release callers.
- Regression: maintenance-first versus lazy-expiry paths produce identical balances,
  debt and history; include subsequent earning and replay.

### A4 — High: expired returns make debt depend on callback order

- Files: `loyalty_wallet.py:58–113`, `loyalty_execution.py:600–630`.
- Trigger: A earns 11 points expiring in one day; B spends all 11 for a fixed reward
  and earns none. After expiry, fully refund both orders.
- Expected: the same final entitlement regardless of callback order. Actual:
  A→B leaves debt 11, B→A leaves debt 0, both available balances 0 and nominal
  reconciliation true. Explicit expiration before each refund does not fix this.
- Impact: a fully unwound purchase/reward cycle can leave an unjustified customer
  debt, blocking future redemptions.
- Proof: actual SQLite checkout/completion/refund consumers in both orders.
- Fix: when returned source points expire, reconcile their retirement against that
  source's assessed reversal. Cap by original source/reversal and handle outstanding
  debt and value already recovered; never forgive unrelated debt.
- Regression: both callback orders, partial return prefixes, repeated notifications,
  unrelated debt and subsequent valid earnings that already repaid the source debt.

### A5 — Medium: campaign-cookie changes break checkout retries

- Files: `api.py:610–615`, `service.py:1275–1289,1307`, `web/index.js:267–308`.
- Trigger: a successful campaign-attributed checkout loses its response; its
  campaign visit cookie changes/disappears/expires before identical POST retry.
- Expected: same payload/key returns the original order and attribution. Actual:
  current cookie attribution changes the server-generated fingerprint, yielding409.
  Explicit recovery still returns200 and only one order exists; no duplicate order
  was demonstrated. The frontend retries its retained intent, so reload/recovery
  is currently needed to escape the conflict.
- Proof: actual in-memory ASGI campaign visit → checkout → cookie deletion → retry;
  same cookie gives200, removed cookie409, recovery200, order count1.
- Fix: replay against original persisted server attribution, keeping public payload
  and secret checks intact; apply current attribution only to first creation.
- Regression: absent/replaced/expired cookies, original attribution/credit retained,
  one order/payment, changed client payload still conflicts; historical fingerprints.

### A6 — Medium: older active delivery loses its dispatch action

- Files: `web/delivery.js:35–41`, `api.py:752–760`, `service.py:889–898,1805–1816`.
- Trigger: one paid/accepted delivery is followed by at least50 newer pickup orders.
  Dashboard independently fetches latest100 deliveries and latest50 orders.
- Expected: the active delivery remains dispatchable. Actual: delivery is present
  but its missing joined order hides the dispatch button. Direct backend dispatch
  still succeeds; this is a UI data-join failure, not invalid order state.
- Proof: SQLite fixture with one accepted delivery and50 later completed pickups:
  delivery quoted, orders50, joined orderNone, dispatch hidden, backend succeeds.
- Fix: supply the necessary associated order summary with each delivery or fetch
  missing scoped order details; increasing a finite limit only postpones the bug.
- Regression: actual browser with >50 mixed orders retains the actionable delivery;
  preserve business scoping and stale-response fencing.

## Suspected risks and optional cleanup

- No additional suspected issue is promoted to a confirmed bug without evidence.
- Configuration list/history (`loyalty_config.py:85–124`) makes N+1 SELECTs and
  returns all version documents. A four-program probe performs five SELECTs.
  Optional future pagination/bulk loading reduces payload/query growth; no current
  production latency claim or arbitrary pagination behavior change is made here.
- Full lint reports existing unused imports, duplicate fixture imports and style
  issues. Some flagged imports register SQLAlchemy metadata and must remain.
  No dependency/subsystem is recommended for removal merely from a lint warning.
  Cleanup is separate from the monetary/reliability repairs above.

## Scope and checks

Inspected flows: customer cart/quote → double-click prevention → checkout request
fingerprint/recovery → durable payment intent/provider boundary → order fulfillment;
staff session/CSRF/tenant checks; ordinary and incremental points/redemption →
expiration/refund/debt; configuration draft/review/publish/pause → frozen variants →
independent enrollment/overlap/exposure → assigned checkout; simulator inputs,
exact arithmetic and sensitivity. Existing campaign attribution and delivery screens
were followed where they consume these flows. The Stage6 UI and Stage7 causal
analytics do not yet exist and are not implied by API/service tests.

Read-only build checks completed: offline wheel build, pip dependency compatibility,
Python compile, and syntax checks for all nine shipped JavaScript files passed.
Full Ruff did **not** pass: isolated rules reported309 findings, inherited workspace
rules946. Native JSON preserves exact categories/files; no F821/F823 undefined-name
finding appeared. There is no project type-check command/configuration and no mypy
or pyright executable in this environment; compilation is not a type-check pass.

The initial two broad baseline test attempts hit the shared tmpfs per-user quota:
SQLite disk-I/O failures and PostgreSQL catalog/WAL write errors. These are retained
as infrastructure failures, not application findings or passing qualification.
Completed task-owned disposable directories were removed; native logs, wheels and
JUnit remain. Tests were relocated to workspace disk. Final counts and repair
regressions will be recorded below after execution, including any remaining failures.

Dependency review checked the actual toolchain inventory and hashed runtime lock.
Installed/locked Starlette1.10.0 and h11 0.16.0 are outside these documented affected
ranges: [Starlette Range parsing](https://github.com/Kludex/starlette/security/advisories/GHSA-7f5h-v6xp-fcq8)
(patched0.49.1), [Host URL parsing](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr)
(patched1.0.1), [urlencoded form limits](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq)
(patched1.3.1), and [h11 chunk parsing](https://github.com/advisories/GHSA-vqfr-h8mv-ghfj)
(patched0.16.0). These are not findings against this artifact. Reviewed official
[FastAPI](https://github.com/fastapi/fastapi/security/advisories) and
[Pydantic](https://github.com/pydantic/pydantic/security/advisories) advisory indexes;
this is a scoped advisory review, not an exhaustive vulnerability scan or certificate.
Existing Starlette TestClient/httpx deprecation is a future migration concern;
current compatibility checks pass. Broad package minimums alone are not evidence
that the qualified deployment lock installs a vulnerable version.

Unverified: live payment/courier/email/WhatsApp behavior, production data/migrations,
HA/multiple deployment nodes, sustained load and provider outage recovery outside
synthetic adapters. Concurrent scanner/security and WhatsApp branches owned by
101-027/032 were not modified or treated as integrated evidence. The OpenAI
[repair-loop guidance](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
and [CLI review documentation](https://learn.chatgpt.com/docs/codex/cli) were consulted;
this report uses executed reproductions and does not claim a `/review` command ran.
