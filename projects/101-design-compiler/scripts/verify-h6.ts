import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadAuditLab } from './load-audit-lab.ts';
import { auditCandidate,chooseAcceptable } from '../src/audit/evaluate.ts';
import { judgeMutation } from '../src/audit/mutate.ts';
import { decodeScreenshot } from '../src/audit/png.ts';
import { measurePixels } from '../src/audit/raster.ts';
import { byteSha256 } from '../src/media/package.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { loadComparisons } from './load-comparisons.ts';
const state=await loadAuditLab(),run=JSON.parse(await readFile('docs/evidence/h6/run.json','utf8'));
if(run.status!=='PASSED'||run.errors.length||run.context_sha256!==state.result.context_sha256||JSON.stringify(run.policy)!==JSON.stringify(state.policy)||JSON.stringify(run.commercial_policy)!==JSON.stringify(state.commercial_policy))throw new Error('H6_RUN_CONTEXT');
const labels=new Set<string>();
for(const r of run.receipts){
 if(labels.has(r.label))throw new Error('H6_DUPLICATE_VIEW');labels.add(r.label);
 const mount=state.mounts.find(m=>m.id===r.mount_id);if(!mount||r.candidate_sha256!==inputSha256(mount.candidate)||r.candidate_sha256!==inputSha256(r.candidate))throw new Error('H6_CANDIDATE_DRIFT');
 if(inputSha256(auditCandidate(mount.candidate,state.lab,r.view,state.policy))!==inputSha256(r.audit)
  ||inputSha256(auditCandidate(mount.candidate,state.lab,r.view,state.commercial_policy))!==inputSha256(r.commercial_audit))throw new Error('H6_AUDIT_REPLAY');
 if(byteSha256(await readFile(resolve('dist',`.${r.view.route}index.html`)))!==r.html_sha256)throw new Error('H6_STALE_HTML');
 for(const css of r.styles)if(byteSha256(await readFile(resolve('dist',`.${css.path}`)))!==css.sha256)throw new Error('H6_STALE_CSS');
 const png=await readFile(r.view.screenshot_path);if(byteSha256(png)!==r.screenshot_sha256)throw new Error('H6_PNG_HASH');
 const decoded=decodeScreenshot(png),raster=measurePixels(decoded.pixels,decoded.width,decoded.height,r.view.geometry.image);
 if(JSON.stringify(raster)!==JSON.stringify(r.view.raster))throw new Error('H6_RASTER_REPLAY');
}
if(run.receipts.length!==27||run.receipts.filter((r:any)=>r.kind==='FINALIST').length!==16||run.receipts.filter((r:any)=>r.seeded_fault).length!==3)throw new Error('H6_VIEW_COVERAGE');
for(const h of run.history){
 if(inputSha256(judgeMutation(h.before,h.after,h.before_reports,h.after_reports,h.evidence))!==inputSha256(h))throw new Error('H6_MUTATION_REPLAY');
}
const restored=run.receipts.filter((r:any)=>r.mount_id==='rollback-restored');
if(!run.rollback_verified||run.history[0].decision!=='KEEP_REPAIR'||run.history[1].decision!=='ROLLBACK'||restored.some((r:any)=>r.candidate_sha256!==run.history[1].kept_sha256||r.audit.status!=='LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW'))throw new Error('H6_ROLLBACK');
const entries=state.mounts.filter(m=>m.kind==='FINALIST').map(m=>({candidate:m.candidate,reports:run.receipts.filter((r:any)=>r.mount_id===m.id&&!r.seeded_fault).map((r:any)=>r.audit)}));
if(inputSha256(chooseAcceptable(entries))!==inputSha256(run.selection)||run.all_failed_selection.status!=='NO_ACCEPTABLE_DESIGN'||run.commercial_selection.status!=='NO_ACCEPTABLE_DESIGN')throw new Error('H6_SELECTION');
const blocked=chooseAcceptable(run.receipts.filter((r:any)=>r.seeded_fault||r.mount_id==='repair-before').map((r:any)=>({candidate:r.candidate,reports:[r.audit]})));
const commercial=chooseAcceptable(state.mounts.filter(m=>m.kind==='FINALIST').map(m=>({candidate:m.candidate,reports:run.receipts.filter((r:any)=>r.mount_id===m.id&&!r.seeded_fault).map((r:any)=>r.commercial_audit)})));
if(inputSha256(blocked)!==inputSha256(run.all_failed_selection)||inputSha256(commercial)!==inputSha256(run.commercial_selection))throw new Error('H6_BLOCKED_SELECTION_REPLAY');
const {ready,pairs}=await loadComparisons(),panel=JSON.parse(await readFile('docs/evidence/h6/panel-audit.json','utf8'));
if(!ready||pairs.length!==24||panel.status!=='PASSED'||panel.errors.length||panel.pairs_sha256!==inputSha256(pairs)||panel.human_votes!=='NOT_COLLECTED'||panel.network_writes!==0)throw new Error('H6_PANEL_CONTEXT');
for(const p of pairs){const html=await readFile(resolve('dist',`.${p.route}index.html`),'utf8');if(!html.includes(JSON.stringify(p).replace(/</g,'\\u003c')))throw new Error('H6_PANEL_METADATA_DRIFT');}
for(const p of panel.receipts){
 if(byteSha256(await readFile(resolve('dist',`.${p.route}index.html`)))!==p.html_sha256||byteSha256(await readFile(p.screenshot_path))!==p.screenshot_sha256||!p.reset_to_not_collected||p.choices.some((c:any)=>c.source!=='TEST_SIMULATION'||!c.downloadable))throw new Error('H6_PANEL_ARTIFACT_DRIFT');
}
console.log('H6 PASSED laboratory: 27 view receipts; PNG pixels independently decoded/recomputed; current HTML/CSS, gate/mutation/rollback replay, four diverse finalists. Commercial profile blocked; human votes NOT_COLLECTED.');
