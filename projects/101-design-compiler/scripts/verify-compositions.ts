import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadCompositionLab } from './load-composition-lab.ts';
import { compositionBindings } from './composition-bindings.ts';
import { compositions, previewPath, type CompositionId } from '../src/composition/registry.ts';
import { auditRender } from '../src/composition/audit.ts';
import type { observePage } from '../src/composition/observe.ts';
import { byteSha256 } from '../src/media/package.ts';

export async function verifyCompositions() {
  const lab=await loadCompositionLab();
  const bindings=JSON.stringify(await compositionBindings(),null,2)+'\n';
  if(await readFile('data/derived/composition-v1/restaurante-bindings.json','utf8')!==bindings)throw new Error('COMPOSITION_BINDINGS_NOT_REPRODUCIBLE');
  const audit=JSON.parse(await readFile('docs/evidence/h4/browser-audit.json','utf8')) as {
    status:string;browser:string;content_sha256:string;plan_sha256:string;manifest_sha256:string;
    receipts:(ReturnType<typeof observePage>&{label:string;status:string;codes:string[];variant:CompositionId;semantic_page:string;route:string;
      viewport:{id:string;width:number;height:number};html_sha256:string;styles:{path:string;sha256:string}[];
      screenshot_path:string;screenshot_sha256:string;original_sha256:string|null;keyboard:{local_navigation:boolean;skip_target:boolean;skip:{focused:boolean};disclosure:{open:boolean;diagnostics:boolean}}})[];
    stress:{variant:string;status:string;geometry:{document_width:number;overflow:unknown[]};width:number;text_scale:number}[];
  };
  if(audit.status!=='PASSED'||!audit.browser||audit.content_sha256!==lab.content.content_sha256||audit.plan_sha256!==lab.content.plan_sha256||audit.manifest_sha256!==lab.manifest_sha256)throw new Error('COMPOSITION_RECEIPT_INVALID');
  const expected=compositions.flatMap(c=>['desktop','mobile'].flatMap(size=>lab.content.pages.map(p=>`${c.id}:${size}:${p.path}`))).sort();
  if(JSON.stringify(audit.receipts.map(r=>`${r.variant}:${r.viewport.id}:${r.semantic_page}`).sort())!==JSON.stringify(expected))throw new Error('COMPOSITION_VIEW_MISSING_OR_DUPLICATED');
  for(const r of audit.receipts){
    if(r.status!=='PASSED'||r.codes.length||!auditRender(r.observation,lab,r.variant,r.semantic_page).success
      ||r.route!==previewPath(r.variant,r.semantic_page)||r.geometry.overflow.length||r.geometry.document_width>r.viewport.width
      ||r.readability.some(t=>t.contrast<4.5||t.font_px<12)||r.animated_elements||!r.reduced_motion||r.resources.some(x=>!x.local)
      ||!r.keyboard.local_navigation||!r.keyboard.skip_target||!r.keyboard.skip.focused||!r.keyboard.disclosure.open||!r.keyboard.disclosure.diagnostics)throw new Error(`COMPOSITION_OBSERVED_FAILURE:${r.label}`);
    if(byteSha256(await readFile(resolve('dist',`.${r.route}index.html`)))!==r.html_sha256)throw new Error(`COMPOSITION_BUILD_DRIFT:${r.label}`);
    for(const css of r.styles)if(byteSha256(await readFile(resolve('dist',`.${css.path}`)))!==css.sha256)throw new Error('COMPOSITION_STYLE_DRIFT');
    if(byteSha256(await readFile(r.screenshot_path))!==r.screenshot_sha256)throw new Error('COMPOSITION_SCREENSHOT_DRIFT');
    if(r.original_sha256!==(r.semantic_page===lab.media.usage.page?lab.media.asset.file_sha256:null))throw new Error('COMPOSITION_ORIGINAL_MISMATCH');
  }
  if(audit.stress.length!==3||new Set(audit.stress.map(s=>s.variant)).size!==3||audit.stress.some(s=>s.status!=='PASSED'||s.width!==320||s.text_scale!==2||s.geometry.document_width>320||s.geometry.overflow.length))throw new Error('COMPOSITION_TEXT_STRESS_FAILURE');
  return {status:'PASSED',views:audit.receipts.length,primary_views:6,bindings_preserved:true,media_preserved:true,original_sha256:lab.media.asset.file_sha256,plan_sha256:lab.content.plan_sha256,content_sha256:lab.content.content_sha256};
}
if(process.argv[1]?.endsWith('verify-compositions.ts'))console.log(JSON.stringify(await verifyCompositions()));
