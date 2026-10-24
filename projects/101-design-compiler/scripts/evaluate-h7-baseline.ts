import { readFile, mkdir, writeFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { loadMappingRegistry } from './load-taxonomy.ts';
import { planBusiness } from '../src/planner/plan.ts';
import { projectContent } from '../src/composition/content.ts';
const reservation=JSON.parse(await readFile('fixtures/cohort/h7/reservation.json','utf8'));
if(await access('docs/evidence/h7/first-evaluation.json').then(()=>true,()=>false))throw Error('FIRST_EVALUATION_ALREADY_RECORDED_DO_NOT_OVERWRITE');
const registry=await loadMappingRegistry();const cases=[];
for(const file of reservation.files){const bytes=await readFile(file.path);if(createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('COHORT_HASH_MISMATCH');const fixture=JSON.parse(bytes.toString('utf8'));const result=planBusiness(fixture.input,{rules:registry.rules,activity_relationships:fixture.activity_relationships});let projection:any={status:'NOT_ATTEMPTED'};if(result.status==='READY'){try{const p=projectContent({input:result.input,profile:result.profile,capabilities:result.capabilities,plan:result.plan},result.requirements);projection={status:'PASS',content_sha256:p.content_sha256};}catch(error){projection={status:'FAIL',reason:String(error)};}}cases.push({scenario:fixture.scenario,input_sha256:file.sha256,result,projection});}
await mkdir('docs/evidence/h7',{recursive:true});await writeFile('docs/evidence/h7/first-evaluation.json',JSON.stringify({baseline_commit:'3ff5356',phase:'FIRST_EXECUTION_BEFORE_PLATFORM_ADJUSTMENTS',lab_only:true,cases,summary:{planner_ready:cases.filter(c=>c.result.status==='READY').length,projection_pass:cases.filter(c=>c.projection.status==='PASS').length,projection_fail:cases.filter(c=>c.projection.status==='FAIL').length}},null,2)+'\n');console.log(cases.map(c=>({scenario:c.scenario,planner:c.result.status,archetypes:c.result.profile?.archetypes.map(a=>a.id),projection:c.projection})));
