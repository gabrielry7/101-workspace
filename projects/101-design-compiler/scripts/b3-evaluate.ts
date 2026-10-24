import {readFile,writeFile,mkdir,access,readdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadB3DepthExperience} from './load-b3-depth-experience.ts';
import {richExperiencePages} from '../src/design/rich-experience-contracts.ts';
import {experienceRoute} from '../src/design/experience-contracts.ts';
import {auditDepthExperience} from '../src/design/depth-experience-audit.ts';
import {normalizeImpeccable,normalizeRaven} from '../src/design/evaluators/normalize.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {capturePresence} from './lib/capture-presence.ts';
const root='docs/evidence/design-evaluation/b3-20261022',phase=process.argv[2];
if(!['before','after','verify'].includes(phase!))throw Error('B3_EVALUATION_PHASE_REQUIRED');
const json=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
const sha=(s:string|Uint8Array)=>createHash('sha256').update(s).digest('hex');
const lab=await loadB3DepthExperience();
// CUA changes object key order. Restore order only, retaining every observed value.
const order=(value:any,template:any):any=>Array.isArray(value)?value.map((v,i)=>order(v,template?.[i]??template?.[0])):value&&typeof value==='object'?Object.fromEntries([...Object.keys(template??{}).filter(k=>k in value),...Object.keys(value).filter(k=>!(k in (template??{})))].map(k=>[k,order(value[k],template?.[k])])):value;
function binding(raw:any){return {...raw,modules:raw.modules.map((m:any)=>({id:m.id,scope:m.scope,page:m.page,component:m.component,required:m.required,facts:m.facts.map((f:any)=>({id:f.id,scope:f.scope,text:f.text})),offerings:m.offerings.map((o:any)=>({id:o.id,scope:o.scope,slot:o.slot,src:o.src,uses:o.uses}))})),reviews:raw.reviews.map((r:any)=>({id:r.id,quote:r.quote,author:r.author,label:r.label})),directory:raw.directory.map((d:any)=>({kind:d.kind,href:d.href,title:d.title,copy:d.copy})),readings:raw.readings.map((r:any)=>({id:r.id,label:r.label,body:r.body})),diagnostics:order(raw.diagnostics,lab.scenario.content.diagnostics)};}
const semantic=(s:string)=>s.replace(/<style\b[^>]*>[\s\S]*?<\/style>/g,'').replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,'').replaceAll(' id="experience-main" tabindex="-1"','');
async function pages(){return Promise.all(lab.site.profiles.flatMap(p=>richExperiencePages.map(async page=>{const route=experienceRoute(p.root,page as any),html=await readFile(`dist${route}index.html`,'utf8');return{route,bytes:Buffer.byteLength(html),sha256:sha(html),semantic_sha256:sha(semantic(html))};})));}
if(phase==='verify'){
 const receipt=await json(root+'/after/audit.json'),before=await json(root+'/before/audit.json');
 assert.equal(receipt.site_sha256,lab.site_sha256);assert.deepEqual(await pages(),receipt.pages);
 assert.deepEqual(receipt.pages.map((p:any)=>[p.route,p.semantic_sha256]),before.pages.map((p:any)=>[p.route,p.semantic_sha256]));
 for(const run of [before,receipt]){const b=await json(root+`/${run.phase}/browser.json`);assert.equal(sha(await readFile(root+`/${run.phase}/browser.json`)),run.browser_sha256);for(const v of b.views){assert.deepEqual(auditDepthExperience(binding(v.observation.binding),lab),{success:true,codes:[]});if(v.screenshot){const bytes=await readFile(v.screenshot.path);assert.equal(sha(bytes),v.screenshot.sha256);assert.equal(bytes.length,v.screenshot.bytes);assert((await capturePresence(bytes)).success,'BLANK_B3_CAPTURE');}}for(const t of run.tool_receipts)assert.equal(sha(await readFile(t.path)),t.sha256);}
 const interactions=await json(root+'/after/interactions.json');assert.equal(interactions.records.length,8);
 for(const profile of lab.site.profiles)for(const viewport of ['desktop','mobile']){const r=interactions.records.find((r:any)=>r.profile===profile.id&&r.viewport.id===viewport);assert(r);assert.equal(r.filtered.cards.length,1);assert.equal(r.filtered.cards[0].padding,'0px');assert(r.filtered.cards[0].card.width>=r.filtered.grid.width*.95);assert.equal(r.empty.cards.length,0);assert(r.empty.count.includes('Prueba otra búsqueda'));assert.equal(r.reset.cards.length,4);assert.equal(r.categories.length,4);assert.equal(new Set(r.categories.map((c:any)=>c.cards[0]?.id)).size,4);assert.equal(r.skip.inside_header,false);assert.equal(r.skip.hash,'#experience-main');assert.equal(sha(await readFile(r.screenshot.path)),r.screenshot.sha256);}
 const sample=(await json(root+'/after/browser.json')).views.find((v:any)=>v.page==='home').observation.binding;
 for(const mutate of [(o:any)=>o.modules[0].facts[0].text+=' corrupted',(o:any)=>o.usage_ids=[],(o:any)=>o.navigation.pop()]){const corrupt=structuredClone(sample);mutate(corrupt);assert.equal(auditDepthExperience(binding(corrupt),lab).success,false,'NEGATIVE_GATE_ACCEPTED_CORRUPTION');}
 const ledger=await json(root+'/ledger.json');assert(ledger.operations.length<=ledger.max_operations);assert(ledger.operations.every((o:any)=>o.status==='OK'));
 const paths:string[]=[];async function walk(dir:string){for(const e of await readdir(dir,{withFileTypes:true})){const p=dir+'/'+e.name;if(e.isDirectory())await walk(p);else if(/\.(ts|astro|css|mjs|json|js|png|jpg)$/.test(p)&&p!==root+'/seal.json')paths.push(p);}}
 for(const dir of ['src/components','src/design','scripts',root])await walk(dir);
 const fingerprints=await Promise.all(paths.sort().map(async path=>{const raw=await readFile(path),normalization=path.startsWith(root)?'BINARY':'LF_UTF8',bytes=normalization==='BINARY'?raw:Buffer.from(raw.toString().replaceAll('\r\n','\n'));return{path,normalization,sha256:sha(bytes)};}));
 const seal={kind:'B3_SHARED_MOLD_REFINEMENT',files:fingerprints,negative_gates:3,interaction_sets:8,default_evaluators_enabled:false,human_preference:'NOT_COLLECTED'};
 if(process.argv.includes('--seal')){assert.equal(await access(root+'/seal.json').then(()=>true,()=>false),false,'B3_SOURCE_SEAL_EXISTS');await writeFile(root+'/seal.json',JSON.stringify(seal,null,2)+'\n');}else assert.deepEqual(await json(root+'/seal.json'),seal,'B3_EVALUATION_SOURCE_OR_EVIDENCE_DRIFT');
 console.log(JSON.stringify({status:'B3_TOOLS_EXACT_REPLAY_PASS',profiles:4,routes:44,before_views:before.views.length,after_views:receipt.views.length,operations:ledger.operations.length,semantic_pages_unchanged:44,negative_gates:3,interaction_sets:8,human_preference:'NOT_COLLECTED'}));
}else{
 const dir=root+'/'+phase;await mkdir(dir,{recursive:true});if(await access(dir+'/audit.json').then(()=>true,()=>false))throw Error('B3_EVALUATION_RECEIPT_EXISTS');
 const browser=await json(dir+'/browser.json');assert(browser.views.length>=16);
 const locations=new Set();for(const v of browser.views){const k=v.route+':'+v.viewport.id;assert(!locations.has(k),'DUPLICATE_VIEW');locations.add(k);assert.deepEqual(auditDepthExperience(binding(v.observation.binding),lab),{success:true,codes:[]},k);}
 for(const p of lab.site.profiles)for(const vp of ['desktop','mobile'])for(const page of ['','carta/'])assert(locations.has(p.root+page+':'+vp),'B3_HOME_MENU_COVERAGE');
 const pageRecords=await pages();if(phase==='after'){const prior=await json(root+'/before/audit.json');assert.deepEqual(pageRecords.map(p=>[p.route,p.semantic_sha256]),prior.pages.map((p:any)=>[p.route,p.semantic_sha256]),'B3_CONTENT_MEDIA_OR_NAV_MUTATION');}
 const bridge='../tooling/design-evaluation/raven-client.mjs',detector='../tooling/design-evaluation/impeccable.mjs';const {RavenSession}=await import(bridge),{detect}=await import(detector);
 const ledger=await access(root+'/ledger.json').then(()=>json(root+'/ledger.json'),()=>({schema_version:'1.0.0',max_operations:100,operations:[]}));
 const receipts:any[]=[];
 async function invoke(tool:string,input:any,fn:()=>Promise<any>){if(ledger.operations.length>=ledger.max_operations)throw Error('B3_CUMULATIVE_OPERATION_BUDGET');const path=dir+`/tool-${receipts.length}.json`,entry={phase,tool,input_sha256:inputSha256(input),status:'RESERVED',started_at:new Date().toISOString(),path};ledger.operations.push(entry);await writeFile(root+'/ledger.json',JSON.stringify(ledger,null,2)+'\n');try{const out=await fn();await writeFile(path,JSON.stringify(out,null,2)+'\n');entry.status=out.status==='ERROR'?'ERROR':'OK';receipts.push({tool,path,sha256:sha(await readFile(path))});await writeFile(root+'/ledger.json',JSON.stringify(ledger,null,2)+'\n');assert.equal(entry.status,'OK');return out;}catch(error){entry.status='ERROR';await writeFile(root+'/ledger.json',JSON.stringify(ledger,null,2)+'\n');throw error;}}
 const raven=await new RavenSession().connect(),findings=[];try{
  if(phase==='before'){await invoke('get_principles',{context:'existing B3 restaurant website keyboard skip navigation filtered menu preserve approved typography palette media',format:'checklist'},()=>raven.call('get_principles',{context:'existing B3 restaurant website keyboard skip navigation filtered menu preserve approved typography palette media',format:'checklist'}));await invoke('get_pattern',{type:'navigation',platform:'responsive',goal:'usability'},()=>raven.call('get_pattern',{type:'navigation',platform:'responsive',goal:'usability'}));}
  const scan=await invoke('impeccable.detect',{target:'dist/b3'},()=>detect('dist/b3'));findings.push(...normalizeImpeccable(scan,{route:'/b3/',viewport:'static-html'}));
  for(const v of browser.views.filter((v:any)=>v.page==='home')){const s=v.observation.evaluators,location={route:v.route,viewport:v.viewport.id};for(const [tool,input] of [['audit_layout',{elements:s.layout,viewport:s.viewport}],['audit_typography',{nodes:s.typography}],['audit_contrast',{dom_snapshot:s.contrast}],['audit_tap_targets',{elements:s.targets,minSize:44}]] as const){const out=await invoke(tool,input,()=>raven.call(tool,input));findings.push(...normalizeRaven(out,location));}}
 }finally{await raven.close();}
 const guidance=await Promise.all(['SKILL.md','reference/polish.md','reference/craft-floor.md'].map(async p=>{const path='.agents/skills/impeccable/'+p;return{path,sha256:sha(await readFile(path))};}));
 await writeFile(dir+'/audit.json',JSON.stringify({schema_version:'1.0.0',phase,site_sha256:lab.site_sha256,content_sha256:lab.scenario.content.content_sha256,plan_sha256:lab.scenario.content.plan_sha256,media_sha256:lab.experience_media.review.review_sha256,browser_sha256:sha(await readFile(dir+'/browser.json')),pages:pageRecords,views:browser.views.map((v:any)=>({route:v.route,viewport:v.viewport.id,bindings:'PASS'})),tool_receipts:receipts,findings,guidance,repair_mode:'AGENT_SUPERVISED_SHARED_REFINEMENT',human_preference:'NOT_COLLECTED',default_evaluators_enabled:false,session_tokens:null,session_cost:null},null,2)+'\n');
 console.log(JSON.stringify({phase,routes:44,views:browser.views.length,tool_calls:receipts.length,findings:findings.length,binding_failures:0}));
}
