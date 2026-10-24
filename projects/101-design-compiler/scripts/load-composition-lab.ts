import { loadMediaPilot } from './load-media-pilot.ts';
import { projectContent } from '../src/composition/content.ts';
import { rightsGate, evaluateSuitability } from '../src/media/gate.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';

// Same H3 client/project and semantic page; /h4 prefixes are local preview mounts.
// Never extend the grant, change a role, or attach media to another module/page.
export async function loadCompositionLab() {
  const pilot = await loadMediaPilot();
  const content = projectContent(pilot.bundle, pilot.requirements);
  const manifest = pilot.output.manifest;
  const usage = manifest.usages[0]!, asset = manifest.assets.find(a => a.id === usage.asset_id)!, grant = manifest.grants.find(g => g.id === usage.grant_id)!;
  if (rightsGate(asset, grant, usage, manifest.assets, manifest.evaluated_at).status !== 'ALLOWED'
    || evaluateSuitability(asset, usage, manifest.evaluated_at).length || usage.role !== 'ATMOSPHERIC'
    || usage.transformations.length || !content.pages.some(p => p.path === usage.page && p.modules.some(m => m.id === usage.module_id))) throw new Error('COMPOSITION_MEDIA_NOT_AUTHORIZED');
  return { content, media: { asset, usage, grant }, gaps: pilot.output.brief.gaps,
    constraints: pilot.output.brief.constraints, manifest_sha256: inputSha256(manifest),
    client_id: manifest.client_id, project_id: manifest.project_id, evaluated_at: manifest.evaluated_at };
}
export type CompositionLab = Awaited<ReturnType<typeof loadCompositionLab>>;
