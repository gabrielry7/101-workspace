import { z } from 'zod';
import { ArchetypeId, CapabilityId } from '../contracts/v1/schemas.ts';

export const TAXONOMY_VERSION = '1.0.0' as const;
const text = z.string().min(1).regex(/\S/);
export const CategoryRecordV1 = z.strictObject({
  id: text,
  provider: text,
  provider_label: text,
  category_field: text,
  category_value: text,
  provider_category_id: z.string().nullable(),
  hierarchy: z.array(text),
  normalized_category: z.string().nullable(),
  provenance: z.strictObject({
    file: text, sha256: z.string().regex(/^[a-f0-9]{64}$/),
    row: z.number().int().positive(), line_start: z.number().int().positive(),
    line_end: z.number().int().positive(),
  }),
  counts: z.strictObject({
    source_observations: z.number().int().nonnegative(),
    business_candidates: z.number().int().nonnegative(),
    other_observations: z.number().int().nonnegative(),
  }),
  raw: z.record(z.string(), z.string()),
});
export const MappingRuleV1 = z.strictObject({
  id: text, provider: text, fields: z.array(text).min(1),
  match: z.enum(['EXACT', 'HIERARCHY_NODE']), values: z.array(text).min(1),
  outcome: z.enum(['MAPPED', 'AMBIGUOUS', 'NON_BUSINESS', 'UNKNOWN']),
  archetypes: z.array(ArchetypeId),
  alternatives: z.array(z.array(ArchetypeId).min(1)),
  rationale: text,
});
export const MappingRegistryV1 = z.strictObject({
  schema_version: z.literal(TAXONOMY_VERSION),
  rules: z.array(MappingRuleV1),
});
export const TaxonomyObservationV1 = z.strictObject({
  id: text, source: text, field: text, value: text,
  provider_category_id: text.optional(), normalized_category: text.optional(),
  hierarchy: z.array(text), evidence_ids: z.array(text),
  provenance: z.array(z.strictObject({
    source_record_id: text, source: text,
    observed_at: z.iso.datetime({ offset: true }),
    source_uri: z.url().optional(),
    inventory_record_id: text.optional(),
    inventory_sha256: z.string().regex(/^[a-f0-9]{64}$/).optional(),
  })),
});
export const ActivityRelationshipV1 = z.strictObject({
  id: text, kind: z.enum(['COEXISTING', 'ALTERNATIVE']),
  category_observation_ids: z.array(text).min(2), evidence_ids: z.array(text).min(1),
});
export const CandidateCapabilityV1 = z.strictObject({
  id: CapabilityId, archetype_ids: z.array(ArchetypeId),
  category_observation_ids: z.array(text),
  authority: z.literal('RELEVANCE_ONLY_NOT_VERIFIED'),
});
export type CategoryRecord = z.infer<typeof CategoryRecordV1>;
export type MappingRule = z.infer<typeof MappingRuleV1>;
export type TaxonomyObservation = z.infer<typeof TaxonomyObservationV1>;
export type ActivityRelationship = z.infer<typeof ActivityRelationshipV1>;
export type Archetype = z.infer<typeof ArchetypeId>;
export type CandidateCapability = z.infer<typeof CandidateCapabilityV1>;

export function canonicalProvider(value: string): string {
  return value.trim().toLowerCase();
}
export function comparisonKey(value: string): string {
  return value.normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase();
}
export function splitHierarchy(value: string): string[] {
  return value.split('>').map(part => part.trim()).filter(Boolean);
}
