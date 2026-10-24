import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {hashBytes,verifyProtectedFiles,workspacePath} from './lib/correction-run.ts';
import {verifyJournal} from './lib/correction-evidence.ts';
import {verifyRuntime} from './lib/correction-runtime.ts';
import {decodeScreenshot} from '../src/audit/png.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {loadB1Fixtures} from './lib/b1-fixtures.ts';
import {loadMappingRegistry} from './load-taxonomy.ts';
import {requirementCatalog,validateRequirementCatalog} from '../src/requirements/catalog.ts';
import {verifyFunctionalDiagnostic} from '../src/requirements/diagnose.ts';
const qaId=process.argv[2],baselineId=process.argv[3];
if(!qaId||!baselineId||![qaId,baselineId].every(id=>/^[a-z0-9-]+$/.test(id)))throw Error('Usage: b1-verify.ts <qa-id> <baseline-id>');
const directory=`docs/evidence/corrections/b1/${qaId}`,qa=JSON.parse(await readFile(`${directory}/qa.json`,'utf8')),runtime=await verifyRuntime();
if(qa.status!=='LAB_INSPECTOR_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW'||qa.production_ready!==false||qa.runtime_sha256!==runtime.snapshot_sha256||
 qa.catalog_sha256!==requirementCatalog.catalog_sha256||qa.metering.total_cost!==null||qa.metering.human_work_seconds!==null||qa.metering.session_tokens!==null)throw Error('B1_QA_STATUS_INVALID');
validateRequirementCatalog(requirementCatalog);
const fixtures=await loadB1Fixtures(),{rules}=await loadMappingRegistry();
const expectedRoutes=['/b1/','/b1/catalogo/',...fixtures.map(f=>`/b1/${f.scenario}/`)];
const keys=new Set<string>();
for(const view of qa.views) {
 const key=`${view.route}|${view.viewport.id}|${view.state}`;
 if(keys.has(key)||!expectedRoutes.includes(view.route)||!['desktop','mobile'].includes(view.viewport.id)||
  !(view.state==='default'||view.route==='/b1/restaurante/'&&view.state==='reservation-expanded'))throw Error('B1_QA_COVERAGE_INVALID');keys.add(key);
 for(const path of [view.html_path,view.screenshot_path])if(!path.startsWith(directory+'/'))throw Error('B1_QA_ARTIFACT_SCOPE');
 const png=await readFile(workspacePath(process.cwd(),view.screenshot_path)),html=await readFile(workspacePath(process.cwd(),view.html_path)),decoded=decodeScreenshot(png);
 if(hashBytes(png)!==view.screenshot_sha256||hashBytes(html)!==view.html_sha256||hashBytes(decoded.pixels)!==view.rgba_sha256||decoded.width!==view.capture_size.width||decoded.height!==view.capture_size.height)throw Error('B1_QA_BYTES_CHANGED');
 const observed=view.observed;
 if(observed.main_count!==1||observed.h1_count!==1||observed.lang!=='es'||observed.document.width>view.viewport.width||observed.overflow.length||observed.forms||observed.buttons||observed.scripts||observed.media||
  observed.resources.some((r:{local:boolean})=>!r.local)||observed.readability.some((r:{font_px:number;contrast:number})=>r.font_px<12||r.contrast<4.5)||
  !view.keyboard.skip||!view.keyboard.disclosure||!view.keyboard.navigation||view.browser_exceptions.length||view.requests.some((u:string)=>!u.startsWith('<LOCAL>/')&&!u.startsWith('data:')))throw Error('B1_QA_GATE_CHANGED');
 if(observed.root.b1Page==='case') {
  const fixture=fixtures.find(f=>view.route===`/b1/${f.scenario}/`)!;
  const value=JSON.parse(await readFile(`data/derived/requirements-v1/${fixture.scenario}.json`,'utf8'));
  const diagnostic=verifyFunctionalDiagnostic(value.diagnostic,fixture.input,{rules,activity_links:fixture.activity_links,activity_relationships:fixture.activity_relationships,category_context:fixture.category_context,objective_decisions:fixture.objective_decisions});
  const goals=diagnostic.entries.map(e=>({scope_id:e.scope_id,capability_id:e.capability_id,relevance:e.relevance,emitted:String(e.emitted_in_plan)}));
  const fields=diagnostic.entries.flatMap(e=>e.levels.flatMap(l=>l.requirements.map(r=>({scope_id:e.scope_id,capability_id:e.capability_id,level_id:l.level_id,requirement_id:r.requirement_id,status:r.status,owner:r.owner}))));
  const ordered=(a:unknown[])=>[...a].sort((a,b)=>inputSha256(a).localeCompare(inputSha256(b)));
  if(observed.root.diagnosticSha256!==diagnostic.diagnostic_sha256||observed.root.contextualSha256!==value.context.interpretation_sha256||
   inputSha256(ordered(goals))!==inputSha256(ordered(observed.goals))||inputSha256(ordered(fields))!==inputSha256(ordered(observed.fields)))throw Error('B1_BINDING_CHANGED');
 }
 if(observed.root.b1Page==='catalog'&&(inputSha256([...observed.catalog_cards].sort())!==inputSha256(requirementCatalog.cards.map(c=>c.id).sort())||observed.root.catalogSha256!==requirementCatalog.catalog_sha256))throw Error('B1_CATALOG_RENDER_CHANGED');
}
if(keys.size!==expectedRoutes.length*2+2||expectedRoutes.some(route=>['desktop','mobile'].some(viewport=>!keys.has(`${route}|${viewport}|default`)))||
 ['desktop','mobile'].some(viewport=>!keys.has(`/b1/restaurante/|${viewport}|reservation-expanded`)))throw Error('B1_QA_COVERAGE_MISSING');
const history=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8')),historical=history.originals.flatMap((group:{views:{view:{route:string};viewport:{id:string};html_sha256:string}[]})=>group.views.map(v=>({route:v.view.route,viewport:v.viewport.id,sha256:v.html_sha256})));
if(inputSha256(qa.legacy_html)!==inputSha256(historical))throw Error('B1_LEGACY_EQUIVALENCE_CHANGED');
for(const file of qa.legacy_html)if(hashBytes(await readFile(resolve(`.tools/corrections/b0/b1-qa/${qaId}`,`.${file.route}index.html`)))!==file.sha256)throw Error('B1_LEGACY_OUTPUT_CHANGED');
const journal=await verifyJournal(`docs/evidence/corrections/b1/${baselineId}/journal.json`);
const expected=['contracts','tests','check','validate','build','b1-replay','taxonomy','planner-replay','media-replay','media-verify','composition-replay','composition-verify','design-replay','design-verify','audit-verify','cohort-replay','cohort-verify','lock-verify','h9-inventory'];
if(journal.steps.length!==expected.length||expected.some(id=>!journal.steps.some(s=>s.id===id)))throw Error('B1_BASELINE_COVERAGE');
const build=await verifyJournal(`${directory}/journal.json`);if(build.steps.length!==1||build.steps[0]!.id!=='build'||build.steps[0]!.status!=='PASS')throw Error('B1_QA_BUILD_RECEIPT');
const preservation=await verifyProtectedFiles('docs/evidence/corrections/b1/pre/preservation.json');
console.log(JSON.stringify({status:'B1_TECHNICAL_EVIDENCE_VERIFIED',qa_views:keys.size,legacy_html:historical.length,protected_files:preservation.checked_files,
 catalog_capabilities:47,catalog_levels:requirementCatalog.cards.reduce((n,c)=>n+c.levels.length,0),definitions:requirementCatalog.definitions.length,
 baseline_passes:journal.steps.filter(s=>s.status==='PASS').length,legacy_blocks:journal.steps.filter(s=>s.status!=='PASS').map(s=>s.id),
 operational_integrations:'NOT_CONNECTED',human_design_approval:'NOT_COLLECTED'},null,2));
