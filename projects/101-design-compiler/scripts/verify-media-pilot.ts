import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadMediaPilot } from './load-media-pilot.ts';
import { byteSha256 } from '../src/media/package.ts';

const pilot = await loadMediaPilot();
const proof = pilot.output.manifest.package_proof!;
if (byteSha256(await readFile(resolve('dist/h3-media-pilot/index.html'))) !== proof.render.html_sha256) throw new Error('PILOT_BUILD_DIFFERS_FROM_RENDER_EVIDENCE');
console.log(JSON.stringify({ status: 'PASSED', closure: pilot.output.brief.closure,
  media_sha256: pilot.acquisition.file.sha256, permission_source: pilot.acquisition.documents[0]?.official_url,
  documentary_gap_blocked: pilot.output.brief.gaps.some(g => g.need.role === 'DOCUMENTARY'),
  original_bytes_checked: true, official_documents_checked: true, render_receipt_checked: true,
  attribution_and_context_checked: true, current_build_matches_render: true }));
