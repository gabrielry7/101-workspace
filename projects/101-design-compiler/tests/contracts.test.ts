import test from 'node:test';
import assert from 'node:assert/strict';
import { fixtureNames, loadFixture } from '../scripts/load-fixtures.ts';
import { validateBundle } from '../src/validation/validate.ts';
import type { FixtureBundle } from '../src/contracts/v1/schemas.ts';

async function fixture(name: typeof fixtureNames[number] = 'ferreteria'): Promise<FixtureBundle> {
  const raw = await loadFixture(name);
  const result = validateBundle(raw);
  assert.equal(result.success, true, JSON.stringify(result.diagnostics));
  assert.ok(result.data);
  return result.data;
}
function expectCode(bundle: unknown, code: string, time?: string) {
  const result = validateBundle(bundle, time);
  assert.equal(result.success, false);
  assert.ok(result.diagnostics.some(x => x.code === code), JSON.stringify(result.diagnostics));
}
for (const name of fixtureNames) test(`${name}: four contracts and bindings pass`, async () => { await fixture(name); });

test('fixtures preserve different semantic needs without category templates', async () => {
  const plans = await Promise.all(fixtureNames.map(async name => (await fixture(name)).plan));
  assert.deepEqual(plans.map(x => x.capabilities), [
    ['identity', 'menu'], ['identity', 'membership', 'class_schedule'], ['identity', 'product_catalog'],
  ]);
});
test('changing observed category does not authorize delivery', async () => {
  const bundle = await fixture('gimnasio');
  bundle.input.category_observations[0]!.value = 'hardware_store';
  assert.equal(validateBundle(bundle).success, true);
  const module = structuredClone(bundle.plan.pages[0]!.modules[1]!);
  module.id = 'fake-delivery'; module.capability_id = 'delivery';
  bundle.plan.pages[0]!.modules.push(module); bundle.plan.capabilities.push('delivery');
  expectCode(bundle, 'CAPABILITY_NOT_CONFIRMED');
});
test('confirmation without evidence fails', async () => {
  const b = await fixture(); b.input.business_capabilities[0]!.evidence_ids = [];
  expectCode(b, 'MISSING_EVIDENCE');
});
test('unrelated evidence cannot confirm capability', async () => {
  const b = await fixture(); b.input.business_capabilities[1]!.evidence_ids = ['f-name'];
  expectCode(b, 'EVIDENCE_KIND_MISMATCH');
});
test('profile cannot upgrade UNKNOWN to present', async () => {
  const b = await fixture(); b.capabilities.capabilities.find(x => x.id === 'delivery')!.status = 'CONFIRMED_PRESENT';
  expectCode(b, 'CAPABILITY_NOT_BACKED');
});
for (const status of ['CONFIRMED_ABSENT', 'UNKNOWN', 'CONFLICTED', 'WITHHELD'] as const) {
  test(`${status} cannot authorize a module`, async () => {
    const b = await fixture();
    b.input.business_capabilities[1]!.status = status;
    b.capabilities.capabilities[1]!.status = status;
    if (status === 'CONFIRMED_ABSENT') b.input.facts.find(x => x.id === 'f-product_catalog')!.value = false;
    expectCode(b, 'CAPABILITY_NOT_CONFIRMED');
  });
}
test('missing identity is structural failure', async () => {
  const b = await fixture();
  const raw = JSON.parse(JSON.stringify(b)) as { input: { identity?: unknown } };
  delete raw.input.identity;
  expectCode(raw, 'SCHEMA_INVALID');
});
test('unknown version is rejected', async () => {
  const b = await fixture(); expectCode({ ...b, plan: { ...b.plan, schema_version: '2.0.0' } }, 'SCHEMA_INVALID');
});
test('arbitrary layout and code are rejected', async () => {
  const b = await fixture(); expectCode({ ...b, plan: { ...b.plan, css: 'body{}' } }, 'SCHEMA_INVALID');
});
test('snapshot mixing fails', async () => {
  const b = await fixture(); b.profile.snapshot_id = 'another-snapshot'; expectCode(b, 'SNAPSHOT_MISMATCH');
});
test('dangling fact reference fails', async () => {
  const b = await fixture(); b.plan.pages[0]!.modules[0]!.fact_ids = ['not-a-fact']; expectCode(b, 'UNKNOWN_FACT');
});
test('withheld facts are retained as input but never bound for publication', async () => {
  const b = await fixture(); b.input.facts.find(x => x.id === 'f-offering-1')!.publication = 'WITHHELD'; expectCode(b, 'FACT_NOT_PUBLISHABLE');
});
test('expired facts block deterministically at supplied evaluation time', async () => {
  const b = await fixture(); b.input.facts.find(x => x.id === 'f-offering-1')!.expires_at = '2026-10-08T00:00:00Z';
  assert.equal(validateBundle(b).success, true);
  expectCode(b, 'FACT_NOT_PUBLISHABLE', '2026-10-09T00:00:00Z');
});
test('cross-branch evidence cannot authorize branch capability', async () => {
  const b = await fixture();
  b.input.locations.push({ id: 'branch-2', coordinate_fact_ids: [], opening_hours_fact_ids: [], exception_fact_ids: [], visit_policy_fact_ids: [] });
  b.input.facts.find(x => x.id === 'f-product_catalog')!.scope_id = 'branch-2';
  expectCode(b, 'SCOPE_MISMATCH');
});
test('incorrect offering kind cannot populate menu', async () => {
  const b = await fixture('restaurante');
  b.input.offerings[0] = { ...b.input.offerings[0]!, kind: 'product_category' };
  expectCode(b, 'OFFERING_KIND_MISMATCH');
});
test('empty catalog bindings report MISSING_INPUT', async () => {
  const b = await fixture(); b.plan.pages[0]!.modules[1]!.offering_ids = []; expectCode(b, 'MISSING_INPUT');
});
test('empty routes are rejected', async () => {
  const b = await fixture(); b.plan.pages.push({ path: '/vacio', intent: 'empty', modules: [] }); expectCode(b, 'SCHEMA_INVALID');
});
test('duplicate facts and routes fail', async () => {
  const b = await fixture(); b.input.facts.push(structuredClone(b.input.facts[0]!)); b.plan.pages.push(structuredClone(b.plan.pages[0]!)); expectCode(b, 'DUPLICATE_ID');
});
test('unknown categories can be preserved but unresolved plans block', async () => {
  const b = await fixture(); b.input.category_observations[0]!.source = 'future-provider'; b.input.category_observations[0]!.value = 'Unknown';
  b.profile.classification = 'UNRESOLVED'; expectCode(b, 'BUSINESS_UNRESOLVED');
});
test('live integration and falsely supported UI fail H0 boundary', async () => {
  const b = await fixture(); b.plan.pages[0]!.modules[1]!.presentation = 'LIVE_CONNECTED_INTEGRATION';
  b.capabilities.capabilities[1]!.backend_status = 'BACKEND_CONNECTED';
  expectCode(b, 'INTEGRATION_OUT_OF_SCOPE'); expectCode(b, 'IMPLEMENTATION_NOT_AVAILABLE');
});
test('fixture cannot silently become a real site', async () => {
  const b = await fixture(); b.plan.stage = 'SEMANTIC_PLAN'; expectCode(b, 'FIXTURE_NOT_LABELED');
});
test('an approved action still needs safe URL and matching scope', async () => {
  const b = await fixture('restaurante');
  const cap = b.capabilities.capabilities.find(x => x.id === 'reservation')!;
  const ref = 'f-reservation-url';
  b.input.facts.push({ ...b.input.facts[0]!, id: ref, kind: 'action_url', value: 'javascript:alert(1)', scope_id: cap.scope_id });
  b.input.action_destinations.push({ id: 'action-reservation', capability_id: 'reservation', scope_id: cap.scope_id, url_fact_id: ref });
  cap.action_destination_ids.push('action-reservation'); cap.missing_inputs = [];
  b.plan.excluded_capabilities = b.plan.excluded_capabilities.filter(x => x.id !== 'reservation');
  b.plan.capabilities.push('reservation');
  b.plan.pages[0]!.modules.push({ id: 'reservation-link', capability_id: 'reservation', scope_id: cap.scope_id, required: false, presentation: 'REAL_APPROVED_EXTERNAL_LINK', fact_ids: ['f-reservation'], offering_ids: [], action_destination_id: 'action-reservation' });
  expectCode(b, 'UNSAFE_ACTION_URL');
  b.input.facts.find(x => x.id === ref)!.value = 'https://example.invalid/reservation';
  assert.equal(validateBundle(b).success, true);
  b.input.facts.find(x => x.id === ref)!.publication = 'UNKNOWN'; expectCode(b, 'FACT_NOT_PUBLISHABLE');
});
test('explicit absence stays absence in exclusion diagnostics', async () => {
  const b = await fixture(); b.plan.excluded_capabilities.find(x => x.id === 'purchase')!.reason = 'UNKNOWN'; expectCode(b, 'EXCLUSION_MISMATCH');
});
test('class data needs a timestamp and timezone, never guessed', async () => {
  const b = await fixture('gimnasio'); b.input.facts.find(x => x.id === 'f-class-zone')!.value = 'not-a-timezone'; expectCode(b, 'FACT_KIND_MISMATCH');
});
test('no business category forbids a verified hybrid capability', async () => {
  const b = await fixture(); b.profile.archetypes[0]!.id = 'membership_and_classes'; b.plan.archetypes = ['membership_and_classes'];
  assert.equal(validateBundle(b).success, true, 'Retail capability evidence remains valid for a gym hybrid');
});
test('capability evidence states cannot be silently omitted', async () => {
  const b = await fixture(); b.capabilities.capabilities = b.capabilities.capabilities.filter(x => x.id !== 'delivery'); expectCode(b, 'CAPABILITY_OMITTED');
});
