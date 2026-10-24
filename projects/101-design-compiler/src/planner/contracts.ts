import { z } from 'zod';
import { ArchetypeId, CapabilityId, EvidenceStatus } from '../contracts/v1/schemas.ts';

export const PLANNER_VERSION = '1.0.0' as const;
const text = z.string().min(1).regex(/\S/);
export const CapabilitySpecV1 = z.strictObject({
  id: CapabilityId, version: z.literal(PLANNER_VERSION),
  semantic_module: z.enum(['identity', 'offering_collection', 'schedule', 'fact_collection', 'location_information', 'external_action', 'deferred_media']),
  semantic_status: z.enum(['AVAILABLE', 'DEFERRED']),
  selector: z.enum(['IDENTITY', 'OFFERINGS', 'FACTS', 'LOCATIONS', 'OPENING_HOURS', 'CONTACT', 'SERVICE_AREA', 'VISIT_POLICY', 'ACTION', 'DEFERRED']),
  offering_kinds: z.array(z.enum(['menu_item', 'product', 'product_category', 'membership_plan', 'class_session', 'service', 'room', 'program', 'event', 'professional'])),
  offering_fact_requirements: z.array(z.strictObject({ kind: text, value: text.optional() })),
  fact_kinds: z.array(text),
  candidate_archetypes: z.array(ArchetypeId),
  route: z.string().regex(/^\/(?:[a-z0-9]+(?:-[a-z0-9]+)*\/)*[a-z0-9-]*$/),
  priority: z.number().int().min(0).max(1000),
  policy: z.enum(['REQUIRED_IF_PRESENT', 'CONDITIONAL', 'OPTIONAL']),
  depends_on: z.array(CapabilityId), depends_on_any: z.array(CapabilityId),
});
export const CapabilityRegistryV1 = z.strictObject({
  schema_version: z.literal(PLANNER_VERSION), specs: z.array(CapabilitySpecV1).min(1),
});
export const SiteRequirementsV1 = z.strictObject({
  schema_version: z.literal(PLANNER_VERSION),
  business_id: text, snapshot_id: text, business_profile_id: text, capability_profile_id: text,
  registry_sha256: z.string().regex(/^[a-f0-9]{64}$/), evaluated_at: z.iso.datetime({ offset: true }),
  business_input_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  taxonomy_registry_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  classification_context_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  requirements: z.array(z.strictObject({
    id: text, capability_id: CapabilityId, scope_id: text,
    source: z.enum(['UPSTREAM', 'CANDIDATE_ONLY', 'ESSENTIAL_UNDECLARED']),
    evidence_status: EvidenceStatus,
    semantic_module: CapabilitySpecV1.shape.semantic_module,
    policy: CapabilitySpecV1.shape.policy, priority: CapabilitySpecV1.shape.priority,
    disposition: z.enum(['INCLUDED', 'BLOCKED', 'OMITTED']),
    required: z.boolean(), blocks_site: z.boolean(), route: CapabilitySpecV1.shape.route,
    depends_on: z.array(text), missing_inputs: z.array(text),
    fact_ids: z.array(text), offering_ids: z.array(text), action_destination_id: text.optional(),
  })),
  omissions: z.array(z.strictObject({
    code: text, scope_id: text, capability_id: CapabilityId.optional(),
    fact_id: text.optional(), offering_id: text.optional(),
    reason: text, requested_from: z.enum(['upstream', 'compiler']),
  })),
  bindings: z.array(z.strictObject({
    fact_id: text, scope_id: text, module_ids: z.array(text),
    status: z.enum(['BOUND', 'EVIDENCE_ONLY', 'NOT_PUBLISHABLE', 'UNBOUND']),
  })),
});
export type CapabilitySpec = z.infer<typeof CapabilitySpecV1>;
export type CapabilityRegistry = z.infer<typeof CapabilityRegistryV1>;
export type SiteRequirements = z.infer<typeof SiteRequirementsV1>;
export type Requirement = SiteRequirements['requirements'][number];
