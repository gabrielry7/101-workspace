# Google Maps identity-review toolkit v2

This is the expanded version of the earlier Maps status probe. It is intentionally
narrow and review-oriented: it helps a human decide whether two source records
refer to the same particular place without turning Google or fuzzy scores into
canonical truth.

It contains three pieces:

1. `google_maps_probe.py` — persistent Playwright browser for visible Maps data.
2. `identity_aids.py` — explainable name/address/phone/domain/category/distance features.
3. `enrich_pair_jsonl.py` — adds those offline aids to a pair-review queue.

`REVIEWER_V2_INTEGRATION.md` describes how to wire them into the existing 101
reviewer without replacing its event store or frozen packet semantics.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## A. Resolve Google Place IDs for free through the visible Maps UI

Given:

```csv
source_id,place_id
lepimp-overture,ChIJHQOOU0OaP44RzdBUsdwt_LA
bagatelle-shared,ChIJwyWHAgCbP44R9fnseFhckc4
```

run:

```bash
python google_maps_probe.py sample_place_ids.csv \
  --mode place-id \
  -o google_place_id_results.csv \
  --db google_place_id_cache.sqlite3
```

For each ID it records the visible result, including:

```text
input_place_id
google_name
status
permanently_closed
visible_address
visible_category
visible_phone
final_url
checked_at
```

Possible statuses:

```text
CLOSED_PERMANENTLY
CLOSED_TEMPORARILY
OPEN_OR_UNMARKED
UNKNOWN
BLOCKED
```

`OPEN_OR_UNMARKED` only means a real place panel loaded and no visible closure
label was found. It is not a claim that the business is currently operating.

The browser uses one persistent profile, sequential requests, randomized pacing,
SQLite checkpoints and cache reuse. If a challenge/block page appears, it stops.
It does not attempt to bypass access controls.

## B. Search by source name + coordinate

Input:

```csv
source_id,name,lat,lon
example-1,lepimp bar,4.6562411,-74.0588202
```

Run:

```bash
python google_maps_probe.py sample_input.csv --mode search
```

`--mode auto` uses a `place_id` when present, otherwise name+coordinates.

## C. Compute pair-review aids offline

The module deliberately keeps several signals separate instead of inventing one
magic confidence score.

Example:

```bash
python enrich_pair_jsonl.py sample_pairs.jsonl enriched_pairs.jsonl
```

Each pair receives:

```json
{
  "review_aids": {
    "name": {
      "strict_sequence_similarity": 1.0,
      "core_sequence_similarity": 1.0,
      "core_token_jaccard": 1.0,
      "relation": "EXACT_NORMALIZED"
    },
    "address": {
      "relation": "..."
    },
    "phone": {"exact": true},
    "domain": {"exact": false},
    "category": {"relation": "COMPATIBLE_FAMILY"},
    "coordinate_distance_m": 10.96
  }
}
```

Name normalization removes case, accents and punctuation. A separate **core**
comparison also treats Spanish articles/connectors and legal suffixes as soft
words. The strict comparison is retained so information is never silently lost.

Bogotá address normalization knows common street abbreviations (`Cl`, `Cra`, `Kr`,
`Av`, `Dg`, `Tv`) and exposes a specific adjacent/cross-street pattern instead of
pretending two differently written addresses are identical.

Category comparison is hierarchical/weak evidence. For example `bar` and
`cocktail bar` are compatible; `restaurant` and `bakery` share a broad food/drink
family. Category compatibility must not establish identity by itself.

## D. Blind audit vs operational review

This matters.

For a **held-out human validation audit**, compute/store the review aids but hide
the derived scores and matcher outputs until the initial verdict is saved. Showing
`name_similarity = 0.97` before the verdict would bias the label you are trying to
use as independent ground truth.

For **operational cleanup**, show the aids prominently to make review fast.

The raw source names, addresses, phones, categories, coordinates, map and newly
observed Google candidate cards can remain visible in both modes because those are
the evidence the human is actually adjudicating.

See `REVIEWER_V2_INTEGRATION.md` for the proposed Tinder-style layout and keyboard
flow.

## Tests

```bash
pytest -q
```

All tests are offline; they do not contact Google.
