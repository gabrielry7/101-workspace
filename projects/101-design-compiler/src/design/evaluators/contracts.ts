import { z } from 'zod';
import {DesignPlanV1} from '../contracts.ts';
const digest=z.string().regex(/^[a-f0-9]{64}$/);
export const EvaluatorFlagsV1=z.strictObject({impeccable:z.boolean().default(false),raven:z.boolean().default(false)});
export const DesignFindingV1=z.strictObject({
 schema_version:z.literal('1.0.0'),id:z.string().min(1),rule:z.string().min(1),
 severity:z.enum(['BLOCKING','WARNING','NOTE']),kind:z.enum(['MEASURED','HEURISTIC','AESTHETIC']),
 route:z.string().startsWith('/'),viewport:z.string().min(1),selector:z.string(),
 evidence:z.array(z.string().min(1)).min(1),recommendation:z.string().min(1),confidence:z.number().min(0).max(1),
 sources:z.array(z.strictObject({tool:z.string().min(1),version:z.string().min(1),receipt_sha256:digest})).min(1),
 repair:z.enum(['NONE','READING_MEASURE','TOUCH_TARGETS','TYPE_RHYTHM','TRACKING','LABEL_PLACEMENT']),
});
export type DesignFinding=z.infer<typeof DesignFindingV1>;
// Additive presentation contract. Business facts, page/module order, media and grants have no patch surface.
export const DesignRefinementV1=z.strictObject({schema_version:z.literal('1.0.0'),
 reading_measure:z.enum(['incumbent','bounded']).default('incumbent'),
 touch_targets:z.enum(['incumbent','comfortable']).default('incumbent'),
 type_rhythm:z.enum(['incumbent','reading']).default('incumbent'),
 tracking:z.enum(['incumbent','natural']).default('incumbent'),
 label_placement:z.enum(['incumbent','after-title']).default('incumbent'),
});
export type DesignRefinement=z.infer<typeof DesignRefinementV1>;
export const EvaluationBudgetV1=z.strictObject({max_iterations:z.number().int().min(0).max(2),max_tool_calls:z.number().int().min(0).max(200),max_wall_seconds:z.number().positive(),max_new_spend:z.literal(0)});
export const DesignPreferenceV1=z.strictObject({schema_version:z.literal('1.0.0'),experiment_id:digest,
 case_id:z.enum(['restaurante','hotel']),viewport:z.enum(['desktop','mobile']),
 preferred:z.enum(['A','B','C','D','TIE','NONE']),rating:z.number().int().min(1).max(10),
 dimensions:z.array(z.enum(['typography','palette','composition','media','navigation','readability'])),
 reason:z.string().min(1).max(4000),recorded_at:z.iso.datetime(),source:z.literal('EXPLICIT_HUMAN_INPUT')});
export const QualityExperimentV1=z.strictObject({schema_version:z.literal('1.0.0'),experiment_id:digest,seed_status:z.string().min(1),budget:EvaluationBudgetV1,
 cases:z.array(z.strictObject({id:z.enum(['restaurante','hotel']),input_sha256:digest,data_mode:z.literal('SYNTHETIC_FIXTURE'),
  variants:z.array(z.strictObject({condition:z.enum(['A','B','C','D']),flags:EvaluatorFlagsV1,design:DesignPlanV1,refinement:DesignRefinementV1,iteration:z.number().int().min(0).max(2),trace:z.array(z.unknown())})).length(4)})).length(2),
 metering:z.strictObject({preflight_tool_calls:z.number().int().nonnegative(),model_api_calls:z.literal(0),session_tokens:z.null(),session_cost:z.null(),paid_provider_spend:z.literal(0)}),human_preferences:z.literal('NOT_COLLECTED'),default_enabled:z.literal(false)});
export const evaluatorContracts={EvaluatorFlagsV1,DesignFindingV1,DesignRefinementV1,EvaluationBudgetV1,DesignPreferenceV1,QualityExperimentV1};
