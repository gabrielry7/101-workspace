# Trail of Bits methods applied to this execution

This is an application of the five requested SKILL.md procedures to the existing
commerce owner, not a claim that the full Trail of Bits plugin executed. Native
plugin orchestration was unavailable. A delegated context/property worker produced
the executable property suite but its review turn ended in a tool policy error;
that incomplete agent run is not counted as completed independent review.

## Sources and provenance

Task-local copies were read at `/tmp/101-adversarial-skills/`. Four skills came from
`https://github.com/trailofbits/skills`; insecure-defaults required historical commit
`9ea55c598763f7cb87ab56933d773d7dc34344a0`, because its former skill path was removed
in the current repository. Skills guide investigation; installed files alone do
not constitute execution evidence. See the run receipts for executable counts.

## audit-context-building — manual application; native workflow PARTIAL

Actual path: HTTP request → Pydantic schemas → API identity/operator checks →
RestaurantCommerceService → SQLAlchemy/PostgreSQL → payment/delivery provider →
local commit → event sink. The disposable wrapper replaces only provider adapters
with networked, inspectable synthetic services. It imports the installed wheel,
not source. Seeded business A and B have separate customers; the application has
no staff membership table, customer login, messaging sender, or independent worker.
Those absences are release gaps, not simulated capabilities.

Critical trust boundaries: public customer fields do not establish customer identity;
order capabilities grant one expiring resource; the global operator token grants
all businesses; payment signatures authenticate webhook bodies but do not solve
financial reconciliation. Provider acceptance and the application transaction are
not atomic. The current checkout calls the provider before committing its order.

## differential-review — focused diff and actual consumers

Starting owner revision: 5390a9d (0.5.1); focused fix: 45e2d40 (0.5.2).
Reviewed schema/API changes against request parsing, both signed webhook routes,
FastAPI error handling and generated OpenAPI consumers. Git blame traced direct
`detail=exc.errors()` in both webhook handlers to original 11969c6; the previous
046bae4 fix covered the global RequestValidationError handler but not these paths.
The fix reuses that serializer rather than adding a third error contract.

The new integer bounds match PostgreSQL INTEGER columns. Recursive NUL rejection
protects decoded body strings and mapping keys; path/query rejection protects
identifiers outside body schemas. OpenAPI now describes the real domain error
shape. Readiness overrides the generic 503 error model with its own status shape.
No financial state machine, operator authentication scheme or provider was replaced.

## insecure-defaults — trace configuration to runtime behavior

The test deployment explicitly enables demo payments, synthetic secrets and a high
rate limit to expose business/load failures. It is NOT a production configuration
qualification. Production configuration has fail-closed secret/demo guards in the
API; existing tests exercise those guards. The global operator token remains a
cross-business authority by design: browser regression intentionally requires the
future isolation contract and remains red until scoped staff identities exist.
No real provider credentials or model calls are used.

## variant-analysis — expanded both sides of each reproduced bug

Live generated requests found PostgreSQL NUL and integer overflow 500s. Variants
cover customer names, cart identifiers/modifiers, idempotency keys, reward integer
fields, decoded URL values, NaN amounts and lone-surrogate signed webhook bodies.
Both payment and delivery webhooks now route validation failures through the safe
serializer. Minimized cases live in `tests/test_postgres_fuzz_boundaries.py` (11
cases); live Schemathesis and Hypothesis reruns provide PostgreSQL evidence beyond
SQLite unit coverage. Remaining service/financial failures are reported separately.

## property-based-testing — executed generated state sequences

`properties.py` uses Hypothesis seed101027, 30 examples per generated property,
fresh intents per example and real HTTP. It checks cart totals, exact/conflicting
replay, wrong capabilities, invalid signatures, order transitions, consent, rejected
inputs and malformed signed webhooks. A late payment after cancellation test
requires a reconciliation record; it deliberately remains failing while that
feature is absent. The request stream, transition counts, JUnit and minimized
failures are retained in each run's properties directory. No healer skips failures.

## Limits

This bounded assessment is not exhaustive. Native Trail of Bits workflow execution
is PARTIAL, even though the procedures above resulted in runnable regressions.
Physical old devices, customer login, scoped staff, live providers, migration from
an existing production PostgreSQL database and durable recovery remain unqualified.
