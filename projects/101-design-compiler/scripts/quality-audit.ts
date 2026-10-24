import {readFile,writeFile} from 'node:fs/promises';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {auditRender} from '../src/composition/audit.ts';
import {loadQualityLab,qualityPath} from './load-quality-lab.ts';
import {consolidateFindings} from '../src/design/evaluators/policy.ts';
import {makeFinding,normalizeImpeccable,normalizeRaven} from '../src/design/evaluators/normalize.ts';
import {bindingObservation} from '../src/design/evaluators/binding-observation.ts';
const bridge='../tooling/design-evaluation/raven-client.mjs',detector='../tooling/design-evaluation/impeccable.mjs';
const {RavenSession}=await import(bridge),{detect}=await import(detector);
const iteration=Number(process.argv[2]??0);if(![0,1,2].includes(iteration))throw Error('ITERATION_BUDGET');
const folder=`docs/evidence/design-evaluation/iteration-${iteration}`,browser=JSON.parse(await readFile(`${folder}/browser.json`,'utf8')),run=await loadQualityLab();
const r=await new RavenSession().connect(),cache=new Map(),views=[];const started=performance.now();
const previous=iteration?JSON.parse(await readFile(`docs/evidence/design-evaluation/iteration-${iteration-1}/audit.json`,'utf8')):null;
const replay=process.argv.includes('--replay'),refresh=process.argv.includes('--refresh'),original=replay||refresh?JSON.parse(await readFile(`${folder}/audit.json`,'utf8')):null;
const reusable=new Map([...(previous?.raven_calls??[]),...(original?.raven_calls??[])].map((c:any)=>[inputSha256({tool:c.tool,input:c.input}),c]));
if(original)for(const c of original.impeccable_calls){const route=c.target.replace(/^dist/,'').replace(/index\.html$/,'');const prior=original.views.find((v:any)=>v.route===route);if(inputSha256(await readFile(c.target,'utf8'))!==prior?.metrics.html_sha256)throw Error('REPLAY_DETECTOR_HTML_DRIFT');cache.set(route,c);}
const usedRaven:any[]=[],reused:string[]=[];
const call=async(tool:string,args:unknown)=>{const key=inputSha256({tool,input:args}),old=reusable.get(key);if(old){usedRaven.push(old);reused.push(key);return old;}
 if(replay)throw Error(`REPLAY_TOOL_INPUT_DRIFT:${tool}`);
 if(r.calls.length+cache.size+(previous?.new_tool_calls??(previous?.raven_calls.length??0)+(previous?.impeccable_calls.length??0))+run.metering.preflight_tool_calls>=run.budget.max_tool_calls)throw Error('EVALUATION_TOOL_BUDGET');
 const receipt=await r.call(tool,args);usedRaven.push(receipt);return receipt;};
try{
 for(const view of browser.receipts){
  const c=run.cases.find((c:any)=>c.id===view.case_id),v=c?.variants.find((v:any)=>v.condition===view.condition);if(!c||!v)throw Error('AUDIT_UNKNOWN_VARIANT');
  const location={route:view.route,viewport:view.viewport.id},snapshot=view.observation.evaluators;
  const own={tool:'101.browser-binding-gate',version:'1.0.0',receipt_sha256:inputSha256(view)};
  const binding=auditRender(bindingObservation(view.observation.base.observation),c.lab,'editorial',view.page,p=>qualityPath(c.id,v.condition,p));
  const findings=binding.codes.map(code=>makeFinding(own,location,code,{screenshot:view.screenshot.path,code},'Preserve the approved content, module, scope, diagnostics and media bindings.',{kind:'MEASURED',severity:'BLOCKING',confidence:1}));
  if(view.observation.base.geometry.overflow.length||snapshot.document_width>snapshot.viewport.w)findings.push(makeFinding(own,location,'OVERFLOW',view.observation.base.geometry,'Repair layout within shared operators, preserving every module.',{kind:'MEASURED',severity:'BLOCKING',confidence:1}));
  if(v.flags.impeccable||v.flags.raven)for(const node of snapshot.typography.filter((t:any)=>t.tag==='p'&&t.fontPx<16))findings.push(makeFinding(own,location,'BODY_READING_SIZE',node,'Use the shared reading type variant for body, attribution and diagnostic text.',{kind:'MEASURED',selector:node.selector,repair:'TYPE_RHYTHM',confidence:1}));
  if(v.flags.impeccable){let receipt=cache.get(view.route);if(!receipt){receipt=await detect(`dist${view.route}index.html`);cache.set(view.route,receipt);}findings.push(...normalizeImpeccable(receipt,location));}
  if(v.flags.raven){
   for(const [tool,args] of [['audit_layout',{elements:snapshot.layout,viewport:snapshot.viewport}],['audit_typography',{nodes:snapshot.typography}],['audit_contrast',{dom_snapshot:snapshot.contrast}],['audit_tap_targets',{elements:snapshot.targets,minSize:44}]] as const){const receipt=await call(tool,args);findings.push(...normalizeRaven(receipt,location));}
   if(view.viewport.id==='desktop'){
    await call('score_page',{html:await readFile(`dist${view.route}index.html`,'utf8'),containerMaxWidth:1280});
    await call('evaluate_design',{description:`Existing ${c.id} composition: ${v.design.pages.map((p:any)=>p.composition.operator+'/'+p.composition.child.operator).join(', ')}. ${v.design.tokens.type} display, ${v.design.tokens.palette} palette, ${v.design.tokens.rhythm} rhythm. Binding audit ${binding.success?'passes':'fails'}. ${c.lab.media?'A single unaltered atmospheric photograph is credited; it does not represent the business.':'No eligible photography; documentary gaps preserved.'}`,goals:['accessibility','mobile-usability'],compact:true});
   }
  }
  views.push({case_id:c.id,condition:v.condition,page:view.page,viewport:view.viewport.id,route:view.route,screenshot:view.screenshot,bindings:binding,findings:consolidateFindings(findings),
   metrics:{document_width:snapshot.document_width,viewport_width:snapshot.viewport.w,targets_below_44:snapshot.targets.filter((t:any)=>t.w<44||t.h<44).length,body_text_below_16:snapshot.typography.filter((t:any)=>t.tag==='p'&&t.fontPx<16).length,contrast_indeterminate:snapshot.indeterminate.length,
    html_bytes:Buffer.byteLength(await readFile(`dist${view.route}index.html`)),html_sha256:inputSha256(await readFile(`dist${view.route}index.html`,'utf8')),media:snapshot.media,resource_measurement:snapshot.resource_measurement,lcp:null,inp:null,cls:null}});
 }
 const expected=run.cases.flatMap((c:any)=>c.variants.flatMap((v:any)=>v.design.pages.flatMap((p:any)=>['desktop','mobile'].map(vp=>`${qualityPath(c.id,v.condition,p.path)}:${vp}`))));
 const actual=views.map(v=>`${v.route}:${v.viewport}`);if(new Set(actual).size!==actual.length||JSON.stringify(actual.sort())!==JSON.stringify(expected.sort()))throw Error('BROWSER_COVERAGE_INCOMPLETE');
 const receipt={schema_version:'1.0.0',experiment_id:run.experiment_id,iteration,wall_seconds:(original?.wall_seconds??0)+(replay?0:(performance.now()-started)/1000),views,raven_calls:usedRaven,new_raven_calls:(original?.new_raven_calls??0)+r.calls.length,reused_raven_calls:original?.reused_raven_calls??reused.length,new_tool_calls:original?(original.new_tool_calls+r.calls.length):r.calls.length+cache.size,impeccable_calls:[...cache.values()],model_api_calls:0,session_cost:null,new_provider_spend:0};
 await writeFile(`${folder}/audit.json`,JSON.stringify(receipt,null,2)+'\n');
 if(usedRaven.some(c=>c.status!=='OK')||views.some(v=>!v.bindings.success||v.findings.some(f=>f.severity==='BLOCKING')))process.exitCode=1;
 console.log(JSON.stringify({iteration,views:views.length,binding_failures:views.filter(v=>!v.bindings.success).length,blocking:views.flatMap(v=>v.findings).filter(f=>f.severity==='BLOCKING').length,new_raven_calls:r.calls.length,reused_raven_calls:reused.length,impeccable_calls:cache.size,tool_errors:r.calls.filter((c:any)=>c.status!=='OK').length}));
}finally{await r.close();}
