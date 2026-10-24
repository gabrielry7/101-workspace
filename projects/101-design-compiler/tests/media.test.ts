import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import type { FixtureBundle } from '../src/contracts/v1/schemas.ts';
import type { MediaAsset, LicenseGrant, MediaUsage } from '../src/media/contracts.ts';
import { mediaContracts } from '../src/media/contracts.ts';
import { rightsGate, evaluateSuitability } from '../src/media/gate.ts';
import { generateMediaNeeds, inventoryMedia, proposeUsage, buildMediaManifest, validateMediaManifest, unknownReview } from '../src/media/plan.ts';
import { permissionFixture, cutoff, syntheticReview } from '../fixtures/media/v1/permissions.ts';
import { checkMediaFixtures } from '../scripts/check-media-fixtures.ts';
import { checkPlannerFixtures } from '../scripts/check-planner-fixtures.ts';

const result = JSON.parse(await readFile(new URL('../data/derived/planner-v1/restaurante.json', import.meta.url), 'utf8'));
const bundle: FixtureBundle = { input: result.input, profile: result.profile, capabilities: result.capabilities, plan: result.plan };
const needs = generateMediaNeeds(result.plan, result.requirements);
const need = needs.find(x => x.role === 'DOCUMENTARY')!;
const context = { client_id: 'synthetic-client', project_id: 'synthetic-project', evaluated_at: cutoff };
function fixture() {
  const { asset, grant } = permissionFixture(need, result.input.business_id);
  const usage = proposeUsage(need, asset, { ...context, business_id: result.input.business_id }, grant.id);
  return { asset, grant, usage };
}
function gate(f: ReturnType<typeof fixture>, assets = [f.asset], at = cutoff, allow = true) {
  return rightsGate(f.asset, f.grant, f.usage, assets, at, { allow_synthetic: allow });
}
test('synthetic valid permission only succeeds under explicit test policy', () => {
  const f = fixture(); assert.equal(gate(f).status, 'ALLOWED');
  assert.equal(gate(f, [f.asset], cutoff, false).status, 'BLOCKED');
  assert.deepEqual(evaluateSuitability(f.asset, f.usage, cutoff), []);
});
const mutations: [string, string, (a: MediaAsset, g: LicenseGrant, u: MediaUsage) => void][] = [
  ['unknown', 'RIGHTS_UNVERIFIED', (_a, g) => { g.review = unknownReview(); }],
  ['document ID is insufficient', 'RIGHTS_UNVERIFIED', (_a, g) => { g.review.evidence_sha256 = null; }],
  ['future review', 'RIGHTS_UNVERIFIED', (_a, g) => { g.review.reviewed_at = '2027-01-01T00:00:00Z'; }],
  ['document changed', 'RIGHTS_UNVERIFIED', (_a, g) => { g.document.sha256 = 'b'.repeat(64); }],
  ['expired at exact boundary', 'RIGHTS_EXPIRED', (_a, g) => { g.valid_until = cutoff; }],
  ['retention expired', 'RIGHTS_EXPIRED', (_a, g) => { g.retention_until = cutoff; }],
  ['not started', 'RIGHTS_NOT_STARTED', (_a, g) => { g.valid_from = '2026-11-01T00:00:00Z'; }],
  ['revoked', 'RIGHTS_REVOKED', (_a, g) => { g.revoked = true; }],
  ['different client', 'CLIENT_NOT_ALLOWED', (_a, _g, u) => { u.client_id = 'other'; }],
  ['different project', 'PROJECT_NOT_ALLOWED', (_a, _g, u) => { u.project_id = 'other'; }],
  ['different use', 'PURPOSE_NOT_ALLOWED', (_a, _g, u) => { u.purpose = 'hero'; }],
  ['different page', 'PAGE_NOT_ALLOWED', (_a, _g, u) => { u.page = '/otra'; }],
  ['different branch', 'SCOPE_NOT_ALLOWED', (_a, _g, u) => { u.scope_id = 'other-branch'; }],
  ['different territory', 'TERRITORY_NOT_ALLOWED', (_a, _g, u) => { u.territory = 'US'; }],
  ['commercial unknown', 'COMMERCIAL_WEB_NOT_ALLOWED', (_a, g) => { g.commercial_web = 'UNKNOWN'; }],
  ['multiclient denied', 'MULTICLIENT_NOT_ALLOWED', (_a, g) => { g.client_ids.push('second'); }],
  ['project reuse denied', 'REUSE_NOT_ALLOWED', (_a, g) => { g.project_ids.push('second'); }],
  ['new transformation', 'TRANSFORMATION_NOT_ALLOWED', (_a, g, u) => { g.transformations = []; u.transformations = ['CROP']; }],
  ['modifications denied', 'DERIVATIVES_NOT_ALLOWED', (_a, g, u) => { g.derivatives = 'DENIED'; u.transformations = ['RESIZE']; }],
  ['AI edit', 'AI_EDIT_NOT_ALLOWED', (_a, _g, u) => { u.transformations = ['AI_EDIT']; }],
  ['AI classification', 'AI_PROCESSING_NOT_ALLOWED', (_a, _g, u) => { u.ai_operations = ['classification']; }],
  ['AI embeddings', 'AI_PROCESSING_NOT_ALLOWED', (_a, _g, u) => { u.ai_operations = ['embedding']; }],
  ['AI vision', 'AI_PROCESSING_NOT_ALLOWED', (_a, _g, u) => { u.ai_operations = ['vision']; }],
  ['AI training', 'AI_PROCESSING_NOT_ALLOWED', (_a, _g, u) => { u.ai_operations = ['training']; }],
  ['automated download', 'AUTOMATION_NOT_ALLOWED', (_a, _g, u) => { u.automated_access = ['download']; }],
  ['automated search', 'AUTOMATION_NOT_ALLOWED', (_a, _g, u) => { u.automated_access = ['search']; }],
  ['attribution absent', 'ATTRIBUTION_REQUIRED', (_a, g) => { g.attribution = { required: true, text: 'Credit' }; }],
  ['unparsed restriction', 'UNRESOLVED_LICENSE_RESTRICTIONS', (_a, g) => { g.restrictions = ['special contract']; }],
  ['source restriction', 'UNRESOLVED_ASSET_RESTRICTIONS', a => { a.restrictions = ['special source']; }],
  ['source blocked', 'SOURCE_BLOCKED', a => { a.upstream_rights_status = 'BLOCKED'; }],
  ['purpose restriction', 'ASSET_PURPOSE_DENIED', (a, _g, u) => { a.denied_purposes = [u.purpose]; }],
  ['original hash absent', 'HASH_UNVERIFIED', a => { a.original_sha256 = null; }],
  ['file changed', 'HASH_UNVERIFIED', a => { a.file_sha256 = 'c'.repeat(64); }],
  ['model release unknown', 'MODEL_RELEASE_REQUIRED', a => { a.third_party.model = 'REQUIRED'; }],
  ['property release unknown', 'PROPERTY_RELEASE_REQUIRED', a => { a.third_party.property = 'REQUIRED'; }],
  ['unknown release requirement', 'MODEL_REQUIREMENT_UNKNOWN', a => { a.third_party.model = 'UNKNOWN'; }],
  ['audio needs independent review', 'AUDIO_RIGHTS_REVIEW_REQUIRED', a => { a.kind = 'audio'; }],
  ['video sound not inspected', 'VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED', a => { a.kind = 'video'; a.audio_track = 'UNKNOWN'; }],
];
for (const [name, code, mutate] of mutations) test(`rights gate blocks ${name}`, () => {
  const f = fixture(); mutate(f.asset, f.grant, f.usage);
  const d = gate(f); assert.equal(d.status, 'BLOCKED'); assert.ok(d.codes.includes(code), JSON.stringify(d));
});
test('missing grant, invalid schema, time, grant hash and wrong IDs fail closed', () => {
  const f = fixture();
  assert.ok(rightsGate(f.asset, null, f.usage, [f.asset], cutoff).codes.includes('RIGHTS_UNKNOWN'));
  assert.ok(rightsGate(f.asset, f.grant, { ...f.usage, script: 'code' }, [f.asset], cutoff).codes.includes('MEDIA_SCHEMA_INVALID'));
  assert.ok(gate(f, [f.asset], 'bad-date').codes.includes('INVALID_EVALUATION_TIME'));
  f.grant.original_sha256 = 'd'.repeat(64); assert.ok(gate(f).codes.includes('GRANT_ASSET_MISMATCH'));
  f.usage.grant_id = 'foreign'; assert.ok(gate(f).codes.includes('GRANT_ASSET_MISMATCH'));
});
test('matching attribution and reviewed release obligations can be fulfilled', () => {
  const f = fixture(); f.asset.third_party.model = 'REQUIRED'; f.asset.third_party.property = 'REQUIRED';
  f.grant.releases.model = syntheticReview('a'.repeat(64)); f.grant.releases.property = syntheticReview('b'.repeat(64));
  f.grant.attribution = { required: true, text: 'Synthetic Credit' }; f.usage.attribution_text = 'Synthetic Credit';
  assert.equal(gate(f).status, 'ALLOWED');
});
function derivedFixture() {
  const f = fixture(); const root = structuredClone(f.asset);
  f.asset.id = 'synthetic-derived'; f.asset.parent_id = root.id; f.asset.transformations = ['TRANSCODE'];
  f.asset.file_sha256 = 'e'.repeat(64); f.asset.hash_review = syntheticReview(f.asset.file_sha256);
  f.asset.inspection.review = syntheticReview(f.asset.file_sha256);
  f.asset.relevance[0]!.review = syntheticReview(f.asset.file_sha256);
  f.asset.documentary!.review = syntheticReview(f.asset.file_sha256); f.usage.asset_id = f.asset.id;
  return { ...f, root };
}
test('derivative retains root permission and lineage, not a fresh unrestricted asset', () => {
  const f = derivedFixture(); const d = gate(f, [f.root, f.asset]);
  assert.equal(d.status, 'ALLOWED'); assert.deepEqual(d.inherited_asset_ids, [f.asset.id, f.root.id]);
  f.root.restrictions = ['no publication']; assert.ok(gate(f, [f.root, f.asset]).codes.includes('UNRESOLVED_ASSET_RESTRICTIONS'));
  f.root.restrictions = []; f.grant.derivatives = 'DENIED'; assert.ok(gate(f, [f.root, f.asset]).codes.includes('DERIVATIVES_NOT_ALLOWED'));
});
test('missing parent, cycle, root hash drift and duplicate inventory block derivatives', () => {
  const f = derivedFixture(); assert.ok(gate(f).codes.includes('MISSING_PARENT'));
  f.root.parent_id = f.asset.id; assert.ok(gate(f, [f.root, f.asset]).codes.includes('LINEAGE_CYCLE'));
  f.root.parent_id = null; f.asset.original_sha256 = 'a'.repeat(64); assert.ok(gate(f, [f.root, f.asset]).codes.includes('LINEAGE_MISMATCH'));
  assert.ok(gate(f, [f.asset, f.asset]).codes.includes('ASSET_INVENTORY_MISMATCH'));
});
test('stock with sufficient rights cannot act as evidence of business, object or branch', () => {
  const f = fixture(); f.asset.documentary = null;
  assert.equal(gate(f).status, 'ALLOWED');
  assert.ok(evaluateSuitability(f.asset, f.usage, cutoff).includes('MISLEADING_BUSINESS_REPRESENTATION'));
  const other = fixture(); other.asset.documentary!.scope_id = 'other-branch';
  assert.ok(evaluateSuitability(other.asset, other.usage, cutoff).includes('MISLEADING_BUSINESS_REPRESENTATION'));
  other.asset.documentary!.scope_id = need.scope_id; other.usage.subject_ids = ['other-product'];
  assert.ok(evaluateSuitability(other.asset, other.usage, cutoff).includes('MISLEADING_BUSINESS_REPRESENTATION'));
});
test('generic illustration needs disclosure and cannot use BUSINESS_EVIDENCE representation', () => {
  const f = fixture(); f.usage.role = 'ILLUSTRATIVE'; f.usage.representation = 'GENERIC_CONTEXT'; f.usage.generic_label = null;
  assert.ok(evaluateSuitability(f.asset, f.usage, cutoff).includes('GENERIC_DISCLOSURE_REQUIRED'));
  f.usage.generic_label = 'Ilustración genérica'; assert.deepEqual(evaluateSuitability(f.asset, f.usage, cutoff), []);
  f.usage.representation = 'BUSINESS_EVIDENCE'; assert.ok(evaluateSuitability(f.asset, f.usage, cutoff).includes('MISLEADING_BUSINESS_REPRESENTATION'));
});
test('uninspected files and changed inspection hashes never pass quality assessment', () => {
  const f = fixture(); f.asset.inspection.status = 'NOT_INSPECTED'; f.asset.inspection.quality = 'UNKNOWN';
  assert.deepEqual(evaluateSuitability(f.asset, f.usage, cutoff), ['NOT_INSPECTED', 'QUALITY_UNCONFIRMED']);
  f.asset.inspection.status = 'REVIEWED'; f.asset.inspection.review.evidence_sha256 = 'a'.repeat(64);
  assert.ok(evaluateSuitability(f.asset, f.usage, cutoff).includes('NOT_INSPECTED'));
});
test('quality alone cannot establish relevance for a use or branch', () => {
  const f = fixture(); f.asset.relevance = [];
  assert.ok(evaluateSuitability(f.asset, f.usage, cutoff).includes('RELEVANCE_UNCONFIRMED'));
});
test('H2 DOCUMENTED inventory neither fabricates hash, dimensions, inspection nor authorization', () => {
  const input = structuredClone(bundle.input);
  input.existing_media = [{ id: 'upstream-photo', source: 'upstream', uri: 'https://example.invalid/photo', kind: 'image',
    scope_id: need.scope_id, rights_status: 'DOCUMENTED', rights_document_ids: ['doc-id'], restrictions: [], width: 999, height: 999 }];
  const a = inventoryMedia(input)[0]!;
  assert.equal(a.original_sha256, null); assert.equal(a.inspection.width, null); assert.equal(a.inspection.status, 'NOT_INSPECTED');
  assert.deepEqual(a.upstream_document_ids, ['doc-id']); assert.ok(a.inspection.findings[0]?.includes('999'));
  assert.ok(rightsGate(a, null, fixture().usage, [a], cutoff).codes.includes('RIGHTS_UNKNOWN'));
});
test('needs bind modules, purposes and scopes; stock is never a documentary substitute', () => {
  assert.ok(needs.some(x => x.role === 'ATMOSPHERIC')); assert.ok(needs.some(x => x.role === 'DOCUMENTARY'));
  assert.ok(need.subject_ids.includes('offering-1')); assert.equal(need.required, false);
  const changed = structuredClone(result.requirements); changed.snapshot_id = 'foreign';
  assert.throws(() => generateMediaNeeds(result.plan, changed), /MISMATCH/);
});
test('branch-specific media needs remain separate and no absent menu is created', async () => {
  const hotel = (await checkPlannerFixtures()).find(x => x.scenario === 'hotel-restaurante-sucursales')!.result;
  assert.equal(hotel.status, 'READY'); if (hotel.status !== 'READY') return;
  const n = generateMediaNeeds(hotel.plan, hotel.requirements);
  const rooms = n.filter(x => x.purpose === 'document:rooms'); assert.equal(new Set(rooms.map(x => x.scope_id)).size, 2);
  assert.equal(new Set(n.filter(x => x.purpose === 'document:menu').map(x => x.scope_id)).size, 1);
});
test('manifest replays and consumer rejects modified approval, needs, gaps or lineage', () => {
  const f = fixture(); const inventory = { assets: [f.asset], grants: [f.grant], usages: [f.usage] };
  const c = { ...context, allow_synthetic: true };
  const output = buildMediaManifest(bundle, result.requirements, inventory, c);
  assert.equal(output.manifest.decisions[0]?.status, 'ALLOWED');
  assert.deepEqual(buildMediaManifest(bundle, result.requirements, inventory, c), output);
  assert.ok(validateMediaManifest(output.manifest, output.brief, bundle, result.requirements, c).success);
  const manifest = structuredClone(output.manifest); manifest.needs = [];
  assert.ok(!validateMediaManifest(manifest, output.brief, bundle, result.requirements, c).success);
  const brief = structuredClone(output.brief); brief.gaps = [];
  assert.ok(!validateMediaManifest(output.manifest, brief, bundle, result.requirements, c).success);
  const blocked = buildMediaManifest(bundle, result.requirements, inventory, context); blocked.manifest.decisions[0]!.status = 'ALLOWED';
  assert.ok(!validateMediaManifest(blocked.manifest, blocked.brief, bundle, result.requirements, context).success);
});
test('manifest rejects duplicates, altered plan and wrong client/need binding', () => {
  const f = fixture(); const c = { ...context, allow_synthetic: true };
  assert.throws(() => buildMediaManifest(bundle, result.requirements, { assets: [f.asset, f.asset], grants: [f.grant], usages: [f.usage] }, c), /DUPLICATE/);
  const bad = structuredClone(bundle); bad.plan.pages[0]!.modules = [];
  assert.throws(() => buildMediaManifest(bad, result.requirements, { assets: [], grants: [], usages: [] }, c), /INVALID/);
  f.usage.business_id = 'other'; f.usage.need_id = 'other';
  const output = buildMediaManifest(bundle, result.requirements, { assets: [f.asset], grants: [f.grant], usages: [f.usage] }, c);
  assert.ok(output.manifest.decisions[0]?.suitability_codes.includes('USAGE_CONTEXT_MISMATCH'));
  assert.ok(output.manifest.decisions[0]?.suitability_codes.includes('NEED_BINDING_MISMATCH'));
});
test('transformation at use time does not borrow inspection of original', () => {
  const f = fixture(); f.usage.transformations = ['CROP'];
  const output = buildMediaManifest(bundle, result.requirements, { assets: [f.asset], grants: [f.grant], usages: [f.usage] }, { ...context, allow_synthetic: true });
  assert.ok(output.manifest.decisions[0]?.suitability_codes.includes('UNINSPECTED_TRANSFORMED_USAGE'));
});
test('quality failure preserves a gap even with valid rights', () => {
  const f = fixture(); f.asset.inspection.quality = 'FAIL';
  const output = buildMediaManifest(bundle, result.requirements, { assets: [f.asset], grants: [f.grant], usages: [f.usage] }, { ...context, allow_synthetic: true });
  assert.equal(output.manifest.decisions[0]?.status, 'BLOCKED'); assert.ok(output.brief.gaps.some(x => x.need.id === need.id));
});
test('seven planner outputs and explicit synthetic controls validate without H3 approval', async () => {
  const fixtures = await checkMediaFixtures(); assert.equal(fixtures.length, 10);
  for (const f of fixtures.filter(f => f.scenario !== 'real-restaurante-pilot')) {
    assert.ok(f.success, f.scenario); assert.equal(f.output.brief.closure, 'PENDING_AUTHORIZED_MEDIA_PACKAGE');
  }
});
for (const [name, schema] of Object.entries(mediaContracts)) test(`${name} rejects unsupported versions and uncontracted fields`, () => {
  assert.equal(schema.safeParse({ schema_version: '2.0.0', code: 'script' }).success, false);
});
