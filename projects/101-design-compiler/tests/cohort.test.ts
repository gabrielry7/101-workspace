import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadCohortLab,cohortBudget,cohortPath } from '../scripts/load-cohort-lab.ts';
import { searchDesigns,validateDesign } from '../src/design/search.ts';
import { auditCandidate,chooseAcceptable } from '../src/audit/evaluate.ts';
import { ArtDirectionV1,ArtDirectionV1_1 } from '../src/design/contracts.ts';
const cohort=await loadCohortLab(true);
test('media-free materiality is explicit version 1.1; historical version 1.0 photograph contract is unchanged',()=>{
 const c=cohort.cases.find(c=>c.scenario==='hotel')!;const d=c.search!.directions[0]!;assert.equal(d.schema_version,'1.1.0');assert.equal(d.materiality,'typography-only');assert.ok(ArtDirectionV1_1.safeParse(d).success);assert.equal(ArtDirectionV1.safeParse(d).success,false);
 const misleading={...d,schema_version:'1.0.0',materiality:'unaltered-photograph'};assert.equal(searchDesigns([misleading],c.lab!,cohortBudget,1).status,'NO_ACCEPTABLE_DESIGN');
});
test('new frozen cohort spans distinct capabilities/archetypes while Unknown remains blocked without a site',()=>{
 assert.equal(cohort.cases.length,6);const ready=cohort.cases.filter(c=>c.lab);assert.equal(ready.length,5);
 const archetypes=new Set(ready.flatMap(c=>c.result.profile?.archetypes.map(a=>a.id)??[]));for(const id of ['lodging','regulated_services','field_service_and_quote','membership_and_classes','product_retail'])assert.ok(archetypes.has(id as any));
 const unknown=cohort.cases.find(c=>c.scenario==='unknown')!;assert.equal(unknown.result.status,'CONTENT_BLOCKED');assert.equal(unknown.lab,null);assert.equal(unknown.search,null);
 assert.ok(ready.every(c=>c.lab!.media===null&&c.search!.finalists.length===2&&c.search!.diversity[0]!.distance>0));
});
test('UNKNOWN media preserves inventory and rejected attempted usage, never lends pilot permission',()=>{
 const c=cohort.cases.find(c=>c.scenario==='media-unknown')!;assert.equal(c.media!.manifest.assets[0]!.upstream_rights_status,'UNKNOWN');assert.equal(c.media!.manifest.grants.length,0);assert.equal(c.media!.manifest.usages.length,1);assert.notEqual(c.media!.manifest.decisions[0]!.status,'ALLOWED');assert.ok(c.media!.brief.gaps.length);assert.equal(c.lab!.media,null);
 for(const p of c.search!.finalists)assert.ok(p.pages.every(p=>p.composition.child.media_usage_refs.length===0));
});
test('no-media context rejects smuggled usage and arbitrary component/code without render allocation',()=>{
 const c=cohort.cases.find(c=>c.scenario==='hotel')!;const d=structuredClone(c.search!.directions[0]!);d.media_usage_ids=['h3-pilot-usage'];assert.equal(searchDesigns([d],c.lab!,cohortBudget,1).finalists.length,0);
 const p=structuredClone(c.search!.finalists[0]!);p.pages[0]!.composition.child.media_usage_refs=['h3-pilot-usage'];assert.ok(validateDesign(p,c.lab!).codes.includes('DESIGN_MEDIA_USAGE_MISMATCH'));
 const arbitrary={...c.search!.directions[0],client_code:'alert(1)'};assert.equal(searchDesigns([arbitrary],c.lab!,cohortBudget,1).status,'NO_ACCEPTABLE_DESIGN');
});
test('generic collection/schedule preserve all approved bound facts; stale scope or omitted module fails',()=>{
 for(const c of cohort.cases.filter(c=>c.lab)){const lab=c.lab!;for(const p of c.search!.finalists){assert.ok(validateDesign(p,lab).success);const loss=structuredClone(p);loss.pages[0]!.composition.child.module_refs.pop();assert.equal(validateDesign(loss,lab).success,false);}}
 const hybrid=cohort.cases.find(c=>c.scenario==='hibrido')!;const schedule=hybrid.lab!.content.pages.flatMap(p=>p.modules).find(m=>m.component==='Schedule')!;assert.ok(schedule.offerings.flatMap(o=>o.facts).some(f=>f.kind==='timezone'));assert.ok(schedule.offerings.flatMap(o=>o.facts).some(f=>f.kind==='class_starts_at'));
});
test('actual browser seeded unbound image, altered fact and contrast fail independent hard gates',async()=>{
 const run=JSON.parse(await readFile('docs/evidence/h7/run.json','utf8'));for(const r of run.receipts.filter((r:any)=>r.seeded_fault)){const c=cohort.cases.find(c=>c.scenario==='media-unknown')!;const report=auditCandidate(r.candidate,c.lab!,r.view,run.policy,p=>cohortPath(c.scenario,r.candidate.plan.id,p));assert.equal(report.status,'FAIL');assert.equal(report.production_ready,false);}
 const denied=chooseAcceptable([]);assert.equal(denied.status,'NO_ACCEPTABLE_DESIGN');
});
