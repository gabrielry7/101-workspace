import {z} from 'zod';
import {ArchetypeId,BusinessProfileV1} from '../contracts/v1/schemas.ts';
import {TaxonomyObservationV1} from './contracts.ts';
const text=z.string().min(1).regex(/\S/),digest=z.string().regex(/^[a-f0-9]{64}$/);
export const ContextualActivityLinkV1=z.strictObject({id:text,scope_id:text,kind:z.enum(['COEXISTING','ALTERNATIVE']),
 archetype_ids:z.array(ArchetypeId).min(2),evidence_ids:z.array(text).min(1)});
export const ActivitySignalV1=z.strictObject({id:text,scope_id:text,rule_id:text,
 kind:z.enum(['CATEGORY','DESCRIPTION','ACTIVITY_ASSERTION','OFFERING']),polarity:z.enum(['POSITIVE','NEGATIVE']),
 candidates:z.array(ArchetypeId).min(1),category_observation_ids:z.array(text),offering_ids:z.array(text),fact_ids:z.array(text)});
export const ContextualInterpretationV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('CONTEXTUAL_ACTIVITY_INTERPRETATION'),
 business_id:text,snapshot_id:text,business_input_sha256:digest,evaluated_at:z.iso.datetime({offset:true}),policy_sha256:digest,
 options_sha256:digest,interpretation_sha256:digest,profile:BusinessProfileV1,
 original_categories:z.array(TaxonomyObservationV1),signals:z.array(ActivitySignalV1),
 ignored:z.array(z.strictObject({id:text,scope_id:text,reason:text})),
 scopes:z.array(z.strictObject({scope_id:text,status:z.enum(['RESOLVED','HYBRID','AMBIGUOUS','CONFLICTED','UNKNOWN','NON_BUSINESS']),
  archetypes:z.array(ArchetypeId),alternatives:z.array(ArchetypeId),signal_ids:z.array(text),diagnostics:z.array(text),
  clarification:z.array(z.strictObject({need:text,requested_from:z.literal('upstream'),message:text}))})),
 status:z.enum(['RESOLVED','HYBRID','MULTISCOPE','AMBIGUOUS','CONFLICTED','UNKNOWN','NON_BUSINESS']),
 authority:z.literal('ACTIVITY_RELEVANCE_ONLY_NOT_OPERATIONAL_CONFIRMATION'),calibrated_confidence:z.null(),
 limitations:z.array(text).min(1)});
export type ContextualActivityLink=z.infer<typeof ContextualActivityLinkV1>;
export type ActivitySignal=z.infer<typeof ActivitySignalV1>;
export type ContextualInterpretation=z.infer<typeof ContextualInterpretationV1>;
export const contextContracts={ContextualActivityLinkV1,ActivitySignalV1,ContextualInterpretationV1};
