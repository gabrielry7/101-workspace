import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadDesignLab } from './load-design-lab.ts';
import { byteSha256 } from '../src/media/package.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { designPreviewPath, validateDesign } from '../src/design/search.ts';
import { auditRender } from '../src/composition/audit.ts';
const {lab,result,provenance}=await loadDesignLab();
const report=JSON.parse(await readFile('docs/evidence/h5/browser-audit.json','utf8'));
if(report.status!=='PASSED'||report.errors.length||report.search_sha256!==inputSha256(result)||report.provenance_sha256!==inputSha256(provenance)||report.context_sha256!==result.context_sha256)throw new Error('H5_REPORT_MISMATCH');
const labels=new Set<string>();
for(const receipt of report.receipts) {
 const plan=result.finalists.find(p=>p.id===receipt.design_id);
 if(!plan||labels.has(receipt.label)||receipt.design_sha256!==inputSha256(plan)||receipt.status!=='PASSED'||receipt.codes.length)throw new Error('H5_RECEIPT_INVALID');
 labels.add(receipt.label);
 const page=plan.pages.find(p=>p.path===receipt.semantic_page);
 if(!page||receipt.route!==designPreviewPath(plan.id,page.path)||!validateDesign(plan,lab).success
  ||!auditRender(receipt.observation,lab,'editorial',page.path,p=>designPreviewPath(plan.id,p)).success)throw new Error('H5_BINDING_INVALID');
 if(byteSha256(await readFile(resolve('dist',`.${receipt.route}index.html`)))!==receipt.html_sha256)throw new Error('H5_STALE_HTML');
 if(byteSha256(await readFile(receipt.screenshot_path))!==receipt.screenshot_sha256)throw new Error('H5_STALE_SCREENSHOT');
 // H5 grammar is fixed, inline CSS; HTML hash also pins it. External Foundation CSS, if any, is pinned separately.
 for(const style of receipt.styles)if(byteSha256(await readFile(resolve('dist',`.${style.path}`)))!==style.sha256)throw new Error('H5_STALE_CSS');
}
const expected=result.finalists.flatMap(p=>p.pages.flatMap(page=>['desktop','mobile'].map(view=>`${p.id}-${view}${page.path==='/'?'':'-offering'}`)));
if(JSON.stringify([...labels].sort())!==JSON.stringify(expected.sort())||report.stress.length!==result.finalists.length*7||report.stress.some((s:any)=>s.status!=='PASSED'||s.codes.length))throw new Error('H5_VIEW_COVERAGE');
console.log(`H5 PASSED lab: ${report.receipts.length} browser views, ${report.stress.length} responsive/text stress views; current HTML/CSS/PNG, bindings, rights and frozen search hashes valid.`);
