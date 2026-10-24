import { z } from 'zod';
import { SitePlanV1, BusinessInputV1 } from '../contracts/v1/schemas.ts';
import type { FixtureBundle } from '../contracts/v1/schemas.ts';
import { SiteRequirementsV1 } from '../planner/contracts.ts';
import { validateSemanticPlan } from '../planner/validate.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
import { MediaAssetV1, LicenseGrantV1, MediaUsageV1, MediaManifestV1, MediaBriefV1 } from './contracts.ts';
import type { MediaAsset, MediaNeed, MediaUsage, MediaManifest, ReviewRecord } from './contracts.ts';
import { rightsGate, evaluateSuitability, lineage } from './gate.ts';

export const unknownReview = (): ReviewRecord => ({ status: 'UNKNOWN', reference: null, reviewer: null, reviewed_at: null, evidence_sha256: null });
// Preserve upstream observations as provenance, never as a verified grant or inspection.
export function inventoryMedia(inputValue: unknown): MediaAsset[] {
  const input = BusinessInputV1.parse(inputValue);
  return input.existing_media.map(m => MediaAssetV1.parse({
    schema_version: '1.0.0', id: m.id, data_mode: input.data_mode === 'SYNTHETIC_FIXTURE' ? 'SYNTHETIC_FIXTURE' : 'REAL',
    kind: m.kind, uri: m.uri, source: m.source, external_id: m.id,
    audio_track: 'UNKNOWN', relevance: [],
    provenance: [{ source: m.source, reference: `${input.snapshot_id}:${m.id}`, recorded_at: input.as_of }],
    upstream_rights_status: m.rights_status, upstream_document_ids: m.rights_document_ids,
    original_id: m.id, parent_id: null, original_sha256: null, file_sha256: null,
    hash_review: unknownReview(), transformations: [], restrictions: m.restrictions, denied_purposes: [], documentary: null,
    inspection: { status: 'NOT_INSPECTED', review: unknownReview(), width: null, height: null,
      duration_seconds: null, codec: null, subject: null, quality: 'UNKNOWN',
      findings: [`Upstream scope: ${m.scope_id}; unverified dimensions: ${m.width ?? 'unknown'} x ${m.height ?? 'unknown'}`] },
    third_party: { model: 'UNKNOWN', property: 'UNKNOWN' },
  }));
}
export function generateMediaNeeds(planValue: unknown, requirementsValue: unknown): MediaNeed[] {
  const plan = SitePlanV1.parse(planValue), reqs = SiteRequirementsV1.parse(requirementsValue);
  if (plan.business_id !== reqs.business_id || plan.snapshot_id !== reqs.snapshot_id
    || plan.business_profile_id !== reqs.business_profile_id || plan.capability_profile_id !== reqs.capability_profile_id) throw new Error('MEDIA_PLAN_REQUIREMENTS_MISMATCH');
  const needs: MediaNeed[] = [];
  const ids = new Set<string>();
  for (const page of plan.pages) for (const module of page.modules) {
    if (ids.has(module.id)) throw new Error('DUPLICATE_MODULE'); ids.add(module.id);
    const req = reqs.requirements.find(x => x.id === module.id);
    if (!req || req.disposition !== 'INCLUDED' || req.scope_id !== module.scope_id || req.route !== page.path
      || req.capability_id !== module.capability_id) throw new Error('MEDIA_REQUIREMENT_BINDING_MISMATCH');
    if (req.semantic_module === 'external_action' || ['documents', 'contact_channels', 'opening_hours', 'social_profiles'].includes(req.capability_id)) continue;
    const subjects = module.offering_ids.length ? module.offering_ids : [module.scope_id];
    const documentary = ['offering_collection', 'schedule', 'location_information'].includes(req.semantic_module)
      || ['portfolio', 'case_studies', 'professional_profiles', 'trainer_profiles', 'branches'].includes(req.capability_id);
    const role = documentary ? 'DOCUMENTARY' as const : req.semantic_module === 'identity' ? 'ATMOSPHERIC' as const : 'ILLUSTRATIVE' as const;
    for (const subject of documentary ? subjects : [module.scope_id]) needs.push({
      id: `need-${inputSha256([module.id, role, subject]).slice(0, 24)}`, requirement_id: req.id,
      module_id: module.id, page: page.path, scope_id: module.scope_id,
      purpose: documentary ? `document:${req.capability_id}` : role === 'ATMOSPHERIC' ? 'generic:atmosphere' : `illustrate:${req.capability_id}`,
      role, subject_ids: documentary ? [subject] : [], kinds: ['image'], required: false, count: 1,
      min_width: null, min_height: null,
    });
  }
  for (const req of reqs.requirements.filter(x => x.capability_id === 'gallery' && x.source === 'UPSTREAM' && x.evidence_status === 'CONFIRMED_PRESENT')) {
    needs.push({ id: `need-${inputSha256([req.id, 'gallery']).slice(0, 24)}`, requirement_id: req.id,
      module_id: null, page: req.route, scope_id: req.scope_id, purpose: 'document:gallery', role: 'DOCUMENTARY',
      subject_ids: [req.scope_id], kinds: ['image', 'video'], required: req.required, count: 1, min_width: null, min_height: null });
  }
  return needs.sort((a, b) => a.id.localeCompare(b.id, 'en'));
}
function decide(manifest: MediaManifest, allowSynthetic: boolean) {
  return manifest.usages.map(usage => {
    const asset = manifest.assets.find(x => x.id === usage.asset_id), grant = manifest.grants.find(x => x.id === usage.grant_id);
    const gate = rightsGate(asset, grant, usage, manifest.assets, manifest.evaluated_at, { allow_synthetic: allowSynthetic });
    const suitability = asset ? evaluateSuitability(asset, usage, manifest.evaluated_at) : ['ASSET_MISSING'];
    const need = manifest.needs.find(x => x.id === usage.need_id);
    if (usage.business_id !== manifest.business_id || usage.client_id !== manifest.client_id || usage.project_id !== manifest.project_id) suitability.push('USAGE_CONTEXT_MISMATCH');
    if (!need || need.module_id === null || usage.module_id !== need.module_id || usage.scope_id !== need.scope_id || usage.page !== need.page
      || usage.role !== need.role || usage.purpose !== need.purpose || JSON.stringify(usage.subject_ids) !== JSON.stringify(need.subject_ids)) suitability.push('NEED_BINDING_MISMATCH');
    if (asset && need) {
      if (!need.kinds.includes(asset.kind)) suitability.push('MEDIA_KIND_MISMATCH');
      if ((need.min_width && (!asset.inspection.width || asset.inspection.width < need.min_width))
        || (need.min_height && (!asset.inspection.height || asset.inspection.height < need.min_height))) suitability.push('INSUFFICIENT_RESOLUTION');
      if (usage.role === 'DOCUMENTARY' && lineage(asset, manifest.assets).chain.some(x => x.transformations.includes('AI_EDIT'))) suitability.push('DOCUMENTARY_AI_EDIT_REQUIRES_REVIEW');
      // No geometry/crop inspection exists in H3. Do not claim quality for a hypothetical transformed file.
      if (usage.transformations.length) suitability.push('UNINSPECTED_TRANSFORMED_USAGE');
    }
    const suitability_codes = [...new Set(suitability)].sort();
    return { usage_id: usage.id, status: gate.status === 'ALLOWED' && !suitability_codes.length ? 'ALLOWED' as const : 'BLOCKED' as const,
      rights_codes: gate.codes, suitability_codes, inherited_asset_ids: gate.inherited_asset_ids };
  });
}
function briefFor(manifest: MediaManifest) {
  const brief = MediaBriefV1.parse({ schema_version: '1.0.0', site_plan_id: manifest.site_plan_id,
    manifest_sha256: inputSha256(manifest), evaluated_at: manifest.evaluated_at,
    gaps: manifest.needs.flatMap(need => {
      const usages = manifest.usages.filter(x => x.need_id === need.id);
      const allowed = new Set(usages.filter(x => manifest.decisions.find(d => d.usage_id === x.id)?.status === 'ALLOWED').map(x => x.asset_id));
      const missing = Math.max(0, need.count - allowed.size);
      if (!missing) return [];
      const reasons = [...new Set(usages.flatMap(x => {
        const d = manifest.decisions.find(d => d.usage_id === x.id); return d ? [...d.rights_codes, ...d.suitability_codes] : [];
      }))].sort();
      if (!reasons.length) reasons.push(need.module_id === null ? 'SEMANTIC_MODULE_DEFERRED' : 'NO_AUTHORIZED_CANDIDATE');
      return [{ need, missing_count: missing, reasons,
        requested_from: reasons.some(x => /RIGHTS|GRANT|LICENSE|ALLOWED|RELEASE|ATTRIBUTION/.test(x)) ? 'rights_review' as const
          : reasons.some(x => /INSPECT|QUALITY|HASH/.test(x)) ? 'inspection' as const
          : need.role === 'DOCUMENTARY' ? 'upstream_or_commission' as const : 'licensed_provider' as const }];
    }),
    constraints: ['GENERIC_MEDIA_IS_NOT_BUSINESS_EVIDENCE', 'NO_PROVIDER_AUTOMATION_AUTHORIZED', 'NO_VISUAL_INSPECTION_IMPLIED_WITHOUT_FILE_REVIEW', 'NO_AUDIO_WITHOUT_SEPARATE_RIGHTS_REVIEW'],
    closure: 'PENDING_AUTHORIZED_MEDIA_PACKAGE',
  });
  const proof = manifest.package_proof;
  // Proof is an externally checked receipt. Consumers must also call verifyPackageFiles;
  // a VERIFIED claim or a REAL label alone never closes the milestone.
  if (proof && proof.client_id === manifest.client_id && proof.project_id === manifest.project_id
    && proof.evaluated_at === manifest.evaluated_at && !brief.gaps.some(x => x.need.required)
    && proof.files.every(f => manifest.assets.some(a => a.id === f.asset_id && a.data_mode === 'REAL' && a.file_sha256 === f.sha256))
    && proof.render.usage_ids.every(id => {
      const usage = manifest.usages.find(u => u.id === id), asset = manifest.assets.find(a => a.id === usage?.asset_id);
      const grant = manifest.grants.find(g => g.id === usage?.grant_id);
      return manifest.decisions.find(d => d.usage_id === id)?.status === 'ALLOWED' && asset?.data_mode === 'REAL'
        && grant?.data_mode === 'REAL' && proof.files.some(f => f.asset_id === asset.id)
        && proof.documents.some(d => d.path === grant.document.reference && d.sha256 === grant.document.sha256);
    })) brief.closure = brief.gaps.length ? 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS' : 'AUTHORIZED_PILOT_PACKAGE';
  return brief;
}
export type MediaContext = { client_id: string; project_id: string; evaluated_at: string; allow_synthetic?: boolean; package_proof?: MediaManifest['package_proof'] };
export function buildMediaManifest(bundle: FixtureBundle, requirements: unknown,
  inventory: { assets: unknown[]; grants: unknown[]; usages: unknown[] }, context: MediaContext) {
  const validation = validateSemanticPlan(bundle, requirements);
  if (!validation.success) throw new Error(`SEMANTIC_PLAN_INVALID:${JSON.stringify(validation.diagnostics)}`);
  const reqs = SiteRequirementsV1.parse(requirements);
  if (Date.parse(context.evaluated_at) < Date.parse(reqs.evaluated_at)) throw new Error('MEDIA_EVALUATION_BEFORE_PLAN');
  const assets = z.array(MediaAssetV1).parse(inventory.assets), grants = z.array(LicenseGrantV1).parse(inventory.grants), usages = z.array(MediaUsageV1).parse(inventory.usages);
  for (const items of [assets, grants, usages]) if (new Set(items.map(x => x.id)).size !== items.length) throw new Error('DUPLICATE_MEDIA_ID');
  if (bundle.input.data_mode !== 'SYNTHETIC_FIXTURE' && [...assets, ...grants].some(x => x.data_mode === 'SYNTHETIC_FIXTURE')) throw new Error('SYNTHETIC_MEDIA_IN_REAL_PROJECT');
  const manifest = MediaManifestV1.parse({ schema_version: '1.0.0', business_id: bundle.input.business_id,
    snapshot_id: bundle.input.snapshot_id, site_plan_id: bundle.plan.id, client_id: context.client_id, project_id: context.project_id,
    evaluated_at: context.evaluated_at, plan_sha256: inputSha256(bundle.plan), requirements_sha256: inputSha256(reqs), input_sha256: inputSha256(bundle.input),
    assets, grants, usages, needs: generateMediaNeeds(bundle.plan, reqs), decisions: [] });
  if (context.package_proof) manifest.package_proof = context.package_proof;
  manifest.decisions = decide(manifest, context.allow_synthetic === true);
  return { manifest, brief: briefFor(manifest) };
}
// Consumer validation recomputes the decision ledger and brief, including gaps.
export function validateMediaManifest(manifestValue: unknown, briefValue: unknown, bundle: FixtureBundle, requirements: unknown, context: MediaContext) {
  try {
    const manifest = MediaManifestV1.parse(manifestValue), brief = MediaBriefV1.parse(briefValue);
    const expected = buildMediaManifest(bundle, requirements, manifest, context);
    const codes: string[] = [];
    if (inputSha256(manifest) !== inputSha256(expected.manifest)) codes.push('MANIFEST_MISMATCH');
    if (inputSha256(brief) !== inputSha256(expected.brief)) codes.push('BRIEF_MISMATCH');
    return { success: !codes.length, codes };
  } catch (error) { return { success: false, codes: ['MEDIA_VALIDATION_FAILED'], message: String(error) }; }
}
export function proposeUsage(need: MediaNeed, asset: MediaAsset, context: MediaContext & { business_id: string }, grantId: string | null): MediaUsage {
  return MediaUsageV1.parse({ schema_version: '1.0.0', id: `usage-${inputSha256([need.id, asset.id]).slice(0, 24)}`,
    need_id: need.id, asset_id: asset.id, grant_id: grantId, client_id: context.client_id, project_id: context.project_id,
    business_id: context.business_id, scope_id: need.scope_id, page: need.page, module_id: need.module_id ?? 'DEFERRED',
    purpose: need.purpose, role: need.role, subject_ids: need.subject_ids,
    representation: need.role === 'DOCUMENTARY' ? 'BUSINESS_EVIDENCE' : 'GENERIC_CONTEXT',
    transformations: [], territory: 'CO', attribution_text: null,
    generic_label: need.role === 'DOCUMENTARY' ? null : 'Imagen ilustrativa; no documenta este negocio.',
    ai_operations: [], automated_access: [],
  });
}
