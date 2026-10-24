# 101 Website Engine + Design Compiler — Conversation Handoff

## Purpose

This document summarizes the website-building work discussed in this chat.

The project has evolved into **two systems that ultimately need to be combined**:

1. **`101-world-model` production website pipeline**
   - acquires and verifies business evidence;
   - decides what can be published;
   - builds `SiteSpec`;
   - binds approved facts/actions;
   - emits Astro sites through `@101/site-runtime`;
   - runs technical and customer-readiness QA.

2. **Experimental Design Compiler**
   - explores art direction and layout;
   - uses controlled spatial/compositional grammars;
   - ingests open-source UI patterns;
   - renders real browser candidates;
   - evaluates screenshots/computer vision;
   - critiques and mutates layouts;
   - experiments with topology-first geometric optimization.

Long-term goal:

> **Business/evidence in → truthful, customer-ready, high-end website out.**

---

# 1. Core design thesis

The target is **not**:

```text
prompt
→ LLM writes HTML
→ hope it looks good
```

and also not:

```text
content
→ fixed template
```

The intended architecture became:

```text
semantic intent
→ art direction
→ controlled design space
→ render candidates
→ hard legality gates
→ aesthetic / visual evaluation
→ screenshot critique
→ mutation
→ rerender
→ final site
```

Key principle:

> **Humans/authored systems provide good design vocabulary; machines search, compose, execute and evaluate it.**

Another principle that emerged later:

> **Determinism should live in the laws and constraints, not necessarily in the composition itself.**

Things that should be deterministic:

- no overlap;
- no clipped text;
- readable minimum font sizes;
- legal crop behavior;
- consistent margins/gaps;
- real alignment when elements are meant to align;
- no unsupported facts.

Things that can remain exploratory:

- topology;
- asymmetry;
- dominance;
- whitespace strategy;
- relative scale;
- component family;
- typography voice;
- motion treatment.

---

# 2. Design Compiler evolution

## v0.1 — semantic layout search

Basic pipeline:

```text
semantic content
→ authored layout variants
→ scoring
→ beam search
→ HTML/CSS output
```

Main limitation: still fundamentally a small catalog of layouts.

## v0.2 — browser geometry

Added real Chromium rendering at desktop/mobile and measured:

- occupancy/fill;
- section height;
- title lines;
- last-line ratio;
- media coverage;
- overflow;
- clipping;
- minimum readable font size;
- content width.

## v0.3 — raster/computer vision

Added screenshot analysis with features such as:

```text
ink ratio
whitespace ratio
edge density
contrast
entropy
visual center X/Y
left/right balance
top/bottom balance
quadrant mass
edge tension
salience concentration
orientation bias
active tile ratio
complexity
```

This was the first serious attempt to give the system “eyes.”

## v0.4 — compositional operators

Rebuilt layout around operators rather than fixed layouts:

```text
Monument
Editorial
Split
Stage
Bleed
Metric Field
Rail
Sequence
```

Each operator exposed parameters such as:

```text
ratio
alignment
gap
media side
media height
title measure
crop behavior
offset
scale
```

Theoretical design space became very large, while expensive rendering stayed bounded:

```text
large theoretical space
→ legality
→ cheap scoring
→ Pareto frontier
→ diversity selection
→ browser finalists
→ raster + geometry
→ page search
```

Art-direction DNA was also introduced:

```text
whitespace
asymmetry
overlap
bleed
display scale
center frequency
crop aggression
etc.
```

## v0.5 — typography, richer spatial grammar, motion

Added:

### Spatial operators

```text
Diptych
Triptych
Overlap
```

### Typography grammar

```text
voice
scale
leading
tracking
weight
case
roman/italic
body scale
body leading
body measure
metadata style
```

Authored voices included:

```text
neo-grotesk
contrast-serif
editorial-serif
humanist-sans
mono-display
```

### Motion grammar

```text
clip-reveal
fade-rise
cascade
media-scale
drift-left
quiet
```

Motion was intended as a late stage, selected by semantic role after static composition was already good.

## v0.6 — screenshot critique

The system began detecting issues like:

```text
dead space
weak mobile fill
bad headline wrapping
overflow/clipping
too-centered visual mass
crop tension
weak hierarchy
small media
desktop/mobile visual drift
```

At this point critique mostly re-ranked existing candidates.

## v0.7 — critique → mutate → rerender

The loop became genuinely iterative:

```text
render
→ screenshot
→ critique
→ mutate parameters
→ rerender
→ compare
→ accept/reject
→ replan
```

Example mutations:

```text
widen title measure
flip axis
tighten spacing
increase media size
soften crop
reduce scale
increase display emphasis
```

## v0.8 — media intelligence

Added local image analysis:

```text
focal mass
negative-space side
edge tension
entropy/detail
text-likeness
UI-screenshot likelihood
crop tolerance
aspect ratio
```

This could influence:

- crop legality;
- object-position;
- caption placement;
- Stage/Split decisions;
- Diptych/Triptych/Overlap scoring.

Important distinction: the system understood **where information is**, not necessarily **what the image depicts**.

---

# 3. Open-source component strategy

Major realization:

> Why invent every navbar, form, card, table, accordion, carousel and interaction from first principles when the OSS ecosystem already contains thousands of professionally authored components?

Libraries/repositories discussed:

```text
shadcn/ui + Base UI
HeroUI
Radix Themes
Origin UI
Kibo UI
Dice UI
Animate UI
Cult UI
Aceternity UI
21st.dev
```

Target architecture:

```text
                         SEMANTIC INTENT
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
        SPATIAL GRAMMAR                    UI GRAMMAR
        our invention                   authored OSS source
               │                               │
               └───────────────┬───────────────┘
                               ▼
                         normalize/adapt
                               ▼
                         design candidates
                               ▼
                     render → judge → mutate
```

## Base UI / shadcn

Role: **behavioral substrate**.

Useful for:

```text
focus management
keyboard navigation
dialogs
menus
popovers
tabs
accordions
forms
ARIA behavior
```

Rule: do not let generic shadcn Card conventions become the visual language of every marketing site.

## Origin UI

Actual repo structure was inspected.

It contains many categorized authored variants, including:

```text
accordion
alert
avatar
button
calendar
dialog
input
navbar
pagination
popover
select
table
tabs
timeline
...
```

Example navbar family:

```text
comp-577 ... comp-596
```

Actual source like `comp-577.tsx` was pulled and inspected.

## Cult UI

Actual source inspected for:

```text
MinimalCard
FeatureCarousel
FeatureSection
Footer
```

Useful authored relationships included:

- nested radii;
- inset shells;
- layered shadows;
- card spacing;
- hover states;
- motion structures.

## Kibo UI

Higher-order components and patterns:

```text
Gantt
Kanban
comparison
dropzone
editor
image crop
image zoom
marquee
QR code
rating
tree
video player
code block
calendar
combobox
...
```

Kibo also contains large pattern families, motivating structural clustering rather than adapting dozens of near-duplicates.

## Dice UI

Advanced application/UI patterns:

```text
file upload
Kanban
media player
masonry
compare slider
color picker
cropper
rating
QR code
timeline
tour
sortable
stepper
scroller
...
```

## Animate UI

Useful especially as motion vocabulary:

```text
accordion
dialog
popover
tabs
tooltip
buttons
background effects
animated code
cursor
avatar groups
motion carousel
...
```

---

# 4. Important correction: fake provenance problem

One version of the corpus work incorrectly labeled compiler-native markup as if it came from OSS libraries.

Example problem:

```text
source: "origin"
```

while the rendered markup was actually our own.

This was explicitly rejected.

Correct rule established:

> **If the compiler claims a component came from Origin, Cult, etc., there must be an exact real source file behind that claim.**

---

# 5. v0.10 — source-backed provenance

Added real vendored/source-backed components and provenance data:

```text
repository
upstream path
vendored path
SHA-256
```

Also tightened visual rejection gates:

```text
horizontal overflow
clipped content
undersized text
bad collisions
pathological blank areas
```

Internal/debug copy was removed from client-facing pages.

---

# 6. v0.11 — repository ingester

Built a generic OSS repository ingester.

Pipeline:

```text
repository
→ discover source
→ parse
→ normalize
→ fingerprint
→ index
→ optionally vendor source
```

Profiles were built/verified for:

```text
Origin
Cult
Kibo
Dice
Animate
```

Features extracted included:

```text
imports
exports
JSX structure
flex/grid/absolute topology
responsive breakpoints
Tailwind spacing
radii
shadows
typography
interaction hooks
motion usage
Radix/Base/headless substrate
state modifiers
source hash
```

Entries were classified honestly as:

```text
SOURCE_BACKED_RENDERABLE
SOURCE_BACKED_NEEDS_ADAPTER
INDEXED_ONLY
COMPILER_NATIVE
```

---

# 7. Corpus clustering / adaptation queue

Next corpus layer:

```text
many source files
→ structural fingerprints
→ similarity clustering
→ diversity-first adaptation queue
```

Goal:

```text
50 accordion variants
→ maybe 8 meaningful structural families
→ adapt one representative per family first
```

Near-duplicates are deprioritized when a cluster is already represented by a source-backed adapter.

---

# 8. v0.12 — topology-first spatial solver

Separate geometric-layout experiment inspired by floorplanning / constraint solving.

Key model:

```text
layout = topology + geometry
```

Pipeline:

```text
semantic objects
→ topology enumeration
→ geometry optimization
→ hard legality
→ aesthetic scoring
→ diverse Top-K layouts
```

5-object prototype evaluated:

```text
symmetry
aspect-ratio distortion
largest unjustified void
gap regularity
visual balance
```

Hard constraints included:

```text
inside canvas
no overlap
minimum dimensions
minimum gaps
bounded aspect distortion
```

Important lesson:

> Do not maximize occupancy blindly. Minimize **structurally unjustified whitespace**.

This remains experimental and was not yet merged into production website layout.

---

# 9. Broader spatial research direction

The problem was connected to:

```text
fixed-outline floorplanning
Sequence Pair
B*-Tree
O-Tree
symmetry-constrained placement
soft block shaping
Cassowary
Auckland Layout Model
ORC Layout / ORCSolver
CP-SAT / NoOverlap2D
Z3 Optimize
MaxRects
Treemaps
computational aesthetics
Visual Moment Equilibrium
CSS Grid
GridStack
Muuri
```

Main architectural conclusion:

```text
composer
+
deterministic geometry
+
hard constraints
+
soft aesthetic objectives
+
visual critic
+
search
```

Not:

```text
LLM → coordinates
```

and not:

```text
content → fixed template
```

---

# 10. Production system: `101-world-model`

Approximate production pipeline found by Codex:

```text
business evidence
→ SiteSpec
→ DesignProfile/component registry
→ ConstrainedCompositionEngine
→ CompilerBindingPlanner
→ WebsiteCompiler
→ @101/site-runtime
→ Astro
→ browser QA
→ CustomerSiteAdequacyEvaluator
```

This system owns things the Design Compiler never tried to solve:

```text
business evidence
truth/approval
source provenance
fact publication
customer adequacy
Astro build/runtime infrastructure
```

---

# 11. Initial production audit

Codex audited the actual repo.

Main finding:

> **facts selected for binding were not necessarily rendered.**

Retained cohort result:

```text
9 sites built
0 customer-ready
```

Businesses with different evidence could produce near-identical placeholder pages.

Also `/homepage` existed while `/` did not.

Browser QA existed but was not yet a full operational repair loop.

Commit:

```text
cc98388
```

---

# 12. Binding/render repair

Commit:

```text
01195f7
```

Fixed:

- approved reputation facts survive into built HTML;
- discarded sections no longer falsely mark bindings consumed;
- homepage loads at `/`;
- `binding-report.json` added;
- controlled fixture proved phone/email/WhatsApp/social/CTA through Astro + browser.

Retained cohort still:

```text
0 customer-ready
```

because content/evidence remained insufficient.

---

# 13. Real-business customer-readiness replay

A replay using real businesses showed:

```text
0 / 3 customer-ready
```

Two businesses rendered approved:

```text
phone
email
WhatsApp
Instagram
```

Sparse business lacked approved contact action.

At that stage none had a publishable business name, and service/location pages lacked approved content.

Commit:

```text
28ba242
```

---

# 14. Broader evidence/acquisition work existed

Conversation history showed acquisition/corroboration had progressed further than that first replay.

Existing/later work included:

- large-scale phone enrichment;
- email enrichment;
- WhatsApp;
- social profiles;
- media evidence;
- service candidates;
- Instagram evidence;
- automatic ownership/corroboration;
- review acquisition;
- Google Maps media probing.

Some automatic corroboration work had already produced actionable compiler bindings.

Problem: not all of those streams had been combined through one canonical production-compatible replay.

---

# 15. Canonical/offline replay

A broader cutoff-compatible replay was run using three businesses.

Result remained:

```text
0 / 3 customer-ready
```

It clarified the remaining boundaries rather than proving failure of the render pipeline.

Commit:

```text
691b9db
```

PostgreSQL was unavailable, so the replay used retained rows/in-memory projection and was **not equivalent to a full production DB-backed replay**.

---

# 16. Narrow Truth-boundary findings

A focused boundary audit found:

```text
2 missing publication paths
1 missing relationship bridge
1 evidence-quality shortfall
```

## Business name

Observed in Genome for all three, but planning-only / owner-confirmation-required.

Missing full path:

```text
name observation
→ Truth Proposition
→ PublicationDecision
→ SiteSpec
→ compiler binding
→ HTML
```

## Address

Observed and business-linked.

Downstream already supported:

```text
Truth → SiteSpec → binding
```

Missing edge:

```text
observed address
→ Truth proposition/publication
```

## WhatsApp

Saved profiles existed, but missing:

```text
WhatsApp profile
→ verified business relationship
→ Truth
```

## Services

Two businesses had many weak service candidates from things like:

```text
page titles
headings
paths
biography fragments
```

Strong strict-service assertions belonged to a different business.

So the service problem was **evidence quality**, not missing SiteSpec plumbing.

---

# 17. Business-name publication slice

Commit:

```text
fb9c0d9
```

Result:

**Dientes y Sonrisa gained a publishable, source-backed business name.**

Rule required a provider observation exactly matching an explicit name on a machine-verified official homepage.

Name now travels:

```text
source
→ Truth
→ SiteSpec
→ compiler
→ HTML
```

Other two names stayed unpublished.

Customer readiness remained:

```text
0 / 3
```

Also fixed an adequacy false positive where repeated identity text could make an empty page look substantive.

---

# 18. Address publication slice

Commit:

```text
e3637ae
```

Implemented address publication when:

```text
provider-observed address
+
exact explicit address
on machine-verified business-linked website
```

None of the three real businesses qualified.

Dientes had conflicting street addresses.

Other businesses lacked matching first-party evidence.

This was considered correct fail-closed behavior.

---

# 19. WhatsApp business-linkage slice

Commit:

```text
48c7957
```

Saved profiles for:

- Dientes y Sonrisa;
- Dentistería Digital

now reach:

```text
machine_verified business relationship
→ Truth
```

using the existing two-source identity policy.

Their WhatsApp CTAs were already approved through Instagram, so this added **supporting provenance**, not duplicate CTAs.

Sparse case had no saved profile.

Customer readiness remained:

```text
0 / 3
```

This demonstrated that contact verification was no longer the main bottleneck.

---

# 20. Unsupported-route bug

Codex then found Dientes was failing adequacy due to:

```text
no_publishable_service_content
no_publishable_location
```

But those failures were partly self-created:

```text
blocked service candidate
→ emitted service page anyway

blocked location candidate
→ emitted location page anyway
```

Then adequacy correctly rejected the empty pages.

Important distinction:

```text
PLANNING CANDIDATE
≠
CUSTOMER-EMITTABLE PAGE
```

---

# 21. Route-emission slice

Commit:

```text
a979ffe
```

Blocked service/location candidates now:

```text
remain visible in planning diagnostics
```

but:

```text
do NOT become customer-facing routes
```

Sparse business also stopped emitting an empty contact utility page.

Customer readiness still:

```text
0 / 3
```

but the Dientes blocker became much more meaningful:

```text
no_substantive_business_content
```

Its homepage currently contains approximately:

```text
publishable name
rating/review fact
Email action
```

but lacks publishable:

```text
business description
services
address
hours
```

At this point the system stopped failing mainly because of plumbing and started failing because of **real evidence/content scarcity**.

---

# 22. Critical reframing: Dientes is only a fixture

The project should **not** optimize for Dientes as an individual business.

Dientes is useful as a regression fixture.

The real product target is thousands of businesses across verticals:

```text
1,000 dentists
1,000 restaurants
1,000 mechanics
1,000 lawyers
1,000 salons
...
```

Therefore the next problem is not:

```text
make Dientes customer-ready
```

It is:

```text
build a generic system that converts first-party business evidence
into trustworthy substantive website content at scale
```

---

# 23. Proposed scalable first-party content architecture

Target:

```text
LOCAL BUSINESS UNIVERSE
        ↓
evidence acquisition
        ↓
entity / ownership graph
        ↓
first-party assertion engine
        ↓
Truth model
        ↓
semantic business model
        ↓
SiteSpec
        ↓
design compiler
```

Common ontology should likely include:

```text
BusinessIdentity
BusinessDescription
Offering
OfferingCategory
OpeningHours
Location
CustomerAction
Reputation
SocialProfile
MediaAsset
Price / PriceRange
BusinessAttribute
```

A dentist treatment, restaurant menu item, lawyer practice area, mechanic service, etc. should map into a shared concept like:

```text
Offering
```

with vertical-specific interpretation.

---

# 24. Strong vs weak first-party evidence

Not all website text should become publishable.

## Strong explicit evidence

```text
"Ofrecemos ortodoncia e implantes."
"Nuestro menú incluye..."
"Prestamos servicios de..."
```

## Strong structural evidence

```text
dedicated service/product page
schema.org Service/Product/MenuItem
explicit pricing/catalog row
```

## Moderate evidence

```text
heading + detailed explanatory body
FAQ explicitly discussing the offering
```

## Weak evidence

```text
URL slug
navigation label
SEO keyword
isolated heading
category tag
```

Weak evidence should remain candidate evidence unless corroborated strongly enough.

---

# 25. Vertical-aware but business-agnostic

Correct architecture:

```text
generic extraction
+
vertical-aware interpretation
```

Not:

```text
one custom extractor per business
```

Vertical knowledge may help classify:

```text
"Ortodoncia"
inside dentistry context
→ likely Offering
```

But must never invent:

```text
"limpieza dental"
```

simply because many dentists offer it.

---

# 26. Cohort-level evaluation

Future progress should be measured across businesses/verticals with metrics such as:

```text
businesses evaluated
businesses with verified first-party site
businesses with substantive candidates
candidate assertions
publishable assertions
publishable descriptions
publishable offerings
publishable hours
publishable prices
businesses gaining >=1 substantive fact
businesses gaining >=3 substantive facts
customer-ready before
customer-ready after
```

The useful question is:

```text
0 / 100
→
37 / 100
```

not:

```text
Dientes failed → passed
```

---

# 27. Intended responsibility split between systems

## 101 should own

```text
business intelligence
evidence acquisition
entity resolution
truth/publication policy
fact approval
semantic SiteSpec
customer adequacy
Astro/runtime/deployment infrastructure
```

## Design Compiler should own

```text
art direction
component selection
OSS component corpus
composition search
topology/layout
geometry
typography
media composition
responsive spatial behavior
motion
screenshot visual QA
visual critique
mutation
```

Likely future architecture:

```text
BUSINESS EVIDENCE
        ↓
      Truth
        ↓
SEMANTIC BUSINESS MODEL
        ↓
     SiteSpec
        ↓
  ART-DIRECTION DNA
        ↓
┌───────────────┬──────────────────┐
│               │                  │
OSS COMPONENT   SPATIAL          TYPOGRAPHY
CORPUS          COMPOSER         GRAMMAR
│               │                  │
└───────────────┴──────────────────┘
                ↓
        GEOMETRIC SOLVER
                ↓
       RESPONSIVE SOLVER
                ↓
          SITE RUNTIME
                ↓
              Astro
                ↓
          TECHNICAL QA
                ↓
        SCREENSHOT CRITIC
                ↓
            MUTATION
                ↓
            RERENDER
```

---

# 28. What is substantially working today

```text
business evidence acquisition/storage
Truth/publication boundaries
binding → rendered HTML
root route generation
binding reports
browser loading
real contact actions for some businesses
publishable business-name path in a strong case
address publication path (no retained real case qualified)
WhatsApp relationship verification
suppression of unsupported customer routes
technical browser QA
experimental Design Compiler
experimental OSS corpus ingestion
experimental screenshot-based visual optimization
experimental topology-first spatial solver
```

---

# 29. What remains unproven

```text
customer-ready real-business site generation at scale
publishable substantive content across multiple verticals
full DB-backed production replay with PostgreSQL
large-scale source-backed OSS component rendering
101 + Design Compiler integration
responsive topology/constraint solving in production
closed production repair loop
customer-grade visual quality
```

---

# 30. Current immediate production blocker

Current bottleneck:

> **not enough substantive publishable business content**

For Dientes as a representative fixture:

```text
name        ✓
reputation  ✓
action      ✓

description ✗
service     ✗
address     ✗
hours       ✗
```

Hence:

```text
no_substantive_business_content
```

---

# 31. Recommended next production milestone

Build a **generic first-party assertion engine** that:

```text
verified first-party surfaces
→ explicit assertions
→ evidence-strength classification
→ common business ontology
→ Truth assessment/publication
→ SiteSpec
→ cohort replay across verticals
```

Suggested first evaluation verticals:

```text
dentistry
restaurants
automotive
legal
beauty/wellness
```

Measure both:

```text
coverage
AND
precision
```

Do not increase coverage by weakening publication policy.

---

# 32. When to begin design integration

Design integration should begin when 101 can produce a meaningful number of **truthful but ugly** customer-usable sites from real businesses.

Baseline:

```text
real business
→ approved identity
→ meaningful substantive content
→ real customer action
→ supporting evidence
→ customer-usable ugly site
```

Then the Design Compiler should transform:

```text
truthful ugly site
```

into:

```text
truthful high-quality site
```

using:

```text
source-backed OSS components
art direction
spatial search
geometric solver
typography
media intelligence
responsive solving
screenshot critic
mutation
motion
```

---

# 33. Important production commits

```text
cc98388  current-state website-system audit
01195f7  binding/render repair
28ba242  real-business customer-readiness replay work
ff753e6  reconciliation / evidence context work
691b9db  canonical real-business replay
fb9c0d9  business-name publication slice
e3637ae  address-publication slice
48c7957  WhatsApp business-linkage slice
a979ffe  unsupported customer-route emission fix
```

---

# 34. Current status in one sentence

> **101 can now truthfully identify, bind, render and technically verify some real business facts/actions, while the separate Design Compiler has developed serious composition/search/OSS/vision capabilities; the next production bottleneck is scalable extraction and publication of substantive first-party business content across many verticals before the two systems should be integrated.**
