import { createHash } from 'node:crypto';
import { MediaAssetV1, LicenseGrantV1 } from '../../../src/media/contracts.ts';
import type { MediaNeed, ReviewRecord } from '../../../src/media/contracts.ts';
import { unknownReview } from '../../../src/media/plan.ts';

// Purely synthetic permission/inspection assertions. No audiovisual file or legal authorization exists.
export const cutoff = '2026-10-08T00:00:00Z';
const digest = (text: string) => createHash('sha256').update(text).digest('hex');
export const syntheticReview = (sha: string): ReviewRecord => ({ status: 'VERIFIED', reference: 'https://example.invalid/synthetic-attestation', reviewer: 'SYNTHETIC_REVIEWER_NOT_REAL', reviewed_at: '2026-10-07T00:00:00Z', evidence_sha256: sha });
export function permissionFixture(need: MediaNeed, businessId: string) {
  const original = digest('SYNTHETIC ORIGINAL TOKEN; NOT IMAGE BYTES');
  const document = digest('SYNTHETIC GRANT TOKEN; NOT A LICENSE DOCUMENT');
  const asset = MediaAssetV1.parse({ schema_version: '1.0.0', id: 'synthetic-original', data_mode: 'SYNTHETIC_FIXTURE',
    kind: 'image', uri: 'https://example.invalid/synthetic-no-file', source: 'synthetic-contract-test', external_id: null,
    audio_track: 'NONE', relevance: [{ purpose: need.purpose, scope_id: need.scope_id, review: syntheticReview(original) }],
    provenance: [{ source: 'synthetic-contract-test', reference: 'fixtures/media/v1/permissions.ts', recorded_at: cutoff }],
    upstream_rights_status: 'DOCUMENTED', upstream_document_ids: ['synthetic-document'],
    original_id: 'synthetic-original', parent_id: null, original_sha256: original, file_sha256: original,
    hash_review: syntheticReview(original), transformations: [], restrictions: [], denied_purposes: [],
    documentary: need.role === 'DOCUMENTARY' ? { business_id: businessId, scope_id: need.scope_id, subject_ids: need.subject_ids, review: syntheticReview(original) } : null,
    inspection: { status: 'REVIEWED', review: syntheticReview(original), width: 1600, height: 1000, duration_seconds: null,
      codec: null, subject: 'SIMULATED_SUBJECT', findings: ['SIMULATED_INSPECTION; NO FILE INSPECTED'], quality: 'PASS' },
    third_party: { model: 'NOT_REQUIRED', property: 'NOT_REQUIRED' },
  });
  const grant = LicenseGrantV1.parse({ schema_version: '1.0.0', id: 'synthetic-grant', data_mode: 'SYNTHETIC_FIXTURE',
    original_asset_id: asset.id, original_sha256: original, provider: 'SYNTHETIC_PROVIDER', license_type: 'SYNTHETIC_TEST_ONLY',
    holder: 'synthetic-holder', purchaser: 'synthetic-purchaser',
    document: { reference: 'https://example.invalid/no-license', version: 'SYNTHETIC', sha256: document }, review: syntheticReview(document),
    client_ids: ['synthetic-client'], project_ids: ['synthetic-project'], scope_ids: [need.scope_id], purposes: [need.purpose], pages: [need.page],
    territories: ['CO'], valid_from: '2026-10-07T00:00:00Z', valid_until: '2027-01-01T00:00:00Z', revoked: false,
    commercial_web: 'ALLOWED', multiple_clients: 'DENIED', reuse: 'DENIED', redistribution: 'DENIED', sublicensing: 'DENIED', exclusive: 'DENIED',
    derivatives: 'ALLOWED', transformations: ['CROP', 'RESIZE', 'TRANSCODE', 'COLOR'],
    automation: { search: 'UNKNOWN', download: 'UNKNOWN' },
    ai: { classification: 'UNKNOWN', embedding: 'UNKNOWN', vision: 'UNKNOWN', editing: 'DENIED', training: 'DENIED' },
    attribution: { required: false, text: null }, releases: { model: unknownReview(), property: unknownReview() },
    restrictions: [], retention_until: null, cost: null,
  });
  return { asset, grant };
}
