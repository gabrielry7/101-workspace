import {z} from 'zod';
import {CapabilityId} from '../contracts/v1/schemas.ts';
import {MediaManifestV1,MediaBriefV1,MediaNeedV1} from './contracts.ts';
const text=z.string().min(1),sha=z.string().regex(/^[a-f0-9]{64}$/);
export const MediaFunctionBindingV1=z.strictObject({id:text,usage_id:text,capability_id:CapabilityId,feature_id:text,
 scope_id:text,page:text,module_id:text,subject_ids:z.array(text),acquisition_event_id:text,processing_event_ids:z.array(text).min(1)});
export const MediaRequirementRequestV1=z.strictObject({id:text,capability_id:CapabilityId,feature_id:text.nullable(),scope_id:text,
 subject_ids:z.array(text),subject_status:z.enum(['EXACT','SUBJECT_PENDING']),role:z.enum(['DOCUMENTARY','ILLUSTRATIVE','ATMOSPHERIC']),
 purpose:text,source:z.enum(['SEMANTIC_PLAN','MASTER_CATALOG']),need:MediaNeedV1.nullable(),
 status:z.enum(['AUTHORIZED','PENDING_AUTHENTIC_MATERIAL','PENDING_LICENSED_RESOURCE','PENDING_EXPLICIT_USE']),reason:text});
const file=z.strictObject({path:text,sha256:sha,bytes:z.number().int().positive()});
export const MediaProcessingEventV1=z.strictObject({id:text,kind:z.enum(['SINGLE_SELECTED_TRANSFER','TECHNICAL_DERIVATION','LOCAL_VISUAL_INSPECTION']),
 asset_ids:z.array(text).min(1),parent_asset_id:text.nullable(),count:z.number().int().positive(),receipt_path:text});
export const MediaLibraryV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('MEDIA_LIBRARY_SIDECAR'),
 library_id:text,library_sha256:sha,catalog_sha256:sha,review_catalog_sha256:sha,
 manifest:MediaManifestV1,brief:MediaBriefV1,bindings:z.array(MediaFunctionBindingV1),requests:z.array(MediaRequirementRequestV1),operations:z.array(MediaProcessingEventV1).min(1),
 files:z.array(file.extend({asset_id:text})).min(1),documents:z.array(file.extend({official_url:z.url(),version:text})).min(1),
 review:file,inspection:file,technical_inspection:file,acquisition:file,provider_policy:z.literal('USDA_ARS_SINGLE_SELECTED_PUBLIC_DOMAIN_PHOTO_V1'),
 proof_boundary:z.literal('PINNED_SOURCE_REVIEW_NOT_FIXTURE_VERIFIED'),human_design_approval:z.literal('NOT_COLLECTED')});
export const BoundMediaDiagnosticV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('B1_BOUND_MEDIA_DIAGNOSTIC'),
 base_diagnostic_sha256:sha,library_sha256:sha,evaluated_at:z.iso.datetime({offset:true}),
 entries:z.array(z.strictObject({capability_id:CapabilityId,scope_id:text,level_id:text,requirement_id:text,
  condition_active:z.boolean(),status:z.enum(['SATISFIED','MISSING','RIGHTS_REVIEW_PENDING','NOT_REQUIRED_BY_CONDITION']),
  usage_ids:z.array(text),codes:z.array(text)})),operational_integrations:z.literal('NOT_CONNECTED')});
export type MediaLibrary=z.infer<typeof MediaLibraryV1>;
export type MediaFunctionBinding=z.infer<typeof MediaFunctionBindingV1>;
export const libraryContracts={MediaFunctionBindingV1,MediaRequirementRequestV1,MediaProcessingEventV1,MediaLibraryV1,BoundMediaDiagnosticV1};
