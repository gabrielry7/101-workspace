import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadMediaPilot } from './load-media-pilot.ts';
import { PackageProof } from '../src/media/contracts.ts';
import { byteSha256 } from '../src/media/package.ts';

const pilot = await loadMediaPilot({ unsealed: true });
const receipt = JSON.parse(await readFile(resolve('docs/evidence/h3-pilot/render-receipt.json'), 'utf8')) as { rendered_at: string };
const proof = PackageProof.parse({ id: 'usda-d255-19-authorized-pilot-package',
  client_id: pilot.context.client_id, project_id: pilot.context.project_id, evaluated_at: receipt.rendered_at,
  files: [{ asset_id: pilot.output.manifest.assets[0]!.id, path: pilot.acquisition.file.path, sha256: pilot.acquisition.file.sha256 }],
  documents: pilot.acquisition.documents,
  render: { page: '/h3-media-pilot/', html_path: 'docs/evidence/h3-pilot/render.html',
    html_sha256: byteSha256(await readFile(resolve('docs/evidence/h3-pilot/render.html'))),
    screenshot_path: 'docs/evidence/h3-pilot/render.png', screenshot_sha256: byteSha256(await readFile(resolve('docs/evidence/h3-pilot/render.png'))),
    receipt_path: 'docs/evidence/h3-pilot/render-receipt.json', receipt_sha256: byteSha256(await readFile(resolve('docs/evidence/h3-pilot/render-receipt.json'))),
    usage_ids: [pilot.output.manifest.usages[0]!.id] },
});
await writeFile(resolve('fixtures/media/pilot/package-proof.json'), JSON.stringify(proof, null, 2) + '\n');
const sealed = await loadMediaPilot();
console.log(JSON.stringify({ closure: sealed.output.brief.closure, gaps: sealed.output.brief.gaps.map(x => x.need.role),
  source: 'official USDA public-domain declaration + actual file hashes + local browser rendering', synthetic_permissions: false }));
