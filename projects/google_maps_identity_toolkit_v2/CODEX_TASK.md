# Codex task — Bogotá pair-review evidence + fast reviewer v2

Work in `/home/t/101-world-model` on the current active branch.

## Preflight

1. Read `AGENTS.md`, `HANDOFF.md`, `docs/SYSTEM_REGISTRY.md`, and any current handoff/state doc referenced there.
2. Require a clean tracked worktree. Preserve unrelated untracked user files; do not absorb them into the commit.
3. Inspect the current Bogotá pair-review implementation and the commits around:
   - `00f4f79` — separate Bogotá ER audit from development review and add local map;
   - `24c6895` — split Google Place-ID evidence;
   - `e6ac6dd` — analyze Google ID disagreements;
   - `769cdce` — provisional development triage.
4. Do **not** create a second reviewer or a new identity subsystem if the current components already exist. Upgrade the current path in place.

## Goal

Make human identity adjudication much faster and more informative while preserving
independence of held-out validation and provenance of the frozen packet.

The reviewer currently asks whether two source records identify the same particular
place. Add four things:

### A. Current Google visible-result/lifecycle observations

For every saved Google Place-ID candidate already present in the packet, support a
local persistent-Playwright enrichment pass that opens:

```text
https://www.google.com/maps/place/?q=place_id:<PLACE_ID>
```

and stores only visible review metadata:

```text
input_place_id
returned_google_name
status:
  CLOSED_PERMANENTLY
  CLOSED_TEMPORARILY
  OPEN_OR_UNMARKED
  UNKNOWN
  BLOCKED
visible_address?       # when reliably available
visible_category?      # when reliably available
visible_phone?         # when reliably available
final_url
observed_at
```

Requirements:

- one persistent Chromium profile;
- sequential requests;
- modest randomized pacing;
- durable cache/checkpoint;
- resume without duplicate probes;
- stop cleanly on CAPTCHA/challenge/block;
- no stealth/proxy/bypass work;
- no paid Google API calls;
- `UNKNOWN` rather than inferring open when the panel did not load cleanly.

This is **Google lifecycle/source evidence**, not canonical identity truth. Do not
write it to canonical Business/Truth and do not let it alter the matcher that
produced the frozen queue.

Also support the same visible status/name lookup by source name + source coordinate
for records that do not already have a Place ID.

### B. Explainable pair-review aids

Add a deterministic evidence-feature layer, separately namespaced from canonical
evidence and matcher decisions. Compute at least:

```text
name:
  strict normalized form
  core normalized form
  sequence similarity
  token overlap
  relation label

address:
  Bogotá abbreviation normalization
  structured street/cross/door numbers where parseable
  sequence/token similarity
  exact/similar/adjacent-corner/different-looking relation

phone:
  normalized exact match

domain:
  normalized exact match

category:
  broad family sets
  shared family
  weak compatibility/conflict relation

coordinate distance
```

Name normalization:

- case-insensitive;
- accent-insensitive;
- punctuation-insensitive;
- legal suffixes may be soft;
- Spanish articles/connectors (`el`, `la`, `los`, `las`, `de`, `del`, `y`) may be
  soft in a **separate core comparison**, but preserve the strict normalized form;
- do not strip branch/location tokens such as street numbers, `Norte`, `Chicó`, etc.

Address normalization must understand common Bogotá forms such as:

```text
Cl / Calle
Cra / Carrera / Kr / Kra
Av / Avenida
Dg / Diagonal
Tv / Transversal
```

Do not collapse addresses into a single equality bit. Example:

```text
Cl 82 # 9-09
Carrera 9 81-18
```

should be allowed to surface an adjacent/cross-street pattern rather than being
called identical.

Category is weak compatibility evidence only. `bar` ↔ `cocktail bar` is compatible;
`restaurant` ↔ `bakery` can share a broad food/drink family; category must never
establish identity alone.

Do **not** invent a new opaque aggregate score unless it is separately calibrated.
Keep the feature vector inspectable.

### C. Preserve independence with two reviewer modes

Implement two display modes over the same event store.

#### `blind_validation`

For held-out accuracy measurement:

- show raw source records;
- show the two-marker local map and distance;
- show Google-resolved candidate cards and lifecycle observations because these are
  newly acquired external evidence available to the human;
- hide derived similarity numbers/relation labels and the matcher's provisional
  decision until the first human verdict is saved;
- after save, they may be revealed for analysis.

#### `operational_review`

For bulk cleanup:

- show the derived pair aids prominently;
- still keep the final human verdict explicit and auditable.

Do not mix the two modes in evaluation metrics.

### D. Fast single-pair / Tinder-style reviewer

Restore/reuse the earlier local two-marker map instead of removing it. The main
screen should fit the decision surface above the fold:

```text
progress + filter

SOURCE A                           SOURCE B
name                               name
source                             source
address                            address
phone                              phone
domain                             domain
category                           category

MAP
- both source markers
- line between them
- distance label
- useful radius rings (25/50/100m)
- fit bounds to the two markers

REVIEW AIDS (operational mode only)
name | phone | address | category | distance

GOOGLE CANDIDATES
candidate ID -> returned Google name -> status -> address/category if available

[1 SAME_PLACE] [2 DISTINCT_PLACE] [3 INSUFFICIENT_EVIDENCE]
reason input
submit + immediately advance
```

Keyboard:

```text
1 / 2 / 3     choose verdict
Ctrl+Enter    save and next
J / K         next / previous without save
M             toggle/expand map
G             open focused Google candidate
/             focus queue search/filter
```

A swipe animation is fine, but never let a gesture create an untraceable implicit
verdict. Existing initial-verdict immutability / append-only revision semantics must
remain intact.

## Data/provenance rules

- Frozen source packet remains byte-for-byte unchanged.
- New Google observations live in a separate derived evidence artifact with
  timestamps and hashes.
- Review aids are derived features, not source facts.
- No canonical Business/Truth publication writes.
- No matcher rule changes in this task.
- No source-record merges in this task.
- Existing human verdict event store remains authoritative.

## Concrete acceptance cases

Include fixtures/tests for at least:

### Lepimp

```text
Overture: Lepimp
FSQ:      lepimp
same phone
same address
10.96m apart
bar vs cocktail bar
```

Expected review aids:

```text
name exact after normalization
phone exact
address exact after normalization
category compatible
~10.96m distance
```

The Google candidate resolver must be able to cache a result such as visible
`Permanently closed` without turning that into an identity verdict.

### Bagatelle

```text
FSQ: Bagatelle, Cl 82 # 9-09
OSM: Bagatelle, Carrera 9 81-18
same phone
75.94m apart
bakery/breakfast/French restaurant vs restaurant
shared Google candidate exists in the packet
```

Expected aids:

```text
name exact after normalization
phone exact
food/drink category compatibility
address strings are not exact
structured address logic surfaces adjacent/cross-street pattern when applicable
~75.94m distance
```

Do not auto-label SAME_PLACE from these features.

## Verification

Run focused tests plus the relevant existing reviewer/entity-resolution suite.
Verify:

- browser probe cache/resume;
- block detection stops cleanly;
- no missing-panel result is called operational;
- Google candidate IDs resolve independently and preserve rank/source association;
- blind mode does not expose derived scores/matcher outcome pre-verdict;
- operational mode does;
- map renders both markers for Lepimp and Bagatelle fixtures;
- keyboard submit advances exactly once;
- frozen packet hashes remain unchanged;
- no canonical/Truth writes occur.

Update the relevant owner note/system registry only if required by the repository
maintenance contract. Commit with a descriptive message and report files changed,
tests, exact artifact paths, and remaining gaps.
