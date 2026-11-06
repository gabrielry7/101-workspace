# Social production — initial working slice, 6 November 2026

Historical slice at6e6d93b. The current [Instagram/intake extension](INSTAGRAM_CONNECTION.md)
supersedes the500KB upload limit and absent connector below:12MB resumable intake and
a tested connector are now implemented, with live Meta access still blocked.

Implements part of the supplied 101 Social master plan inside the existing workspace.
Stage 0/1 are **not complete**. Honorato is the selected pilot; the owner is identifying
approved material and current facts. No real Honorato photo/fact has been approved
through this implementation yet. No social or model provider was called.

## Reuse and actual boundary

`api.create_app` → existing `scoped_staff` membership/CSRF/growth permissions →
`social_production.register` → existing commerce SQLAlchemy database → versioned
pack, source bytes and permission statement → Pillow render → existing React workspace
`/workspace/social` → digest-bound human approval → downloadable ZIP.

Commerce business IDs are reused through foreign keys, but are not automatically
canonical World Model Business IDs. Pack statements are explicit operator confirmations;
they do not alter Genome or Truth. Existing campaign tables are email/WhatsApp/SMS
recipient dispatch, so social does not manufacture recipients to reuse that schema.
Existing GBP caches remain isolated. Instagram archives are historical source material,
not permission to publish or evidence that prices remain current.

The separate Astro design compiler produces web compositions, with no demonstrated
static image-export boundary. This first photo-first renderer uses Pillow's EXIF-aware
crop and JPEG export; no compiler integration is claimed. No overlays or generated
product imagery. Image source, crop, confirmed statements and renderer version remain
editable. Original bytes are retained separately; deletion purges derived pixels and
blocks subsequent preview/export. Already downloaded copies cannot be remotely revoked.

## Working scope and limits

- Existing staff login and tenant permissions; no owner invitations added.
- Actual JPEG/PNG upload bytes, at most 500 KB in UI (bounded JSON intake), max24M pixels;
  photo must support1080×1350 without upscaling. No resumable large-media uploads yet.
- Explicit use permission and expiry; reference-only/revoked/expired material rejected.
- Confirmed statements, objective, owner-sourced question, hypothesis, brand direction,
  intended inquiry measure; no fabricated diagnosis or search volume.
- Deterministic caption from confirmed statements; **not model-generated copy**.
- Editable horizontal crop and caption; rendered1080×1350JPEG.
- Version conflict checks; repeat create request returns same saved pack; sequential
  approval retries are idempotent. Concurrent duplicate-create/approve races still need
  qualification; this is not a general durable render-job implementation.
- Exact image/document hash approval, independent human craft/brand/purpose attestations;
  changed revision needs new approval. Export revalidates source and fact expiry.
- ZIP contains post.jpg, original, caption.txt, editable.json, approval.json, measurement.json.
- No publication: account is null, action is manual export. Metrics are null with reason,
  not zero. Generation provider cost is zero; compute/storage cost remains unmeasured.

## Migration and rollback

New tables: social_assets, social_packs, social_revisions, social_approvals. No alteration
of existing business/campaign data. Fresh database creation includes them; existing
installations require explicit offline `social_production.upgrade(engine)` after backup
and stopping writers. Demo script uses a dedicated disposable DB. No existing running
database was migrated. For rollback, restore prior application build and backup; retain
new tables for recovery. Do not drop customer uploads to roll back application code.

Pillow12.3.0 is pinned (HPND/PIL license family; distribution review remains). Existing
React/Vite stack and local Manrope assets reused. No FFmpeg, transcription model,
Remotion, trained ranker, new external services or paid generation added.

## Verification and demo

From the application directory, use its installed Python environment with `PYTHONPATH=src`:

- `python -m pytest tests/test_social_production.py -q`
- `python -m pytest tests/test_campaigns.py -q`
- `npm run build --prefix frontend`
- `python scripts/social_demo.py --db /tmp/social-demo.db --port 8833`

The local demo accepts `101` / `101` through the existing explicit demo alias, which authenticates the seeded campaign manager. Normal production authentication is unchanged. The underlying synthetic campaign-manager credentials are defined in
`campaign_demo.py`, never real merchant credentials. Browser evidence is retained in
World Model `artifacts/social-production-20261106`: synthetic uploaded fixture,
editable exported package, desktop/mobile screenshots and repeatable browser script.
The browser logs in, uploads a real file, saves, approves, edits, confirms old approval
is invalid, reapproves and downloads. This is fixture quality proof, not creative or
commercial quality proof for a client.

Visual review uses saved reference3 (workspace shell) and existing identity: clear
navigation and white work surfaces. Initial phone overflow was corrected; final390px
render has390px scroll width. Desktop1440 and phone390 were visually inspected.

## Capability matrix

| Capability | State / evidence |
|---|---|
| Workspace authentication/scoping | Existing implementation; exercised with synthetic accounts |
| Upload/render/revision/approval/export | Actual bytes and browser workflow; synthetic material |
| Instagram connection/import/publication | Not integrated here; no live probe or access claim |
| GBP | Existing separate adapter/cache; no social cross-use |
| Model copy generation | Not enabled; deterministic confirmed statements only |
| Metrics/diagnosis | Unknown baseline honestly shown; real import/analysis not built |
| Honorato approved output | Pending owner-designated material/facts and actual review |
| Video | Not built in this slice |

## Required next work under the accepted master plan

Complete Stage1: invitations, canonical binding/Truth boundary, larger resumable uploads,
asset reuse/retention lifecycle, source-bound diagnosis, persistent brand examples and
pairwise judgments (A/B/tie/both unacceptable/insufficient context), richer editable design
layers, targeted renderer checks, cost/effort records and durable job concurrency.
Use a real authorized Honorato photograph/facts and obtain actual owner approval.
Then Stage2: one shot recipe, bounded clip intake, probe/transcript with corrections,
validated source-span EDL, controlled FFmpeg preview/final/cover and complete human
watch/listen review. Preserve originals, negations and natural sound.
Stage3 remains separately authorized publication with reconciliation and correctly
defined result snapshots. Stages4/5 research and learned ranking do not block production.
No route here executes model-supplied code, publishes, sends messages or spends money.
