# 101 Design Compiler Constitution

## Core Principles

### I. Intent and acceptance precede implementation

Every new feature or architectural change MUST start with a bounded specification
of the user outcome, scope, exclusions, acceptance scenarios and missing information.
The technical plan MUST cite the existing code it will reuse and the constraints it
will preserve. Tasks MUST trace back to requirements. Implementation MUST follow
those artifacts, and discoveries MUST be reconciled into them before completion.
This applies to frontend, backend, loyalty, messaging, integrations and tooling.
Routine fixes and documentation changes MAY use a proportionately smaller written
scope and verification record; they MUST NOT create paperwork without user value.

### II. Section bones, behavior and brand skin

The new page pipeline MUST compose versioned section bones with explicit parts,
purposes, data requirements, states, responsive composition and compatibility.
Scroll, movement, transitions and interaction MUST belong to the bone's declared
behavior, including its accessible alternatives. Brand skin MUST provide bounded
typography, palette, logo and graphic treatment; it MUST NOT implicitly replace
composition or behavior. Business content and media MUST remain separately bound.
New client instances MUST reuse executable code and configuration rather than
regenerating layout code. Each section MUST support a task, communicate a relevant
fact or help a decision; visual quality MUST also support interest, trust and brand
coherence. The planner MUST explain omissions and incompatibilities. A family MAY
contain many bones; neither 1,000 hero options nor 90% automation is an existing
inventory or authorization for bulk generation. Compatible brands MUST be reusable
without a preset count limit. This user-directed definition of 2026-11-05 governs
the new pipeline; earlier whole-page assets remain preserved legacy references.

### III. Factual authority and media permissions remain explicit

Business data MUST retain its source, publication decision, date and business or
branch scope through planning and rendering. Unknown, withheld, expired and
conflicting states MUST remain distinguishable. A preview MUST NOT imply a live
reservation, payment, message delivery or loyalty balance without the corresponding
operational authority. Synthetic data MUST be labelled. Images and video MUST pass
the existing rights, scope, inspection and credit gates for their intended use.

### IV. Existing systems and user work are preserved

Changes MUST reuse the existing Astro/CSS application, semantic planner, contracts
and media controls and integrate the existing upstream component owners rather
than introduce a parallel renderer, duplicate evidence system or duplicate service.
An explicit plan MUST justify and version any required interface change.
Unrelated working-tree changes and approved reference versions MUST be preserved.
Legacy history and uncommitted work MUST be recoverable under `old`; retaining
source paths for dependency or regression integrity MUST be documented.
Operational customer, order, payment and loyalty authority MUST NOT be duplicated
to make a preview appear integrated. Breaking interfaces MUST have a versioned
migration plan. The user's 2026-11-05 instruction authorizes scoped commits and
pushes to their GitHub repository for completed deliveries. Changes MUST exclude
unrelated work and restricted material. Automatic merges, force pushes and changes
to collaborators' repositories are not implied by that delivery instruction.

### V. Verification follows the changed behavior

Tasks MUST define observable completion evidence. Contract and integration changes
MUST have meaningful positive and failure-case checks. UI changes MUST receive
native-browser inspection across narrow mobile, tablet, desktop, breakpoint edges
and font fallback as applicable. Names and headings MUST preserve whole words,
remain readable and avoid clipping or overflow. Keyboard use, reduced motion and
the existing pointer-effect policies MUST remain covered. Technical checks MUST NOT
be presented as human visual approval. Low-impact reversible edits do not require
tests that merely repeat their implementation.

### VI. Reproduction and honest status

Specifications and results MUST identify component or template versions, input
references, adaptation settings and verification scope needed to reproduce a case.
Family, bone, behavior variant, visual profile and human approval MUST remain
distinguishable. Fourteen review variants MUST NOT be reported as fourteen heroes
or as approval of a new library. Upstream APIs named `bones` that own visual
profiles MUST NOT silently redefine the product's structural/behavioral bones.
Completion reports MUST distinguish implemented, simulated, integrated, verified and
pending behavior. A failed or blocked run MUST retain its reason. Historical lock
failures MUST NOT be resealed to hide environment drift. The target of approximately
90% automatic page completion is a hypothesis to measure in pilots, not a result
established by this adoption or a guarantee for every business.

### VII. Proportional process with measurable outcomes

Use the official Spec Kit process, with one bounded feature at a time. Plans MUST
justify new dependencies, services and layers against concrete needs. Measure pilot
outcomes using elapsed work, correction effort, requirement fulfillment and observed
failures, including the cost of writing and maintaining specs. Framework popularity,
document count and generated code volume MUST NOT be used as evidence of quality
or efficiency. Changes to process MUST be grounded in those observations.

## Repository Constraints

- Astro, TypeScript, existing CSS and versioned data contracts remain the current
  application context. Spec Kit is development tooling, not an application runtime.
- New component work MUST preserve the approved originals and the current shared
  semantic/media boundaries. The rejected `/scenarios/` demos remain rejected.
- Shared upstream recipes, parts, actions and workshop owners MUST be mapped before
  extending them. Reference testimonials MUST retain their original attribution.
- Workshop controls, anatomy guides and diagnostic measurements MUST remain
  operator-only. An unknown photo-background contrast or surface percentage MUST
  NOT be presented as a universal aesthetic score.
- Pointer rules in `AGENTS.md` remain in force, including a single pointer identity,
  native fallbacks and the prohibition of contextual pointer labels.
- Credentials, private business evidence, browser profiles and original media with
  restricted scope MUST stay out of committed specifications and artifacts.
- Deployment, paid services and actual customer communications require their own
  applicable user authorization. Setting up Spec Kit does not authorize them.

## Development Workflow

1. Specify the next bounded change in `specs/<feature>/spec.md` using the official
   template. Capture assumptions and acceptance scenarios before writing code.
2. Clarify material uncertainties. Continue independent work when appropriate;
   ask only for decisions that cannot be inferred or safely bounded.
3. Produce `plan.md` against the real repository and this constitution. Record
   contracts, integration boundaries and verification appropriate to that feature.
4. Produce `tasks.md` with traceable requirements, dependencies and completion
   evidence. Analyze consistency before a material implementation.
5. Implement the scoped tasks and execute their checks. Update the artifacts when
   implementation uncovers a requirement or design change.
6. Converge code, requirements and tasks. Record remaining gaps until they are
   resolved or explicitly identified as external dependencies. Seek visual approval
   for a concrete version when visual approval is part of the feature.
7. Review the scoped diff, commit and push each delivery to the user's GitHub
   repository, verifying the remote commit. Do not include unrelated working-tree
   changes, private reference assets or credentials. Report a concrete push failure
   if delivery cannot be completed; never claim a local commit reached GitHub.

Specs are living contracts while a feature evolves. Amend the spec, plan and tasks
together when intended behavior changes, and retain version history. Completed
records MUST identify the behavior and evidence of their delivered version.

## Governance

This constitution derives from Spec Kit adoption on 2026-11-04 and the user's
2026-11-05 definition of section bones, archival and GitHub delivery. Version 2.0.0
redefines the reusable unit to include behavior and separates it from brand skin.
It is a baseline for development, not acceptance of new visual designs.
Explicit user instructions take precedence over this document and `AGENTS.md`.
The dated 2026-11-04 and 2026-11-05 directions supersede the earlier whole-page-only
reuse requirement for the new pipeline. The 2026-11-05 delivery instruction
supersedes earlier default restrictions on automatic scoped commits and pushes.
Other existing constraints persist. The previous constitution is locally archived;
spec 002 and the integration map record the migration and terminology.

Every material plan MUST include a constitution check and explain any applicable
deviation. Amend this constitution when agreed rules change. Use MAJOR for
incompatible principle changes, MINOR for added obligations and PATCH for
clarifications. Record the reason, affected artifacts and migration implications.
Constitution changes alone MUST NOT execute deferred feature implementation.

**Version**: 2.0.0 | **Ratified**: 2026-11-04 | **Last Amended**: 2026-11-05
