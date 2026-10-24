import { CapabilityProfileV1, SitePlanV1 } from '../contracts/v1/schemas.ts';
import type { BusinessInput, BusinessProfile, Capability, CapabilityProfile, SitePlan } from '../contracts/v1/schemas.ts';
import { classifyBusiness } from '../taxonomy/resolve.ts';
import { classifyContextually } from '../taxonomy/context.ts';
import type { ContextualActivityLink } from '../taxonomy/context-contracts.ts';
import type { ActivityRelationship, MappingRule, TaxonomyObservation } from '../taxonomy/contracts.ts';
import { validateBusinessInput } from '../validation/input.ts';
import type { Diagnostic } from '../validation/validate.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
import { SiteRequirementsV1 } from './contracts.ts';
import type { Requirement, SiteRequirements } from './contracts.ts';
import { capabilityRegistry, validateCapabilityRegistry } from './registry.ts';
import { offeringFactIds, offeringKindsValid, publishable, safeExternalUrl, sorted, validClass } from './content.ts';
import { validateSemanticPlan } from './validate.ts';

type Artifacts = { input: BusinessInput; profile: BusinessProfile; capabilities: CapabilityProfile; requirements: SiteRequirements };
export type PlannerResult =
  | (Artifacts & { status: 'READY'; plan: SitePlan; diagnostics: Diagnostic[] })
  | (Partial<Artifacts> & { status: 'INPUT_INVALID' | 'CONTENT_BLOCKED'; plan?: never; diagnostics: Diagnostic[] });
export type PlannerOptions = {
  rules: readonly MappingRule[]; registry?: unknown; evaluation_time?: string;
  category_context?: TaxonomyObservation[]; activity_relationships?: ActivityRelationship[];
  classification_mode?: 'CATEGORY_V1' | 'CONTEXTUAL_V1'; contextual_activity_links?: ContextualActivityLink[];
};
const compare = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;
export const requirementId = (scope: string, id: Capability): string => `semantic-${inputSha256([scope, id]).slice(0, 24)}`;
export function scopedRoute(route: string, scope: string, businessId: string): string {
  if (scope === businessId) return route;
  const prefix = `/sedes/s-${inputSha256(scope).slice(0, 24)}`;
  return route === '/' ? prefix : prefix + route;
}

// Pure semantic planner. No I/O, system clock, category templates or action execution.
export function planBusiness(value: unknown, options: PlannerOptions): PlannerResult {
  const boundary = validateBusinessInput(value);
  if (!boundary.success || !boundary.data) return { status: 'INPUT_INVALID', diagnostics: boundary.diagnostics };
  const input = boundary.data;
  let registry;
  let classification;
  try {
    registry = validateCapabilityRegistry(options.registry ?? capabilityRegistry);
    if(options.classification_mode&&!['CATEGORY_V1','CONTEXTUAL_V1'].includes(options.classification_mode))throw Error('INVALID_CLASSIFICATION_MODE');
    const classificationOptions = {
      rules: options.rules,
      ...(options.category_context ? { category_context: options.category_context } : {}),
      ...(options.activity_relationships ? { activity_relationships: options.activity_relationships } : {}),
    };
    classification = options.classification_mode==='CONTEXTUAL_V1'
      ? classifyContextually(input,{...classificationOptions,evaluation_time:options.evaluation_time??input.as_of,activity_links:options.contextual_activity_links??[]})
      : classifyBusiness(input,classificationOptions);
  } catch (error) {
    return { status: 'INPUT_INVALID', diagnostics: [{ code: 'PLANNER_CONTEXT_INVALID', path: 'options', message: error instanceof Error ? error.message : 'Invalid planner context' }] };
  }
  const evaluated_at = options.evaluation_time ?? input.as_of;
  const instant = Date.parse(evaluated_at);
  if (!Number.isFinite(instant) || instant < Date.parse(input.as_of) || !SiteRequirementsV1.shape.evaluated_at.safeParse(evaluated_at).success) return {
    status: 'INPUT_INVALID', diagnostics: [{ code: 'INVALID_EVALUATION_TIME', path: 'options.evaluation_time', message: 'An explicit ISO instant at/after snapshot cutoff is required' }],
  };
  const profile = classification.profile;
  profile.scope_ids = sorted(profile.scope_ids); profile.offering_ids = sorted(profile.offering_ids);
  for (const archetype of profile.archetypes) archetype.category_observation_ids = sorted(archetype.category_observation_ids);
  let hashes: { registry_sha256: string; business_input_sha256: string; taxonomy_registry_sha256: string; classification_context_sha256: string };
  try {
    hashes = {
      registry_sha256: inputSha256(registry), business_input_sha256: inputSha256(input),
      taxonomy_registry_sha256: inputSha256({ version: '1.0.0', rules: options.rules }),
      classification_context_sha256: inputSha256({ category_context: options.category_context ?? [], activity_relationships: options.activity_relationships ?? [],
        ...(options.classification_mode==='CONTEXTUAL_V1'?{classification_mode:'CONTEXTUAL_V1',contextual_activity_links:options.contextual_activity_links??[],
          contextual_interpretation_sha256:'context' in classification?classification.context.interpretation_sha256:null}:{}) }),
    };
  } catch {
    return { status: 'INPUT_INVALID', diagnostics: [{ code: 'NON_JSON_PLANNER_INPUT', path: 'input/options', message: 'Planning inputs must be finite JSON, without undefined properties' }] };
  }
  const fingerprint = inputSha256({ planner_version: '1.0.0', ...hashes, evaluated_at }).slice(0, 24);
  const capabilities: CapabilityProfile = {
    schema_version: '1.0.0', business_id: input.business_id, snapshot_id: input.snapshot_id,
    id: `${input.snapshot_id}:h2-capabilities:${fingerprint}`, business_profile_id: profile.id,
    capabilities: input.business_capabilities.map<CapabilityProfile['capabilities'][number]>(cap => ({
      ...cap, evidence_ids: [...cap.evidence_ids].sort(), frontend_status: 'NOT_SUPPORTED_YET',
      backend_status: 'BACKEND_NOT_CONNECTED', offering_ids: [], action_destination_ids: [], missing_inputs: [],
    })).sort((a, b) => compare(a.scope_id, b.scope_id) || compare(a.id, b.id)),
  };
  const requirements: SiteRequirements = {
    schema_version: '1.0.0', business_id: input.business_id, snapshot_id: input.snapshot_id,
    business_profile_id: profile.id, capability_profile_id: capabilities.id, ...hashes,
    evaluated_at, requirements: [], omissions: [], bindings: [],
  };
  const facts = new Map(input.facts.map(x => [x.id, x]));
  const specifications = new Map(registry.specs.map(x => [x.id, x]));
  const omission = (entry: SiteRequirements['omissions'][number]) => requirements.omissions.push(entry);
  const fail = (req: Requirement, reason: string) => {
    req.disposition = 'BLOCKED'; req.missing_inputs.push(reason);
    omission({ code: 'MISSING_INPUT', scope_id: req.scope_id, capability_id: req.capability_id, reason, requested_from: 'upstream' });
  };
  for (const cap of capabilities.capabilities) {
    const spec = specifications.get(cap.id);
    // Unregistered capabilities retain their evidence status, without pretending support.
    const req: Requirement = {
      id: requirementId(cap.scope_id, cap.id), capability_id: cap.id, scope_id: cap.scope_id,
      source: 'UPSTREAM', evidence_status: cap.status, semantic_module: spec?.semantic_module ?? 'fact_collection',
      policy: spec?.policy ?? 'CONDITIONAL', priority: spec?.priority ?? 1000,
      disposition: cap.status === 'CONFIRMED_ABSENT' ? 'OMITTED' : 'BLOCKED',
      required: cap.id === 'identity' && cap.scope_id === input.business_id || spec?.policy === 'REQUIRED_IF_PRESENT' && cap.status === 'CONFIRMED_PRESENT',
      blocks_site: false, route: scopedRoute(spec?.route ?? '/', cap.scope_id, input.business_id),
      depends_on: [], missing_inputs: [], fact_ids: [], offering_ids: [],
    };
    requirements.requirements.push(req);
    if (cap.status !== 'CONFIRMED_PRESENT') {
      req.missing_inputs = cap.status === 'UNKNOWN' ? ['approved_capability_assertion'] : [];
      omission({ code: cap.status, scope_id: cap.scope_id, capability_id: cap.id, reason: 'Evidence state preserved from upstream', requested_from: 'upstream' });
      continue;
    }
    if (!cap.evidence_ids.every(id => publishable(facts.get(id), instant))) { fail(req, 'refresh_capability_evidence'); continue; }
    if (!spec || spec.semantic_status === 'DEFERRED') {
      omission({ code: 'NOT_SUPPORTED_YET', scope_id: cap.scope_id, capability_id: cap.id, reason: cap.id === 'gallery' ? 'H3 media eligibility and rights gate required' : 'Semantic specification unavailable', requested_from: 'compiler' });
      continue;
    }
    req.disposition = 'INCLUDED';
    const inScope = input.facts.filter(fact => fact.scope_id === cap.scope_id && spec.fact_kinds.includes(fact.kind));
    let candidates: string[] = [];
    switch (spec.selector) {
      case 'IDENTITY':
        candidates = [input.identity.name_fact_id, ...input.identity.alias_fact_ids, ...(input.identity.brand_fact_id ? [input.identity.brand_fact_id] : [])];
        break;
      case 'OFFERINGS': {
        for (const item of [...input.offerings].sort((a, b) => compare(a.id, b.id))) {
          if (item.scope_id !== cap.scope_id || !spec.offering_kinds.includes(item.kind)) continue;
          const refs = offeringFactIds(item);
          const rejected = refs.filter(id => !publishable(facts.get(id), instant));
          const factsSufficient = spec.offering_fact_requirements.every(requirement => refs.some(id => {
            const fact = facts.get(id); return fact?.kind === requirement.kind && (!requirement.value || fact.value === requirement.value);
          }));
          if (rejected.length || !offeringKindsValid(item, facts) || !validClass(item, facts) || !factsSufficient) {
            omission({ code: 'OFFERING_NOT_PUBLISHABLE', scope_id: cap.scope_id, capability_id: cap.id, offering_id: item.id,
              reason: rejected.length ? `Unapproved or stale facts: ${rejected.join(',')}` : 'Offering fact kinds, required role or class date/timezone invalid', requested_from: 'upstream' });
          } else req.offering_ids.push(item.id);
        }
        if (!req.offering_ids.length) fail(req, `publishable_offering:${spec.offering_kinds.join('|')}`);
        break;
      }
      case 'LOCATIONS': {
        const branch = input.locations.find(x => x.id === cap.scope_id);
        candidates = branch ? [branch.address_fact_id ?? '', ...branch.coordinate_fact_ids].filter(Boolean) : inScope.map(x => x.id);
        if (!candidates.some(id => facts.get(id)?.kind === 'address' && publishable(facts.get(id), instant))) fail(req, 'approved_address_in_scope');
        break;
      }
      case 'OPENING_HOURS': {
        const branch = input.locations.find(x => x.id === cap.scope_id);
        candidates = branch ? [...branch.opening_hours_fact_ids, ...branch.exception_fact_ids] : inScope.map(x => x.id);
        if (!candidates.some(id => facts.get(id)?.kind === 'opening_hours' && publishable(facts.get(id), instant))) fail(req, 'approved_opening_hours_in_scope');
        if (branch?.exception_fact_ids.some(id => facts.get(id)?.kind !== 'opening_hours_exception' || !publishable(facts.get(id), instant))) fail(req, 'approved_current_hours_exceptions');
        break;
      }
      case 'CONTACT': candidates = input.contact_fact_ids; break;
      case 'SERVICE_AREA': candidates = input.service_area_fact_ids; break;
      case 'VISIT_POLICY': candidates = input.locations.find(x => x.id === cap.scope_id)?.visit_policy_fact_ids ?? inScope.map(x => x.id); break;
      case 'FACTS': candidates = inScope.map(x => x.id); break;
      case 'ACTION': {
        const destinations = input.action_destinations.filter(x => x.capability_id === cap.id && x.scope_id === cap.scope_id).sort((a, b) => compare(a.id, b.id));
        const approved = destinations.filter(action => {
          const fact = facts.get(action.url_fact_id);
          return fact?.scope_id === cap.scope_id && fact.kind === 'action_url' && publishable(fact, instant) && safeExternalUrl(fact.value);
        });
        for (const action of destinations.filter(x => !approved.includes(x))) omission({ code: 'ACTION_NOT_APPROVED', scope_id: cap.scope_id, capability_id: cap.id,
          fact_id: action.url_fact_id, reason: 'Destination needs a current exact-scope HTTPS URL without credentials', requested_from: 'upstream' });
        if (approved.length) {
          // One external intent per module. Preserve other approved destinations in profile.
          cap.action_destination_ids = approved.map(x => x.id);
          req.action_destination_id = approved[0]!.id; req.fact_ids = [approved[0]!.url_fact_id];
          for (const action of approved.slice(1)) omission({ code: 'ALTERNATE_ACTION_DESTINATION', scope_id: cap.scope_id, capability_id: cap.id,
            fact_id: action.url_fact_id, reason: 'Canonical destination selected by ID; alternate retained in CapabilityProfile', requested_from: 'compiler' });
        } else fail(req, 'approved_action_destination');
        break;
      }
      case 'DEFERRED': break;
    }
    if (candidates.length) {
      for (const id of sorted(candidates)) {
        const fact = facts.get(id);
        const expectedScope = spec.selector === 'IDENTITY' ? input.business_id : cap.scope_id;
        const allowedKind = spec.selector === 'IDENTITY'
          ? id === input.identity.name_fact_id || id === input.identity.brand_fact_id || input.identity.alias_fact_ids.includes(id)
          : spec.selector === 'LOCATIONS' ? ['address', 'latitude', 'longitude'].includes(fact?.kind ?? '') : spec.fact_kinds.includes(fact?.kind ?? '');
        const coordinateValid = fact?.kind !== 'latitude' && fact?.kind !== 'longitude' || typeof fact?.value === 'number' && Math.abs(fact.value) <= (fact.kind === 'latitude' ? 90 : 180);
        if (fact?.scope_id === expectedScope && allowedKind && coordinateValid && publishable(fact, instant)) req.fact_ids.push(id);
        else omission({ code: 'FACT_NOT_ELIGIBLE', scope_id: cap.scope_id, capability_id: cap.id, fact_id: id,
          reason: 'Fact must have the expected kind, exact scope, valid value and current approval', requested_from: 'upstream' });
      }
    }
    req.fact_ids = sorted(req.fact_ids);
    if (spec.selector === 'IDENTITY' && !req.fact_ids.includes(input.identity.name_fact_id)) fail(req, 'approved_business_name');
    if (req.disposition === 'INCLUDED' && !req.fact_ids.length && !req.offering_ids.length) fail(req, 'substantive_approved_content');
    cap.offering_ids = [...req.offering_ids];
  }
  // Category suggestions live only in requirements, never added to the authoritative
  // CapabilityProfile as invented UNKNOWN/PRESENT branch claims.
  for (const id of sorted(['identity', ...profile.candidate_capabilities]) as Capability[]) {
    if (requirements.requirements.some(x => x.capability_id === id && (id !== 'identity' || x.scope_id === input.business_id))) continue;
    const spec = specifications.get(id);
    if (!spec) continue;
    requirements.requirements.push({
      id: requirementId(input.business_id, id), capability_id: id, scope_id: input.business_id,
      source: id === 'identity' ? 'ESSENTIAL_UNDECLARED' : 'CANDIDATE_ONLY', evidence_status: 'UNKNOWN',
      semantic_module: spec.semantic_module, policy: spec.policy, priority: spec.priority,
      disposition: 'BLOCKED', required: id === 'identity', blocks_site: id === 'identity',
      route: spec.route, depends_on: [], missing_inputs: ['approved_capability_assertion'], fact_ids: [], offering_ids: [],
    });
  }
  // Monotone dependency gate: scopes never inherit another branch's capabilities.
  let changed = true;
  const dependency = (req: Requirement, id: Capability) => requirements.requirements.find(x => x.capability_id === id && x.scope_id === (id === 'identity' ? input.business_id : req.scope_id));
  while (changed) {
    changed = false;
    for (const req of requirements.requirements.filter(x => x.disposition === 'INCLUDED')) {
      const spec = specifications.get(req.capability_id)!;
      const all = spec.depends_on.map(id => dependency(req, id));
      const any = spec.depends_on_any.map(id => dependency(req, id)).filter(x => x?.disposition === 'INCLUDED');
      if (all.some(x => x?.disposition !== 'INCLUDED') || spec.depends_on_any.length && !any.length) {
        fail(req, `eligible_dependency:${[...spec.depends_on, ...spec.depends_on_any].join('|')}`); changed = true;
      } else req.depends_on = sorted([...all, ...any].flatMap(x => x ? [x.id] : []));
    }
  }
  requirements.requirements.sort((a, b) => a.priority - b.priority || compare(a.scope_id, b.scope_id) || compare(a.capability_id, b.capability_id));
  for (const req of requirements.requirements) {
    req.missing_inputs = sorted(req.missing_inputs);
    req.blocks_site = req.required && req.disposition !== 'INCLUDED';
    const cap = capabilities.capabilities.find(x => x.id === req.capability_id && x.scope_id === req.scope_id);
    if (cap) cap.missing_inputs = [...req.missing_inputs];
  }
  const plan: SitePlan = {
    schema_version: '1.0.0', business_id: input.business_id, snapshot_id: input.snapshot_id,
    id: `${input.snapshot_id}:h2-plan:${fingerprint}`, business_profile_id: profile.id, capability_profile_id: capabilities.id,
    stage: input.data_mode === 'SYNTHETIC_FIXTURE' ? 'FIXTURE_PREVIEW' : 'SEMANTIC_PLAN',
    archetypes: profile.archetypes.map(x => x.id).sort(),
    capabilities: sorted(requirements.requirements.filter(x => x.disposition === 'INCLUDED').map(x => x.capability_id)) as Capability[],
    pages: [], excluded_capabilities: [],
  };
  const pages = new Map<string, SitePlan['pages'][number]>();
  for (const req of requirements.requirements.filter(x => x.disposition === 'INCLUDED')) {
    const page = pages.get(req.route) ?? { path: req.route, intent: req.route === '/' ? 'approved_business_identity' : 'approved_capabilities_in_scope', modules: [] };
    page.modules.push({
      id: req.id, capability_id: req.capability_id, scope_id: req.scope_id, required: req.required,
      presentation: specifications.get(req.capability_id)!.selector === 'ACTION' ? 'REAL_APPROVED_EXTERNAL_LINK' : 'STATIC_PUBLIC_INFORMATION',
      fact_ids: [...req.fact_ids], offering_ids: [...req.offering_ids], ...(req.action_destination_id ? { action_destination_id: req.action_destination_id } : {}),
    });
    pages.set(req.route, page);
  }
  plan.pages = [...pages.values()].sort((a, b) => a.path === '/' ? -1 : b.path === '/' ? 1 : compare(a.path, b.path));
  for (const cap of capabilities.capabilities) {
    const req = requirements.requirements.find(x => x.capability_id === cap.id && x.scope_id === cap.scope_id)!;
    if (req.disposition === 'INCLUDED') continue;
    plan.excluded_capabilities.push({ id: cap.id, scope_id: cap.scope_id,
      reason: cap.status !== 'CONFIRMED_PRESENT' ? cap.status : req.missing_inputs.length ? 'MISSING_INPUT' : 'NOT_SUPPORTED_YET' });
  }
  const allModules = plan.pages.flatMap(x => x.modules);
  const evidenceIds = new Set([...input.business_capabilities.flatMap(x => x.evidence_ids), ...input.category_observations.flatMap(x => x.evidence_ids), ...(options.activity_relationships ?? []).flatMap(x => x.evidence_ids)]);
  requirements.bindings = [...input.facts].sort((a, b) => compare(a.id, b.id)).map(fact => {
    const module_ids = allModules.filter(x => x.fact_ids.includes(fact.id) || x.offering_ids.some(id => {
      const item = input.offerings.find(offering => offering.id === id); return !!item && offeringFactIds(item).includes(fact.id);
    })).map(x => x.id).sort();
    const status = module_ids.length ? 'BOUND' : !publishable(fact, instant) ? 'NOT_PUBLISHABLE' : evidenceIds.has(fact.id) ? 'EVIDENCE_ONLY' : 'UNBOUND';
    if (!module_ids.length && status !== 'EVIDENCE_ONLY') omission({ code: status, scope_id: fact.scope_id, fact_id: fact.id,
      reason: status === 'NOT_PUBLISHABLE' ? 'Publication/freshness gate' : 'No eligible semantic binding for this fact', requested_from: 'upstream' });
    return { fact_id: fact.id, scope_id: fact.scope_id, module_ids, status };
  });
  requirements.omissions.sort((a, b) => compare(inputSha256(a), inputSha256(b)));
  const diagnostics: Diagnostic[] = [];
  if (profile.classification !== 'RESOLVED') diagnostics.push({ code: 'CLASSIFICATION_BLOCKED', path: 'profile.classification', message: classification.status });
  if (input.identity.status !== 'ACTIVE') diagnostics.push({ code: 'BUSINESS_NOT_ACTIVE', path: 'input.identity.status', message: input.identity.status });
  if ((options.activity_relationships ?? []).some(x => !x.evidence_ids.every(id => publishable(facts.get(id), instant)))) diagnostics.push({ code: 'CLASSIFICATION_EVIDENCE_STALE', path: 'options.activity_relationships', message: 'Refresh activity relationship evidence' });
  for (const req of requirements.requirements.filter(x => x.blocks_site)) diagnostics.push({ code: 'CONTENT_BLOCKED', path: req.id, message: `${req.capability_id}: ${req.missing_inputs.join(',') || req.evidence_status}` });
  if (!allModules.some(x => x.capability_id !== 'identity')) diagnostics.push({ code: 'INSUFFICIENT_SUBSTANTIVE_CONTENT', path: 'plan', message: 'Identity alone is not an honest substantive site' });
  const artifacts = { input, profile, capabilities: CapabilityProfileV1.parse(capabilities), requirements: SiteRequirementsV1.parse(requirements) };
  if (diagnostics.length) return { status: 'CONTENT_BLOCKED', ...artifacts, diagnostics };
  const result = validateSemanticPlan({ input, profile, capabilities, plan }, requirements, registry);
  if (!result.success) return { status: 'CONTENT_BLOCKED', ...artifacts, diagnostics: result.diagnostics };
  return { status: 'READY', ...artifacts, plan: SitePlanV1.parse(plan), diagnostics };
}
