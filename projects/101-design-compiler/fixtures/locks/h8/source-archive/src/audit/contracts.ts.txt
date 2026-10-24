import { z } from 'zod';
import { DesignPlanV1 } from '../design/contracts.ts';
const hash=z.string().regex(/^[a-f0-9]{64}$/);
export const AuditCandidateV1=z.strictObject({schema_version:z.literal('1.0.0'),plan:DesignPlanV1,
 fixture_mode:z.enum(['FROZEN_LAB','SEEDED_DEFECT_TEST']),layout:z.strictObject({measure:z.enum(['fluid','fixed-wide'])})});
export const AuditPolicyV1=z.strictObject({schema_version:z.literal('1.0.0'),profile:z.enum(['LAB','COMMERCIAL']),
 max_page_bytes:z.number().int().positive(),max_requests:z.number().int().nonnegative(),max_client_js_bytes:z.number().int().nonnegative(),
 original_media_exception:z.boolean()});
export const AuditIssueV1=z.strictObject({id:z.string().min(1),family:z.enum(['input','capabilities','semantic','rights','geometry','accessibility','performance','visual','diversity']),
 severity:z.enum(['BLOCKING','OBSERVATION']),code:z.string().min(1),route:z.string().min(1),viewport:z.strictObject({width:z.number().positive(),height:z.number().positive()}),
 selector:z.string(),evidence_ref:z.string().min(1),observation:z.string().min(1),repair:z.enum(['FLUID_MEASURE','NONE'])});
export const AuditReportV1=z.strictObject({schema_version:z.literal('1.0.0'),candidate_sha256:hash,policy_sha256:hash,
 semantic_page:z.string().min(1),route:z.string().min(1),viewport:z.strictObject({width:z.number().positive(),height:z.number().positive()}),
 status:z.enum(['LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW','FAIL']),production_ready:z.literal(false),
 families:z.array(z.strictObject({family:AuditIssueV1.shape.family,status:z.enum(['PASS','FAIL','LAB_EXCEPTION','NOT_MEASURED','NOT_APPLICABLE']),evidence_ref:z.string()})),
 issues:z.array(AuditIssueV1),raster_status:z.enum(['MEASURED_AUXILIARY','NOT_MEASURED']),human_preference:z.literal('NOT_COLLECTED'),
 measurements:z.strictObject({page_body_bytes:z.number().int().nonnegative(),requests_including_document:z.number().int().positive(),
  byte_status:z.literal('MEASURED_LOCAL_UNCOMPRESSED'),client_js_status:z.enum(['ZERO_SCRIPTS_OBSERVED','SCRIPT_PRESENT_BYTES_NOT_MEASURED']),
  lcp:z.literal('NOT_MEASURED'),inp:z.literal('NOT_MEASURED'),cls:z.literal('NOT_MEASURED'),field_p75:z.literal('NOT_MEASURED'),video:z.literal('NOT_APPLICABLE')})});
export const MutationV1=z.strictObject({schema_version:z.literal('1.0.0'),id:z.string().min(1),reason_issue_id:z.string().min(1),
 patch:z.strictObject({measure:z.enum(['fluid','fixed-wide'])})});
export const PreferenceV1=z.strictObject({schema_version:z.literal('1.0.0'),source:z.literal('HUMAN_LOCAL_PANEL'),
 comparison_id:z.string().min(1),context_sha256:hash,left_id:z.string().min(1),right_id:z.string().min(1),
 left_sha256:hash,right_sha256:hash,left_screenshot_sha256:hash,right_screenshot_sha256:hash,
 semantic_page:z.string().min(1),viewport:z.strictObject({width:z.number().positive(),height:z.number().positive()}),
 decision:z.enum(['A','B','TIE','NONE']),reason:z.string().max(3000),recorded_at:z.iso.datetime(),
 acceptance_scope:z.literal('THIS_PAIR_ROUTE_VIEWPORT_ONLY')});
export type AuditCandidate=z.infer<typeof AuditCandidateV1>;
export type AuditPolicy=z.infer<typeof AuditPolicyV1>;
export type AuditIssue=z.infer<typeof AuditIssueV1>;
export type AuditReport=z.infer<typeof AuditReportV1>;
export const auditContracts={AuditCandidateV1,AuditPolicyV1,AuditIssueV1,AuditReportV1,MutationV1,PreferenceV1};
