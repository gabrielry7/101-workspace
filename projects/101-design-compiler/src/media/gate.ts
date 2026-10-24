import { z } from 'zod';
import { MediaAssetV1, LicenseGrantV1, MediaUsageV1 } from './contracts.ts';
import type { MediaAsset, MediaUsage, ReviewRecord } from './contracts.ts';

// Reviews are trusted, externally supplied attestations, not document authentication.
// The evaluator does no I/O, downloads, vision calls or wall-clock reads.
export function verified(review: ReviewRecord, at: string, sha: string | null): boolean {
  return review.status === 'VERIFIED' && !!review.reference && !!review.reviewer && !!review.reviewed_at
    && Date.parse(review.reviewed_at) <= Date.parse(at) && !!sha && review.evidence_sha256 === sha;
}
export function lineage(asset: MediaAsset, assets: readonly MediaAsset[]) {
  const chain: MediaAsset[] = []; const codes: string[] = []; const seen = new Set<string>();
  let current: MediaAsset | undefined = asset;
  while (current) {
    if (seen.has(current.id)) { codes.push('LINEAGE_CYCLE'); break; }
    seen.add(current.id); chain.push(current);
    if (!current.parent_id) break;
    current = assets.find(x => x.id === current!.parent_id);
    if (!current) codes.push('MISSING_PARENT');
  }
  const root = chain.at(-1);
  if (!root || root.parent_id || root.id !== asset.original_id || root.original_id !== root.id
    || root.transformations.length || chain.some(x => x.original_id !== root.id || x.original_sha256 !== root.original_sha256 || x.data_mode !== root.data_mode || x.kind !== root.kind)
    || chain.some(x => x.parent_id && !x.transformations.length)) codes.push('LINEAGE_MISMATCH');
  return { chain, root, codes };
}
export function rightsGate(assetValue: unknown, grantValue: unknown, usageValue: unknown,
  assetValues: readonly unknown[], evaluationTime: string, options: { allow_synthetic?: boolean } = {}) {
  const a = MediaAssetV1.safeParse(assetValue), g = LicenseGrantV1.safeParse(grantValue), u = MediaUsageV1.safeParse(usageValue);
  const all = z.array(MediaAssetV1).safeParse(assetValues);
  const codes: string[] = []; let inherited_asset_ids: string[] = [];
  if (!z.iso.datetime({ offset: true }).safeParse(evaluationTime).success) codes.push('INVALID_EVALUATION_TIME');
  if (!a.success || !u.success || !all.success) codes.push('MEDIA_SCHEMA_INVALID');
  if (!g.success) codes.push(grantValue == null ? 'RIGHTS_UNKNOWN' : 'GRANT_SCHEMA_INVALID');
  if (codes.length || !a.success || !g.success || !u.success || !all.success) return { status: 'BLOCKED' as const, codes, inherited_asset_ids };
  const asset = a.data, grant = g.data, usage = u.data, assets = all.data;
  const tree = lineage(asset, assets); codes.push(...tree.codes); inherited_asset_ids = tree.chain.map(x => x.id);
  if (new Set(assets.map(x => x.id)).size !== assets.length || assets.filter(x => x.id === asset.id).length !== 1
    || JSON.stringify(assets.find(x => x.id === asset.id)) !== JSON.stringify(asset)) codes.push('ASSET_INVENTORY_MISMATCH');
  if (usage.asset_id !== asset.id || usage.grant_id !== grant.id || grant.original_asset_id !== asset.original_id
    || grant.original_sha256 !== asset.original_sha256) codes.push('GRANT_ASSET_MISMATCH');
  if (grant.data_mode !== asset.data_mode || (asset.data_mode === 'SYNTHETIC_FIXTURE' && !options.allow_synthetic)) codes.push('SYNTHETIC_RIGHTS_REJECTED');
  if (!verified(grant.review, evaluationTime, grant.document.sha256)) codes.push('RIGHTS_UNVERIFIED');
  const at = Date.parse(evaluationTime);
  if (Date.parse(grant.valid_from) > at) codes.push('RIGHTS_NOT_STARTED');
  if ((grant.valid_until && Date.parse(grant.valid_until) <= at) || (grant.retention_until && Date.parse(grant.retention_until) <= at)) codes.push('RIGHTS_EXPIRED');
  if (grant.valid_until && Date.parse(grant.valid_until) <= Date.parse(grant.valid_from)) codes.push('INVALID_GRANT_PERIOD');
  if (grant.revoked) codes.push('RIGHTS_REVOKED');
  if (grant.commercial_web !== 'ALLOWED') codes.push('COMMERCIAL_WEB_NOT_ALLOWED');
  for (const [allowed, value, code] of [
    [grant.client_ids, usage.client_id, 'CLIENT_NOT_ALLOWED'], [grant.project_ids, usage.project_id, 'PROJECT_NOT_ALLOWED'],
    [grant.scope_ids, usage.scope_id, 'SCOPE_NOT_ALLOWED'], [grant.purposes, usage.purpose, 'PURPOSE_NOT_ALLOWED'],
    [grant.pages, usage.page, 'PAGE_NOT_ALLOWED'], [grant.territories, usage.territory, 'TERRITORY_NOT_ALLOWED'],
  ] as const) if (!allowed.includes(value)) codes.push(code);
  if (grant.client_ids.length > 1 && grant.multiple_clients !== 'ALLOWED') codes.push('MULTICLIENT_NOT_ALLOWED');
  if (grant.project_ids.length > 1 && grant.reuse !== 'ALLOWED') codes.push('REUSE_NOT_ALLOWED');
  const checkRestrictions = (restrictions: string[], unknownCode: string) => {
    if (restrictions.some(x => x !== 'NO_PROVIDER_ENDORSEMENT')) codes.push(unknownCode);
    if (restrictions.includes('NO_PROVIDER_ENDORSEMENT')) {
      if (usage.endorsement_claimed !== false) codes.push('PROVIDER_ENDORSEMENT_NOT_DISCLAIMED');
      if (!grant.required_notices?.length) codes.push('PROVIDER_NOTICE_REQUIRED');
    }
  };
  checkRestrictions(grant.restrictions, 'UNRESOLVED_LICENSE_RESTRICTIONS');
  if (grant.required_notices?.some(x => !usage.context_notices?.includes(x))) codes.push('REQUIRED_NOTICE_MISSING');
  const transforms = [...tree.chain.flatMap(x => x.transformations), ...usage.transformations];
  if ((asset.parent_id || transforms.length) && grant.derivatives !== 'ALLOWED') codes.push('DERIVATIVES_NOT_ALLOWED');
  if (transforms.some(x => !grant.transformations.includes(x))) codes.push('TRANSFORMATION_NOT_ALLOWED');
  if (transforms.includes('AI_EDIT') && grant.ai.editing !== 'ALLOWED') codes.push('AI_EDIT_NOT_ALLOWED');
  if (usage.ai_operations.some(x => grant.ai[x] !== 'ALLOWED')) codes.push('AI_PROCESSING_NOT_ALLOWED');
  if (usage.automated_access.some(x => grant.automation[x] !== 'ALLOWED')) codes.push('AUTOMATION_NOT_ALLOWED');
  if (grant.attribution.required && (!grant.attribution.text || usage.attribution_text !== grant.attribution.text)) codes.push('ATTRIBUTION_REQUIRED');
  for (const node of tree.chain) {
    if (node.upstream_rights_status === 'BLOCKED') codes.push('SOURCE_BLOCKED');
    checkRestrictions(node.restrictions, 'UNRESOLVED_ASSET_RESTRICTIONS');
    if (node.denied_purposes.includes(usage.purpose)) codes.push('ASSET_PURPOSE_DENIED');
    if (!verified(node.hash_review, evaluationTime, node.file_sha256) || !node.original_sha256
      || (!node.parent_id && node.file_sha256 !== node.original_sha256)) codes.push('HASH_UNVERIFIED');
    for (const release of ['model', 'property'] as const) {
      if (node.third_party[release] === 'UNKNOWN') codes.push(`${release.toUpperCase()}_REQUIREMENT_UNKNOWN`);
      if (node.third_party[release] === 'REQUIRED' && !verified(grant.releases[release], evaluationTime, grant.releases[release].evidence_sha256)) codes.push(`${release.toUpperCase()}_RELEASE_REQUIRED`);
    }
    if (node.kind === 'audio') codes.push('AUDIO_RIGHTS_REVIEW_REQUIRED');
    if (node.kind === 'video' && node.audio_track !== 'NONE') codes.push('VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
  }
  return { status: codes.length ? 'BLOCKED' as const : 'ALLOWED' as const, codes: [...new Set(codes)].sort(), inherited_asset_ids };
}
export function evaluateSuitability(asset: MediaAsset, usage: MediaUsage, evaluationTime: string) {
  const codes: string[] = [];
  if (asset.inspection.status !== 'REVIEWED' || !verified(asset.inspection.review, evaluationTime, asset.file_sha256)) codes.push('NOT_INSPECTED');
  if (asset.inspection.quality !== 'PASS') codes.push('QUALITY_UNCONFIRMED');
  if (!asset.relevance.some(x => x.purpose === usage.purpose && x.scope_id === usage.scope_id
    && verified(x.review, evaluationTime, asset.file_sha256))) codes.push('RELEVANCE_UNCONFIRMED');
  if (usage.role === 'DOCUMENTARY' || usage.representation === 'BUSINESS_EVIDENCE') {
    const d = asset.documentary;
    if (usage.role !== 'DOCUMENTARY' || usage.representation !== 'BUSINESS_EVIDENCE' || !d
      || !verified(d.review, evaluationTime, asset.file_sha256) || d.business_id !== usage.business_id
      || d.scope_id !== usage.scope_id || !usage.subject_ids.length || usage.subject_ids.some(x => !d.subject_ids.includes(x))) codes.push('MISLEADING_BUSINESS_REPRESENTATION');
    if (usage.transformations.includes('AI_EDIT') || asset.transformations.includes('AI_EDIT')) codes.push('DOCUMENTARY_AI_EDIT_REQUIRES_REVIEW');
  } else if (!usage.generic_label) codes.push('GENERIC_DISCLOSURE_REQUIRED');
  return [...new Set(codes)].sort();
}
