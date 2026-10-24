import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { z } from 'zod';
import restaurante from '../data/derived/planner-v1/restaurante.json' with { type: 'json' };
import { BusinessInputV1, BusinessProfileV1, CapabilityProfileV1, SitePlanV1 } from '../src/contracts/v1/schemas.ts';
import { SiteRequirementsV1 } from '../src/planner/contracts.ts';
import { MediaAssetV1, LicenseGrantV1, MediaUsageV1, PackageProof } from '../src/media/contracts.ts';
import { buildMediaManifest, validateMediaManifest } from '../src/media/plan.ts';
import { readPackageFile, byteSha256, verifyPackageFiles } from '../src/media/package.ts';

export async function loadMediaPilot(options: { unsealed?: boolean } = {}) {
  const acquisition = JSON.parse(await readFile(resolve('fixtures/media/pilot/acquisition.json'), 'utf8')) as {
    reviewed_at: string; review_path: string; review_sha256: string;
    file: { path: string; source_url: string; sha256: string; bytes: number; width: number; height: number };
    documents: { path: string; official_url: string; sha256: string; version: string }[];
  };
  const inventory = z.strictObject({ assets: z.array(MediaAssetV1), grants: z.array(LicenseGrantV1), usages: z.array(MediaUsageV1) }).parse(
    JSON.parse(await readFile(resolve('fixtures/media/pilot/reviewed-inventory.json'), 'utf8')));
  const bytes = await readPackageFile(acquisition.file.path);
  if (bytes.length !== acquisition.file.bytes || byteSha256(bytes) !== acquisition.file.sha256) throw new Error('PILOT_ORIGINAL_HASH_MISMATCH');
  if (byteSha256(await readPackageFile(acquisition.review_path)) !== acquisition.review_sha256) throw new Error('PILOT_REVIEW_HASH_MISMATCH');
  const sourceTexts: string[] = [];
  for (const document of acquisition.documents) {
    const body = await readPackageFile(document.path);
    if (new URL(document.official_url).hostname !== 'www.ars.usda.gov' || byteSha256(body) !== document.sha256) throw new Error('PILOT_OFFICIAL_DOCUMENT_MISMATCH');
    sourceTexts.push(body.toString('utf8'));
  }
  // The source's assertion, download link and author must exist in the actual archived bytes.
  // These checks corroborate the reviewed evidence; they are not a generic legal-text parser.
  if (!sourceTexts[0]?.includes('Copyright free, public domain image') || !sourceTexts[0]?.includes('Photo by Steve Ausmus, USDA/ARS')
    || !sourceTexts[0]?.includes(new URL(acquisition.file.source_url).pathname)
    || !sourceTexts[1]?.includes('copyright-free, public domain') || !sourceTexts[1]?.includes('infer or imply ARS endorsement')) throw new Error('PILOT_PERMISSION_SOURCE_MISSING');
  const asset = inventory.assets[0]!, grant = inventory.grants[0]!;
  if (inventory.assets.length !== 1 || asset.data_mode !== 'REAL' || asset.documentary !== null || asset.file_sha256 !== acquisition.file.sha256
    || asset.inspection.width !== acquisition.file.width || asset.inspection.height !== acquisition.file.height
    || grant.document.reference !== acquisition.documents[0]?.path || grant.document.sha256 !== acquisition.documents[0]?.sha256
    || !asset.restrictions.includes('NO_PROVIDER_ENDORSEMENT') || !grant.restrictions.includes('NO_PROVIDER_ENDORSEMENT')) throw new Error('PILOT_REVIEWED_INVENTORY_MISMATCH');
  if (restaurante.status !== 'READY') throw new Error('PILOT_SEMANTIC_PLAN_BLOCKED');
  const bundle = { input: BusinessInputV1.parse(restaurante.input), profile: BusinessProfileV1.parse(restaurante.profile),
    capabilities: CapabilityProfileV1.parse(restaurante.capabilities), plan: SitePlanV1.parse(restaurante.plan) };
  const requirements = SiteRequirementsV1.parse(restaurante.requirements);
  const proof = options.unsealed ? undefined : PackageProof.parse(JSON.parse(await readFile(resolve('fixtures/media/pilot/package-proof.json'), 'utf8')));
  const context = { client_id: '101-design-compiler-fixture-review', project_id: 'h3-restaurante-media-pilot',
    evaluated_at: proof?.evaluated_at ?? acquisition.reviewed_at, ...(proof ? { package_proof: proof } : {}) };
  const output = buildMediaManifest(bundle, requirements, inventory, context);
  const validation = validateMediaManifest(output.manifest, output.brief, bundle, requirements, context);
  if (!validation.success || output.manifest.decisions[0]?.status !== 'ALLOWED') throw new Error(`PILOT_USAGE_BLOCKED:${JSON.stringify(output.manifest.decisions)}`);
  if (proof) {
    const checked = await verifyPackageFiles(proof, output.manifest);
    if (!checked.success) throw new Error(`PILOT_PACKAGE_NOT_VERIFIED:${JSON.stringify(checked.codes)}`);
    if (output.brief.closure !== 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS') throw new Error('PILOT_CLOSURE_INCORRECT');
  }
  return { output, acquisition, inventory, context, bundle, requirements };
}
