import { z } from 'zod';

const id = z.string().regex(/^[a-z0-9][a-z0-9-]{0,79}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const path = z.string().regex(/^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/);
export const TopologyV1 = z.strictObject({ frame: z.enum(['Flow', 'Rail']), stage: z.enum(['Sequence', 'Split']) });
export const TokensV1 = z.strictObject({ palette: z.enum(['olive', 'ink', 'earth']), type: z.enum(['serif', 'sans']),
  hierarchy: z.enum(['monument', 'compact']), rhythm: z.enum(['quiet', 'dense']), media_width: z.enum(['full', 'inset']), media_alignment: z.enum(['center', 'end']) });
export const ArtDirectionV1 = z.strictObject({ schema_version: z.literal('1.0.0'), id, context_sha256: hash,
  principle: z.string().min(12).max(600), dominance: z.enum(['typography', 'navigation', 'dialogue']),
  materiality: z.literal('unaltered-photograph'), rationale: z.string().min(12).max(900),
  topologies: z.array(TopologyV1).min(1).max(4), tokens: TokensV1,
  media_usage_ids: z.array(id).max(20), motion: z.literal('quiet'),
  risks: z.array(z.string().min(1).max(240)).min(1).max(12),
  constraints_acknowledged: z.strictObject({ truth: z.literal(true), rights: z.literal(true), modules: z.literal(true), no_code: z.literal(true) }),
});
export const DesignPlanV1 = z.strictObject({ schema_version: z.literal('1.0.0'), id, art_direction_id: id,
  site_plan_id: z.string().min(1).max(240), plan_sha256: hash, content_sha256: hash, manifest_sha256: hash, context_sha256: hash,
  registry_version: z.literal('h5-lab-1.0.0'), tokens: TokensV1, motion: z.literal('quiet'),
  pages: z.array(z.strictObject({ path, composition: z.strictObject({ operator: z.enum(['Flow', 'Rail']),
    navigation: z.literal('before-content'), child: z.strictObject({ operator: z.enum(['Sequence', 'Split']),
      module_refs: z.array(id).min(1).max(200), media_usage_refs: z.array(id).max(20) }) }) })).min(1).max(100),
});
export const SearchBudgetV1 = z.strictObject({ proposals: z.number().int().min(1).max(12), samples: z.number().int().min(1).max(100),
  renders: z.number().int().min(1).max(12), finalists: z.number().int().min(1).max(12),
  max_output_bytes: z.number().int().min(100).max(1000000), new_provider_calls: z.literal(0), new_spend: z.literal(0) });
// Separate compatible version for truly media-free artistic materiality; V1 bytes/schema stay intact.
export const ArtDirectionV1_1 = ArtDirectionV1.extend({schema_version:z.literal('1.1.0'),materiality:z.literal('typography-only')});
export const CompatibleArtDirection = z.union([ArtDirectionV1,ArtDirectionV1_1]);
export type ArtDirection = z.infer<typeof CompatibleArtDirection>;
export type DesignPlan = z.infer<typeof DesignPlanV1>;
export type SearchBudget = z.infer<typeof SearchBudgetV1>;
export const designContracts = { ArtDirectionV1, DesignPlanV1, SearchBudgetV1 };
export const designContractsV1_1 = {ArtDirectionV1_1};
