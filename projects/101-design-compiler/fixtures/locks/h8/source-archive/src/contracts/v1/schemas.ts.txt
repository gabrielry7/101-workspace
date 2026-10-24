import { z } from 'zod';

export const CONTRACT_VERSION = '1.0.0' as const;
const id = z.string().min(1).regex(/\S/);
const ids = z.array(id);
const timestamp = z.iso.datetime({ offset: true });
const header = {
  schema_version: z.literal(CONTRACT_VERSION),
  business_id: id,
  snapshot_id: id,
};
export const EvidenceStatus = z.enum([
  'CONFIRMED_PRESENT', 'CONFIRMED_ABSENT', 'UNKNOWN', 'CONFLICTED', 'WITHHELD',
]);
export const CapabilityId = z.enum([
  'identity', 'about', 'locations', 'opening_hours', 'contact_channels',
  'social_profiles', 'reputation', 'gallery', 'service_catalog', 'product_catalog',
  'menu', 'product_variants', 'price_list', 'packages', 'rooms', 'programs',
  'professional_profiles', 'trainer_profiles', 'portfolio', 'case_studies',
  'reservation', 'appointment', 'quote_request', 'contact_request', 'purchase',
  'order', 'delivery', 'pickup', 'membership', 'membership_signup', 'class_enrollment',
  'ticketing', 'room_booking', 'visit_booking', 'service_request', 'class_schedule',
  'events', 'availability_display', 'service_area', 'delivery_policy', 'visit_policy',
  'payment_methods', 'amenities', 'accessibility_info', 'branches', 'faqs', 'documents',
]);
export const ArchetypeId = z.enum([
  'food_hospitality', 'product_retail', 'appointment_service', 'membership_and_classes',
  'lodging', 'field_service_and_quote', 'vehicle_service', 'professional_advisory',
  'education_programs', 'events_and_entertainment', 'industrial_b2b',
  'property_and_spaces', 'transport_and_logistics', 'regulated_services',
]);
export const Fact = z.strictObject({
  id, kind: id, value: z.union([z.string().min(1).regex(/\S/), z.number(), z.boolean()]),
  scope_id: id,
  publication: z.enum(['APPROVED', 'WITHHELD', 'CONFLICTED', 'UNKNOWN']),
  publication_decision_id: id,
  source: id,
  observed_at: timestamp,
  expires_at: timestamp.optional(),
});
const capabilityEvidence = {
  id: CapabilityId, scope_id: id, status: EvidenceStatus, evidence_ids: ids,
};
const offeringBase = { id, scope_id: id, name_fact_id: id, fact_ids: ids };
// Kinds are commercial objects, never templates. Fields are fact references.
export const Offering = z.discriminatedUnion('kind', [
  z.strictObject({ ...offeringBase, kind: z.literal('menu_item'), price_fact_id: id.optional() }),
  z.strictObject({ ...offeringBase, kind: z.literal('product'), sku_fact_id: id.optional(), price_fact_id: id.optional() }),
  z.strictObject({ ...offeringBase, kind: z.literal('product_category') }),
  z.strictObject({ ...offeringBase, kind: z.literal('membership_plan'), price_fact_id: id.optional(), terms_fact_id: id.optional() }),
  z.strictObject({ ...offeringBase, kind: z.literal('class_session'), starts_at_fact_id: id, timezone_fact_id: id }),
  z.strictObject({ ...offeringBase, kind: z.literal('service') }),
  z.strictObject({ ...offeringBase, kind: z.literal('room') }),
  z.strictObject({ ...offeringBase, kind: z.literal('program') }),
  z.strictObject({ ...offeringBase, kind: z.literal('event') }),
  z.strictObject({ ...offeringBase, kind: z.literal('professional') }),
]);
export const BusinessInputV1 = z.strictObject({
  ...header,
  data_mode: z.enum(['SYNTHETIC_FIXTURE', 'UPSTREAM_SNAPSHOT']),
  as_of: timestamp,
  identity: z.strictObject({
    name_fact_id: id, alias_fact_ids: ids,
    organization_id: id.optional(), brand_fact_id: id.optional(),
    status: z.enum(['ACTIVE', 'INACTIVE', 'UNKNOWN']),
    languages: z.array(id).min(1),
  }),
  category_observations: z.array(z.strictObject({
    id, source: id, field: id, value: id, provider_category_id: id.optional(),
    normalized_category: id.optional(), confidence: z.number().min(0).max(1), evidence_ids: ids,
  })),
  facts: z.array(Fact).min(1),
  locations: z.array(z.strictObject({
    id, address_fact_id: id.optional(), coordinate_fact_ids: ids,
    opening_hours_fact_ids: ids, exception_fact_ids: ids, visit_policy_fact_ids: ids,
  })),
  contact_fact_ids: ids,
  service_area_fact_ids: ids,
  offerings: z.array(Offering),
  business_capabilities: z.array(z.strictObject(capabilityEvidence)),
  action_destinations: z.array(z.strictObject({
    id, capability_id: CapabilityId, scope_id: id, url_fact_id: id,
  })),
  existing_media: z.array(z.strictObject({
    id, source: id, uri: id, kind: z.enum(['image', 'video', 'audio']), scope_id: id,
    rights_status: z.enum(['UNKNOWN', 'DOCUMENTED', 'BLOCKED']),
    rights_document_ids: ids, restrictions: z.array(id),
    width: z.number().int().positive().optional(), height: z.number().int().positive().optional(),
  })),
  restrictions: z.array(id), preference_fact_ids: ids,
});
export const BusinessProfileV1 = z.strictObject({
  ...header, id,
  classification: z.enum(['RESOLVED', 'UNRESOLVED', 'NON_BUSINESS']),
  scope_ids: ids,
  archetypes: z.array(z.strictObject({
    id: ArchetypeId, relevance: z.enum(['primary', 'secondary', 'modifier']),
    confidence: z.number().min(0).max(1),
    category_observation_ids: ids, offering_ids: ids, evidence_ids: ids,
  })),
  offering_ids: ids, candidate_capabilities: z.array(CapabilityId),
  missing_inputs: z.array(z.strictObject({
    need: id, scope_id: id, reason: id, requested_from: z.literal('upstream'),
  })),
  restrictions: z.array(id),
});
export const CapabilityProfileV1 = z.strictObject({
  ...header, id, business_profile_id: id,
  capabilities: z.array(z.strictObject({
    ...capabilityEvidence,
    frontend_status: z.enum(['FRONTEND_SUPPORTED', 'NOT_SUPPORTED_YET']),
    backend_status: z.enum(['BACKEND_NOT_CONNECTED', 'BACKEND_CONNECTED']),
    offering_ids: ids, action_destination_ids: ids,
    missing_inputs: z.array(id),
  })),
});
export const SitePlanV1 = z.strictObject({
  ...header, id, business_profile_id: id, capability_profile_id: id,
  stage: z.enum(['FIXTURE_PREVIEW', 'SEMANTIC_PLAN']),
  archetypes: z.array(ArchetypeId),
  capabilities: z.array(CapabilityId),
  pages: z.array(z.strictObject({
    path: z.string().regex(/^\/(?:[a-z0-9]+(?:-[a-z0-9]+)*\/)*[a-z0-9-]*$/),
    intent: id,
    modules: z.array(z.strictObject({
      id, capability_id: CapabilityId, scope_id: id,
      required: z.boolean(),
      presentation: z.enum([
        'VISUAL_PREVIEW_ONLY', 'STATIC_PUBLIC_INFORMATION',
        'REAL_APPROVED_EXTERNAL_LINK', 'LIVE_CONNECTED_INTEGRATION',
      ]),
      fact_ids: ids, offering_ids: ids, action_destination_id: id.optional(),
    })).min(1),
  })).min(1),
  excluded_capabilities: z.array(z.strictObject({
    id: CapabilityId, scope_id: id,
    reason: z.enum(['CONFIRMED_ABSENT', 'UNKNOWN', 'CONFLICTED', 'WITHHELD', 'MISSING_INPUT', 'NOT_SUPPORTED_YET']),
  })),
});

export const contracts = { BusinessInputV1, BusinessProfileV1, CapabilityProfileV1, SitePlanV1 };
export type BusinessInput = z.infer<typeof BusinessInputV1>;
export type BusinessProfile = z.infer<typeof BusinessProfileV1>;
export type CapabilityProfile = z.infer<typeof CapabilityProfileV1>;
export type SitePlan = z.infer<typeof SitePlanV1>;
export type Capability = z.infer<typeof CapabilityId>;
export type FixtureBundle = {
  input: BusinessInput; profile: BusinessProfile;
  capabilities: CapabilityProfile; plan: SitePlan;
};
