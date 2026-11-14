# Social in the shared workspace

Social is registered by the normal `api.create_app`, rendered inside the existing
React shell at `/workspace/social`, and authorized by the same staff cookie,
membership and growth permissions used by Customers/Campaigns. No social-specific
account or business registry is introduced. Demo aliases remain explicitly limited
to development demo composition; they are not production credentials.

The provisioner creates the commerce profile with the canonical Business UUID as
its existing `business_id`. Social assets/packs reference that profile directly.
Historical free-form demo IDs stay historical; integration does not remap them.
Pack facts are owner-confirmed statements with sources/validity, not automatic
Genome promotion or new canonical Truth. Existing analytics remains intact.

## Existing database upgrade

Back up and verify the selected database and stop writers. Install the reviewed
commerce package and its declared Pillow dependency. Then run through the existing
maintenance owner (database URL comes from the private environment):

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-social --offline
```

This additively creates `social_assets`, `social_packs`, `social_revisions`,
`social_approvals`, `social_uploads`, `social_contexts`, `social_context_versions`
and `social_fact_dependencies`; it is repeatable. It refuses incomplete
existing social tables rather than silently accepting an incompatible schema.
No contacts, orders, memberships, campaigns or provisioning records are replaced.
Startup does not silently install social tables into an existing database. An
authorized request receives a clear 503 until the upgrade is applied; unauthorized
requests still fail authorization first. No credentials are required for offline
coding or this migration. Configured Instagram independently requires the existing
`upgrade-connections` maintenance command and live provider qualification.

Rollback: stop writers and restore the previous application release; leave additive
social tables/data intact. If database restore is needed, retain/quarantine new
uploads and reconcile writes made since backup before restoring. Do not drop social
records or overwrite the separate demo database as an application rollback.

## Verification

`tests/test_social_workspace.py` exercises an existing workspace upgrade twice,
contact/campaign preservation, actual asset/render/approval/export, app restart
with the same staff session, and membership revocation. Run its PostgreSQL case
only with `SOCIAL_TEST_DISPOSABLE_POSTGRES_URL` pointing to an explicitly disposable
database: the fixture drops social tables to rehearse an old installation.
Missing configuration skips that one case, not a PostgreSQL qualification claim.

`tests/test_social_workspace_browser.py` logs into the combined workspace once,
creates/approves a post, navigates Customers/Sales/Campaigns, returns to the saved
post and downloads it. A multi-business account switching contexts must clear the
previous business's form, library and approval. Captures go to a temporary directory
unless `SOCIAL_BROWSER_EVIDENCE` explicitly selects an evidence destination.

The base repository's `tests/provisioning/test_social_workspace.py` exercises a
normally provisioned canonical business and owner across social and analytics,
including foreign-owner denial and membership revocation. This is synthetic
integration proof, not a live Instagram or Honorato creative approval.

Production hosting, current owner-approved material, stronger static design/copy,
video and publication/outcome learning remain on `docs/social/ROADMAP.md` in the
base repository. The existing public social preview stays independently configured
until a shared deployment is explicitly verified.

## Current marketing assertions and recovery (N02)

`social_context.py` adds three tables: `social_contexts` (current pointer per existing
business/location), `social_context_versions` (immutable context/fact snapshots),
and `social_fact_dependencies` (exact pack revision → fact version). Run the same
explicit offline `upgrade-social` command after backup and stopping writers. It
backfills old pack facts as `legacy_pack_assertion` versions; it never rewrites old
pack JSON, approval digests, original media or rendered bytes. Repeating it is safe.
Startup on the previous five-table schema returns scoped503 until upgraded.
Rollback to the previous application retains all eight tables and original bytes;
new context data becomes inaccessible in that old UI. Re-upgrade before using new
facts again. Do not drop tables or restore over later uploads as a code rollback.

The short business brief saves offering, objective, buying destination, constraints
and locale. Optional capacity/margin are null when unknown. Individual facts retain
a typed string representation (`text`, exact decimal `number`/`money`, `boolean`),
unit/currency, source, effective/expiry timestamps, authenticated verifier and
revision. A price caption is derived from its exact stored amount/currency, not a
second independently editable price string. Changes increment only the affected
fact revision; omitted facts become withdrawn tombstones, so re-adding an ID cannot
make an old approval valid again. Concurrent edits require the expected version.

These are **owner/operator marketing assertions for explicit manual review**, not
canonical Business records, legal-ownership verification or global Truth decisions.
No historical caption, Genome value or connection import is automatically confirmed.
The provisioning composition installs `social_location_belongs_to_business`; it
checks the canonical BusinessLocation row's Business FK. An uncomposed demo can use
its ordinary business scope but cannot invent canonical location membership. Location
facts cannot be selected into business-wide or another location's packs. No canonical
Genome/Truth rows are written, and no automated publishing authority is granted.

`GET /social/context` and `PUT /social/context` operate on current assertions;
`GET /social/context/history` retains their historical basis. A pack includes exact
`fact_refs` plus optional `context_version_id` and snapshots its business brief.
Changed, withdrawn or expired selected facts and changed brief fields block approval
and export. Unrelated fact changes do not invalidate selected facts. A scoped pack
GET remains readable for correction, with `stale_reasons` and historical approval
status. Valid photographs remain previewable; revoked/expired source pixels remain
blocked. The owner chooses current data, confirms the correction, saves a new pack
revision and reviews it again. Old exported/approved snapshots remain unchanged;
there is still no publication receipt subsystem.

## Repeatable focused release command (N01)

Build the frontend, then run `scripts/verify_social.sh` using a Python environment
with the declared test dependencies and an installed Playwright browser. Set
`SOCIAL_TEST_DISPOSABLE_POSTGRES_URL` to a UTF-8 **disposable** PostgreSQL database;
the script refuses to omit this gate. The PG test uses a fresh uniquely named schema
per run and removes only that schema afterward. Existing retained DBs must not be
used. Optional `PYTHON`, `COMMERCE_BROWSER_EXECUTABLE`, `SOCIAL_BROWSER_EVIDENCE`
select the interpreter/browser/artifact location. No credentials are printed.

The command covers API scope/CSRF/viewer denials, both resumable JPEG/PNG uploads,
duplicate completion, revision approval/export, legacy schema/backfill, expiry and
withdrawal, lost-update rejection, SQLite/PG restart, mocked Instagram behavior and
two desktop/mobile browser journeys through Presencia → Instagram. It makes no
provider/model/publication calls. Canonical provisioning scope is separately tested
in the World Model consumer suite with `PROVISIONING_COMMERCE_SOURCE` pointing to
the installed/reviewed commerce package source.

## Brand references and sourced questions (N03)

`social_creative.py` owns two additive tables, `social_creative_boards` and
`social_creative_versions`, keyed to the existing business and optionally validated
canonical location. Use the same offline `upgrade-social` command after backup and
stopping writers. Existing facts, originals, pack revisions and approvals are not
rewritten. Rollback retains these tables; the previous UI simply cannot edit them.
No customer references or questions are invented during migration.

`GET/PUT /social/creative` reads/saves the board with optimistic revision checks.
`GET /social/creative/history` returns prior snapshots. Voice/visual rules are
independent of the business fact store. References retain positive/negative/borderline
judgments, reasons, source, observation/expiry, permission statement, content type,
and local-alternative/remote-comparable/creative/own-brand purpose. A URL is a saved
reference, never a fetch authorization. Links are not automatically collected; no
third-party pixels are downloaded. Existing owned library assets may be referenced
without acquiring additional output rights. Reference-only media still cannot become
the production photo, and revoked/expired reference assets block dependent exports.

Questions distinguish owner suggestion, actual customer question, platform observation,
manual research and hypothesis. They retain source context/date, intent, next action
and IDs of facts needed to answer. Questions without an answer can be saved, but
cannot be selected for production until current answer facts are supplied. Selection
requires exact fact versions under the existing N02 validation. There are no search
volume/rank/view input fields: unknown demand remains null, including for a platform
observation. This is manual research intake, not a live social-search integration.

Pack fields `creative_version_id`, `reference_ids` and `question_id` resolve on the
server into an immutable `creative_snapshot`. Only selected references/question are
snapshotted with the voice rules and version. Relevant changed/withdrawn/expired
context invalidates current approval/export while keeping recovery metadata readable.
Unselected example edits do not unnecessarily invalidate a pack. Per-item and style
revision counters prevent reviving an old approval by retiring and re-adding context.
Historical versions remain unchanged. `revision_reason` distinguishes factual,
style, strategy and crop edits; editing a pack never silently trains or overwrites
persistent brand preferences. Explicit board edits retain actor, date and reason.

The existing UI adds a collapsible board with References / Voice and style / Questions,
then selection controls in the post brief. The review displays the selected source
context. Saved context can be reused in another pack after leaving and returning,
with no retyping. Source text remains untrusted data, never executable instructions.
The exported editable JSON is an internal posting-package record, not permission
to republish references; only the approved post image/caption are finished content.
No taste model, competitor crawler, generated copy or automatic planning is added.

### Guided business setup

`social_onboarding.py` validates explicit choice IDs and custom details;
`PUT /social/context/onboarding` compiles them into the existing business brief
and appends an immutable context version. The normal owner scope, CSRF, canonical
location check and expected-revision conflict protection apply. No new table or
provider call. Unknown offering/objective/buying destination/locale are null.
The snapshot retains the original answers, selected IDs, materials and dates/actor
from the context writer. Choices do not create confirmed marketing facts.

`social-onboarding.tsx` presents four short questions then review with optional
conditions/lead time. A custom answer is retained across reloads. Nothing is
preselected; selection is not saved until final confirmation. Unsaved navigation
is intentionally not resumable: the form says when saving happens. Current facts,
capacity/margin and historical versions survive. Unchanged expired facts stay
expired without being reverified when only onboarding changes. Existing manual
fact editing remains available. Guided summary fields are edited through the guide;
a direct API rewrite of those fields retires the old guided projection while
preserving its historical version. Capacity/margin/fact-only edits retain answers.

Material choices describe what the owner says they have; they are not uploaded
files, usage permission or a promise of an automated proposal. Photo upload and
approval/export remain the actual production path. Video capture/editing and
automatic research/proposals remain future work. The voice examples use the
existing creative board and do not turn factual corrections into style preferences.

Validation: `scripts/verify_social.sh` now includes onboarding API cases and the
fourth owner browser workflow. Source and renderer output remain synthetic fixtures.
Rollback should retain context JSON; older clients cannot safely edit newly nullable
brief fields. Prefer a forward fix or temporarily disable writes before an older
application rollback; never discard saved answers or fact history.
