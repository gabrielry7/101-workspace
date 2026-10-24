import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadAuditLab } from '../scripts/load-audit-lab.ts';
import { auditCandidate,chooseAcceptable } from '../src/audit/evaluate.ts';
import { AuditReportV1,MutationV1,PreferenceV1 } from '../src/audit/contracts.ts';
import { judgeMutation,mutate,proposeRepair } from '../src/audit/mutate.ts';
import { decodeScreenshot } from '../src/audit/png.ts';
import { measurePixels } from '../src/audit/raster.ts';
import { validatePreference } from '../src/audit/preference.ts';
import { loadComparisons } from '../scripts/load-comparisons.ts';
const state=await loadAuditLab(),run=JSON.parse(await readFile('docs/evidence/h6/run.json','utf8'));
test('nine-family audit gates actual DOM and reports objective instrument vs uncollected human preference separately',()=>{
 const baseline=run.receipts.filter((r:any)=>r.kind==='FINALIST');assert.equal(baseline.length,16);
 for(const r of baseline){assert.ok(AuditReportV1.safeParse(r.audit).success);assert.equal(r.audit.families.length,9);assert.equal(r.audit.status,'LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW');assert.equal(r.audit.production_ready,false);assert.equal(r.audit.human_preference,'NOT_COLLECTED');assert.equal(r.audit.families.find((f:any)=>f.family==='visual').status,'NOT_MEASURED');}
});
test('real seeded overflow, altered fact, credit loss and contrast each produce localized blocking issues',()=>{
 for(const [mount,code] of [['repair-before','OVERFLOW'],['seed-truth','RENDER_BINDING_LOSS_OR_INVENTION'],['seed-rights','MEDIA_BINDING_OR_PRESENTATION_INVALID'],['seed-contrast','CONTRAST_OR_TEXT']]){
  const r=run.receipts.find((r:any)=>r.mount_id===mount||r.label.includes(mount));assert.equal(r.audit.status,'FAIL');
  const issue=r.audit.issues.find((i:any)=>i.code===code);assert.ok(issue);assert.equal(issue.severity,'BLOCKING');assert.ok(issue.route&&issue.selector&&issue.evidence_ref&&issue.observation);
 }
});
test('permission UNKNOWN fails independently and cannot be offset by favorable raster statistics',()=>{
 const r=run.receipts[0],lab=structuredClone(state.lab);lab.media.grant.commercial_web='UNKNOWN';
 const audit=auditCandidate(r.candidate,lab,r.view,state.policy);assert.equal(audit.status,'FAIL');assert.ok(audit.issues.some(i=>i.family==='rights'&&i.severity==='BLOCKING'));
});
test('oversized original photo is an explicit lab exception and fails commercial byte policy',()=>{
 const r=run.receipts[0];assert.equal(r.audit.families.find((f:any)=>f.family==='performance').status,'LAB_EXCEPTION');assert.equal(r.commercial_audit.status,'FAIL');assert.ok(r.commercial_audit.issues.some((i:any)=>i.code==='BYTE_BUDGET'));assert.equal(run.commercial_selection.status,'NO_ACCEPTABLE_DESIGN');
});
test('critic repair is bounded to layout and real rerender removes overflow while preserving all semantic/media refs',()=>{
 const h=run.history[0];assert.equal(h.decision,'KEEP_REPAIR');assert.equal(h.blocking_before,2);assert.equal(h.blocking_after,0);
 assert.deepEqual(h.before.plan,h.after.plan);assert.deepEqual(h.after,mutate(h.before,proposeRepair(h.before_reports[0])));
 assert.equal(h.after.layout.measure,'fluid');assert.ok(h.evidence.before.length&&h.evidence.after.length);
});
test('worse mutation restores exact previous artifact/hash and browser result, not only a rollback label',()=>{
 const h=run.history[1];assert.equal(h.decision,'ROLLBACK');assert.equal(h.kept_sha256,h.before_sha256);assert.deepEqual(h.kept,h.before);assert.equal(run.rollback_verified,true);
 for(const r of run.receipts.filter((r:any)=>r.mount_id==='rollback-restored')){assert.equal(r.candidate_sha256,h.before_sha256);assert.equal(r.audit.status,'LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW');}
});
test('mutation rejects mismatched viewport/route coverage, duplicate views, stale hashes and changed policy',()=>{
 const h=run.history[0];
 for(const change of [(r:any)=>r[0].viewport.width=768,(r:any)=>r[0].semantic_page='/other',(r:any)=>r[1]=structuredClone(r[0]),(r:any)=>r[0].candidate_sha256='0'.repeat(64),(r:any)=>r[0].policy_sha256='0'.repeat(64)]){
  const after=structuredClone(h.after_reports);change(after);assert.throws(()=>judgeMutation(h.before,h.after,h.before_reports,after,h.evidence));
 }
});
test('same fault code in a new location cannot hide behind a lower global count',()=>{
 const h=run.history[0],before=structuredClone(h.before_reports),after=structuredClone(h.after_reports);
 before[1].issues=[];before[0].issues.push({...before[0].issues[0],id:'second-fault',code:'SECOND_FAULT'});
 after[1].issues=[{...before[0].issues[0],route:after[1].route,viewport:after[1].viewport}];
 assert.equal(judgeMutation(h.before,h.after,before,after,h.evidence).decision,'ROLLBACK');
});
test('mutator rejects arbitrary CSS/code, factual and license edits; no repair exists for hard rights failure',()=>{
 for(const patch of [{css:'body{}'},{module_refs:[]},{grant:'allow'}])assert.ok(!MutationV1.safeParse({schema_version:'1.0.0',id:'bad',reason_issue_id:'x',patch}).success);
 const r=run.receipts.find((r:any)=>r.seeded_fault==='rights');assert.equal(proposeRepair(r.audit),null);
});
test('missing coverage or no valid design emits NO_ACCEPTABLE_DESIGN; cosmetics do not create a new finalist',()=>{
 assert.equal(chooseAcceptable([]).status,'NO_ACCEPTABLE_DESIGN');assert.equal(run.all_failed_selection.status,'NO_ACCEPTABLE_DESIGN');
 const m=state.mounts[0]!,reports=run.receipts.filter((r:any)=>r.mount_id===m.id&&!r.seeded_fault).map((r:any)=>r.audit);
 assert.equal(chooseAcceptable([{candidate:m.candidate,reports:reports.slice(0,1)}]).status,'NO_ACCEPTABLE_DESIGN');assert.equal(chooseAcceptable([{candidate:m.candidate,reports},{candidate:m.candidate,reports}]).finalists.length,1);
});
test('raster recomputes actual screenshot pixels and masks original photograph; unsupported formats fail',async()=>{
 const r=run.receipts[0],png=await readFile(r.view.screenshot_path),d=decodeScreenshot(png),metrics=measurePixels(d.pixels,d.width,d.height,r.view.geometry.image);
 assert.deepEqual(metrics,r.view.raster);assert.ok(metrics.sampled_pixels>1000);assert.ok(metrics.ignored_media_pixels>0);assert.ok(metrics.entropy_bits>0);assert.throws(()=>decodeScreenshot(new Uint8Array([0,1,2])),/PNG/);
 const white=new Uint8Array(4*16).fill(255),black=new Uint8Array(4*16);assert.notEqual(measurePixels(white,4,4,null).ink_ratio,measurePixels(black,4,4,null).ink_ratio);
});
test('pair ordering, snapshot hashes and route/viewport are recorded without manufacturing a human preference',async()=>{
 const {pairs}=await loadComparisons();assert.equal(pairs.length,24);assert.equal(new Set(pairs.map(p=>p.id)).size,24);assert.ok(pairs.every(p=>p.human_preference==='NOT_COLLECTED'&&p.left_id!==p.right_id));
 const p=pairs[0];const record={schema_version:'1.0.0',source:'TEST_SIMULATION',comparison_id:p.id,context_sha256:p.context_sha256,left_id:p.left_id,right_id:p.right_id,left_sha256:p.left_sha256,right_sha256:p.right_sha256,left_screenshot_sha256:p.left_screenshot_sha256,right_screenshot_sha256:p.right_screenshot_sha256,semantic_page:p.semantic_page,viewport:p.viewport,decision:'NONE',reason:'Automated test only',recorded_at:'2026-10-09T00:00:00Z',acceptance_scope:'THIS_PAIR_ROUTE_VIEWPORT_ONLY'};
 assert.ok(!PreferenceV1.safeParse(record).success);assert.ok(!validatePreference(record,p).success);
});
