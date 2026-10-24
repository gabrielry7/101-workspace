# 101 World Model — Chat Handoff
**Date:** 2026-09-28  
**Branch:** `post-day21-bogota-business-universe`  
**Current HEAD:** `45c3c16` — `Repair targetability decision semantics`

---

# 1. What this chat has been about

This conversation has mostly been a post-Day-21 repair campaign for **101 / UnoCeroUno**, with one central goal:

> Make the system actually understand real Bogotá businesses well enough to know who they are, what they offer, how they can be reached, what is wrong with their digital presence, what 101 could improve, and eventually generate useful customer-facing output without inventing facts.

The original long-term system remains:

```text
Discover businesses
→ Understand business
→ Understand market
→ Diagnose
→ Design optimal presence
→ Build/change it
→ Measure
→ Learn
```

The original 30-day plan was organized as:

```text
Week 1 — World Model
Business Observatory
+ Business Genome
+ Website Audit

Week 2 — Search Market
Query Universe
+ Search Observatory
+ Competitor Graph
+ Maps Grid

Week 3 — Intelligence + Grader
Market coverage
+ website-vs-competitor
+ entity/content/technical/maps/AI gaps
+ 101 Grader

Week 4 — Counterfactual Website
BusinessGenome
+ MarketGraph
+ Grader
→ SiteSpec
→ generated site
→ automated QA
→ preview URL
```

The numbered engineering roadmap nominally reached **Day 21**, but the real-world trial showed that downstream generation/QA had advanced faster than the upstream information artery.

So:

```text
Day 21 nominally complete
→ Reality Trial
→ upstream evidence/data-flow gaps discovered
→ Day 22 frozen
→ post-Day-21 repair campaign
```

**Day 22 has still not started.**

---

# 2. Core architectural principle that emerged

The system now increasingly respects:

```text
observation
≠ candidate
≠ corroborated identity
≠ publishable Truth
≠ SiteSpec value
≠ rendered HTML
≠ customer-ready output
```

That distinction has become one of the strongest parts of the architecture.

The system is deliberately conservative:

- raw observations stay traceable;
- LLM outputs do not automatically become facts;
- reviews do not directly publish services;
- ambiguous identity does not become ownership;
- source-family independence is preserved;
- branch-specific evidence cannot silently leak into business-wide truth;
- missing evidence is not treated as a negative fact;
- operational failures do not erase prior factual observations.

---

# 3. Business Universe / Bogotá-scale discovery

The project moved from a tiny retained cohort toward a city-scale candidate inventory.

## 3.1 Canonical retained cohort

The original integrated Bogotá universe currently has:

```text
396 canonical businesses
```

A first targetability partition originally produced:

```text
TARGET_NOW      254
TARGET_LATER     39
LOW_FIT          59
UNRESOLVED       44
```

But that first classifier was too coarse.

Important defects found:

- all 254 `TARGET_NOW` businesses had the same generic explanation;
- all 59 `LOW_FIT` businesses were labeled that way only because of `NO_EVIDENCED_REACH_CHANNEL`;
- `TARGET_LATER` mixed genuinely weak/no opportunity with incomplete diagnosis;
- “missing contact” was being conflated with “low fit.”

This motivated a richer targetability audit.

---

## 3.2 Bulk Bogotá source trial

Instead of trying to enumerate Bogotá through Google Places alone, the project tested bulk sources.

### Overture

Real download:

```text
142,512 Overture place IDs
inside Bogotá official locality polygons
```

Important:

> This is not a business count.

Overture contains non-business destinations and duplicates/uncertain places.

### Public RUES

A public RUES dentistry subset was downloaded:

```text
7,938 entity rows
3,414 establishment rows
```

But the public schema lacked usable municipality/address/coordinate/contact fields for defensibly filtering those rows to Bogotá.

The RUES beneficiary portal remains the more promising municipality-filtered registry route, but it requires eligible merchant authentication.

---

## 3.3 Bogotá commercial inventory

The Overture inventory was classified offline:

```text
142,512 source records

114,028 commercial candidates
  8,246 noncommercial destinations
 20,238 uncertain
```

The commercial records resolved to:

```text
113,989 provisional operating-location candidates
106,142 with syntactically usable direct-contact evidence
```

These are still **provisional locations**, not verified canonical businesses.

Commit:

```text
e3195cf — Build auditable Bogotá commercial inventory
```

---

# 4. Prospecting pilot and what it taught us

A frozen 200-location pilot was created from the Bogotá inventory.

Initial narrow pilot:

```text
200 fixed locations
16 supported business-identity candidates
6 associated contact candidates
5 specific website findings
2 inspectable prospect proposals
```

But both proposals came from the first 20 debug cases.

The held-out 180 produced:

```text
0 proposals
```

So repeatable prospect yield was **not** validated.

## 4.1 Why the initial pilot failed

A later diagnosis showed the pilot was not actually exercising the full 101 system.

It was too narrow:

- 106 / 200 had no eligible standalone site URL;
- 52 website attempts produced no titled HTTP-200 page;
- only 42 titled pages existed;
- 20 passed the v1 name rule;
- 16 reached candidate identity.

More importantly, the pilot did **not** call the full production:

- Truth;
- Genome;
- Instagram;
- WhatsApp;
- full diagnostic services.

It also exposed a real attribution bug:

> a directory vendor email was being counted as the veterinary clinic’s contact.

That was fixed.

## 4.2 Integrated replay

The repaired replay used the canonical system more correctly.

Results:

```text
200 cases
6 supported candidate identities
5 cases with attributed contact routes
5 cases with technical findings
0 defensible prospect proposals
```

Both original debug proposals became unresolved.

One important success:

```text
106 cases previously stranded by "no eligible standalone URL"
→ 105 received assessment of saved source evidence
```

So the system became more complete without manufacturing prospects.

Commit:

```text
d570b7d
```

---

# 5. Current Gate C state — prospecting / targetability

The latest targetability semantics repair is:

```text
45c3c16 — Repair targetability decision semantics
```

The frozen 200-case replay now produces:

```text
0 supported prospect proposals

5 promising but incomplete
3 currently without an attributed reach route
34 identity unresolved
158 insufficient diagnostic
0 fully assessed as low opportunity
```

This is a much healthier partition because it no longer confuses missingness with low fit.

Examples:

- **DOAK’ (#10)**:
  - Website Intelligence found three specific site issues;
  - commercial effect remains untested;
  - therefore no proposal.

- **Geserprosas (#2)**:
  - identity unresolved.

- **Veterinary directory case (#181)**:
  - directory vendor email remains third-party evidence;
  - not attributed to the clinic.

These are agent-inspected cases, **not human verdicts**.

Current review queue:

```text
32 checksum-frozen cases
Human reviews completed: 0
```

No fresh sample has yet been drawn.

Therefore:

```text
GATE C = OPEN
```

The 200-case replay and the 396-business projection still do **not** establish repeatable prospect yield, citywide prevalence, or Bogotá-wide targetable-market size.

---

# 6. WhatsApp work

WhatsApp became one of the strongest real evidence experiments in this chat.

## 6.1 Public surface

A public WhatsApp landing-page acquisition path was built for:

- public display name;
- avatar reference/hash;
- public identity presentation.

The public cohort completed:

```text
51 / 51 public requests
```

## 6.2 Protocol surface

A `whatsmeow`-based WhatsApp Business Profile acquisition CLI was built.

The first version suffered a session lifecycle bug:

```text
link
→ status yes
→ successful query
→ process exits
→ status no
```

This was traced to session/device selection semantics, not normal `Disconnect()`.

Repair:

```text
75a1af2 — Fix WhatsApp session lifecycle persistence
```

The fix introduced:

- `GetAllDevices()`-based linked-device selection;
- deterministic paired-device selection;
- worker refusal before network if no paired session;
- real `LoggedOut` event recording;
- cohort-wide stop on `SESSION_UNAVAILABLE`;
- retryable `QUERY_FAILED`;
- preservation of pairing across normal `Disconnect()`.

The invariant was empirically proven:

```text
linked yes
→ successful worker
→ linked yes
```

## 6.3 Final protocol cohort

Final semantic result:

```text
51 unique candidate phones

36 SUCCESS_BUSINESS_PROFILE
15 NOT_ON_WHATSAPP
0 unresolved
```

So:

```text
36 / 51 = 70.6%
```

of this deliberately selected phone cohort yielded structured WhatsApp Business Profiles.

This is **not** a Bogotá-wide WhatsApp prevalence estimate.

---

# 7. First-party content bridge / site content

A generic fail-closed first-party content bridge was built.

Commit:

```text
b2bbf3e
```

It can extract source-backed descriptions and offerings from verified first-party pages, pass qualifying evidence through Truth, and render approved content.

Measured retained cohort:

```text
52 website-associated canonical businesses
33 had pages passing website-relationship check
3 also passed exact-name linkage
2 gained publishable substantive facts

Published:
7 services
1 description
```

Three-case regression:

```text
0 / 3 customer-ready
→ 1 / 3 customer-ready
```

This was explicitly **not** treated as cohort readiness.

## 7.1 Identity-gate audit

The 33 → 3 drop was explained:

```text
52 retained website associations

19 no eligible verified page
33 remain

22 no eligible website.presented_name observation
11 remain

8 recorded name mismatch
3 pass
```

The exact-name gate was not removed because the existing website relationship only establishes:

```text
provider URL
+ same-domain crawl
```

not full business/branch identity.

A branch-scope leak was fixed:

> location-specific services/products/descriptions can no longer enter a business-wide or different-branch SiteSpec.

An isolated PostgreSQL replay through production services matched offline counts:

```text
3 names
7 services
1 description
```

Two qualifying location-bound sites built.

But:

```text
only 2 of 7 approved offerings reached service-page HTML
```

That exposed a downstream rendering/data-flow loss.

---

# 8. Site generation / QA gates

The project now has a working:

```text
Truth
→ SiteSpec
→ Compiler
→ Generated Site
→ Browser QA
```

with real rendered tests.

Important recent commits:

```text
9f7cefd — Fix SiteSpec service rendering completeness
832b534 — Close post-Day21 engineering integrity gate
a0042a6 — Prove end-to-end generated-site repair path
45c3c16 — Repair targetability decision semantics
```

Current closure state:

```text
Gate A
= bounded engineering-integrity proof exists

Gate B
= OPEN
  32 unexplained approved-fact losses
  79 failing QA check keys

Gate C
= OPEN
  0 supported prospect proposals
  human review pending
```

Therefore:

```text
POST-DAY-21 REPAIR CAMPAIGN = NOT CLOSED
DAY_22_BLOCKED
```

---

# 9. Review Acquisition

The system originally had the Google Places ~5-review sample limitation.

That was expanded with a deeper DataForSEO review-acquisition path.

Architecture:

```text
RawArtifact
→ ReviewObservation append-only ledger
→ latest Review projection
→ ReviewEvidence
```

Deep-review transport supports:

- exact place-ID binding;
- bounded depth;
- task submission;
- persisted provider task IDs;
- collection/resume;
- request fingerprints;
- no duplicate paid submission when a pending task already exists.

---

# 10. Review Intelligence — the recovered subsystem

A major discovery in this chat was that Review Intelligence had been built much more deeply in an earlier prototype:

```text
~/Downloads/review_semantic_bakeoff
```

The historical prototype already contained:

```text
ReviewIntelligenceEngine
ReviewSemanticExtractor
SemanticEvidenceValidator
CategoryRegistry
ReviewAnalyticsEngine
ReviewBusinessInsightEngine
ReviewDiagnosticEngine
ReviewBusinessBriefBuilder
ReviewIntelligencePipeline
```

And the intended full pipeline was:

```text
raw public reviews
↓
deterministic + semantic extraction
↓
analytics
↓
business insights
↓
diagnostics / prioritization
↓
ReviewBusinessBrief
```

The semantic provider path explicitly distinguished:

```text
valid semantic empty result
≠ provider failure
```

## 10.1 Historical provider evidence recovered

The prototype contains retained live provider results:

```text
NVIDIA: 44 / 44 completed requests
Groq OSS 20B: 37 / 44 completed requests
```

This corrected the historical-memory gap.

It does **not** prove current credential availability, current endpoint availability, current zero-cost billing, or current accuracy on the dental corpus.

---

# 11. System registry / persistent project memory

Because the project was starting to forget already-built systems, a persistent capability registry was added.

Files:

```text
docs/SYSTEM_REGISTRY.md
docs/subsystems/*.md
docs/system-registry.json
```

The registry tracks subsystem ownership, code entry points, real-data proof, and distinct status dimensions.

Important distinction:

```text
IMPLEMENTED
INTEGRATED
REAL_DATA_PROVEN
HUMAN_VALIDATED
PRODUCTION_READY
```

are separate.

`AGENTS.md` now requires an **existing-capability check** before substantial new work.

This prevents agents from inventing another parallel subsystem when an existing owner already exists.

Commit:

```text
97c4981
```

Runtime-proof semantics were later added:

```text
historically verified
≠ available in current shell
```

Zero-network doctor:

```bash
python scripts/provider_doctor.py
```

Commit:

```text
a40bcf2
```

---

# 12. Review Intelligence reconciliation

A prototype → canonical reconciliation was performed.

Result:

> The prototype already had category-aware deterministic and semantic extraction, analytics, diagnostics, prioritization, and a substantial business brief.

The canonical repo had preserved extraction, quote validation, and the historical `ReviewIntelligenceService`, but had reduced much of the richer analysis/brief.

The reconciliation recovered a bounded subset **inside the existing canonical pipeline**:

- richer sample metrics;
- freshness measures;
- source-linked theme diagnostics;
- customer-mentioned offerings;
- operational signals;
- risks;
- investigation candidates;
- richer business brief;
- explicit semantic run states:
  - `not_run`
  - `partial`
  - `failed`
  - valid empty result.

It deliberately did **not** copy:

- the old parallel orchestrator;
- weaker attribution rules;
- numerical opportunity scores.

Commit:

```text
9f310e2
```

---

# 13. Dental deep-review canary

A real paid canary was run using exact retained Google place IDs.

Cohort:

```text
4 dental locations
301 stored reviews
232 with text
```

Review Intelligence → Offering Intelligence produced:

```text
9 location-scoped offering candidates
across 3 businesses
```

No review-derived offering was published.

Provider cost for four accepted DataForSEO tasks:

```text
$0.0300
```

Two provider-adapter bugs were also fixed:

- missing required location code on submission;
- POST incorrectly used against the GET task-results endpoint.

---

# 14. Review semantic-boundary repair

Real review examples exposed semantic errors.

### Salud Bucal Familiar

A candidate for `limpieza dental` was falsely triggered by:

> “La limpieza es impecable”

which referred to facility cleanliness.

### Dientes y Sonrisa

An implant-support row incorrectly involved a UK dentist recommending implant/bridge while the focal Bogotá dentist actually performed a crown.

### DentiSalud Kennedy

Two orthodontics-treatment reviews were legitimate branch-scoped supports.

Commit:

```text
c663c91
```

On the same 301-review corpus:

```text
9 offering candidates before
8 after
```

Support-level change:

```text
39 original supports
28 positive remain
6 removed
5 uncertain
```

Important outcomes:

- “La limpieza es impecable” no longer supports dental cleaning;
- UK dentist implant/bridge mention no longer counts as focal-business support;
- a separate Dientes review still supports implant treatment performed there;
- DentiSalud Kennedy orthodontics supports remain.

But conservative filtering also removed four Dientes `limpieza` mentions that might describe real treatment.

So precision/recall remains unmeasured.

Independent human labels:

```text
0
```

---

# 15. Offering Intelligence

A bounded multi-source Offering Intelligence layer now exists.

Sources proven in some form:

```text
website evidence
Instagram candidate evidence
review candidate evidence
```

Key principle:

> candidate evidence is not automatically publishable business Truth.

A no-website business can now yield an offering candidate from stored reviews without that review claim becoming a publishable service fact.

Instagram replay:

```text
23 saved Instagram profiles
6 offering spans
5 candidate groups
0 publishable due missing independent relationship assessment in that replay
```

Examples:

- `1485dentalspa`
  - “Implantes Dentales”
  - candidate only because profile ownership remained ambiguous in that replay.

- `dentisteriadigital`
  - “Alineadores”
  - “Brackets”
  - normalized into orthodontics candidate.

- `aquaodonto`
  - “Todas las especialidades”
  - correctly produced no specific offering.

---

# 16. Semantic LLM work — current state

A richer category-aware semantic review path exists in the architecture.

The intended model input is:

```text
full review text
+ focal business identity
+ branch/location context
+ observed business category/domain context
```

Category context is:

```text
INTERPRETATION PRIOR ONLY
```

not evidence.

The semantic contract includes concepts such as:

```text
provider_role:
FOCAL_BUSINESS
EXTERNAL_PROVIDER
REVIEWER
UNKNOWN

event_type:
PERFORMED
CURRENTLY_OFFERED
SCHEDULED
RECOMMENDED
DISCUSSED
REFERRED_ELSEWHERE
HYPOTHETICAL
HISTORICAL
UNKNOWN

stance:
AFFIRMED
NEGATED
UNCERTAIN

sentiment:
POSITIVE
NEGATIVE
NEUTRAL
MIXED

branch_scope:
THIS_LOCATION
BUSINESS_GENERAL
OTHER_LOCATION
UNKNOWN
```

Exact quote validation remains mandatory.

No semantic provider run has yet been executed on the current 232-text dental corpus in the canonical repo.

Current issue is runtime/provider access, not missing architecture.

---

# 17. Human review is still the biggest empirical gap

Across several subsystems, agent inspection exists but independent human validation remains:

```text
0 completed reviews
```

There is now a frozen human review queue:

```text
32 cases
```

This is needed to evaluate:

- prospecting decisions;
- contact attribution;
- offering precision;
- semantic-vs-deterministic disagreements;
- false positives;
- false negatives.

No agent review should be counted as an independent human verdict.

---

# 18. Current repair gates

## Gate A — Engineering integrity

Status:

```text
bounded proof exists
```

## Gate B — Generated-site completeness / QA

Status:

```text
OPEN
```

Known unresolved issues:

```text
32 unexplained approved-fact losses
79 failing QA check keys
```

## Gate C — Prospecting / real customer usefulness

Status:

```text
OPEN
```

Latest frozen 200-case partition:

```text
0 supported prospect proposals
5 promising but incomplete
3 without attributed reach route
34 identity unresolved
158 insufficient diagnostic
0 fully assessed low opportunity
```

Human reviews:

```text
0 / 32
```

Fresh validation has not yet run.

---

# 19. Current official roadmap state

```text
Day 21: nominally complete
Post-Day-21 repair campaign: still active
Day 22: NOT STARTED
```

The latest closure runner explicitly ended with:

```text
DAY_22_BLOCKED
```

because Gates B and C remain open.

---

# 20. Latest relevant commit chain

Current HEAD:

```text
45c3c16 — Repair targetability decision semantics
```

Recent commits:

```text
45c3c16  Repair targetability decision semantics
a0042a6  Prove end-to-end generated-site repair path
832b534  Close post-Day21 engineering integrity gate
9f7cefd  Fix SiteSpec service rendering completeness
769cdce  Triage Bogotá development matches with provisional labels
e6ac6dd  Analyze Google ID disagreements in Bogotá development cases
24c6895  Collect split Google Place ID evidence for Bogotá review queue
cd75e34  Add independent provisional Codex review of held-out business audit
240d435  Preserve Bogotá brand operator and lifecycle source evidence
00f4f79  Separate Bogotá ER audit from development review and add local map
```

Tracked worktree:

```text
clean
```

---

# 21. What is actually next

The project should **not** add another major subsystem right now.

## A. Close Gate B

Explain and repair:

```text
32 unexplained approved-fact losses
79 failing QA check keys
```

Goal:

```text
approved facts
→ SiteSpec
→ compiler
→ rendered HTML
→ QA
```

without silent information loss.

## B. Close Gate C

Use the frozen 32-case human review queue.

Need real human verdicts on:

- business identity;
- contact attribution;
- whether the observed issue is real;
- whether the issue justifies an actual 101 proposition;
- whether the business is worth investigating/approaching;
- what evidence is still missing.

Then draw a **fresh bounded validation sample** after the current system is frozen.

Goal:

> prove that 101 can repeatedly turn business records into evidence-backed, inspectable prospects.

## C. Run semantic Review Intelligence on the already-paid dental corpus

Once a provider is callable:

```text
232 saved review texts
→ existing Review Intelligence semantic backend
→ exact-quote validation
→ deterministic vs semantic comparison
→ disagreement queue
→ human labels
```

Do not redesign Review Intelligence again.

## D. Then go cross-vertical

Once review semantics are validated:

```text
dentistry
→ restaurants
→ beauty
→ mechanics
→ vets
→ gyms
→ professional services
```

Same architecture, different category context.

---

# 22. Major lesson from this chat

The project’s biggest risk is no longer:

> “Can we build the pieces?”

The bigger risks are:

```text
1. forgetting systems we already built;
2. building parallel versions of existing capabilities;
3. proving each subsystem on a different cohort without proving composition;
4. treating tests as product proof;
5. lacking independent human validation;
6. endlessly repairing architecture without closing the final usefulness loop.
```

The system registry was introduced specifically to stop capability amnesia.

The outcome-first reporting contract was introduced so Codex must always show:

- what actually ran;
- what a person would see;
- concrete success/block/ambiguous examples;
- what failed;
- what remains unproven;
- exact artifacts;
- tests and commit.

---

# 23. Short state summary

```text
BOGOTÁ INVENTORY
~114k provisional commercial candidates
→ city-scale candidate base exists

EVIDENCE SOURCES
Google / website / reviews / Instagram / WhatsApp / Overture
→ integrated to varying depths

REVIEW INTELLIGENCE
rich deterministic + semantic architecture recovered
→ real 301-review dental corpus exists
→ semantic real run still pending
→ human validation still 0

OFFERING INTELLIGENCE
works across website / Instagram / review candidate evidence
→ review claims remain non-publishable

WEBSITE GENERATION
Truth → SiteSpec → Compiler → HTML works
→ approved fact loss still exists
→ QA failures remain

PROSPECTING
semantics repaired
→ 200-case frozen replay still 0 supported proposals
→ human review queue ready
→ fresh validation not yet run

POST-DAY-21
Gate A: bounded proof
Gate B: open
Gate C: open

DAY 22
blocked / not started
```

---

# 24. Immediate operating principle

Before any new subsystem:

```text
1. Read SYSTEM_REGISTRY.
2. Check subsystem history.
3. Search git history.
4. Reuse existing owners.
5. Prove real product output.
6. Prefer human-reviewed evidence over another layer of architecture.
```

Current practical priority:

```text
close Gate B
+
human-review Gate C
+
run the existing semantic Review Intelligence on real saved reviews
```

—not another redesign.
