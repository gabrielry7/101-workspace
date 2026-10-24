import { validateBusinessInput } from './input.ts';
import { capabilityRegistry } from '../planner/registry.ts';
import { contracts } from '../contracts/v1/schemas.ts';
import type { BusinessInput, Capability, FixtureBundle } from '../contracts/v1/schemas.ts';

export type Diagnostic = { code: string; path: string; message: string };
export type ValidationResult = { success: boolean; diagnostics: Diagnostic[]; data?: FixtureBundle };

// H2 reuses the same typed commercial-object vocabulary as the semantic registry.
const requiredOfferingKinds = Object.fromEntries(capabilityRegistry.specs
  .filter(x => x.offering_kinds.length).map(x => [x.id, x.offering_kinds])) as Partial<Record<Capability, readonly string[]>>;

export function validateBundle(value: unknown, evaluationTime?: string): ValidationResult {
  const diagnostics: Diagnostic[] = [];
  const issue = (code: string, path: string, message: string) => diagnostics.push({ code, path, message });
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return { success: false, diagnostics: [{ code: 'SCHEMA_INVALID', path: '', message: 'Expected fixture bundle' }] };
  }
  const raw = value as Record<string, unknown>;
  const parsed = {
    input: contracts.BusinessInputV1.safeParse(raw['input']),
    profile: contracts.BusinessProfileV1.safeParse(raw['profile']),
    capabilities: contracts.CapabilityProfileV1.safeParse(raw['capabilities']),
    plan: contracts.SitePlanV1.safeParse(raw['plan']),
  };
  for (const [key, result] of Object.entries(parsed)) {
    if (!result.success) for (const error of result.error.issues) {
      issue('SCHEMA_INVALID', `${key}.${error.path.join('.')}`, error.message);
    }
  }
  for (const key of Object.keys(raw)) if (!(key in parsed)) issue('SCHEMA_INVALID', key, 'Unknown bundle field');
  if (!parsed.input.success || !parsed.profile.success || !parsed.capabilities.success || !parsed.plan.success) {
    return { success: false, diagnostics };
  }
  const input = parsed.input.data;
  const profile = parsed.profile.data;
  const capabilities = parsed.capabilities.data;
  const plan = parsed.plan.data;
  if (input.identity.status === 'INACTIVE') issue('BUSINESS_INACTIVE', 'input.identity.status', 'Inactive business cannot have an active site plan');
  const instant = Date.parse(evaluationTime ?? input.as_of);
  if (!Number.isFinite(instant) || instant < Date.parse(input.as_of)) issue('INVALID_EVALUATION_TIME', 'input.as_of', 'Evaluation must be at or after snapshot cutoff');
  for (const [key, artifact] of Object.entries({ profile, capabilities, plan })) {
    if (artifact.business_id !== input.business_id || artifact.snapshot_id !== input.snapshot_id) {
      issue('SNAPSHOT_MISMATCH', key, 'Business and snapshot must match input');
    }
  }
  if (capabilities.business_profile_id !== profile.id || plan.business_profile_id !== profile.id || plan.capability_profile_id !== capabilities.id) {
    issue('ARTIFACT_MISMATCH', 'plan', 'Profile references do not match supplied artifacts');
  }
  if (input.data_mode === 'SYNTHETIC_FIXTURE' && plan.stage !== 'FIXTURE_PREVIEW') issue('FIXTURE_NOT_LABELED', 'plan.stage', 'Synthetic data must remain a fixture preview');
  if (profile.classification !== 'RESOLVED') issue('BUSINESS_UNRESOLVED', 'profile.classification', 'A plan requires resolved business activity');
  if (profile.classification === 'RESOLVED' && !profile.archetypes.length) issue('MISSING_INPUT', 'profile.archetypes', 'Resolved profile requires an archetype');
  const unique = (values: readonly string[], path: string) => {
    if (new Set(values).size !== values.length) issue('DUPLICATE_ID', path, 'Identifiers must be unique');
  };
  const key = (x: { id: string; scope_id: string }) => `${x.scope_id}:${x.id}`;
  for (const [path, values] of Object.entries({
    'input.facts': input.facts.map(x => x.id), 'input.locations': input.locations.map(x => x.id),
    'input.offerings': input.offerings.map(x => x.id), 'input.category_observations': input.category_observations.map(x => x.id),
    'input.action_destinations': input.action_destinations.map(x => x.id), 'input.existing_media': input.existing_media.map(x => x.id),
    'input.business_capabilities': input.business_capabilities.map(key), 'capabilities.capabilities': capabilities.capabilities.map(key),
    'profile.archetypes': profile.archetypes.map(x => x.id), 'plan.pages': plan.pages.map(x => x.path),
    'plan.modules': plan.pages.flatMap(x => x.modules.map(m => m.id)), 'plan.capabilities': plan.capabilities,
    'plan.excluded_capabilities': plan.excluded_capabilities.map(key),
  })) unique(values, path);
  const scopes = new Set([input.business_id, ...input.locations.map(x => x.id)]);
  if (input.locations.some(x => x.id === input.business_id)) issue('DUPLICATE_ID', 'input.locations', 'Branch ID cannot equal business ID');
  const facts = new Map(input.facts.map(x => [x.id, x]));
  const offerings = new Map(input.offerings.map(x => [x.id, x]));
  const actions = new Map(input.action_destinations.map(x => [x.id, x]));
  const upstream = new Map(input.business_capabilities.map(x => [key(x), x]));
  const checkedScope = (scope: string, path: string) => {
    if (!scopes.has(scope)) issue('UNKNOWN_SCOPE', path, `Unknown scope ${scope}`);
  };
  const checkFact = (ref: string, path: string, scope?: string, publishable = false) => {
    const fact = facts.get(ref);
    if (!fact) { issue('UNKNOWN_FACT', path, `Unknown fact ${ref}`); return; }
    if (scope && fact.scope_id !== scope && fact.scope_id !== input.business_id) issue('SCOPE_MISMATCH', path, `Fact ${ref} belongs to another branch`);
    if (publishable && (fact.publication !== 'APPROVED' || Date.parse(fact.observed_at) > instant || (fact.expires_at && Date.parse(fact.expires_at) <= instant))) {
      issue('FACT_NOT_PUBLISHABLE', path, `Fact ${ref} is not approved and current`);
    }
  };
  const checkOffering = (ref: string, path: string, scope?: string, publishable = false) => {
    const item = offerings.get(ref);
    if (!item) { issue('UNKNOWN_OFFERING', path, `Unknown offering ${ref}`); return; }
    if (scope && item.scope_id !== scope && item.scope_id !== input.business_id) issue('SCOPE_MISMATCH', path, `Offering ${ref} belongs to another branch`);
    for (const [field, refs] of Object.entries(item)) {
      if (field.endsWith('_fact_id') && typeof refs === 'string') checkFact(refs, `${path}.${field}`, item.scope_id, publishable);
      if (field === 'fact_ids' && Array.isArray(refs)) for (const ref of refs) checkFact(ref, `${path}.${field}`, item.scope_id, publishable);
    }
  };
  diagnostics.push(...validateBusinessInput(input).diagnostics);
  for (const scope of profile.scope_ids) checkedScope(scope, 'profile.scope_ids');
  for (const missing of profile.missing_inputs) checkedScope(missing.scope_id, 'profile.missing_inputs');
  for (const ref of profile.offering_ids) checkOffering(ref, 'profile.offering_ids');
  for (const archetype of profile.archetypes) {
    if (!archetype.category_observation_ids.length && !archetype.offering_ids.length && !archetype.evidence_ids.length) issue('MISSING_EVIDENCE', 'profile.archetypes', 'Archetype justification required');
    for (const ref of archetype.category_observation_ids) if (!input.category_observations.some(x => x.id === ref)) issue('UNKNOWN_CATEGORY', 'profile.archetypes', `Unknown category observation ${ref}`);
    for (const ref of archetype.offering_ids) checkOffering(ref, 'profile.archetypes.offering_ids');
    for (const ref of archetype.evidence_ids) checkFact(ref, 'profile.archetypes.evidence_ids');
  }
  if (JSON.stringify([...plan.archetypes].sort()) !== JSON.stringify(profile.archetypes.map(x => x.id).sort())) issue('ARTIFACT_MISMATCH', 'plan.archetypes', 'Plan archetypes differ from profile');
  const capMap = new Map(capabilities.capabilities.map(x => [key(x), x]));
  for (const source of input.business_capabilities) if (!capMap.has(key(source))) issue('CAPABILITY_OMITTED', 'capabilities.capabilities', `Missing upstream status ${key(source)}`);
  for (const cap of capabilities.capabilities) {
    checkedScope(cap.scope_id, 'capabilities.capabilities');
    const source = upstream.get(key(cap));
    if (!source || cap.status !== source.status || JSON.stringify([...cap.evidence_ids].sort()) !== JSON.stringify([...source.evidence_ids].sort())) {
      issue('CAPABILITY_NOT_BACKED', `capabilities.${key(cap)}`, 'Status/evidence must match upstream; categories never authorize capabilities');
    }
    if (cap.backend_status !== 'BACKEND_NOT_CONNECTED' || cap.frontend_status !== 'NOT_SUPPORTED_YET') issue('IMPLEMENTATION_NOT_AVAILABLE', `capabilities.${key(cap)}`, 'H0 has no commercial UI or connected backend');
    for (const ref of cap.offering_ids) checkOffering(ref, 'capabilities.offering_ids', cap.scope_id, cap.status === 'CONFIRMED_PRESENT');
    for (const ref of cap.action_destination_ids) {
      const action = actions.get(ref);
      if (!action || action.capability_id !== cap.id || action.scope_id !== cap.scope_id) issue('ACTION_MISMATCH', 'capabilities.action_destination_ids', 'Action must match capability and branch');
    }
  }
  const used = new Set<string>();
  const usedKeys = new Set<string>();
  for (const page of plan.pages) for (const module of page.modules) {
    const path = `plan.pages.${page.path}.${module.id}`;
    checkedScope(module.scope_id, path);
    const cap = capMap.get(key({ id: module.capability_id, scope_id: module.scope_id }));
    used.add(module.capability_id); usedKeys.add(`${module.scope_id}:${module.capability_id}`);
    if (!cap || cap.status !== 'CONFIRMED_PRESENT') issue('CAPABILITY_NOT_CONFIRMED', path, 'Module requires confirmed capability in the same scope');
    if (!plan.capabilities.includes(module.capability_id)) issue('CAPABILITY_NOT_DECLARED', path, 'Module capability missing from plan');
    if (module.presentation === 'LIVE_CONNECTED_INTEGRATION') issue('INTEGRATION_OUT_OF_SCOPE', path, 'Live integrations are outside H0');
    if (module.presentation === 'VISUAL_PREVIEW_ONLY' && plan.stage !== 'FIXTURE_PREVIEW') issue('PREVIEW_NOT_LABELED', path, 'Preview requires explicit fixture stage');
    if (!module.fact_ids.length && !module.offering_ids.length) issue('MISSING_INPUT', path, 'Module must have substantive content bindings');
    for (const ref of module.fact_ids) checkFact(ref, path, module.scope_id, true);
    for (const ref of module.offering_ids) {
      checkOffering(ref, path, module.scope_id, true);
      if (!cap?.offering_ids.includes(ref)) issue('OFFERING_NOT_BOUND', path, 'Offering must belong to capability profile');
    }
    const kinds = requiredOfferingKinds[module.capability_id];
    if (kinds && !module.offering_ids.some(ref => kinds.includes(offerings.get(ref)?.kind ?? ''))) issue('MISSING_INPUT', path, `Capability needs ${kinds.join(' or ')}`);
    if (kinds && module.offering_ids.some(ref => !kinds.includes(offerings.get(ref)?.kind ?? ''))) issue('OFFERING_KIND_MISMATCH', path, 'Offering kind incompatible with capability');
    if (module.capability_id === 'identity' && !module.fact_ids.includes(input.identity.name_fact_id)) issue('MISSING_INPUT', path, 'Identity must bind business name');
    for (const ref of module.offering_ids) {
      const item = offerings.get(ref);
      if (item?.kind === 'class_session') {
        const start = facts.get(item.starts_at_fact_id);
        const zone = facts.get(item.timezone_fact_id);
        if (start?.kind !== 'class_starts_at' || typeof start.value !== 'string' || !Number.isFinite(Date.parse(start.value))) issue('FACT_KIND_MISMATCH', path, 'Class requires a valid start timestamp');
        try {
          if (zone?.kind !== 'timezone' || typeof zone.value !== 'string') throw new Error('Missing timezone');
          new Intl.DateTimeFormat('es', { timeZone: zone.value });
        } catch { issue('FACT_KIND_MISMATCH', path, 'Class requires a valid timezone'); }
      }
    }
    if (module.presentation === 'REAL_APPROVED_EXTERNAL_LINK' || module.action_destination_id) {
      const action = actions.get(module.action_destination_id ?? '');
      if (!action || action.capability_id !== module.capability_id || action.scope_id !== module.scope_id || !cap?.action_destination_ids.includes(action.id)) {
        issue('ACTION_MISMATCH', path, 'Approved action matching capability and scope is required');
      } else {
        checkFact(action.url_fact_id, path, module.scope_id, true);
        const fact = facts.get(action.url_fact_id);
        if (fact?.kind !== 'action_url' || !isApprovedUrl(fact.value)) issue('UNSAFE_ACTION_URL', path, 'External actions require an HTTPS URL without credentials');
      }
    }
  }
  unique(plan.archetypes, 'plan.archetypes');
  for (const cap of plan.capabilities) if (!used.has(cap)) issue('CAPABILITY_WITHOUT_MODULE', 'plan.capabilities', `${cap} has no bound module`);
  if (!used.has('identity')) issue('MISSING_INPUT', 'plan', 'Plan must preserve identity');
  for (const excluded of plan.excluded_capabilities) {
    checkedScope(excluded.scope_id, 'plan.excluded_capabilities');
    const cap = capMap.get(key(excluded));
    if (!cap) issue('CAPABILITY_NOT_BACKED', 'plan.excluded_capabilities', 'Excluded capability must be recorded in profile');
    else if (cap.status !== 'CONFIRMED_PRESENT' && excluded.reason !== cap.status) issue('EXCLUSION_MISMATCH', 'plan.excluded_capabilities', 'Exclusion must preserve evidence state');
    else if (cap.status === 'CONFIRMED_PRESENT' && !(excluded.reason === 'MISSING_INPUT' && cap.missing_inputs.length || excluded.reason === 'NOT_SUPPORTED_YET' && cap.frontend_status === 'NOT_SUPPORTED_YET')) issue('EXCLUSION_MISMATCH', 'plan.excluded_capabilities', 'Confirmed capability needs explicit data/support reason');
    if (usedKeys.has(key(excluded))) issue('EXCLUDED_CAPABILITY_USED', 'plan.excluded_capabilities', 'Excluded capability has a module');
  }
  for (const cap of capabilities.capabilities) {
    if (!usedKeys.has(key(cap)) && !plan.excluded_capabilities.some(x => key(x) === key(cap))) issue('CAPABILITY_WITHOUT_DISPOSITION', 'plan.excluded_capabilities', `${key(cap)} must be represented or explicitly excluded`);
  }
  return { success: diagnostics.length === 0, diagnostics, data: { input, profile, capabilities, plan } };
}

function isApprovedUrl(value: BusinessInput['facts'][number]['value']): boolean {
  if (typeof value !== 'string') return false;
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password; }
  catch { return false; }
}
