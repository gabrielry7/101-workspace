import assert from 'node:assert/strict';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import sharp from 'sharp';
import {loadQualityLab,qualityPath} from './load-quality-lab.ts';
import {auditRender} from '../src/composition/audit.ts';
import {bindingObservation} from '../src/design/evaluators/binding-observation.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {DesignFindingV1} from '../src/design/evaluators/contracts.ts';
const hash=(v:Uint8Array|string)=>createHash('sha256').update(v).digest('hex');
const directory='docs/evidence/design-evaluation',run=await loadQualityLab(),browsers=await Promise.all([0,1].map(async i=>JSON.parse(await readFile(`${directory}/iteration-${i}/browser.json`,'utf8')))),audits=await Promise.all([0,1].map(async i=>JSON.parse(await readFile(`${directory}/iteration-${i}/audit.json`,'utf8'))));
const expected=run.cases.flatMap(c=>c.variants.flatMap(v=>v.design.pages.flatMap(p=>['desktop','mobile'].map(vp=>`${qualityPath(c.id,v.condition,p.path)}:${vp}`)))).sort();
const files=new Set<string>(),pngs=[];
for(let i=0;i<2;i++){
 const browser=browsers[i],audit=audits[i];assert.equal(browser.experiment_id,run.experiment_id);assert.equal(audit.experiment_id,run.experiment_id);
 assert.ok(audit.raven_calls.every((c:any)=>c.status==='OK'),'REQUIRED_RAVEN_AUDIT_FAILED');
 assert.ok(audit.impeccable_calls.every((c:any)=>[0,2].includes(c.exit_code)),'REQUIRED_IMPECCABLE_SCAN_FAILED');
 assert.equal(new Set(browser.receipts.map((v:any)=>`${v.route}:${v.viewport.id}`)).size,expected.length);
 assert.deepEqual(browser.receipts.map((v:any)=>`${v.route}:${v.viewport.id}`).sort(),expected);
 assert.deepEqual(audit.views.map((v:any)=>`${v.route}:${v.viewport}`).sort(),expected);
 for(const view of browser.receipts){
  const c=run.cases.find(c=>c.id===view.case_id)!,v=c.variants.find(v=>v.condition===view.condition)!;
  const gate=auditRender(bindingObservation(view.observation.base.observation),c.lab,'editorial',view.page,p=>qualityPath(c.id,v.condition,p));assert.deepEqual(gate,{success:true,codes:[]});
  const a=audit.views.find((a:any)=>a.route===view.route&&a.viewport===view.viewport.id);assert.deepEqual(a.bindings,gate);assert.equal(a.findings.some((f:any)=>f.severity==='BLOCKING'),false);a.findings.forEach((f:any)=>DesignFindingV1.parse(f));
  if(v.flags.raven){const s=view.observation.evaluators;for(const [tool,input] of [['audit_layout',{elements:s.layout,viewport:s.viewport}],['audit_typography',{nodes:s.typography}],['audit_contrast',{dom_snapshot:s.contrast}],['audit_tap_targets',{elements:s.targets,minSize:44}]] as const)assert.ok(audit.raven_calls.some((r:any)=>r.tool===tool&&inputSha256(r.input)===inputSha256(input)),`RAVEN_SNAPSHOT_COVERAGE:${view.route}:${tool}`);}
  if(v.flags.impeccable)assert.ok(audit.impeccable_calls.some((r:any)=>r.target===`dist${view.route}index.html`),'IMPECCABLE_ROUTE_COVERAGE');
  const bytes=await readFile(view.screenshot.path);assert.equal(hash(bytes),view.screenshot.sha256);assert.equal(bytes.length,view.screenshot.bytes);assert.equal(view.screenshot.full_page,true);
  const m=await sharp(bytes).metadata(),stats=await sharp(bytes).resize({width:160}).toBuffer().then(b=>sharp(b).stats());
  assert.ok(m.width!>=view.viewport.width-20&&m.height!>=view.viewport.height-20);assert.ok(stats.channels.some(c=>c.max-c.min>32),'BLANK_SCREENSHOT');
  if(i===1){assert.equal(view.paint_stability?.status,'TWO_IDENTICAL_CONSECUTIVE_CAPTURES');assert.equal(view.paint_stability?.sha256,hash(bytes));assert.ok(m.height!>=Math.max(view.viewport.height,view.observation.evaluators.document_height)-20,'INCOMPLETE_FULL_PAGE');}
  pngs.push({path:view.screenshot.path,width:m.width,height:m.height,bytes:bytes.length,sha256:hash(bytes)});files.add(view.screenshot.path);
  if(i===1){const htmlPath=`dist${view.route}index.html`,html=await readFile(htmlPath,'utf8');assert.equal(inputSha256(html),a.metrics.html_sha256);assert.equal(/<script\b/.test(html),false,'EVALUATOR_RUNTIME_IN_SITE');files.add(htmlPath);}
 }
}
const judgment=JSON.parse(await readFile(`${directory}/judgment-1.json`,'utf8'));assert.equal(judgment.decisions.length,2);assert.ok(judgment.decisions.every((d:any)=>d.keep&&d.before>d.after));
const live=JSON.parse(await readFile(`${directory}/raven-url.json`,'utf8'));assert.equal(live.length,2);assert.ok(live.every((c:any)=>c.status==='OK'&&c.output.coverage.complete&&c.output.coverage.succeeded===2));
const toolCalls=run.metering.preflight_tool_calls+audits.reduce((n,a)=>n+(a.new_tool_calls??a.raven_calls.length+a.impeccable_calls.length),0)+live.length;assert.ok(toolCalls<=run.budget.max_tool_calls,'TOOL_CALL_BUDGET_EXCEEDED');
const stop=JSON.parse(await readFile(`${directory}/repair-2.json`,'utf8'));assert.ok(stop.decisions.every((d:any)=>['BASELINE_FROZEN','STOP_NO_SAFE_PATCH'].includes(d.status)));
const preservation=JSON.parse(await readFile('docs/evidence/corrections/b3/pre/preservation.json','utf8')),allowed:string[]=[];let preserved=0;
for(const f of preservation.files){if(allowed.includes(f.path))continue;const bytes=await readFile(f.path),normalized=f.normalization==='BINARY'?bytes:Buffer.from(bytes.toString().replaceAll('\r\n','\n'));assert.equal(hash(normalized),f.sha256,`PROTECTED_INPUT_CHANGED:${f.path}`);preserved++;}
const walk=async(path:string)=>{for(const entry of await readdir(path,{withFileTypes:true})){const f=`${path}/${entry.name}`;if(entry.isDirectory()){if(entry.name!=='node_modules'&&entry.name!=='state')await walk(f);}else files.add(f);}};
for(const p of ['src/design/evaluators','src/pages/quality','src/components/quality','tooling/design-evaluation','contracts/design/evaluation-v1','data/derived/design-evaluation-v1'])await walk(p);
for(const f of await readdir('scripts'))if(f.startsWith('quality-')||f==='load-quality-lab.ts')files.add(`scripts/${f}`);
files.add('tests/design-evaluators.test.ts');files.add('src/components/composition/DesignComposition.astro');
files.add('astro.config.mjs');
for(const f of ['preflight/raven.json','iteration-0/browser.json','iteration-0/audit.json','iteration-1/browser.json','iteration-1/audit.json','repair-1.json','repair-2.json','judgment-1.json','raven-url.json','raven-url-initial-unavailable.json','interactions.json','capture-anomalies/hotel-b-mobile-stale-paint.png','baseline-without-tools.json','baseline-without-tools.txt','comparison-panel.json','comparison-desktop.png','comparison-mobile.json','comparison-mobile.png'])files.add(`${directory}/${f}`);
const fingerprints=await Promise.all([...files].sort().map(async path=>{const raw=await readFile(path),normalization=(/\.(ts|mjs|astro|css|json)$/.test(path)||path.endsWith('/.gitignore'))&&!path.startsWith('docs/evidence/')?'LF_UTF8':'BINARY',b=normalization==='BINARY'?raw:Buffer.from(raw.toString().replaceAll('\r\n','\n'));return{path,normalization,bytes:b.length,sha256:hash(b)};}));
const seal={schema_version:'1.0.0',experiment_id:run.experiment_id,files:fingerprints,screenshots:pngs,preservation:{checked:preserved,associated_extensions:allowed},status:'TECHNICAL_PILOT_NEEDS_HUMAN_PREFERENCE',human_preference:'NOT_COLLECTED',external_business_validation:'PENDING'};
if(process.argv.includes('--seal')){await writeFile(`${directory}/seal.json`,JSON.stringify(seal,null,2)+'\n');console.log(JSON.stringify({status:'SEALED_TECHNICAL_PILOT',final_views:40,initial_observations:40,preserved,files:fingerprints.length}));}
else{assert.deepEqual(JSON.parse(await readFile(`${directory}/seal.json`,'utf8')),seal);console.log(JSON.stringify({status:'EXACT_REPLAY_PASS',final_views:40,initial_observations:40,preserved,files:fingerprints.length,human_preference:'NOT_COLLECTED'}));}
