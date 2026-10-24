import {z} from 'zod';
const id=z.string().regex(/^[a-z][a-z0-9-]{0,79}$/),sha=z.string().regex(/^[a-f0-9]{64}$/);
export const ContextualRecipeV2=z.strictObject({
 navigation:z.enum(['Top','Rail','Index']),hero:z.enum(['Split','Monument','Diptych','Stage']),
 collection:z.enum(['Grid','Rows','Mosaic']),mobile_collection:z.enum(['Stack','Compact','Sequence']),
 narrative:z.enum(['BeforeCollection','AfterCollection']),visit:z.enum(['Columns','Band']),
 proportion:z.enum(['balanced','image-led','type-led']),measure:z.enum(['wide','contained']),
});
export const ContextualTokensV2=z.strictObject({palette:z.enum(['paper','tomato','night','olive']),voice:z.enum(['editorial','humanist','grotesk']),
 scale:z.enum(['monument','display','compact']),rhythm:z.enum(['airy','measured','tight']),corners:z.enum(['square','soft']),motion:z.literal('quiet')});
export const ArtDirectionV2=z.strictObject({schema_version:z.literal('2.0.0'),id,context_sha256:sha,label:z.string().min(1).max(80),
 feeling:z.string().min(1).max(120),principle:z.string().min(30).max(700),rationale:z.string().min(30).max(1000),
 references:z.array(z.string().regex(/^reference-\d{2}$/)).min(1).max(21),risks:z.array(z.string().min(1)).min(1),
 recipe:ContextualRecipeV2,tokens:ContextualTokensV2,constraints_acknowledged:z.strictObject({truth:z.literal(true),rights:z.literal(true),modules:z.literal(true),no_code:z.literal(true)})});
export const ContextualDesignPlanV2=z.strictObject({schema_version:z.literal('2.0.0'),id,art_direction_id:id,registry_version:z.literal('shared-contextual-2.0.0'),
 context_sha256:sha,plan_sha256:sha,content_sha256:sha,media_sha256:sha,route:z.string().regex(/^\/b3\/[a-z0-9-]+\/$/),
 module_refs:z.array(z.string().min(1)).min(1),recipe:ContextualRecipeV2,tokens:ContextualTokensV2,
 sections:z.strictObject({identity:z.string().min(1),narrative:z.string().min(1),collection:z.string().min(1),information:z.array(z.string().min(1)),preview_intents:z.array(z.enum(['request','selection'])).max(2)}),
 operational_state:z.literal('SYNTHETIC_PREVIEW_NO_BACKEND'),human_approval:z.literal('NOT_COLLECTED')});
export const ContextualPresentationV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('SYNTHETIC_EDITORIAL_PRESENTATION'),source:z.string().min(1),hero_kicker:z.string().min(1),hero_note:z.string().min(1),
 module_headings:z.record(z.string(),z.string().min(1)),anchors:z.record(z.string(),z.string().regex(/^[a-z][a-z0-9-]*$/)),offering_order:z.array(z.string()).min(1),offering_media:z.record(z.string(),z.string()),
 sections:ContextualDesignPlanV2.shape.sections,preview_catalog_references:z.strictObject({selection:z.string(),request:z.string()}),operation:z.literal('DEMO_ONLY')});
export const contextualContracts={ArtDirectionV2,ContextualDesignPlanV2};
export type ContextualDesignPlan=z.infer<typeof ContextualDesignPlanV2>;
export type ContextualRecipe=z.infer<typeof ContextualRecipeV2>;

// Associated revision: V2 records remain valid and byte-stable.
export const ReferenceCompositionV1=z.strictObject({
 schema_version:z.literal('1.0.0'),kind:z.literal('ASSISTANT_REFERENCE_APPLICATION'),
 source_context_sha256:sha,research_sha256:sha,content_sha256:sha,media_sha256:sha,
 authority:z.literal('ASSISTANT_OBSERVATIONS_NOT_NEW_USER_VOTES'),human_approval:z.literal('NOT_COLLECTED'),
 variants:z.array(z.strictObject({id,art_direction_id:id,
  relationship:z.enum(['EditorialCard','OffsetPair','TypeGallery','FramedCover']),
  chapters:z.enum(['Editorial','Direct','Exhibit','Notebook']),
  mobile:z.enum(['ReadingFirst','CompactIndex','ImageSequence','CoverFirst']),
  palette:ContextualTokensV2.shape.palette,voice:ContextualTokensV2.shape.voice,
  references:ArtDirectionV2.shape.references,decision:z.string().min(30),
  media_policy:z.literal('NATURAL_RATIO_NO_CROP_STATIC_HERO_REQUEST_VIDEO_640'),
 })).length(4),
});
export type ReferenceComposition=z.infer<typeof ReferenceCompositionV1>;
