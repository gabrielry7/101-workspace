import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadCompositionLab } from '../scripts/load-composition-lab.ts';
import { compositionBindings } from '../scripts/composition-bindings.ts';
import { projectContent } from '../src/composition/content.ts';
import { auditRender, type RenderObservation } from '../src/composition/audit.ts';
import { compositions, previewPath } from '../src/composition/registry.ts';
import { loadMediaPilot } from '../scripts/load-media-pilot.ts';

test('shared content preserves both original H2 routes, required modules and branch offering bindings',async()=>{
  const lab=await loadCompositionLab(),pilot=await loadMediaPilot();
  assert.deepEqual(lab.content.pages.map(p=>p.path),pilot.bundle.plan.pages.map(p=>p.path));
  assert.equal(lab.content.pages.flatMap(p=>p.modules).filter(m=>m.required).length,2);
  assert.equal(lab.content.pages[1]!.modules[0]!.offerings[0]!.facts[0]!.text,'Ítem de menú de prueba');
  assert.equal(lab.content.pages[1]!.modules[0]!.scope_id,'fixture-restaurante-001-branch-1');
  assert.equal(lab.media.usage.page,'/');assert.equal(lab.gaps[0]!.need.role,'DOCUMENTARY');
});
test('render consumer audits actual DOM from twelve browser views against shared content',async()=>{
  const lab=await loadCompositionLab(),audit=JSON.parse(await readFile('docs/evidence/h4/browser-audit.json','utf8'));
  assert.equal(audit.receipts.length,12);assert.equal(audit.status,'PASSED');
  for(const r of audit.receipts)assert.deepEqual(auditRender(r.observation,lab,r.variant,r.semantic_page),{success:true,codes:[]});
});
test('missing mandatory module, altered fact, wrong scope and invented content fail DOM binding audit',async()=>{
  const lab=await loadCompositionLab(),audit=JSON.parse(await readFile('docs/evidence/h4/browser-audit.json','utf8'));
  for(const mutate of [
    (o:RenderObservation)=>{o.modules=[];},
    (o:RenderObservation)=>{o.modules[0]!.facts[0]!.text='Inventado';},
    (o:RenderObservation)=>{o.modules[0]!.scope='other-branch';},
    (o:RenderObservation)=>{o.modules[0]!.facts.push({id:'fake',scope:'fake',text:'fake'});},
    (o:RenderObservation)=>{o.modules[0]!.required='false';},
  ]){const o:RenderObservation=structuredClone(audit.receipts[0].observation);mutate(o);assert.equal(auditRender(o,lab,'editorial','/').success,false);}
});
test('media role, page, credit, notices, crop, hash and authorization context cannot be lost',async()=>{
  const lab=await loadCompositionLab(),audit=JSON.parse(await readFile('docs/evidence/h4/browser-audit.json','utf8'));
  for(const mutate of [
    (o:RenderObservation)=>{o.media[0]!.role='DOCUMENTARY';},
    (o:RenderObservation)=>{o.media[0]!.page='/other';},
    (o:RenderObservation)=>{o.media[0]!.credit='';},
    (o:RenderObservation)=>{o.media[0]!.notices=[];},
    (o:RenderObservation)=>{o.media[0]!.object_fit='cover';},
    (o:RenderObservation)=>{o.media[0]!.hash='0'.repeat(64);},
    (o:RenderObservation)=>{o.client_id='another-client';},
  ]){const o:RenderObservation=structuredClone(audit.receipts[0].observation);mutate(o);assert.equal(auditRender(o,lab,'editorial','/').success,false);}
  const offering:RenderObservation=structuredClone(audit.receipts[1].observation);offering.media=structuredClone(audit.receipts[0].observation.media);
  assert.ok(auditRender(offering,lab,'editorial',lab.content.pages[1]!.path).codes.includes('MEDIA_ON_UNAUTHORIZED_PAGE'));
});
test('lost diagnostics, restrictions, evidence ledger, navigation or fake commercial controls block',async()=>{
  const lab=await loadCompositionLab(),audit=JSON.parse(await readFile('docs/evidence/h4/browser-audit.json','utf8'));
  for(const mutate of [
    (o:RenderObservation)=>{o.diagnostics=[];},(o:RenderObservation)=>{o.restrictions=[];},
    (o:RenderObservation)=>{o.bindings=[];},(o:RenderObservation)=>{o.navigation=[];},
    (o:RenderObservation)=>{o.gaps=[];},(o:RenderObservation)=>{o.forms=1;},
  ]){const o:RenderObservation=structuredClone(audit.receipts[0].observation);mutate(o);assert.equal(auditRender(o,lab,'editorial','/').success,false);}
});
test('three operators share one binding ledger; no sector or client chooses the composition',async()=>{
  const bindings=await compositionBindings();assert.equal(new Set(compositions.map(c=>c.operator)).size,3);
  assert.deepEqual(bindings.variants[0]!.pages.map(p=>p.modules),bindings.variants[1]!.pages.map(p=>p.modules));
  assert.deepEqual(bindings.variants[1]!.pages.map(p=>p.modules),bindings.variants[2]!.pages.map(p=>p.modules));
  assert.throws(()=>previewPath('split','/../escape'));assert.throws(()=>previewPath('fake' as 'split','/'));
});
test('unsupported semantic component and altered mandatory plan fail instead of falling back',async()=>{
  const p=await loadMediaPilot();const bundle=structuredClone(p.bundle);bundle.plan.pages[1]!.modules=[];
  assert.throws(()=>projectContent(bundle,p.requirements),/COMPOSITION_SEMANTIC_INVALID/);
  const requirements=structuredClone(p.requirements);requirements.requirements[1]!.semantic_module='schedule';
  assert.throws(()=>projectContent(p.bundle,requirements));
});
