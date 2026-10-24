import { structuralSignature } from '../src/design/validate.ts';
import { auditCandidate,type BrowserView } from '../src/audit/evaluate.ts';
import type { GeneralCompositionLab } from '../src/composition/lab.ts';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { DesignLockV1 } from '../src/lock/contracts.ts';
import { validateLock,lockHash } from '../src/lock/validate.ts';
import { selectRollback } from '../src/lock/rollback.ts';
const lock=DesignLockV1.parse(JSON.parse(await readFile('fixtures/locks/h8/pilot-flow.json','utf8')));
const reseal=(value:typeof lock)=>({...value,lock_sha256:lockHash(value)});
test('technical lock retains frozen rights/client/project/AST and cannot claim human or production approval',()=>{
 assert.ok(validateLock(lock).success);assert.equal(lock.approval.human_preference,'NOT_COLLECTED');assert.equal(lock.media.manifest.client_id,'101-design-compiler-fixture-review');assert.equal(lock.media.manifest.project_id,'h3-restaurante-media-pilot');for(const approval of [{...lock.approval,production_ready:true},{...lock.approval,human_preference:'APPROVED'}])assert.equal(DesignLockV1.safeParse({...lock,approval}).success,false);
});
test('lock digest detects snapshot mutation; resealing cannot bypass bindings or routes',()=>{
 const changed=structuredClone(lock);changed.resolved_plan.tokens.palette='earth';assert.ok(validateLock(changed).codes.includes('LOCK_HASH_MISMATCH'));assert.equal(validateLock(reseal(changed)).success,false);
 const missing=structuredClone(lock);missing.resolved_plan.pages.pop();assert.equal(validateLock(reseal(missing)).success,false);
});
test('a different client grant, missing exact media bytes or rights document cannot become an accepted lock',()=>{
 const forged=structuredClone(lock);forged.media.manifest.grants[0]!.client_ids=['other-client'];assert.equal(validateLock(reseal(forged)).success,false);
 const bytes=structuredClone(lock);bytes.files.find(f=>f.role==='AUTHORIZED_MEDIA')!.sha256='0'.repeat(64);assert.ok(validateLock(reseal(bytes)).codes.includes('LOCK_RIGHTS_FILE_MISMATCH'));
 const doc=structuredClone(lock);doc.files=doc.files.filter(f=>f.role!=='RIGHTS_DOCUMENT');assert.ok(validateLock(reseal(doc)).codes.includes('LOCK_RIGHTS_FILE_MISMATCH'));
});
test('media-free resolved lock retains typography-only direction and empty usage refs without pilot grant',async()=>{
 const noMedia=DesignLockV1.parse(JSON.parse(await readFile('fixtures/locks/h8/hybrid-no-media.json','utf8')));assert.ok(validateLock(noMedia).success);assert.equal((noMedia.lab as any).media,null);assert.equal(noMedia.files.length,0);assert.equal(noMedia.media.manifest.grants.length,0);assert.ok(noMedia.creative.proposals.every(d=>d.materiality==='typography-only'));
});
test('arbitrary lock code, unsupported version and escaping file paths reject strictly',()=>{
 for(const value of [{...lock,code:'alert(1)'},{...lock,schema_version:'2.0.0'},{...lock,source_snapshot_root:'../outside'},{...lock,source_snapshot_root:'C:/outside'}])assert.equal(DesignLockV1.safeParse(value).success,false);
});
test('rollback selects an actually verified exact lock/output snapshot and rejects stale or failed history',()=>{
 const history=[{lock_id:lock.id,lock_sha256:lock.lock_sha256,output_sha256:'a'.repeat(64),status:'LAB_EQUIVALENCE_PASS' as const}];assert.equal(selectRollback(history,lock).expected_output_sha256,'a'.repeat(64));assert.throws(()=>selectRollback([{...history[0]!,status:'FAIL'}],lock),/NOT_VERIFIED/);assert.throws(()=>selectRollback([{...history[0]!,lock_sha256:'0'.repeat(64)}],lock),/NOT_VERIFIED/);
});

test('rollback experiment retains distinct frozen pilot ASTs',async()=>{
 const alternate=DesignLockV1.parse(JSON.parse(await readFile('fixtures/locks/h8/pilot-rail.json','utf8')));assert.notEqual(structuralSignature(alternate.resolved_plan),structuralSignature(lock.resolved_plan));assert.notDeepEqual(alternate.resolved_plan,lock.resolved_plan);assert.notEqual(alternate.resolved_plan.id,lock.resolved_plan.id);
});

test('normal technical approval requires actual complete audit coverage, not the approval literal',()=>{
 const missing:any=structuredClone(lock);delete missing.audit_state;assert.equal(validateLock(reseal(missing)).success,false);
 for(const change of ['missing','duplicate','viewport'] as const){const value=structuredClone(lock);if(change==='missing')value.audit_state.entries.pop();if(change==='duplicate')value.audit_state.entries.push(value.audit_state.entries[0]!);if(change==='viewport')value.audit_state.entries[0]!.viewport.width=999;assert.ok(validateLock(reseal(value)).codes.includes('LOCK_AUDIT_COVERAGE_INCOMPLETE'));}
});
test('audit context, location, real gates and recoverable evidence cannot be forged by resealing',()=>{
 for(const change of ['context','policy','route','report','evidence','source'] as const){const value=structuredClone(lock);if(change==='context')value.audit_state.context_sha256='0'.repeat(64);if(change==='policy')value.audit_state.policy.max_page_bytes=100;if(change==='route')value.audit_state.entries[0]!.audit.route='/other/';if(change==='report')value.audit_state.entries[0]!.audit.families.find(f=>f.family==='performance')!.status='PASS';if(change==='evidence')value.audit_state.evidence.pop();if(change==='source')value.audit_state.renderer_sources[0]!.sha256='0'.repeat(64);assert.equal(validateLock(reseal(value)).success,false,change);}
});
test('an internally consistent failed browser report still blocks a normal lock',()=>{
 const value=structuredClone(lock),entry=value.audit_state.entries[0]!,view=entry.view as BrowserView;view.geometry.document_width=5000;
 entry.audit=auditCandidate({schema_version:'1.0.0',plan:value.resolved_plan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}},value.lab as GeneralCompositionLab,view,value.audit_state.policy,p=>`/${value.mount.kind}/${value.mount.id}${p==='/'?'/':`${p}/`}`);
 assert.equal(entry.audit.status,'FAIL');assert.ok(validateLock(reseal(value)).codes.includes('LOCK_AUDIT_FAILED'));
});
test('audit preserves laboratory exceptions and unmeasured human/commercial gates; seeded baseline is never normal acceptance',()=>{
 assert.ok(lock.audit_state.entries.every(e=>['PASS','LAB_EXCEPTION'].includes(e.audit.families.find(f=>f.family==='performance')!.status)&&e.audit.families.find(f=>f.family==='visual')!.status==='NOT_MEASURED'&&e.audit.measurements.field_p75==='NOT_MEASURED'&&e.audit.human_preference==='NOT_COLLECTED'));
 assert.ok(lock.audit_state.entries.some(e=>e.audit.families.find(f=>f.family==='performance')!.status==='LAB_EXCEPTION'));const value=structuredClone(lock);value.audit_state.status='BASELINE_ONLY_SEEDED_NOT_ACCEPTED';assert.ok(validateLock(reseal(value)).codes.includes('LOCK_AUDIT_PURPOSE_MISMATCH'));
});
