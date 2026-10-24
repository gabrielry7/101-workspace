import test from 'node:test';
import assert from 'node:assert/strict';
import { loadPlannerFixtures } from '../scripts/load-planner-fixtures.ts';
import { loadMappingRegistry } from '../scripts/load-taxonomy.ts';
import { CapabilityId, CapabilityProfileV1, SitePlanV1 } from '../src/contracts/v1/schemas.ts';
import type { BusinessInput, Capability } from '../src/contracts/v1/schemas.ts';
import { planBusiness, scopedRoute } from '../src/planner/plan.ts';
import type { PlannerOptions, PlannerResult } from '../src/planner/plan.ts';
import { capabilityRegistry, validateCapabilityRegistry } from '../src/planner/registry.ts';
import { SiteRequirementsV1 } from '../src/planner/contracts.ts';
import { validateSemanticPlan } from '../src/planner/validate.ts';
import { offeringFactIds, publishable } from '../src/planner/content.ts';

const fixtures = await loadPlannerFixtures();
const { rules } = await loadMappingRegistry();
function fixture(name = 'ferreteria') { return structuredClone(fixtures.find(x => x.scenario === name)!); }
function run(name: string, mutate?: (input: BusinessInput) => void, options: Partial<PlannerOptions> = {}) {
  const f = fixture(name); mutate?.(f.input);
  return planBusiness(f.input, { rules, activity_relationships: f.activity_relationships, ...options });
}
function ready(result: PlannerResult) {
  assert.equal(result.status, 'READY', JSON.stringify(result.diagnostics));
  if (result.status !== 'READY') throw new Error('Expected READY');
  return result;
}
function bundle(result: ReturnType<typeof ready>) {
  return { input: result.input, profile: result.profile, capabilities: result.capabilities, plan: result.plan };
}
function modules(result: ReturnType<typeof ready>) { return result.plan.pages.flatMap(x => x.modules); }
function fact(input: BusinessInput, id: string, kind: string, value: string | boolean | number, scope = input.locations[0]!.id) {
  input.facts.push({ id, kind, value, scope_id: scope, publication: 'APPROVED', publication_decision_id: `synthetic-${id}`,
    source: 'synthetic-test', observed_at: '2026-10-01T00:00:00Z' });
}
function cap(input: BusinessInput, id: Capability, scope = input.locations[0]!.id) {
  fact(input, `assert-${id}`, `capability:${id}`, true, scope);
  input.business_capabilities.push({ id, scope_id: scope, status: 'CONFIRMED_PRESENT', evidence_ids: [`assert-${id}`] });
}
function expectCode(result: PlannerResult, code: string) {
  assert.notEqual(result.status, 'READY'); assert.ok(result.diagnostics.some(x => x.code === code), JSON.stringify(result.diagnostics));
  assert.ok(!('plan' in result));
}
for (const source of fixtures) test(`planner/${source.scenario}: same planner returns ${source.expected_status}`, () => {
  const original = structuredClone(source);
  const result = run(source.scenario);
  assert.equal(result.status, source.expected_status, JSON.stringify(result.diagnostics));
  assert.deepEqual(source, original);
  if (result.status !== 'READY') { assert.ok(!('plan' in result)); return; }
  assert.equal(CapabilityProfileV1.safeParse(result.capabilities).success, true);
  assert.equal(SitePlanV1.safeParse(result.plan).success, true);
  assert.equal(SiteRequirementsV1.safeParse(result.requirements).success, true);
  const validation = validateSemanticPlan(bundle(result), result.requirements);
  assert.equal(validation.success, true, JSON.stringify(validation.diagnostics));
  assert.equal(result.plan.stage, 'FIXTURE_PREVIEW');
  assert.ok(result.plan.pages.every(page => page.modules.length > 0));
  assert.ok(result.capabilities.capabilities.every(x => x.frontend_status === 'NOT_SUPPORTED_YET' && x.backend_status === 'BACKEND_NOT_CONNECTED'));
});

test('registry covers the V1 vocabulary with shared semantic modules and no renderers', () => {
  assert.equal(validateCapabilityRegistry(capabilityRegistry).specs.length, CapabilityId.options.length);
  assert.ok(capabilityRegistry.specs.filter(x => x.selector === 'OFFERINGS').every(x => x.semantic_module === 'offering_collection' || x.semantic_module === 'schedule'));
  assert.ok(!JSON.stringify(capabilityRegistry).includes('template'));
  assert.equal(capabilityRegistry.specs.find(x => x.id === 'gallery')!.semantic_status, 'DEFERRED');
});

test('three original inputs produce different substantive semantics from the same planner', () => {
  const capabilities = (name: string) => modules(ready(run(name))).map(x => x.capability_id).sort();
  assert.deepEqual(capabilities('restaurante'), ['identity', 'menu']);
  assert.deepEqual(capabilities('gimnasio'), ['class_schedule', 'identity', 'membership']);
  assert.deepEqual(capabilities('ferreteria'), ['identity', 'product_catalog']);
});

test('changing category alone changes no verified capability or module', () => {
  const before = ready(run('restaurante'));
  const after = ready(run('restaurante', input => {
    input.category_observations = [{ id: 'category-1', source: 'osm', field: 'leisure', value: 'fitness_centre', confidence: 1, evidence_ids: [] }];
  }));
  assert.deepEqual(modules(after), modules(before));
  assert.deepEqual(after.capabilities.capabilities, before.capabilities.capabilities);
  assert.ok(!modules(after).some(x => x.capability_id === 'membership'));
});

test('a gym can have verified retail capabilities without a category whitelist', () => {
  const result = ready(run('gimnasio', input => {
    input.business_capabilities.find(x => x.id === 'product_catalog')!.status = 'CONFIRMED_PRESENT';
    input.facts.find(x => x.id === 'f-product_catalog')!.value = true;
    fact(input, 'shop-name', 'offering_name', 'Synthetic product category');
    input.offerings.push({ id: 'shop-item', kind: 'product_category', scope_id: input.locations[0]!.id, name_fact_id: 'shop-name', fact_ids: [] });
  }));
  assert.ok(modules(result).some(x => x.capability_id === 'product_catalog'));
  assert.ok(modules(result).some(x => x.capability_id === 'membership'));
});

test('UNKNOWN stays UNKNOWN even with an unrelated matching assertion or category', () => {
  const result = ready(run('ferreteria', input => fact(input, 'unsolicited', 'capability:delivery', true)));
  assert.equal(result.capabilities.capabilities.find(x => x.id === 'delivery')!.status, 'UNKNOWN');
  assert.ok(!modules(result).some(x => x.capability_id === 'delivery'));
  assert.equal(result.plan.excluded_capabilities.find(x => x.id === 'delivery')!.reason, 'UNKNOWN');
});
for (const status of ['UNKNOWN', 'CONFLICTED', 'WITHHELD', 'CONFIRMED_ABSENT'] as const) test(`planner preserves ${status} without modules`, () => {
  const result = ready(run('ferreteria', input => {
    const entry = input.business_capabilities.find(x => x.id === 'quote_request')!;
    entry.status = status;
    if (status === 'CONFIRMED_ABSENT') input.facts.find(x => x.id === 'f-quote_request')!.value = false;
  }));
  assert.equal(result.capabilities.capabilities.find(x => x.id === 'quote_request')!.status, status);
  assert.equal(result.plan.excluded_capabilities.find(x => x.id === 'quote_request')!.reason, status);
});

test('approved capability with no content is blocked without changing its factual status', () => {
  const result = run('informacion-incompleta'); expectCode(result, 'CONTENT_BLOCKED');
  assert.equal(result.capabilities!.capabilities.find(x => x.id === 'product_catalog')!.status, 'CONFIRMED_PRESENT');
  assert.ok(result.capabilities!.capabilities.find(x => x.id === 'product_catalog')!.missing_inputs.length);
});
test('confirmation requires matching current exact-scope evidence', () => {
  expectCode(run('restaurante', input => { input.business_capabilities.find(x => x.id === 'menu')!.evidence_ids = ['f-category']; }), 'UNVERIFIED_CAPABILITY');
  expectCode(run('restaurante', input => { input.business_capabilities.find(x => x.id === 'menu')!.evidence_ids = []; }), 'MISSING_EVIDENCE');
});
test('contradictory approved true/false assertions block instead of selecting one', () => {
  expectCode(run('ferreteria', input => fact(input, 'negative-catalog', 'capability:product_catalog', false)), 'CAPABILITY_EVIDENCE_CONFLICT');
});
test('global capability assertions never authorize a branch implicitly', () => {
  expectCode(run('ferreteria', input => { input.facts.find(x => x.id === 'f-product_catalog')!.scope_id = input.business_id; }), 'UNVERIFIED_CAPABILITY');
});

test('approved hybrid combines real offers and does not turn delivery into a functionality', () => {
  const result = ready(run('hibrido-gimnasio-tienda'));
  assert.deepEqual(result.plan.archetypes, ['membership_and_classes', 'product_retail']);
  assert.ok(modules(result).some(x => x.capability_id === 'product_catalog'));
  assert.ok(modules(result).some(x => x.capability_id === 'membership'));
  assert.ok(!modules(result).some(x => x.capability_id === 'delivery'));
});
test('ambiguous hybrid without coexistence blocks even when offers are verified', () => {
  expectCode(run('hibrido-sin-evidencia'), 'CLASSIFICATION_BLOCKED');
});
for (const value of ['Unknown', 'Non Business', 'Professional Services/Other Professional']) test(`classification abstention ${value} produces no SitePlan`, () => {
  expectCode(run('restaurante', input => {
    input.category_observations = [{ id: 'category-1', source: 'osm', field: '101.normalized_category', value, confidence: 0, evidence_ids: [] }];
  }), 'CLASSIFICATION_BLOCKED');
});
test('no categories, inactive status and insufficient identity-only data block', () => {
  expectCode(run('restaurante', input => { input.category_observations = []; }), 'CLASSIFICATION_BLOCKED');
  expectCode(run('restaurante', input => { input.identity.status = 'INACTIVE'; }), 'BUSINESS_NOT_ACTIVE');
  expectCode(run('restaurante', input => {
    input.business_capabilities = input.business_capabilities.filter(x => x.id === 'identity');
  }), 'INSUFFICIENT_SUBSTANTIVE_CONTENT');
});
test('identity is mandatory and cannot be inferred from a public name', () => {
  expectCode(run('restaurante', input => { input.business_capabilities = input.business_capabilities.filter(x => x.id !== 'identity'); }), 'CONTENT_BLOCKED');
});

test('two hotel branches retain distinct menu, rooms, addresses and UNKNOWN claims', () => {
  const result = ready(run('hotel-restaurante-sucursales'));
  const second = result.input.locations[1]!.id;
  assert.ok(!modules(result).some(x => x.scope_id === second && x.capability_id === 'menu'));
  assert.equal(modules(result).filter(x => x.capability_id === 'rooms').length, 2);
  for (const module of modules(result).filter(x => x.capability_id === 'rooms')) {
    assert.ok(module.offering_ids.every(id => result.input.offerings.find(x => x.id === id)!.scope_id === module.scope_id));
  }
  assert.equal(result.plan.excluded_capabilities.find(x => x.id === 'menu' && x.scope_id === second)!.reason, 'UNKNOWN');
  assert.ok(result.plan.pages.filter(x => x.path.includes('/sedes/')).every(x => new Set(x.modules.map(m => m.scope_id)).size === 1));
});
test('cross-branch factual references are rejected before planning', () => {
  expectCode(run('hotel-restaurante-sucursales', input => {
    input.locations[1]!.address_fact_id = input.locations[0]!.address_fact_id;
  }), 'SCOPE_MISMATCH');
});
test('route IDs are deterministic, scope-safe and do not expose arbitrary source IDs', () => {
  const route = scopedRoute('/catalogo', '../private?branch=2', 'business');
  assert.match(route, /^\/sedes\/s-[a-f0-9]{24}\/catalogo$/);
  assert.equal(route, scopedRoute('/catalogo', '../private?branch=2', 'business'));
  assert.notEqual(route, scopedRoute('/catalogo', 'other', 'business'));
});

test('all content bindings are approved, current and retain original offering references', () => {
  const result = ready(run('hibrido-gimnasio-tienda'));
  for (const module of modules(result)) for (const id of [...module.fact_ids, ...module.offering_ids.flatMap(id => offeringFactIds(result.input.offerings.find(x => x.id === id)!))]) {
    assert.ok(publishable(result.input.facts.find(x => x.id === id), Date.parse(result.requirements.evaluated_at)), id);
  }
  assert.equal(result.requirements.bindings.length, result.input.facts.length);
});
test('withheld/expired offer content is omitted and never replaced with invented text', () => {
  expectCode(run('restaurante', input => { input.facts.find(x => x.id === 'f-offering-1')!.publication = 'WITHHELD'; }), 'CONTENT_BLOCKED');
  expectCode(run('restaurante', input => { input.facts.find(x => x.id === 'f-offering-1')!.expires_at = '2026-10-08T00:00:00Z'; }, { evaluation_time: '2026-10-09T00:00:00Z' }), 'CONTENT_BLOCKED');
});
test('a public subset is preserved while an unpublishable offering receives an omission', () => {
  const result = ready(run('restaurante', input => {
    fact(input, 'withheld-name', 'offering_name', 'Synthetic withheld item');
    input.facts.find(x => x.id === 'withheld-name')!.publication = 'WITHHELD';
    input.offerings.push({ id: 'withheld-item', kind: 'menu_item', scope_id: input.locations[0]!.id, name_fact_id: 'withheld-name', fact_ids: [] });
  }));
  assert.deepEqual(modules(result).find(x => x.capability_id === 'menu')!.offering_ids, ['offering-1']);
  assert.ok(result.requirements.omissions.some(x => x.offering_id === 'withheld-item'));
});
test('unapproved optional price cannot leak through an approved offering name', () => {
  expectCode(run('restaurante', input => {
    fact(input, 'price', 'price', 'Synthetic price withheld');
    input.facts.find(x => x.id === 'price')!.publication = 'WITHHELD';
    const item = input.offerings[0]!; if (item.kind === 'menu_item') item.price_fact_id = 'price';
  }), 'CONTENT_BLOCKED');
});
test('price and class facts must have the correct types; no guessed schedules', () => {
  expectCode(run('gimnasio', input => { input.facts.find(x => x.id === 'f-class-zone')!.value = 'Unknown/Timezone'; }), 'CONTENT_BLOCKED');
  expectCode(run('restaurante', input => {
    const item = input.offerings[0]!; if (item.kind === 'menu_item') item.price_fact_id = 'f-category';
  }), 'CONTENT_BLOCKED');
});
test('boolean prices and numeric identities are not coerced into invented display text', () => {
  expectCode(run('restaurante', input => {
    fact(input, 'price', 'price', true);
    const item = input.offerings[0]!; if (item.kind === 'menu_item') item.price_fact_id = 'price';
  }), 'CONTENT_BLOCKED');
  expectCode(run('restaurante', input => { input.facts.find(x => x.id === 'f-name')!.value = 101; }), 'IDENTITY_NOT_PUBLISHABLE');
});
test('dangling references, duplicate IDs and foreign scopes fail the input boundary', () => {
  expectCode(run('restaurante', input => { input.offerings[0]!.name_fact_id = 'missing'; }), 'UNKNOWN_FACT');
  expectCode(run('restaurante', input => { input.facts.push(structuredClone(input.facts[0]!)); }), 'DUPLICATE_ID');
  expectCode(run('restaurante', input => { input.offerings[0]!.scope_id = 'foreign'; }), 'UNKNOWN_SCOPE');
});
test('future cutoff and explicit invalid evaluation instants are rejected deterministically', () => {
  expectCode(run('restaurante', input => { input.facts[0]!.observed_at = '2026-10-10T00:00:00Z'; }), 'FUTURE_EVIDENCE');
  for (const evaluation_time of ['2026-10-06T00:00:00Z', '2027-02-30T00:00:00Z', 'invalid']) expectCode(run('restaurante', undefined, { evaluation_time }), 'INVALID_EVALUATION_TIME');
});
test('expired capability evidence blocks eligibility while preserving PRESENT at snapshot', () => {
  expectCode(run('restaurante', input => { input.facts.find(x => x.id === 'f-menu')!.expires_at = '2026-10-08T00:00:00Z'; }, { evaluation_time: '2026-10-09T00:00:00Z' }), 'CONTENT_BLOCKED');
});
test('expired coexistence evidence cannot authorize a hybrid later', () => {
  expectCode(run('hibrido-gimnasio-tienda', input => { input.facts.find(x => x.id === 'hybrid-evidence')!.expires_at = '2026-10-08T00:00:00Z'; }, { evaluation_time: '2026-10-09T00:00:00Z' }), 'CLASSIFICATION_EVIDENCE_STALE');
});

test('only current safe exact-scope external actions are planned; no backend is claimed', () => {
  const result = ready(run('clinica'));
  const module = modules(result).find(x => x.capability_id === 'appointment')!;
  assert.equal(module.presentation, 'REAL_APPROVED_EXTERNAL_LINK'); assert.equal(module.action_destination_id, 'action-appointment');
  assert.ok(result.requirements.requirements.find(x => x.id === module.id)!.depends_on.length > 1);
  for (const url of ['javascript:alert(1)', 'http://example.invalid', 'https://user:password@example.invalid']) {
    const changed = ready(run('clinica', input => { input.facts.find(x => x.id === 'external-url')!.value = url; }));
    assert.ok(!modules(changed).some(x => x.capability_id === 'appointment'));
    assert.equal(changed.plan.excluded_capabilities.find(x => x.id === 'appointment')!.reason, 'MISSING_INPUT');
  }
});
test('an action cannot bypass a missing verified domain dependency', () => {
  const result = ready(run('clinica', input => {
    input.business_capabilities = input.business_capabilities.filter(x => !['service_catalog', 'professional_profiles'].includes(x.id));
    cap(input, 'contact_channels'); fact(input, 'email', 'email', 'fixture@example.invalid'); input.contact_fact_ids = ['email'];
  }));
  assert.ok(!modules(result).some(x => x.capability_id === 'appointment'));
  assert.ok(result.requirements.requirements.find(x => x.capability_id === 'appointment')!.missing_inputs.some(x => x.startsWith('eligible_dependency:')));
});
test('service area is information and never authorizes delivery', () => {
  const result = ready(run('ferreteria', input => {
    cap(input, 'service_area'); fact(input, 'area', 'service_area', 'Synthetic coverage area'); input.service_area_fact_ids = ['area'];
  }));
  assert.ok(modules(result).some(x => x.capability_id === 'service_area'));
  assert.ok(!modules(result).some(x => x.capability_id === 'delivery'));
});
test('opening hours require actual approved schedule and all known exceptions', () => {
  const missing = ready(run('restaurante', input => { cap(input, 'opening_hours'); }));
  assert.ok(!modules(missing).some(x => x.capability_id === 'opening_hours'));
  const addHours = (input: BusinessInput) => {
    cap(input, 'opening_hours'); fact(input, 'hours', 'opening_hours', 'Synthetic approved schedule; not real operating hours');
    input.locations[0]!.opening_hours_fact_ids = ['hours'];
  };
  const complete = ready(run('restaurante', addHours));
  assert.deepEqual(modules(complete).find(x => x.capability_id === 'opening_hours')!.fact_ids, ['hours']);
  const conflict = ready(run('restaurante', input => {
    addHours(input); fact(input, 'exception', 'opening_hours_exception', 'Synthetic withheld exception');
    input.facts.find(x => x.id === 'exception')!.publication = 'WITHHELD'; input.locations[0]!.exception_fact_ids = ['exception'];
  }));
  assert.ok(!modules(conflict).some(x => x.capability_id === 'opening_hours'));
});
test('an approved external action for one branch cannot be moved to another', () => {
  expectCode(run('hotel-restaurante-sucursales', input => {
    const first = input.locations[0]!.id; const second = input.locations[1]!.id;
    fact(input, 'reservation-url', 'action_url', 'https://example.invalid/synthetic', first);
    input.action_destinations.push({ id: 'reservation', capability_id: 'reservation', scope_id: second, url_fact_id: 'reservation-url' });
  }), 'SCOPE_MISMATCH');
});
test('production mode changes only the stage and never connects a backend', () => {
  const result = ready(run('restaurante', input => { input.data_mode = 'UPSTREAM_SNAPSHOT'; }));
  assert.equal(result.plan.stage, 'SEMANTIC_PLAN');
  assert.ok(result.capabilities.capabilities.every(x => x.backend_status === 'BACKEND_NOT_CONNECTED'));
  assert.ok(!modules(result).some(x => x.presentation === 'LIVE_CONNECTED_INTEGRATION' || x.presentation === 'VISUAL_PREVIEW_ONLY'));
});
test('media stays deferred even with documented upstream rights', () => {
  const result = ready(run('restaurante', input => {
    cap(input, 'gallery');
    input.existing_media.push({ id: 'media', source: 'synthetic', uri: 'https://example.invalid/image.jpg', kind: 'image', scope_id: input.business_id,
      rights_status: 'DOCUMENTED', rights_document_ids: ['synthetic-rights-reference'], restrictions: [] });
  }));
  assert.ok(!modules(result).some(x => x.capability_id === 'gallery'));
  assert.equal(result.plan.excluded_capabilities.find(x => x.id === 'gallery')!.reason, 'NOT_SUPPORTED_YET');
});
test('a professional offering never becomes a trainer without explicit approved role', () => {
  expectCode(run('clinica', input => { cap(input, 'trainer_profiles'); }), 'CONTENT_BLOCKED');
  const result = ready(run('clinica', input => {
    cap(input, 'trainer_profiles');
    fact(input, 'trainer-name', 'offering_name', 'Synthetic trainer');
    fact(input, 'trainer-role', 'professional_role', 'trainer');
    input.offerings.push({ id: 'trainer', kind: 'professional', scope_id: input.locations[0]!.id, name_fact_id: 'trainer-name', fact_ids: ['trainer-role'] });
  }));
  assert.deepEqual(modules(result).find(x => x.capability_id === 'trainer_profiles')!.offering_ids, ['trainer']);
});

test('mandatory modules cannot be removed, downgraded or concealed by dropping requirements', () => {
  for (const mutation of ['remove', 'downgrade', 'conceal']) {
    const result = ready(run('restaurante')); const module = modules(result).find(x => x.capability_id === 'menu')!;
    if (mutation === 'downgrade') module.required = false;
    else {
      result.plan.pages = result.plan.pages.filter(x => !x.modules.includes(module));
      if (mutation === 'conceal') result.requirements.requirements = result.requirements.requirements.filter(x => x.id !== module.id);
    }
    const validation = validateSemanticPlan(bundle(result), result.requirements);
    assert.equal(validation.success, false); assert.ok(validation.diagnostics.some(x => x.code.startsWith('REQUIRED_MODULE_')));
  }
});
test('dropping an approved fact or offering is detected as binding loss', () => {
  const result = ready(run('restaurante')); const identity = modules(result).find(x => x.capability_id === 'identity')!;
  identity.fact_ids = [];
  assert.ok(validateSemanticPlan(bundle(result), result.requirements).diagnostics.some(x => x.code === 'BINDING_LOSS'));
});
test('module dependencies cannot be erased from SiteRequirements', () => {
  const result = ready(run('clinica'));
  result.requirements.requirements.find(x => x.capability_id === 'appointment')!.depends_on = [];
  assert.ok(validateSemanticPlan(bundle(result), result.requirements).diagnostics.some(x => x.code === 'DEPENDENCY_NOT_DECLARED'));
});
test('registry rejects cycles, unknown dependencies and duplicate specifications', () => {
  let registry = structuredClone(capabilityRegistry); registry.specs.push(structuredClone(registry.specs[0]!));
  assert.throws(() => validateCapabilityRegistry(registry), /DUPLICATE_CAPABILITY_SPEC/);
  registry = structuredClone(capabilityRegistry); registry.specs.find(x => x.id === 'menu')!.depends_on.push('order');
  assert.throws(() => validateCapabilityRegistry(registry), /DEPENDENCY_CYCLE/);
  registry = structuredClone(capabilityRegistry); registry.specs = registry.specs.filter(x => x.id !== 'menu');
  assert.throws(() => validateCapabilityRegistry(registry), /UNKNOWN_DEPENDENCY/);
});
test('extending an existing capability spec uses the same planner and retains registry hash', () => {
  const registry = structuredClone(capabilityRegistry); registry.specs.find(x => x.id === 'faqs')!.route = '/ayuda';
  const result = ready(run('restaurante', input => {
    cap(input, 'faqs'); fact(input, 'faq', 'faq_answer', 'Synthetic approved answer');
  }, { registry }));
  assert.ok(result.plan.pages.some(x => x.path.endsWith('/ayuda')));
  assert.notEqual(result.requirements.registry_sha256, ready(run('restaurante')).requirements.registry_sha256);
});
test('plans are pure and reproducible, including priorities and omission diagnostics', () => {
  const f = fixture('hotel-restaurante-sucursales'); const before = structuredClone(f);
  const options = { rules, activity_relationships: f.activity_relationships };
  const a = ready(planBusiness(f.input, options)); const b = ready(planBusiness(f.input, options));
  assert.deepEqual(a, b); assert.deepEqual(f, before);
  const priorities = a.requirements.requirements.map(x => x.priority);
  assert.deepEqual(priorities, [...priorities].sort((a, b) => a - b));
});
test('artifact lineage changes with taxonomy rules or classification sidecars', () => {
  const original = ready(run('hibrido-gimnasio-tienda'));
  const f = fixture('hibrido-gimnasio-tienda'); f.activity_relationships[0]!.id = 'another-verified-relation-id';
  const changed = ready(planBusiness(f.input, { rules, activity_relationships: f.activity_relationships }));
  assert.notEqual(original.plan.id, changed.plan.id);
  assert.notEqual(original.requirements.classification_context_sha256, changed.requirements.classification_context_sha256);
  const amended = structuredClone(rules); amended[0]!.rationale += ' Reviewed test revision.';
  const revised = ready(run('hibrido-gimnasio-tienda', undefined, { rules: amended }));
  assert.notEqual(original.plan.id, revised.plan.id);
  assert.notEqual(original.requirements.taxonomy_registry_sha256, revised.requirements.taxonomy_registry_sha256);
});
test('non-JSON optional values are rejected with diagnostics instead of throwing', () => {
  const f = fixture('restaurante'); Object.assign(f.input.identity, { brand_fact_id: undefined });
  expectCode(planBusiness(f.input, { rules }), 'NON_JSON_PLANNER_INPUT');
});

for (const [offering_kind, capability, source, field, value] of [
  ['program', 'programs', 'osm', 'amenity', 'language_school'],
  ['event', 'events', 'osm', 'amenity', 'theatre'],
  ['product', 'product_catalog', 'osm', 'man_made', 'works'],
  ['service', 'service_catalog', 'osm', 'craft', 'plumber'],
  ['service', 'service_catalog', 'osm', 'office', 'logistics'],
] as const) test(`generalization/${value}: approved ${offering_kind} uses shared semantic collection`, () => {
  const result = ready(run('servicios-profesionales', input => {
    input.category_observations = [{ id: 'category-1', source, field, value, confidence: 1, evidence_ids: [] }];
    input.offerings[0]!.kind = offering_kind;
    if (capability !== 'service_catalog') {
      input.business_capabilities = input.business_capabilities.filter(x => x.id !== 'service_catalog');
      cap(input, capability);
    }
  }));
  assert.ok(modules(result).some(x => x.capability_id === capability));
  assert.equal(result.requirements.requirements.find(x => x.capability_id === capability && x.disposition === 'INCLUDED')!.semantic_module, 'offering_collection');
});
