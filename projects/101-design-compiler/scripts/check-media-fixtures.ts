import { checkPlannerFixtures } from './check-planner-fixtures.ts';
import { buildMediaManifest, inventoryMedia, generateMediaNeeds, proposeUsage, validateMediaManifest } from '../src/media/plan.ts';
import { permissionFixture, cutoff } from '../fixtures/media/v1/permissions.ts';
import { loadMediaPilot } from './load-media-pilot.ts';

export async function checkMediaFixtures() {
  const results = [];
  for (const fixture of await checkPlannerFixtures()) {
    const result = fixture.result;
    if (result.status !== 'READY') continue; // No fabricated plan for blocked businesses.
    const bundle = { input: result.input, profile: result.profile, capabilities: result.capabilities, plan: result.plan };
    const context = { client_id: 'synthetic-client', project_id: 'synthetic-project', evaluated_at: cutoff };
    const inventory = { assets: inventoryMedia(result.input), grants: [], usages: [] };
    const output = buildMediaManifest(bundle, result.requirements, inventory, context);
    const validation = validateMediaManifest(output.manifest, output.brief, bundle, result.requirements, context);
    results.push({ scenario: fixture.scenario, output, success: validation.success, codes: validation.codes });
    if (fixture.scenario === 'restaurante') {
      const need = generateMediaNeeds(result.plan, result.requirements).find(x => x.role === 'DOCUMENTARY')!;
      const { asset, grant } = permissionFixture(need, result.input.business_id);
      const usage = proposeUsage(need, asset, { ...context, business_id: result.input.business_id }, grant.id);
      const controlled = buildMediaManifest(bundle, result.requirements, { assets: [asset], grants: [grant], usages: [usage] }, { ...context, allow_synthetic: true });
      const valid = validateMediaManifest(controlled.manifest, controlled.brief, bundle, result.requirements, { ...context, allow_synthetic: true });
      results.push({ scenario: 'synthetic-permission-control', output: controlled,
        success: valid.success && controlled.manifest.decisions[0]?.status === 'ALLOWED', codes: valid.codes });
      const blocked = buildMediaManifest(bundle, result.requirements, { assets: [asset], grants: [grant], usages: [usage] }, context);
      results.push({ scenario: 'synthetic-permission-default-blocked', output: blocked,
        success: blocked.manifest.decisions[0]?.status === 'BLOCKED', codes: blocked.manifest.decisions[0]?.rights_codes ?? [] });
    }
  }
  const pilot = await loadMediaPilot();
  results.push({ scenario: 'real-restaurante-pilot', output: pilot.output,
    success: pilot.output.brief.closure === 'AUTHORIZED_PILOT_PACKAGE_WITH_GAPS', codes: [] });
  return results;
}
