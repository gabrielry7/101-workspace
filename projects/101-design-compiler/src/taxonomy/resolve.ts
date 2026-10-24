import { BusinessInputV1, BusinessProfileV1 } from '../contracts/v1/schemas.ts';
import type { BusinessInput, BusinessProfile, Capability } from '../contracts/v1/schemas.ts';
import { ActivityRelationshipV1, MappingRegistryV1, TaxonomyObservationV1, canonicalProvider, comparisonKey, splitHierarchy } from './contracts.ts';
import type { ActivityRelationship, Archetype, CandidateCapability, MappingRule, TaxonomyObservation } from './contracts.ts';

export type ObservationResolution = {
  observation: TaxonomyObservation;
  outcome: 'MAPPED' | 'AMBIGUOUS' | 'NON_BUSINESS' | 'UNKNOWN' | 'UNMAPPED';
  archetypes: Archetype[]; alternatives: Archetype[][]; rule_ids: string[];
  diagnostics: string[];
};
export type ResolutionStatus = 'RESOLVED' | 'HYBRID' | 'AMBIGUOUS' | 'PARTIAL' | 'UNKNOWN' | 'ABSTAINED' | 'NON_BUSINESS';

export function validateRegistry(rules: readonly MappingRule[]): MappingRule[] {
  const parsed = MappingRegistryV1.parse({ schema_version: '1.0.0', rules });
  if (new Set(parsed.rules.map(x => x.id)).size !== parsed.rules.length) throw new Error('DUPLICATE_RULE_ID');
  for (const rule of parsed.rules) {
    if (rule.outcome === 'MAPPED' && (!rule.archetypes.length || rule.alternatives.length)) throw new Error(`INVALID_MAPPED_RULE:${rule.id}`);
    if (rule.outcome === 'AMBIGUOUS' && (rule.alternatives.length < 2 || rule.archetypes.length)) throw new Error(`INVALID_AMBIGUOUS_RULE:${rule.id}`);
    if (['NON_BUSINESS', 'UNKNOWN'].includes(rule.outcome) && (rule.archetypes.length || rule.alternatives.length)) throw new Error(`INVALID_ABSTENTION_RULE:${rule.id}`);
  }
  return parsed.rules;
}

function matches(observation: TaxonomyObservation, rules: readonly MappingRule[]): MappingRule[] {
  const scored = rules.flatMap(rule => {
    if (canonicalProvider(rule.provider) !== canonicalProvider(observation.source) || !rule.fields.some(field => comparisonKey(field) === comparisonKey(observation.field))) return [];
    const values = rule.values.map(comparisonKey);
    if (rule.match === 'EXACT') return values.includes(comparisonKey(observation.value)) ? [{ rule, score: 100_000 }] : [];
    // Only whole hierarchy nodes; never substring keywords. Most specific node wins.
    const depth = observation.hierarchy.map((node, index) => values.includes(comparisonKey(node)) ? index : -1).reduce((a, b) => Math.max(a, b), -1);
    return depth >= 0 ? [{ rule, score: depth }] : [];
  });
  const best = Math.max(-1, ...scored.map(x => x.score));
  return scored.filter(x => x.score === best).map(x => x.rule);
}
const sorted = <T extends string>(values: readonly T[]): T[] => [...new Set(values)].sort();
const cores = (values: readonly Archetype[]) => sorted(values.filter(x => x !== 'regulated_services'));

function resolutionFor(observation: TaxonomyObservation, rules: MappingRule[]): ObservationResolution {
  if (!rules.length) return { observation, outcome: 'UNMAPPED', archetypes: [], alternatives: [], rule_ids: [], diagnostics: ['NO_MAPPING_RULE'] };
  const signatures = sorted(rules.map(rule => JSON.stringify([rule.outcome, sorted(rule.archetypes), rule.alternatives.map(sorted).sort()])));
  if (signatures.length > 1) return {
    observation, outcome: 'AMBIGUOUS', archetypes: [],
    alternatives: rules.flatMap(rule => rule.outcome === 'MAPPED' ? [rule.archetypes] : rule.alternatives),
    rule_ids: rules.map(x => x.id).sort(), diagnostics: ['CONFLICTING_MAPPING_RULES'],
  };
  const rule = rules[0]!;
  return { observation, outcome: rule.outcome, archetypes: sorted(rule.archetypes), alternatives: rule.alternatives.map(sorted), rule_ids: rules.map(x => x.id).sort(), diagnostics: [rule.rationale] };
}

export function resolveObservation(value: TaxonomyObservation, rules: readonly MappingRule[]): ObservationResolution {
  const observation = TaxonomyObservationV1.parse(value);
  if (canonicalProvider(observation.source) === 'foursquare' && ['foursquare.category', 'category'].includes(comparisonKey(observation.field))) {
    const expected = splitHierarchy(observation.value);
    const valid = observation.value.includes('>')
      ? JSON.stringify(observation.hierarchy) === JSON.stringify(expected)
      : comparisonKey(observation.hierarchy.at(-1) ?? '') === comparisonKey(observation.value);
    if (!valid) return { observation, outcome: 'AMBIGUOUS', archetypes: [], alternatives: [], rule_ids: [], diagnostics: ['HIERARCHY_SOURCE_CONFLICT'] };
  }
  const primary = resolutionFor(observation, matches(observation, rules));
  if (!observation.normalized_category || comparisonKey(observation.field) === '101.normalized_category') return primary;
  const normalized = resolutionFor(observation, matches({ ...observation, field: '101.normalized_category', value: observation.normalized_category }, rules));
  if (normalized.outcome === 'UNMAPPED' || normalized.outcome === 'UNKNOWN') return primary;
  if (primary.outcome === 'UNMAPPED' || primary.outcome === 'UNKNOWN') return { ...normalized, diagnostics: [...normalized.diagnostics, 'EXPLICIT_NORMALIZED_CATEGORY_FALLBACK'] };
  if (primary.outcome === 'MAPPED' && (normalized.outcome === 'MAPPED' && cores(primary.archetypes).every(x => cores(normalized.archetypes).includes(x)) || normalized.outcome === 'AMBIGUOUS' && normalized.alternatives.some(values => cores(primary.archetypes).every(x => cores(values).includes(x))))) {
    return { ...primary, rule_ids: sorted([...primary.rule_ids, ...normalized.rule_ids]), diagnostics: [...primary.diagnostics, 'SPECIFIC_ORIGINAL_CATEGORY_REFINES_NORMALIZED_LABEL'] };
  }
  if (primary.outcome === normalized.outcome && primary.outcome === 'NON_BUSINESS') return primary;
  return { observation, outcome: 'AMBIGUOUS', archetypes: [], alternatives: [...(primary.outcome === 'MAPPED' ? [primary.archetypes] : primary.alternatives), ...(normalized.outcome === 'MAPPED' ? [normalized.archetypes] : normalized.alternatives)], rule_ids: sorted([...primary.rule_ids, ...normalized.rule_ids]), diagnostics: ['ORIGINAL_NORMALIZED_CONFLICT'] };
}

// Relevance vocabulary only. This is not H2's operational/renderer registry.
export const candidateCapabilitiesByArchetype: Partial<Record<Archetype, readonly Capability[]>> = {
  food_hospitality: ['menu', 'reservation', 'order', 'delivery', 'opening_hours'],
  product_retail: ['product_catalog', 'purchase', 'delivery', 'pickup', 'quote_request'],
  appointment_service: ['service_catalog', 'professional_profiles', 'appointment'],
  membership_and_classes: ['membership', 'class_schedule', 'trainer_profiles', 'membership_signup', 'class_enrollment'],
  lodging: ['rooms', 'amenities', 'room_booking'],
  field_service_and_quote: ['service_catalog', 'service_area', 'quote_request'],
  vehicle_service: ['service_catalog', 'appointment', 'quote_request'],
  professional_advisory: ['service_catalog', 'professional_profiles', 'contact_request'],
  education_programs: ['programs', 'class_schedule', 'class_enrollment'],
  events_and_entertainment: ['events', 'ticketing', 'reservation'],
  industrial_b2b: ['product_catalog', 'documents', 'quote_request'],
  property_and_spaces: ['portfolio', 'visit_booking', 'availability_display'],
  transport_and_logistics: ['service_catalog', 'service_area', 'quote_request'],
  regulated_services: ['documents'],
};

export function classifyBusiness(inputValue: BusinessInput, options: {
  rules: readonly MappingRule[];
  category_context?: readonly TaxonomyObservation[];
  activity_relationships?: readonly ActivityRelationship[];
}): { status: ResolutionStatus; profile: BusinessProfile; observations: ObservationResolution[]; candidate_capabilities: CandidateCapability[]; diagnostics: string[] } {
  const input = BusinessInputV1.parse(inputValue);
  if (new Set(input.category_observations.map(x => x.id)).size !== input.category_observations.length) throw new Error('DUPLICATE_CATEGORY_ID');
  const rules = validateRegistry(options.rules);
  const contexts = options.category_context ?? [];
  const diagnostics: string[] = [];
  if (new Set(contexts.map(x => x.id)).size !== contexts.length) throw new Error('DUPLICATE_CATEGORY_CONTEXT');
  for (const context of contexts) {
    const observed = input.category_observations.find(x => x.id === context.id);
    if (!observed || observed.source !== context.source || observed.field !== context.field || observed.value !== context.value || observed.provider_category_id !== context.provider_category_id || observed.normalized_category !== context.normalized_category || JSON.stringify(sorted(observed.evidence_ids)) !== JSON.stringify(sorted(context.evidence_ids))) throw new Error('CATEGORY_CONTEXT_MISMATCH');
  }
  const observations = input.category_observations.map(observation => {
    const { confidence: _confidence, ...category } = observation;
    return resolveObservation(contexts.find(x => x.id === observation.id) ?? {
      ...category, hierarchy: splitHierarchy(observation.value), provenance: [],
    }, rules);
  });
  const mapped = observations.filter(x => x.outcome === 'MAPPED');
  const inferred = sorted(mapped.flatMap(x => x.archetypes));
  const observationIds = new Set(observations.map(x => x.observation.id));
  const relationships = (options.activity_relationships ?? []).map(x => ActivityRelationshipV1.parse(x));
  if (new Set(relationships.map(x => x.id)).size !== relationships.length) throw new Error('DUPLICATE_RELATIONSHIP_ID');
  for (const relationship of relationships) {
    if (new Set(relationship.category_observation_ids).size !== relationship.category_observation_ids.length || relationship.category_observation_ids.some(x => !observationIds.has(x))) throw new Error('UNKNOWN_RELATIONSHIP_CATEGORY');
    const approved = relationship.evidence_ids.every(id => {
      const fact = input.facts.find(x => x.id === id);
      return fact && fact.scope_id === input.business_id && fact.publication === 'APPROVED' && Date.parse(fact.observed_at) <= Date.parse(input.as_of) && (!fact.expires_at || Date.parse(fact.expires_at) > Date.parse(input.as_of));
    });
    const assertion = relationship.evidence_ids.some(id => {
      const fact = input.facts.find(x => x.id === id);
      return fact?.kind === `activity:${relationship.kind.toLowerCase()}` && fact.value === true;
    });
    if (!approved || !assertion) throw new Error('UNVERIFIED_ACTIVITY_RELATIONSHIP');
  }
  let status: ResolutionStatus;
  if (!observations.length) status = 'ABSTAINED';
  else if (observations.some(x => x.outcome === 'AMBIGUOUS') || mapped.length && observations.some(x => x.outcome === 'NON_BUSINESS') || relationships.some(x => x.kind === 'ALTERNATIVE')) status = 'AMBIGUOUS';
  else if (observations.every(x => x.outcome === 'NON_BUSINESS')) status = 'NON_BUSINESS';
  else if (!mapped.length) status = 'UNKNOWN';
  else if (observations.some(x => x.outcome === 'UNKNOWN' || x.outcome === 'UNMAPPED')) status = 'PARTIAL';
  else if (cores(inferred).length > 1) {
    // Multiple labels alone do not prove a hybrid rather than conflicting sources.
    const related = relationships.some(x => x.kind === 'COEXISTING' && mapped.every(observation => x.category_observation_ids.includes(observation.observation.id)));
    status = related ? 'HYBRID' : 'AMBIGUOUS';
    if (!related) diagnostics.push('MULTIPLE_ARCHETYPES_REQUIRE_COEXISTENCE_EVIDENCE');
  } else status = cores(inferred).length ? 'RESOLVED' : 'AMBIGUOUS';
  const candidate_capabilities: CandidateCapability[] = sorted(inferred.flatMap(archetype => candidateCapabilitiesByArchetype[archetype] ?? [])).map(id => ({
    id, archetype_ids: inferred.filter(x => candidateCapabilitiesByArchetype[x]?.includes(id)),
    category_observation_ids: mapped.filter(x => x.archetypes.some(arch => candidateCapabilitiesByArchetype[arch]?.includes(id))).map(x => x.observation.id),
    authority: 'RELEVANCE_ONLY_NOT_VERIFIED',
  }));
  const profile = BusinessProfileV1.parse({
    schema_version: '1.0.0', business_id: input.business_id, snapshot_id: input.snapshot_id,
    id: `${input.snapshot_id}:taxonomy-profile:1.0.0`,
    classification: status === 'RESOLVED' || status === 'HYBRID' ? 'RESOLVED' : status === 'NON_BUSINESS' ? 'NON_BUSINESS' : 'UNRESOLVED',
    scope_ids: [input.business_id, ...input.locations.map(x => x.id)],
    archetypes: inferred.map(id => ({
      id, relevance: id === 'regulated_services' ? 'modifier' : id === cores(inferred)[0] ? 'primary' : 'secondary',
      // Uncalibrated rule certainty, bounded by upstream observation confidence.
      confidence: Math.min(...input.category_observations.filter(x => mapped.some(m => m.observation.id === x.id && m.archetypes.includes(id))).map(x => x.confidence)),
      category_observation_ids: mapped.filter(x => x.archetypes.includes(id)).map(x => x.observation.id),
      offering_ids: [], evidence_ids: sorted(mapped.filter(x => x.archetypes.includes(id)).flatMap(x => x.observation.evidence_ids)),
    })),
    offering_ids: input.offerings.map(x => x.id), candidate_capabilities: candidate_capabilities.map(x => x.id),
    missing_inputs: status === 'RESOLVED' || status === 'HYBRID' ? [] : [{ need: 'classification_review', scope_id: input.business_id, reason: status, requested_from: 'upstream' }],
    restrictions: input.restrictions,
  });
  return { status, profile, observations, candidate_capabilities, diagnostics };
}
