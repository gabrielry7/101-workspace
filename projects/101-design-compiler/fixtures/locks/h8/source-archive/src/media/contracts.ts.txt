import { z } from 'zod';

export const MEDIA_VERSION = '1.0.0' as const;
const text = z.string().min(1).regex(/\S/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const time = z.iso.datetime({ offset: true });
const header = { schema_version: z.literal(MEDIA_VERSION) };
export const MediaRole = z.enum(['DOCUMENTARY', 'ILLUSTRATIVE', 'ATMOSPHERIC']);
export const Transformation = z.enum(['CROP', 'RESIZE', 'TRANSCODE', 'COLOR', 'AI_EDIT']);
const permission = z.enum(['ALLOWED', 'DENIED', 'UNKNOWN']);
export const Review = z.strictObject({
  status: z.enum(['UNKNOWN', 'VERIFIED', 'REJECTED']),
  reference: text.nullable(),
  reviewer: text.nullable(), reviewed_at: time.nullable(), evidence_sha256: hash.nullable(),
});
export const MediaAssetV1 = z.strictObject({
  ...header, id: text, data_mode: z.enum(['SYNTHETIC_FIXTURE', 'REAL']),
  kind: z.enum(['image', 'video', 'audio']), uri: text, source: text, external_id: text.nullable(),
  audio_track: z.enum(['UNKNOWN', 'NONE', 'PRESENT']),
  provenance: z.array(z.strictObject({ source: text, reference: text, recorded_at: time })).min(1),
  upstream_rights_status: z.enum(['UNKNOWN', 'DOCUMENTED', 'BLOCKED']).nullable(),
  upstream_document_ids: z.array(text),
  original_id: text, parent_id: text.nullable(), original_sha256: hash.nullable(), file_sha256: hash.nullable(),
  hash_review: Review, transformations: z.array(Transformation),
  restrictions: z.array(text), // Uninterpreted conditions fail closed; never silently discarded.
  denied_purposes: z.array(text),
  documentary: z.strictObject({ business_id: text, scope_id: text, subject_ids: z.array(text).min(1), review: Review }).nullable(),
  relevance: z.array(z.strictObject({ purpose: text, scope_id: text, review: Review })),
  inspection: z.strictObject({
    status: z.enum(['NOT_INSPECTED', 'REVIEWED']), review: Review,
    width: z.number().int().positive().nullable(), height: z.number().int().positive().nullable(),
    duration_seconds: z.number().positive().nullable(), codec: text.nullable(),
    subject: text.nullable(), findings: z.array(text),
    quality: z.enum(['UNKNOWN', 'PASS', 'FAIL']),
  }),
  third_party: z.strictObject({ model: z.enum(['UNKNOWN', 'REQUIRED', 'NOT_REQUIRED']), property: z.enum(['UNKNOWN', 'REQUIRED', 'NOT_REQUIRED']) }),
});
export const LicenseGrantV1 = z.strictObject({
  ...header, id: text, data_mode: MediaAssetV1.shape.data_mode,
  original_asset_id: text, original_sha256: hash, provider: text, license_type: text,
  holder: text, purchaser: text,
  document: z.strictObject({ reference: text, version: text, sha256: hash }), review: Review,
  client_ids: z.array(text).min(1), project_ids: z.array(text).min(1),
  scope_ids: z.array(text).min(1), purposes: z.array(text).min(1), pages: z.array(text).min(1),
  territories: z.array(text).min(1), valid_from: time, valid_until: time.nullable(), revoked: z.boolean(),
  commercial_web: permission, multiple_clients: permission, reuse: permission,
  redistribution: permission, sublicensing: permission, exclusive: permission,
  derivatives: permission, transformations: z.array(Transformation),
  automation: z.strictObject({ search: permission, download: permission }),
  ai: z.strictObject({ classification: permission, embedding: permission, vision: permission, editing: permission, training: permission }),
  attribution: z.strictObject({ required: z.boolean(), text: text.nullable() }),
  required_notices: z.array(text).optional(),
  releases: z.strictObject({ model: Review, property: Review }),
  restrictions: z.array(text), retention_until: time.nullable(),
  cost: z.strictObject({ amount: z.number().nonnegative(), currency: text, reference: text }).nullable(),
});
export const MediaUsageV1 = z.strictObject({
  ...header, id: text, need_id: text, asset_id: text, grant_id: text.nullable(),
  client_id: text, project_id: text, business_id: text, scope_id: text,
  page: text, module_id: text, purpose: text, role: MediaRole,
  representation: z.enum(['BUSINESS_EVIDENCE', 'GENERIC_CONTEXT']), subject_ids: z.array(text),
  transformations: z.array(Transformation), territory: text,
  attribution_text: text.nullable(), generic_label: text.nullable(),
  endorsement_claimed: z.boolean().optional(), context_notices: z.array(text).optional(),
  ai_operations: z.array(z.enum(['classification', 'embedding', 'vision', 'editing', 'training'])),
  automated_access: z.array(z.enum(['search', 'download'])),
});
export const MediaNeedV1 = z.strictObject({
  id: text, requirement_id: text, module_id: text.nullable(), page: text,
  scope_id: text, purpose: text, role: MediaRole, subject_ids: z.array(text),
  kinds: z.array(MediaAssetV1.shape.kind).min(1), required: z.boolean(), count: z.number().int().positive(),
  min_width: z.number().int().positive().nullable(), min_height: z.number().int().positive().nullable(),
});
const decision = z.strictObject({ usage_id: text, status: z.enum(['ALLOWED', 'BLOCKED']), rights_codes: z.array(text), suitability_codes: z.array(text), inherited_asset_ids: z.array(text) });
export const PackageProof = z.strictObject({
  id: text, client_id: text, project_id: text, evaluated_at: time,
  files: z.array(z.strictObject({ asset_id: text, path: text, sha256: hash })).min(1),
  documents: z.array(z.strictObject({ path: text, sha256: hash, official_url: z.url(), version: text })).min(1),
  render: z.strictObject({ page: text, html_path: text, html_sha256: hash,
    screenshot_path: text, screenshot_sha256: hash, receipt_path: text, receipt_sha256: hash, usage_ids: z.array(text).min(1) }),
});
export const MediaManifestV1 = z.strictObject({
  ...header, business_id: text, snapshot_id: text, site_plan_id: text,
  client_id: text, project_id: text, evaluated_at: time,
  plan_sha256: hash, requirements_sha256: hash, input_sha256: hash,
  assets: z.array(MediaAssetV1), grants: z.array(LicenseGrantV1), usages: z.array(MediaUsageV1),
  needs: z.array(MediaNeedV1), decisions: z.array(decision),
  package_proof: PackageProof.optional(),
});
export const MediaBriefV1 = z.strictObject({
  ...header, site_plan_id: text, manifest_sha256: hash, evaluated_at: time,
  gaps: z.array(z.strictObject({ need: MediaNeedV1, missing_count: z.number().int().positive(), reasons: z.array(text).min(1), requested_from: z.enum(['rights_review', 'inspection', 'upstream_or_commission', 'licensed_provider']) })),
  constraints: z.array(text), closure: z.enum(['PENDING_AUTHORIZED_MEDIA_PACKAGE', 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS', 'AUTHORIZED_PILOT_PACKAGE']),
});
export const mediaContracts = { MediaAssetV1, LicenseGrantV1, MediaUsageV1, MediaManifestV1, MediaBriefV1 };
export type MediaAsset = z.infer<typeof MediaAssetV1>;
export type LicenseGrant = z.infer<typeof LicenseGrantV1>;
export type MediaUsage = z.infer<typeof MediaUsageV1>;
export type MediaNeed = z.infer<typeof MediaNeedV1>;
export type MediaManifest = z.infer<typeof MediaManifestV1>;
export type MediaBrief = z.infer<typeof MediaBriefV1>;
export type ReviewRecord = z.infer<typeof Review>;
