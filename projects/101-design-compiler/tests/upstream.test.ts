import test from 'node:test';
import assert from 'node:assert/strict';
import { loadFixture, fixtureNames } from '../scripts/load-fixtures.ts';
import { BusinessInputV1 } from '../src/contracts/v1/schemas.ts';
import { inputSha256, canonicalJson, validateUpstreamEnvelope } from '../src/upstream/v1/protocol.ts';
import type { UpstreamEnvelope } from '../src/upstream/v1/protocol.ts';
import { splitHierarchy } from '../src/taxonomy/contracts.ts';

async function envelope(name: typeof fixtureNames[number] = 'restaurante'): Promise<UpstreamEnvelope> {
  const fixture = await loadFixture(name) as { input: unknown };
  const input = BusinessInputV1.parse(fixture.input);
  return {
    protocol_version: '1.0.0', message_id: `synthetic-message-${name}`,
    producer: { system: '101-world-model', source_schema: 'SYNTHETIC_CONTRACT_TEST_NOT_REAL_SITESPEC', source_schema_version: 'test-v1', source_revision: 'synthetic-fixture', adapter_version: '1.0.0' },
    produced_at: input.as_of, business_input_sha256: inputSha256(input), business_input: input,
    category_context: input.category_observations.map(({ confidence: _confidence, ...category }) => ({
      ...category, hierarchy: splitHierarchy(category.value),
      provenance: [{ source_record_id: `synthetic:${category.id}`, source: category.source, observed_at: input.as_of }],
    })), activity_relationships: [],
  };
}
function code(raw: unknown, expected: string) {
  const result = validateUpstreamEnvelope(raw, { allow_synthetic: true });
  assert.equal(result.success, false); assert.ok(result.diagnostics.some(x => x.code === expected), JSON.stringify(result.diagnostics));
}
for (const name of fixtureNames) test(`${name}: proposed upstream envelope preserves H0 BusinessInputV1`, async () => {
  const raw = await envelope(name); const result = validateUpstreamEnvelope(raw, { allow_synthetic: true });
  assert.equal(result.success, true, JSON.stringify(result.diagnostics));
  assert.deepEqual(result.data!.business_input, raw.business_input);
  assert.equal(BusinessInputV1.safeParse(result.data!.business_input).success, true);
});
test('synthetic inputs cannot pass as real upstream without explicit test policy', async () => {
  const result = validateUpstreamEnvelope(await envelope()); assert.equal(result.success, false);
  assert.ok(result.diagnostics.some(x => x.code === 'SYNTHETIC_INPUT_REJECTED'));
});
test('snapshot checksum rejects changes and is stable across object key insertion order', async () => {
  assert.equal(inputSha256({ b: [1, 2], a: 'test' }), inputSha256({ a: 'test', b: [1, 2] }));
  assert.notEqual(inputSha256([1, 2]), inputSha256([2, 1]));
  assert.throws(() => canonicalJson({ a: undefined }), /NON_JSON_VALUE/);
  const raw = await envelope(); raw.business_input.restrictions.push('new restriction'); code(raw, 'INPUT_HASH_MISMATCH');
});
test('unknown protocol/schema versions and arbitrary fields are rejected', async () => {
  const raw = await envelope(); code({ ...raw, protocol_version: '2.0.0' }, 'PROTOCOL_SCHEMA_INVALID');
  code({ ...raw, runtime_js: 'alert(1)' }, 'PROTOCOL_SCHEMA_INVALID');
});
test('category provenance, original text and hierarchy cannot be silently rewritten', async () => {
  const raw = await envelope('gimnasio');
  raw.category_context[0]!.hierarchy = ['Gym']; code(raw, 'HIERARCHY_MISMATCH');
  raw.category_context[0]!.value = 'Restaurant'; code(raw, 'CATEGORY_CONTEXT_MISMATCH');
});
test('every category needs actual source provenance in the envelope', async () => {
  const raw = await envelope(); raw.category_context[0]!.provenance = []; code(raw, 'INVALID_PROVENANCE');
  raw.category_context = []; code(raw, 'MISSING_CATEGORY_CONTEXT');
});
test('a category or unrelated fact cannot confirm an operational capability', async () => {
  const raw = await envelope(); const cap = raw.business_input.business_capabilities.find(x => x.id === 'delivery')!;
  cap.status = 'CONFIRMED_PRESENT'; cap.evidence_ids = ['f-category'];
  raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'UNVERIFIED_CAPABILITY');
});
test('snapshot references, identity publication, scopes and evidence are checked at the boundary', async () => {
  const raw = await envelope(); raw.business_input.facts.find(x => x.id === 'f-name')!.publication = 'WITHHELD';
  raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'IDENTITY_NOT_PUBLISHABLE');
  raw.business_input.offerings[0]!.name_fact_id = 'missing'; raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'UNKNOWN_FACT');
  raw.business_input.offerings[0]!.scope_id = 'foreign-branch'; raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'UNKNOWN_SCOPE');
});
test('withheld and conflicted non-identity facts survive the envelope without approval upgrade', async () => {
  const raw = await envelope(); const fact = raw.business_input.facts.find(x => x.id === 'f-offering-1')!;
  fact.publication = 'CONFLICTED'; raw.business_input_sha256 = inputSha256(raw.business_input);
  const result = validateUpstreamEnvelope(raw, { allow_synthetic: true }); assert.equal(result.success, true);
  assert.equal(result.data!.business_input.facts.find(x => x.id === fact.id)!.publication, 'CONFLICTED');
});
test('branch data cannot bind the address of another branch', async () => {
  const raw = await envelope();
  raw.business_input.locations.push({ id: 'branch-2', coordinate_fact_ids: [], opening_hours_fact_ids: [], exception_fact_ids: [], visit_policy_fact_ids: [] });
  raw.business_input.facts.push({ ...raw.business_input.facts[0]!, id: 'f-address-other', kind: 'address', scope_id: 'branch-2', value: 'Synthetic address only' });
  raw.business_input.locations[0]!.address_fact_id = 'f-address-other';
  raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'SCOPE_MISMATCH');
});
test('coexistence cannot be declared without approved explicit activity evidence', async () => {
  const raw = await envelope(); raw.business_input.category_observations.push({ ...raw.business_input.category_observations[0]!, id: 'category-2' });
  raw.category_context.push({ ...raw.category_context[0]!, id: 'category-2' });
  raw.activity_relationships.push({ id: 'hybrid', kind: 'COEXISTING', category_observation_ids: ['category-1', 'category-2'], evidence_ids: ['f-name'] });
  raw.business_input_sha256 = inputSha256(raw.business_input); code(raw, 'UNVERIFIED_ACTIVITY_RELATIONSHIP');
});
