import {z} from 'zod';
import {CapabilityId,ArchetypeId,EvidenceStatus} from '../contracts/v1/schemas.ts';
import {CapabilitySpecV1} from '../planner/contracts.ts';
const text=z.string().min(1).regex(/\S/),digest=z.string().regex(/^[a-f0-9]{64}$/);
export const RequirementOwner=z.enum(['BUSINESS_UPSTREAM','PROJECT_CONFIGURATION','PLATFORM','PROVIDER_RIGHTS']);
export const FutureVisitorInputV1=z.strictObject({id:text,label:text,value_type:z.enum(['IDENTIFIER','DATE','TIME','POSITIVE_INTEGER','TEXT','ACKNOWLEDGEMENT']),
 required_when:text,validation:text,purpose:text});
export const DataRequirementV1=z.strictObject({id:text,label:text,description:text,owner:RequirementOwner,
 kind:z.enum(['DATA','EVIDENCE','PERMISSION','CONFIGURATION','PLATFORM']),
 condition:z.enum(['ALWAYS','PRICES_PRESENT','COORDINATES_PRESENT','MEDIA_PRESENT','SCOPE_IS_BRANCH']),
 check:z.enum(['IDENTITY','ACTIVE_BUSINESS','LANGUAGES','CAPABILITY_ASSERTION','OFFERINGS','CONTENT_FACTS','FACT','ACTION_DESTINATION','CONTACT_CHANNEL',
  'MEDIA_FILE','MEDIA_RIGHTS','RIGHTS_REVIEW','PUBLICATION','SEMANTIC_SUPPORT','FRONTEND_SUPPORT','BACKEND_SUPPORT']),
 fact_kinds:z.array(text),binding:z.enum(['SCOPE','EACH_OFFERING','GLOBAL_IDENTITY']),
 validation:z.enum(['PRESENT','TEXT','NONNEGATIVE_NUMBER','POSITIVE_NUMBER','CURRENCY','TIMEZONE','ISO_DATETIME','HTTPS','COORDINATE_PAIR']),
 next_step:text});
export const ServiceLevelV1=z.strictObject({id:text,label:text,objective:text,expected_behavior:text,
 requirement_ids:z.array(text).min(1),specification:z.literal('SPECIFIED'),
 implementation:z.enum(['LAB_INFORMATION_PRIMITIVE','EXTERNAL_LINK_SEMANTICS_ONLY','SPECIFICATION_ONLY']),
 verification:z.literal('NOT_VERIFIED_OPERATIONALLY'),backend:z.literal('NOT_CONNECTED'),
 acceptance_criteria:z.array(text).min(1),interaction_states:z.array(text).min(1),visitor_inputs:z.array(FutureVisitorInputV1)});
export const CapabilityRequirementCardV1=z.strictObject({id:CapabilityId,label:text,objective:text,
 semantic_module:CapabilitySpecV1.shape.semantic_module,selector:CapabilitySpecV1.shape.selector,
 offering_kinds:CapabilitySpecV1.shape.offering_kinds,offering_fact_requirements:CapabilitySpecV1.shape.offering_fact_requirements,
 fact_kinds:z.array(text),candidate_archetypes:z.array(ArchetypeId),depends_on:z.array(CapabilityId),depends_on_any:z.array(CapabilityId),
 scope_policy:z.enum(['BUSINESS_ONLY','EXACT_SCOPE_WITH_GLOBAL_IDENTITY_DEPENDENCY']),levels:z.array(ServiceLevelV1).min(1),
 semantic_status:CapabilitySpecV1.shape.semantic_status,component_path:text.nullable(),semantic_test_reference:text,
 media_roles:z.array(z.enum(['DOCUMENTARY','ILLUSTRATIVE','ATMOSPHERIC'])),
 future_notes:z.array(text).min(1)});
export const RequirementCatalogV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('MASTER_CAPABILITY_REQUIREMENTS'),
 catalog_id:text,registry_sha256:digest,catalog_sha256:digest,definitions:z.array(DataRequirementV1).min(1),cards:z.array(CapabilityRequirementCardV1).min(1),
 groups:z.array(z.strictObject({archetype_id:ArchetypeId,capability_ids:z.array(CapabilityId)})),
 common_capabilities:z.array(CapabilityId),scope_inheritance:z.literal('IDENTITY_ONLY_NO_OPERATIONAL_BRANCH_INHERITANCE')});
export const FunctionalObjectiveDecisionV1=z.strictObject({id:text,scope_id:text,capability_id:CapabilityId,
 disposition:z.enum(['REQUESTED','NOT_APPLICABLE','REJECTED']),evidence_ids:z.array(text).min(1),reason:text});
export const FunctionalDiagnosticV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('FUNCTIONAL_OBJECTIVE_DIAGNOSTIC'),
 business_id:text,snapshot_id:text,business_input_sha256:digest,evaluated_at:z.iso.datetime({offset:true}),catalog_sha256:digest,
 contextual_interpretation_sha256:digest,diagnostic_sha256:digest,data_mode:z.enum(['SYNTHETIC_FIXTURE','UPSTREAM_SNAPSHOT']),
 planner_status:z.enum(['READY','INPUT_INVALID','CONTENT_BLOCKED']),plan_id:text.nullable(),plan_sha256:digest.nullable(),
 objective_sha256:digest,entries:z.array(z.strictObject({capability_id:CapabilityId,scope_id:text,
  relevance:z.enum(['REQUESTED','SUGGESTED','UPSTREAM_DECLARED','APPLICABILITY_NOT_EVALUATED','NOT_APPLICABLE_JUSTIFIED','REJECTED']),
  decision_evidence_ids:z.array(text),evidence_status:EvidenceStatus,emitted_in_plan:z.boolean(),
  module_ids:z.array(text),factual_evidence_ids:z.array(text),h2_missing_inputs:z.array(text),
  levels:z.array(z.strictObject({level_id:text,label:text,implementation:ServiceLevelV1.shape.implementation,
   status:z.enum(['INFORMATION_PLANNED','EXTERNAL_INTENT_PLANNED','PENDING','NOT_APPLICABLE_JUSTIFIED','REJECTED']),
   requirements:z.array(z.strictObject({requirement_id:text,label:text,owner:RequirementOwner,
    status:z.enum(['SATISFIED','MISSING','WITHHELD','CONFLICTED','STALE','NOT_REQUIRED_BY_CONDITION','SUPPORT_PENDING','RIGHTS_REVIEW_PENDING']),
    fact_ids:z.array(text),offering_ids:z.array(text),message:text,next_step:text.nullable()})),
   dependency_checks:z.array(z.strictObject({capability_ids:z.array(CapabilityId),mode:z.enum(['ALL','ANY']),scope_id:text,satisfied:z.boolean(),message:text})),
   blockers:z.array(text),next_steps:z.array(text)}))})),
 warnings:z.array(text),operational_integrations:z.literal('NOT_CONNECTED'),human_design_approval:z.literal('NOT_COLLECTED')});
export type RequirementDefinition=z.infer<typeof DataRequirementV1>;
export type RequirementCatalog=z.infer<typeof RequirementCatalogV1>;
export type RequirementCard=z.infer<typeof CapabilityRequirementCardV1>;
export type FunctionalDiagnostic=z.infer<typeof FunctionalDiagnosticV1>;
export type ObjectiveDecision=z.infer<typeof FunctionalObjectiveDecisionV1>;
export const requirementContracts={FutureVisitorInputV1,DataRequirementV1,ServiceLevelV1,CapabilityRequirementCardV1,RequirementCatalogV1,FunctionalObjectiveDecisionV1,FunctionalDiagnosticV1};
