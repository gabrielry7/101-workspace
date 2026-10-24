import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadDesignLab } from '../scripts/load-design-lab.ts';
import { H5_BUDGET, H5_SEED } from '../scripts/load-design-lab.ts';
import { ArtDirectionV1, DesignPlanV1 } from '../src/design/contracts.ts';
import { contextHash, validateDirection, validateDesign, searchDesigns, structuralDistance, structuralSignature, designPreviewPath } from '../src/design/search.ts';
import { auditRender } from '../src/composition/audit.ts';
const fixture=await loadDesignLab();
const {lab,result}=fixture;
const directions=JSON.parse(await readFile(new URL('../fixtures/design/h5/llm-output.json',import.meta.url),'utf8'));
test('H5 search explores six declarative plans and selects four distinct nested topologies with identical frozen bindings',()=>{
 assert.equal(result.candidates.length,6);assert.equal(result.finalists.length,4);assert.equal(result.attempts.length,24);
 assert.equal(new Set(result.finalists.map(structuralSignature)).size,4);
 for(const p of result.candidates) {assert.ok(validateDesign(p,lab,result.directions.find(d=>d.id===p.art_direction_id)).success);assert.deepEqual(p.pages.map(p=>p.path),lab.content.pages.map(p=>p.path));}
 assert.ok(result.finalists.some(p=>p.pages[0]!.composition.operator==='Rail'&&p.pages[0]!.composition.child.operator==='Split'));
 assert.ok(result.diversity.every(p=>p.distance>0));
});
test('LLM source records actual session output, hashes and unavailable metering without invented API calls',()=>{
 assert.equal(fixture.provenance.source,'ACTIVE_CODEX_SESSION_LLM');assert.equal(fixture.provenance.tokens,null);assert.equal(fixture.provenance.cost,null);assert.equal(fixture.provenance.new_provider_calls,0);
 assert.equal(result.context_sha256,contextHash(lab));assert.equal(result.usage.human_preference,'NOT_COLLECTED');
});
test('same recorded proposals, budget, context and local seed replay without creative or provider calls',()=>{
 assert.deepEqual(searchDesigns(directions,lab,H5_BUDGET,H5_SEED),result);
 assert.notDeepEqual(searchDesigns(directions,lab,H5_BUDGET,H5_SEED+1).attempts,result.attempts);
});
test('arbitrary code, dependencies, unknown tokens, AST operators and incompatible versions reject strictly',()=>{
 for(const patch of [{css:'body{}'},{dependencies:['react']},{schema_version:'2.0.0'},{tokens:{...directions[0].tokens,palette:'unbounded'}}])assert.ok(!ArtDirectionV1.safeParse({...directions[0],...patch}).success);
 const p=structuredClone(result.finalists[0]!);(p.pages[0]!.composition as any).operator='WebGL';assert.ok(!DesignPlanV1.safeParse(p).success);
});
test('loss, duplication, reordering, cross-route module moves and unknown fact text cannot pass DesignPlan',()=>{
 for(const mutate of [(p:any)=>p.pages[0].composition.child.module_refs=[],(p:any)=>p.pages.pop(),(p:any)=>p.pages.reverse(),
  (p:any)=>p.pages[0].composition.child.module_refs.push(p.pages[0].composition.child.module_refs[0]),
  (p:any)=>p.pages[0].composition.child.module_refs=[p.pages[1].composition.child.module_refs[0]],(p:any)=>p.pages[0].text='Invented menu']) {
  const p=structuredClone(result.finalists[0]!);mutate(p);assert.ok(!validateDesign(p,lab).success);
 }
});
test('stock usage, another context, crop and unapproved rights cannot be smuggled through candidate validation',()=>{
 for(const mutate of [(p:any)=>p.manifest_sha256='0'.repeat(64),(p:any)=>p.pages[1].composition.child.media_usage_refs=[lab.media.usage.id],
  (p:any)=>p.pages[0].composition.child.media_usage_refs=['unknown-usage']]) {const p=structuredClone(result.finalists[0]!);mutate(p);assert.ok(!validateDesign(p,lab).success);}
 const changed=structuredClone(lab);changed.media.grant.commercial_web='UNKNOWN';assert.ok(!validateDesign(result.finalists[0],changed).success);
 const cropped=structuredClone(lab);cropped.media.usage.transformations=['CROP'];assert.ok(!validateDirection({...directions[0],context_sha256:contextHash(cropped)},cropped).success);
});
test('prefilter records schema/rights/content rejection before allocating any render slot',()=>{
 const bad=structuredClone(directions);bad.forEach((p:any)=>p.media_usage_ids=['invented']);
 const failed=searchDesigns(bad,lab,H5_BUDGET,H5_SEED);assert.equal(failed.status,'NO_ACCEPTABLE_DESIGN');assert.equal(failed.finalists.length,0);assert.equal(failed.usage.render_slots,0);assert.equal(failed.rejections.length,3);
 const dup=searchDesigns([directions[0],directions[0]],lab,H5_BUDGET,H5_SEED);assert.ok(dup.rejections.some(r=>r.codes.includes('DUPLICATE_DIRECTION')));
});
test('budgets bound proposal bytes/count, samples and render slots with no spend or provider invocation',()=>{
 assert.throws(()=>searchDesigns([...directions,...directions],lab,H5_BUDGET,H5_SEED),/COUNT_BUDGET/);
 assert.throws(()=>searchDesigns(directions,lab,{...H5_BUDGET,max_output_bytes:100},H5_SEED),/BYTES_BUDGET/);
 assert.throws(()=>searchDesigns(directions,lab,{...H5_BUDGET,new_spend:1} as any,H5_SEED));
 assert.throws(()=>searchDesigns(directions,lab,H5_BUDGET,-1),/SEED/);
 const small=searchDesigns(directions,lab,{...H5_BUDGET,samples:2,renders:1},H5_SEED);assert.equal(small.attempts.length,2);assert.equal(small.finalists.length,1);
});
test('cosmetic differences cannot create structural diversity or additional finalist slots',()=>{
 const p=structuredClone(result.finalists[0]!);p.tokens.palette='earth';p.tokens.type='sans';assert.equal(structuralDistance(p,result.finalists[0]!),0);
 const repeated=searchDesigns([directions[0]],lab,H5_BUDGET,H5_SEED);assert.equal(repeated.finalists.length,2);
});
test('contextual sampler conditions weights on content density and permitted media presence without sector templates',()=>{
 const dense=structuredClone(lab);dense.content.pages[0]!.modules[0]!.offerings=Array.from({length:9},()=>({id:'synthetic-density-test',scope_id:'density',facts:[]}));
 const adjusted=directions.map((d:any)=>({...d,context_sha256:contextHash(dense)}));
 const sampled=searchDesigns(adjusted,dense,H5_BUDGET,H5_SEED);
 assert.ok(sampled.attempts.some((a:any)=>a.estimate.dense&&JSON.stringify(a.estimate.weights)!==JSON.stringify((result.attempts.find((b:any)=>b.direction_id===a.direction_id) as any).estimate.weights)));
});
test('design preview routes reject path traversal and arbitrary mounts',()=>{
 assert.equal(designPreviewPath('candidate-01','/'),'/h5/candidate-01/');assert.throws(()=>designPreviewPath('../bad','/'));assert.throws(()=>designPreviewPath('candidate-01','/../bad'));
});
test('all sixteen actual DOM observations retain facts, scopes, media, required modules and honest interaction states',async()=>{
 const report=JSON.parse(await readFile('docs/evidence/h5/browser-audit.json','utf8'));
 assert.equal(report.receipts.length,16);assert.equal(report.stress.length,28);assert.equal(report.status,'PASSED');
 for(const r of report.receipts) {
  assert.ok(auditRender(r.observation,lab,'editorial',r.semantic_page,p=>designPreviewPath(r.design_id,p)).success);
  assert.equal(r.geometry.overflow.length,0);assert.ok(r.readability.every((e:any)=>e.contrast>=4.5));
  const missing=structuredClone(r.observation);missing.modules.pop();assert.ok(!auditRender(missing,lab,'editorial',r.semantic_page,p=>designPreviewPath(r.design_id,p)).success);
 }
});
