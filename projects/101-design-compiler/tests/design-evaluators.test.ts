import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {EvaluatorFlagsV1,DesignRefinementV1,DesignPreferenceV1,QualityExperimentV1} from '../src/design/evaluators/contracts.ts';
import {guidedRefinement} from '../src/design/evaluators/preflight.ts';
import {makeFinding,normalizeRaven} from '../src/design/evaluators/normalize.ts';
import {consolidateFindings,proposeRefinement,judgeRefinement} from '../src/design/evaluators/policy.ts';
import {bindingObservation} from '../src/design/evaluators/binding-observation.ts';
import {auditRender} from '../src/composition/audit.ts';
import {loadQualityLab,qualityPath} from '../scripts/load-quality-lab.ts';
const base=()=>DesignRefinementV1.parse({schema_version:'1.0.0'}),source={tool:'101.browser',version:'1.0.0',receipt_sha256:'a'.repeat(64)},loc={route:'/test/',viewport:'mobile'};
const finding=(rule='TARGET_44')=>makeFinding(source,loc,rule,{w:20,h:20},'Use the shared comfortable target variant.',{kind:'MEASURED',repair:'TOUCH_TARGETS',selector:'a',confidence:1});
const budget={max_iterations:2,max_tool_calls:200,max_wall_seconds:600,max_new_spend:0};
test('Both flags default off; baseline needs neither tool nor fabricated guidance',()=>{
 assert.deepEqual(EvaluatorFlagsV1.parse({}),{impeccable:false,raven:false});assert.deepEqual(guidedRefinement({},{}),base());
 assert.throws(()=>guidedRefinement({impeccable:true},{}),/GUIDANCE_MISSING/);assert.throws(()=>guidedRefinement({raven:true},{raven_principles:[],raven_pattern_ok:true}),/GUIDANCE_MISSING/);
});
test('Presentation patches cannot carry facts, scripts, CSS, media URLs or licenses',()=>{
 for(const key of ['facts','scripts','css','media','grants','module_refs','palette'])assert.equal(DesignRefinementV1.safeParse({...base(),[key]:[]}).success,false);
 assert.equal(DesignRefinementV1.safeParse({...base(),type_rhythm:'unbounded'}).success,false);
});
test('Deduplication preserves independent evidence, severity and provenance without merging viewports',()=>{
 const a=finding(),b={...a,id:'second',severity:'BLOCKING' as const,evidence:['independent'],sources:[{...source,tool:'raven.audit_tap_targets'}]},m={...a,id:'desktop',viewport:'desktop'};
 const merged=consolidateFindings([a,b,m]);assert.equal(merged.length,2);assert.equal(merged[0]!.sources.length,2);assert.equal(merged[0]!.evidence.length,2);assert.equal(merged[0]!.severity,'BLOCKING');
});
test('Aesthetic and low-confidence findings cannot automatically flatten the design',()=>{
 assert.equal(proposeRefinement(base(),[{...finding(),kind:'AESTHETIC'}]).changed,false);
 assert.equal(proposeRefinement(base(),[{...finding(),confidence:.6}]).changed,false);
 assert.equal(proposeRefinement(base(),[finding()]).refinement.touch_targets,'comfortable');
});
test('Raven passing checks are not failures; taste heuristics never become measured evidence',()=>{
 const r={tool:'audit_layout',version:'2.6.0',status:'OK',output:{findings:[{check:'alignment',status:'pass',message:'Good'},{check:'gap-rhythm',status:'warn',message:'Varied rhythm'}]}};
 const f=normalizeRaven(r,loc);assert.equal(f.length,1);assert.equal(f[0]!.kind,'HEURISTIC');assert.equal(f[0]!.repair,'NONE');
 assert.equal(normalizeRaven({...r,status:'ERROR'},loc)[0]!.rule,'TOOL_UNAVAILABLE');
 assert.equal(normalizeRaven({...r,status:'ERROR'},loc)[0]!.severity,'BLOCKING');
});
test('Bounded loop rolls back regression/non-improvement and stops at either resource or iteration limit',()=>{
 assert.equal(judgeRefinement([finding()],[],1,10,1,budget).keep,true);
 assert.equal(judgeRefinement([finding()],[finding()],1,10,1,budget).reason,'NO_VERIFIED_IMPROVEMENT');
 assert.equal(judgeRefinement([finding()],[{...finding('CONTRAST_AA'),severity:'BLOCKING',repair:'NONE'}],1,10,1,budget).reason,'REGRESSION');
 assert.equal(judgeRefinement([finding()],[],2,10,1,budget).stop,true);
 assert.equal(judgeRefinement([finding()],[],1,200,1,budget).stop,true);
 assert.throws(()=>judgeRefinement([],[],3,1,1,budget),/ITERATION_BUDGET/);
});
test('Pilot preserves exact plans and inputs and does not claim real verified businesses or human votes',async()=>{
 const run=await loadQualityLab();assert.equal(run.cases.length,2);assert.equal(run.default_enabled,false);assert.equal(run.human_preferences,'NOT_COLLECTED');
 for(const c of run.cases){assert.equal(c.data_mode,'SYNTHETIC_FIXTURE');for(const v of c.variants){assert.deepEqual(v.design,c.variants[0]!.design);assert.ok(v.iteration<=2);}assert.deepEqual(c.variants[0]!.refinement,base());}
 assert.equal(QualityExperimentV1.safeParse({...JSON.parse(await readFile('data/derived/design-evaluation-v1/experiment.json','utf8')),default_enabled:true}).success,false);
});
test('Browser key ordering is normalized; changed/missing/reordered factual evidence still fails',async()=>{
 const run=await loadQualityLab(),captured=JSON.parse(await readFile('docs/evidence/design-evaluation/iteration-0/browser.json','utf8')).receipts[0],c=run.cases.find(c=>c.id===captured.case_id)!;
 const o=bindingObservation(captured.observation.base.observation),audit=(v:typeof o)=>auditRender(v,c.lab,'editorial',captured.page,p=>qualityPath(c.id,'A',p));
 assert.equal(audit(o).success,true);const altered=structuredClone(o);altered.modules[0]!.facts[0]!.text='Invented business claim';assert.ok(audit(altered).codes.includes('RENDER_BINDING_LOSS_OR_INVENTION'));
 const omitted=structuredClone(o);omitted.navigation.pop();assert.ok(audit(omitted).codes.includes('ROUTE_LOSS'));
});
test('Preferences require explicit human source, experiment binding, valid rating and explanation',()=>{
 const record={schema_version:'1.0.0',experiment_id:'b'.repeat(64),case_id:'hotel',viewport:'mobile',preferred:'NONE',rating:1,dimensions:['composition'],reason:'Testing schema only; not a collected vote.',recorded_at:'2026-10-22T00:00:00Z',source:'EXPLICIT_HUMAN_INPUT'};
 assert.ok(DesignPreferenceV1.safeParse(record).success);for(const patch of [{rating:0},{rating:11},{source:'TOOL_SCORE'},{reason:''}])assert.equal(DesignPreferenceV1.safeParse({...record,...patch}).success,false);
});
test('Compiler binding is scoped, rejects replay and unknown patches, and preserves factual bytes',async()=>{
 const modulePath='../tooling/design-evaluation/compiler-extension.mjs';const {bindRefinement}=await import(modulePath);
 const lab={content:{content_sha256:'a'.repeat(64),pages:[{path:'/',modules:[]}]},media:null};
 const variant={condition:'B',design:{id:'candidate-01'},refinement:{...base(),tracking:'natural'}};
 const html=`<html><head><style>foundation</style></head><body><div class="lab h5 frame-flow" data-content-sha256="${'a'.repeat(64)}" data-composition="h5"><style>/* Shared laboratory grammar: fixture */</style><header><span>H7 · candidate-01 · Ficticio</span></header><a href="/h7/hotel-b/" data-route="/"><span>01</span>Identidad</a><h1 data-fact-id="name">A literal &amp; approved fact</h1></div></body></html>`;
 const output=bindRefinement(html,{lab,variant,caseId:'hotel',styles:'.lab {font-size:16px}'});
 assert.ok(output.includes('<style>foundation</style>'));assert.ok(output.includes('href="/quality/hotel-b/"'));assert.ok(output.includes('<h1 data-fact-id="name">A literal &amp; approved fact</h1>'));
 assert.throws(()=>bindRefinement(output,{lab,variant,caseId:'hotel',styles:''}),/ALREADY_BOUND/);
 assert.throws(()=>bindRefinement(html,{lab,variant:{...variant,refinement:{...variant.refinement,facts:[]}},caseId:'hotel',styles:''}));
 assert.throws(()=>bindRefinement(html,{lab,variant,caseId:'../outside',styles:''}),/UNSAFE_MOUNT/);
});
