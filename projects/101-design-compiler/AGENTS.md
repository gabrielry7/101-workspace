# 101 collaboration

Codex is the primary orchestrator and owns architecture, requirements, code
review, verification and integration decisions. Preserve uncommitted user work.
Do not merge agent work automatically. Follow the dated GitHub delivery instruction
below for scoped commits and pushes explicitly authorized by the user.

## Approved template architecture (user direction, 2026-10-27)

An approved design is executable template code, not a palette, font pair,
reference image or prompt. Instantiate and parameterize the actual approved
Astro components/CSS, preserving their composition, navigation, interior
layouts and interactions. Reusing only tokens in a newly authored renderer
does not count as reusing a template. Do not introduce a parallel renderer
to adapt an approved design to another business.

Refactor the existing template only as needed to expose business data,
semantic capabilities, media slots and bounded configuration. With its
reference input, the refactored code must reproduce the approved design.
Show the approved original beside the adapted result before expanding to
more cases. Unsupported capabilities or missing essential media make a
template ineligible or require an explicit approved fallback; do not silently
replace its composition. Keep existing media rights/scope gates.

The intended product is a library of 100+ individually approved, versioned
code templates and a selector that filters compatibility and ranks suitable
templates with an explicit, explainable scoring rubric. This is a target,
not authorization to generate 100 designs in one batch. Store template ID,
version, selection reasons and adaptation configuration for reproduction.
Model-assisted authoring of a new template is distinct from instantiating
an approved one; ordinary instantiation must not regenerate layout code.

Business names and display headings must not break inside a word, clip or
overflow when an approved template receives different content. Preserve whole
words, fit typography to its real font/container, and flag unreadable results
for review instead of silently shrinking indefinitely. Before presenting an
adaptation, inspect native browser output on narrow/mobile, tablet, desktop,
both sides of layout breakpoints, and font fallback. Automated word-integrity
and overflow checks supplement visual inspection; passing them is not human
approval. This is a required quality gate from user feedback on 2026-10-28.

The four /scenarios/ visual demos from fictional-scenarios-20261026 were
rejected by the user on 2026-10-27. They are not approved templates and must
not become the production base. Retain their synthetic data/test evidence
for possible reuse. Technical checks and an agent's review verdict do not
override human rejection or establish visual fidelity.

When asked to ask Claude, collaborate with Claude Code, or iterate with Claude
on an existing page, use the real CLI bridge documented in
[tooling/claude-code/README.md](tooling/claude-code/README.md).
Run its doctor first, create an explicit scoped task JSON, invoke `start`,
inspect its actual response and worktree diff, then use `feedback` with the
same task ID. Never substitute a Codex subagent or mocked response for Claude.
If authentication fails, report the exact blocker and user login command.

Claude acts as a frontend design/development specialist. Keep changes in the
existing shared Astro/CSS renderer and semantic business modules. Preserve
media gates, fictional labels, credits, navigation, accessibility, mobile
usability, reduced motion and performance. Reuse existing design references
and `scripts/lib/local-browser.ts` for screenshots. Do not create a new
generator, pipeline, framework or service.

Before delegation, review selected context and media vision permissions;
exclude credentials and unrelated private material. Claude worktrees start at
committed HEAD. Disclose differences from a dirty working tree; never copy
uncommitted user changes without reviewing and explicitly selecting them.
Each task has bounded calls, turns, time and estimated spend. Codex runs
builds, tests, browser/accessibility/performance checks, reviews screenshots,
and retains the implementation for user review. A successful CLI response is
not evidence that a design passes quality checks.

## Pointer effects (user direction, 2026-11-02)

Contextual cursors and text labels attached to the pointer are rejected. Never
apply this effect to current or future templates. Keep one pointer identity
throughout each page; do not swap it on links, buttons or photographs. On a
trail page, the coloured head is the pointer and the traditional pointer must
disappear while that head is active. Retain native fallback for touch, reduced
motion, forced colours, disabled effects and embedded-map views.

Reuse bounded magnetic attraction on meaningful action buttons. Tilt and glare
may enhance photographs without replacing their composition. Spotlight and
mouse-following gradients belong exclusively on explicitly light surfaces;
do not apply either effect to dark backgrounds. Review categories one at a
time as requested by the user.


## Current direction: SDD and reusable components (2026-11-04)

The user adopts the official GitHub Spec Kit process as the general development
method for frontend, backend, loyalty, messaging, integrations and tooling.
Read `.specify/memory/constitution.md` for the current project principles and
`docs/spec-kit-adoption-20261104.md` for installed commands and scope. New features
and architectural changes proceed through specification, clarification as needed,
technical planning, traceable tasks, implementation and verified convergence.
Keep small fixes proportional. Do not infer that installing the process completes
a feature, approves a visual design or authorizes deployment or customer messages.

For the NEW page pipeline, the user changes the unit of reuse from exclusively
whole-page templates to versioned, useful components with explicit data, variants,
states, compatibility rules and bounded brand settings. This dated instruction
supersedes the whole-page-only reuse requirement above for new pipeline work.
Preserve the approved original templates and their reference output as existing
assets and regression cases. Reuse and refactor the existing Astro/CSS components
and semantic planner instead of creating a parallel renderer or duplicate service.
Existing media gates, factual authority, fictional labels, accessibility, responsive
word integrity, pointer policies and version-specific human approval remain in force.

The component library and approximately 90% automatic page completion are product
targets to specify and evaluate, not implementations or measured results established
by this adoption. Start with a bounded pilot; do not generate all variants at once.

## Current direction: section bones, brand skin and GitHub (2026-11-05)

The user's new direction defines bones as reusable section structure AND behavior:
named parts, composition, responsive rules, scroll, motion, transitions, interaction
and accessible fallbacks. Brand skin supplies bounded fonts, colors, logo and
graphic treatment. Content/media are separately sourced business inputs. Changing
skin must not silently change composition or behavior. A large catalog, including
roughly 1,000 hero options, is a scale target, not an existing inventory or an
instruction to generate that many now. Reuse has no preset limit of compatible brands.

The active specification is `specs/002-section-bones/spec.md`; read
`docs/bones/section-model.md` and `docs/bones/integration.md` before planning.
Thomas's pinned review-bones handoff is the worked reference, with fourteen REVIEW
variants, not fourteen heroes. Reuse its actual recipe/parts/action/workshop owners;
do not make a parallel renderer. Its existing API named `bones` owns visual
profiles and is not synonymous with the product's structure/behavior definition.
The first new navigation/hero scope remains a bounded proposal in spec 002.

Prior work is archived under `old` with verified history and working-change
snapshots. Original application source paths remain in place where imports and
regression checks require them. They are preserved legacy, not an obligation to
use the old whole-page composition for the new system. Preserve all unrelated
working-tree changes and original approved outputs.

The user explicitly requests: "siempre commits al github". For completed scoped
deliveries, review the diff, commit and push to `gabrielry7/101-workspace` under
`projects/101-design-compiler`, and verify the remote commit. This supersedes earlier
default no-push instructions for the user's authorized work. Do not merge, force
push, publish restricted media/data or push to Thomas's repository automatically.
The local standalone history differs from the GitHub monorepo: use a clean clone
or worktree of the destination and transfer only reviewed task files. See
`docs/bones/github.md`. Report any push failure explicitly instead of claiming delivery.

## Current map refinement and recovery priority (2026-11-08)

The user explicitly deprioritizes the sixty missing historical restaurant media
files. Focus on the current section bones; do not pursue those originals or treat
their legacy global-build failures as blockers for unrelated bone deliveries.

Map refinement is recorded in `specs/006-neutral-location-bones/`: three neutral
compositions of the existing location family, named slots like Little Amps, and a
logo contained inside a geographically anchored pin. Current version is 0.2.0.
These are three compositions, not three independent approved library families.
The user confirmed that no Google project, Map ID or cloud style is configured yet.
The existing Google adapter and offline checks do not establish live cartography
verification. Keep the neutral local sample identified and Google setup pending;
do not create billing or report the live Google result as complete.

## Authorized Honorato Google trial (2026-11-09)

The user now explicitly requests creation of the Google Cloud project, active
cloud style, Map ID and restricted browser key, with a maximum authorized trial
budget of US$1. This supersedes the previous setup-pending instruction for this
dedicated trial. Spec 007 records the scope. Actual cloud resources and Google
Maps JavaScript rendering have been verified; this is still a private local trial,
not commercial publication or human approval of the location family.

Use the existing SingleBusinessLocation component and pinned geographic owner.
Keep account details, OAuth, browser key, retained Honorato data, bundles and
screenshots under ignored `.tools/honorato-google-live/`. The browser key is limited
to Maps JavaScript and localhost/127.0.0.1 port 8780. Preserve BOTH the verified
Google daily quota of ten map loads and the persistent local ten-initialization
budget. Do not delete/reset the counter to obtain more trial loads or expand the
authorized services. The map currently uses the neutral pin because no eligible
Honorato logo evidence was retained. Do not fabricate a media grant.
