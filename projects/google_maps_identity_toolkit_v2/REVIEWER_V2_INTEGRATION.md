# Pair reviewer v2 integration target

This package does **not** replace the existing 101 reviewer/event store. The current
review UI should be upgraded in place so existing frozen packets, provenance and
human-review semantics remain intact.

## What to add

### 1. Current Google lifecycle observation

For each source record and each saved Google Place-ID candidate, the offline
browser probe can resolve visible Maps metadata:

- returned Google name;
- `CLOSED_PERMANENTLY`, `CLOSED_TEMPORARILY`, `OPEN_OR_UNMARKED`, `UNKNOWN`, or `BLOCKED`;
- visible address when present;
- visible category when present;
- visible phone when present;
- checked timestamp.

This is **lifecycle/source evidence**, not canonical identity truth. A stale source
record can still be the same place even if Google now marks it permanently closed.

### 2. Explainable pair aids

Compute and persist under a separate `review_aids` namespace:

- strict normalized-name similarity;
- core-name similarity after accents/punctuation/legal suffixes and soft articles;
- token overlap;
- normalized Bogotá address comparison;
- street/cross-street swap/near-corner pattern;
- normalized phone exactness;
- normalized domain exactness;
- broad category-family compatibility;
- coordinate distance.

Never turn these into a canonical identity verdict by themselves.

### 3. Two reviewer modes

**Blind validation mode**

Use for the held-out audit. Show raw source evidence, map, Google-resolved candidate
cards and lifecycle observations, but hide derived similarity scores and matcher
outputs until the first human verdict is saved. Otherwise the evaluation is no
longer meaningfully independent.

**Operational review mode**

Use for high-throughput cleanup. Show the derived aids prominently.

### 4. Tinder-style single-pair layout

The page should fit the important decision surface above the fold:

```text
┌────────────────────────────────────────────────────────────────────┐
│  31 / 325                                      progress / filters   │
├─────────────────────────────┬──────────────────────────────────────┤
│ SOURCE A                    │ SOURCE B                             │
│ Lepimp                      │ lepimp                               │
│ Overture                    │ Foursquare                           │
│ Calle 71 Carrera 10         │ Calle 71 Carrera 10                  │
│ +57 301 579 9409            │ +57 301 579 9409                     │
│ Bar                         │ Cocktail Bar                         │
├─────────────────────────────┴──────────────────────────────────────┤
│ MAP: both markers, connecting line, distance, 25/50/100m rings     │
├────────────────────────────────────────────────────────────────────┤
│ REVIEW AIDS (ops mode only)                                        │
│ Name EXACT | phone EXACT | category compatible | distance 10.96m   │
│ Address EXACT                                                     │
├────────────────────────────────────────────────────────────────────┤
│ GOOGLE CANDIDATES                                                  │
│ A #1  ChIJ...  → lepimp bar  | PERMANENTLY CLOSED | address ...    │
│ B #1  ChIJ...  → ...         | ...                                 │
│ B #2  ChIJ...  → ...         | ...                                 │
├────────────────────────────────────────────────────────────────────┤
│ [1 SAME PLACE]     [2 DISTINCT]     [3 INSUFFICIENT]               │
│ reason: ________________________________      [submit + next]       │
└────────────────────────────────────────────────────────────────────┘
```

### 5. Keyboard throughput

Keep the current semantics but remove unnecessary mouse travel:

- `1`, `2`, `3` select verdict;
- `Enter` focuses reason if empty;
- `Ctrl+Enter` saves and immediately advances;
- `J/K` or arrow keys next/previous without saving;
- `/` focuses search/filter;
- `M` expands/collapses map;
- `G` opens selected Google candidate in a new tab;
- after submit, preserve reviewer and mode query parameters.

Do not auto-submit a verdict merely from a swipe gesture. A swipe animation can be
used, but the explicit verdict event must remain auditable.

## Important separation

The enrichment/probe outputs should be appended as review evidence artifacts and
linked by hashes/timestamps. They must not mutate the frozen source packet or be
silently fed into the matcher that produced the queue being evaluated.
