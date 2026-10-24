import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadFixture } from '../scripts/load-fixtures.ts';
import { loadMappingRegistry } from '../scripts/load-taxonomy.ts';
import { BusinessInputV1, BusinessProfileV1 } from '../src/contracts/v1/schemas.ts';
import { loadInventoryBytes } from '../src/taxonomy/inventory.ts';
import { classifyBusiness, resolveObservation, validateRegistry } from '../src/taxonomy/resolve.ts';
import { splitHierarchy } from '../src/taxonomy/contracts.ts';
import type { ActivityRelationship, Archetype, MappingRule, TaxonomyObservation } from '../src/taxonomy/contracts.ts';

const registry = await loadMappingRegistry();
const rules = registry.rules;
const cases = JSON.parse(await readFile(new URL('../fixtures/taxonomy/v1/cases.json', import.meta.url), 'utf8')) as {
  data_mode: string; cases: { source: string; field: string; value: string; archetypes: Archetype[] }[];
};
const observation = (source: string, field: string, value: string): TaxonomyObservation => ({
  id: 'category-1', source, field, value, hierarchy: splitHierarchy(value), evidence_ids: [], provenance: [],
});
const headers = 'source\tcategory_field\tcategory_value\tprovider_category_id\tsource_observations\tbusiness_candidates\tother_observations';
const bytes = (text: string) => new TextEncoder().encode(text);
async function input() {
  const bundle = await loadFixture('gimnasio') as { input: unknown };
  return BusinessInputV1.parse(bundle.input);
}
for (const entry of cases.cases) test(`${entry.source}/${entry.field}/${entry.value} maps commercial hypotheses`, () => {
  assert.equal(cases.data_mode, 'SYNTHETIC_FIXTURE');
  const result = resolveObservation(observation(entry.source, entry.field, entry.value), rules);
  assert.equal(result.outcome, 'MAPPED');
  assert.deepEqual(result.archetypes, [...entry.archetypes].sort());
});
test('inventory retains provider, literal hierarchy, provider code, counts, raw fields and byte provenance', () => {
  const text = `${headers}\nFoursquare\tfoursquare.category\tSports > Gym > Gym\t00123\t7\t5\t2\n`;
  const records = loadInventoryBytes(bytes(text), 'data/reference/synthetic-test.tsv');
  const record = records[0]!;
  assert.equal(record.provider, 'foursquare'); assert.equal(record.provider_label, 'Foursquare');
  assert.equal(record.provider_category_id, '00123');
  assert.deepEqual(record.hierarchy, ['Sports', 'Gym', 'Gym']);
  assert.deepEqual(record.counts, { source_observations: 7, business_candidates: 5, other_observations: 2 });
  assert.equal(record.raw['category_value'], 'Sports > Gym > Gym');
  assert.equal(record.provenance.line_start, 2); assert.match(record.provenance.sha256, /^[a-f0-9]{64}$/);
  assert.deepEqual(loadInventoryBytes(bytes(text), 'data/reference/synthetic-test.tsv'), records);
});
test('original and normalized inventory rows remain separate, not business associations', () => {
  const text = `${headers}\nosm\tshop\thardware\t\t9\t7\t2\nosm\t101.normalized_category\tRetail/Other Retail\t\t9\t7\t2\nfoursquare\t101.normalized_category\tRetail/Other Retail\t\t9\t7\t2\n`;
  const records = loadInventoryBytes(bytes(text), 'synthetic.tsv');
  assert.equal(records.length, 3);
  assert.equal(records[0]!.normalized_category, null);
  assert.equal(records[1]!.normalized_category, 'Retail/Other Retail');
  assert.deepEqual(records[1]!.hierarchy, ['Retail', 'Other Retail']);
  assert.equal(records[0]!.counts.business_candidates, 7); assert.equal(records[2]!.counts.business_candidates, 7);
  assert.ok(records.every(x => !('business_id' in x)));
});
test('quoted CSV supports escaped quotes, commas, newline spans and UTF-8 BOM', () => {
  const text = '\uFEFF' + headers.replaceAll('\t', ',') + '\r\n"OSM",shop,"category, with ""quote""\r\nand newline",,1,1,0\r\n';
  const record = loadInventoryBytes(bytes(text), 'synthetic.csv')[0]!;
  assert.equal(record.category_value, 'category, with "quote"\r\nand newline');
  assert.equal(record.provenance.line_start, 2); assert.equal(record.provenance.line_end, 3);
});
test('duplicate inventory rows are preserved, never deduplicated into businesses', () => {
  const row = '\nosm\tshop\thardware\t\t1\t1\t0';
  const records = loadInventoryBytes(bytes(headers + row + row), 'synthetic.tsv');
  assert.equal(records.length, 2); assert.notEqual(records[0]!.id, records[1]!.id);
});
test('invalid headers, malformed counts, column counts and encoding fail explicitly', () => {
  assert.throws(() => loadInventoryBytes(bytes('source,value\nosm,hardware'), 'bad.csv'), /Expected all seven/);
  assert.throws(() => loadInventoryBytes(bytes(headers + '\nosm\tshop\thardware\t\t-1\t1\t0'), 'bad.tsv'), /Invalid source_observations/);
  assert.throws(() => loadInventoryBytes(bytes(headers + '\nosm\tshop'), 'bad.tsv'), /Wrong column count/);
  assert.throws(() => loadInventoryBytes(new Uint8Array([0xff]), 'bad.tsv'));
});
test('provider and field restrict a mapping; substrings never activate a rule', () => {
  assert.equal(resolveObservation(observation('osm', 'shop', 'restaurant'), rules).outcome, 'UNMAPPED');
  assert.equal(resolveObservation(observation('foursquare', 'foursquare.category', 'Not a Gym'), rules).outcome, 'UNMAPPED');
  assert.equal(resolveObservation(observation('future-provider', 'shop', 'hardware'), rules).outcome, 'UNMAPPED');
});
test('registry is extensible without changing the resolver and rejects conflicting rules', () => {
  const rule: MappingRule = { id: 'new-provider-retail', provider: 'future-provider', fields: ['classification'], match: 'EXACT', values: ['tools'], outcome: 'MAPPED', archetypes: ['product_retail'], alternatives: [], rationale: 'Reviewed test extension' };
  assert.equal(resolveObservation(observation('future-provider', 'classification', 'tools'), [...rules, rule]).outcome, 'MAPPED');
  const conflicting = { ...rule, id: 'conflicting-extension', archetypes: ['lodging'] as Archetype[] };
  assert.equal(resolveObservation(observation('future-provider', 'classification', 'tools'), [...rules, rule, conflicting]).outcome, 'AMBIGUOUS');
  assert.throws(() => validateRegistry([rule, rule]), /DUPLICATE_RULE_ID/);
});
test('deepest Foursquare hierarchy node wins over broad ancestors', () => {
  const result = resolveObservation(observation('foursquare', 'foursquare.category', 'Travel > Hotel > Restaurant'), rules);
  assert.deepEqual(result.archetypes, ['food_hospitality']);
});
test('hierarchy metadata cannot replace an original category with another activity', () => {
  const result = resolveObservation({ ...observation('foursquare', 'foursquare.category', 'Restaurant'), hierarchy: ['Gym'] }, rules);
  assert.equal(result.outcome, 'AMBIGUOUS'); assert.ok(result.diagnostics.includes('HIERARCHY_SOURCE_CONFLICT'));
});
test('explicit broad normalized label can be refined, incompatible labels require abstention', () => {
  const base = observation('foursquare', 'foursquare.category', 'Sports > Gym');
  assert.equal(resolveObservation({ ...base, normalized_category: 'Beauty and Wellness/Fitness and Wellness' }, rules).outcome, 'MAPPED');
  assert.equal(resolveObservation({ ...base, normalized_category: 'Food/Restaurant' }, rules).outcome, 'AMBIGUOUS');
});
test('classification returns V1 profile and candidate relevance without changing verified upstream capabilities', async () => {
  const business = await input(); const before = structuredClone(business);
  const result = classifyBusiness(business, { rules });
  assert.equal(result.status, 'RESOLVED'); assert.equal(BusinessProfileV1.safeParse(result.profile).success, true);
  assert.ok(result.candidate_capabilities.some(x => x.id === 'membership_signup'));
  assert.ok(result.candidate_capabilities.every(x => x.authority === 'RELEVANCE_ONLY_NOT_VERIFIED'));
  assert.deepEqual(business, before);
  assert.equal(business.business_capabilities.find(x => x.id === 'membership_signup')!.status, 'UNKNOWN');
  assert.ok(!('capabilities' in result)); assert.ok(!('site_plan' in result));
});
test('all category fixtures leave operational capabilities empty when upstream has verified none', async () => {
  for (const entry of cases.cases) {
    const business = await input();
    business.business_capabilities = []; business.offerings = [];
    business.category_observations = [{ id: 'category-1', source: entry.source, field: entry.field, value: entry.value, confidence: 1, evidence_ids: [] }];
    const before = structuredClone(business);
    const result = classifyBusiness(business, { rules });
    assert.deepEqual(business, before);
    assert.deepEqual(business.business_capabilities, []);
    assert.ok(result.candidate_capabilities.every(x => !('status' in x) && !('frontend_status' in x)));
    assert.ok(!('capability_profile' in result) && !('site_plan' in result));
  }
});
test('two unrelated commercial labels are ambiguous, not automatically a hybrid', async () => {
  const business = await input();
  business.category_observations.push({ id: 'category-2', source: 'osm', field: 'shop', value: 'hardware', confidence: 1, evidence_ids: [] });
  const result = classifyBusiness(business, { rules });
  assert.equal(result.status, 'AMBIGUOUS'); assert.equal(result.profile.classification, 'UNRESOLVED');
});
test('approved coexistence enables combinable hybrid archetypes but no capability verification', async () => {
  const business = await input(); const capabilitiesBefore = structuredClone(business.business_capabilities);
  business.category_observations.push({ id: 'category-2', source: 'osm', field: 'shop', value: 'hardware', confidence: 1, evidence_ids: [] });
  business.facts.push({ ...business.facts[0]!, id: 'f-hybrid', kind: 'activity:coexisting', value: true, scope_id: business.business_id });
  const relationship: ActivityRelationship = { id: 'hybrid-1', kind: 'COEXISTING', category_observation_ids: ['category-1', 'category-2'], evidence_ids: ['f-hybrid'] };
  const result = classifyBusiness(business, { rules, activity_relationships: [relationship] });
  assert.equal(result.status, 'HYBRID'); assert.equal(result.profile.classification, 'RESOLVED');
  assert.deepEqual(result.profile.archetypes.map(x => x.id), ['membership_and_classes', 'product_retail']);
  assert.deepEqual(business.business_capabilities, capabilitiesBefore);
  business.facts.find(x => x.id === 'f-hybrid')!.publication = 'WITHHELD';
  assert.throws(() => classifyBusiness(business, { rules, activity_relationships: [relationship] }), /UNVERIFIED_ACTIVITY_RELATIONSHIP/);
});
test('regulated modifier combines with a commercial archetype without claiming a second activity', async () => {
  const business = await input(); business.category_observations = [{ id: 'category-1', source: 'osm', field: 'amenity', value: 'dentist', confidence: 0.7, evidence_ids: [] }];
  const result = classifyBusiness(business, { rules });
  assert.equal(result.status, 'RESOLVED'); assert.equal(result.profile.archetypes.find(x => x.id === 'regulated_services')!.relevance, 'modifier');
  assert.equal(result.profile.archetypes[0]!.confidence, 0.7);
});
test('unknown, no categories, broad ambiguity and non-business have separate abstention reasons', async () => {
  const business = await input();
  business.category_observations = []; assert.equal(classifyBusiness(business, { rules }).status, 'ABSTAINED');
  business.category_observations = [{ id: 'category-1', source: 'overture', field: '101.normalized_category', value: 'Unknown', confidence: 0, evidence_ids: [] }];
  assert.equal(classifyBusiness(business, { rules }).status, 'UNKNOWN');
  business.category_observations[0]!.value = 'Professional Services/Other Professional'; assert.equal(classifyBusiness(business, { rules }).status, 'AMBIGUOUS');
  business.category_observations[0]!.value = 'Non Business'; const result = classifyBusiness(business, { rules });
  assert.equal(result.status, 'NON_BUSINESS'); assert.deepEqual(result.candidate_capabilities, []);
});
test('partial known + unknown labels do not silently resolve all activity', async () => {
  const business = await input(); business.category_observations.push({ id: 'category-2', source: 'future-provider', field: 'classification', value: 'unknown', confidence: 0, evidence_ids: [] });
  const result = classifyBusiness(business, { rules }); assert.equal(result.status, 'PARTIAL'); assert.equal(result.profile.classification, 'UNRESOLVED');
});
test('commercial versus non-business conflict is ambiguous, never silently eligible', async () => {
  const business = await input(); business.category_observations.push({ id: 'category-2', source: 'osm', field: 'amenity', value: 'bench', confidence: 1, evidence_ids: [] });
  assert.equal(classifyBusiness(business, { rules }).status, 'AMBIGUOUS');
});
