import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {hashBytes,treeHashes,verifyProtectedFiles,workspacePath} from './lib/correction-run.ts';
import {verifyRuntime} from './lib/correction-runtime.ts';
import {verifyJournal,verifyViewCoverage} from './lib/correction-evidence.ts';
import {browserSourceOverlay,B0_BROWSER_FLAGS} from './lib/correction-browser.ts';
import {DesignLockV1} from '../src/lock/contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {decodeScreenshot} from '../src/audit/png.ts';
import {measurePixels} from '../src/audit/raster.ts';
import {auditCandidate} from '../src/audit/evaluate.ts';
import type {BrowserView} from '../src/audit/evaluate.ts';
import type {GeneralCompositionLab} from '../src/composition/lab.ts';

const id=process.argv[2],baseline=process.argv[3];
if(!id||!baseline||![id,baseline].every(v=>/^[a-z0-9-]+$/.test(v)))throw Error('Usage: b0-verify.ts <capture-id> <baseline-id>');
const directory=`docs/evidence/corrections/b0/${id}`;
const receipt=JSON.parse(await readFile(`${directory}/capture.json`,'utf8'));
const runtime=await verifyRuntime();
if(receipt.status!=='CONTROLLED_SAME_HOST_REPEATABILITY_PASS'||receipt.production_ready!==false||
 receipt.runtime_sha256!==runtime.snapshot_sha256||receipt.metering.human_approval!=='NOT_COLLECTED'||
 [receipt.metering.human_work_seconds,receipt.metering.total_cost,receipt.metering.session_tokens].some(v=>v!==null))throw Error('B0_INVALID_CAPTURE_STATUS');
for(const pin of receipt.recipe)if(hashBytes(await readFile(workspacePath(process.cwd(),pin.path)))!==pin.sha256)throw Error('B0_RECIPE_DRIFT');
const source=await readFile('scripts/lib/local-browser.ts','utf8');
if(receipt.browser_harness.source_sha256!==hashBytes(source)||receipt.browser_harness.adapted_sha256!==hashBytes(browserSourceOverlay(source))||
 hashBytes(await readFile(`${directory}/browser-harness.ts.txt`))!==receipt.browser_harness.adapted_sha256||
 inputSha256(receipt.browser_harness.flags)!==inputSha256(B0_BROWSER_FLAGS)||receipt.browser_harness.production_browser!==false)throw Error('B0_HARNESS_DRIFT');
const locks=await Promise.all(['pilot-flow','pilot-rail','hybrid-no-media'].map(async name=>DesignLockV1.parse(JSON.parse(await readFile(`fixtures/locks/h8/${name}.json`,'utf8')))));
const routeFor=(lock:typeof locks[number],path:string)=>`/${lock.mount.kind}/${lock.mount.id}${path==='/'?'/':`${path}/`}`;
const expected=locks.flatMap(lock=>lock.environment.viewports.flatMap(viewport=>lock.resolved_plan.pages.map(page=>({label:'',lock_id:lock.id,semantic_page:page.path,viewport}))));
if(receipt.captures.length!==2||receipt.outputs.length!==2)throw Error('B0_BUILD_COVERAGE');
const history=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8'));
for(const [iteration,group] of receipt.captures.entries()) {
 if(group.browser!==runtime.browser_version)throw Error('B0_CAPTURE_BROWSER_DRIFT');
 verifyViewCoverage(group.receipts,expected);
 for(const view of group.receipts) {
  const lock=locks.find(lock=>lock.id===view.lock_id)!;
  const relative=(path:string)=>{
   if(!path.startsWith(directory+'/'))throw Error('B0_ARTIFACT_SCOPE');return workspacePath(process.cwd(),path);
  };
  const png=await readFile(relative(view.screenshot_path)),html=await readFile(relative(view.html_path)),decoded=decodeScreenshot(png);
  if(hashBytes(png)!==view.screenshot_sha256||hashBytes(html)!==view.html_sha256||hashBytes(decoded.pixels)!==view.decoded_rgba_sha256||
   decoded.width!==view.capture_size.width||decoded.height!==view.capture_size.height||view.lock_sha256!==lock.lock_sha256||
   view.route!==routeFor(lock,view.semantic_page))throw Error('B0_CAPTURE_BYTES_CHANGED');
  if(view.blocked_requests.length||view.browser_exceptions.length||view.page_requests.some((url:string)=>!url.startsWith('<LOCAL>/')&&!url.startsWith('data:')))throw Error('B0_NONLOCAL_OR_EXCEPTION');
  const raster=measurePixels(decoded.pixels,decoded.width,decoded.height,view.view.geometry.image);
  if(inputSha256(raster)!==inputSha256(view.view.raster))throw Error('B0_RASTER_CHANGED');
  const candidate={schema_version:'1.0.0',plan:lock.resolved_plan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}} as const;
  const audit=auditCandidate(candidate,lock.lab as GeneralCompositionLab,view.view as BrowserView,
   {schema_version:'1.0.0',profile:'LAB',max_page_bytes:2500000,max_requests:3,max_client_js_bytes:0,original_media_exception:true},path=>routeFor(lock,path));
  if(audit.status!=='LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW'||inputSha256(audit)!==inputSha256(view.audit))throw Error('B0_AUDIT_CHANGED');
  const media=(lock.lab as GeneralCompositionLab).media;
  const expectedMedia=media&&media.usage.page===view.semantic_page?media.asset.file_sha256:null;
  if(view.served_media_sha256!==expectedMedia)throw Error('B0_MEDIA_CHANGED');
  const historic=history.originals.find((v:{label:string})=>v.label===`${lock.id}-original`).views.find((v:{semantic_page:string;viewport:{id:string}})=>v.semantic_page===view.semantic_page&&v.viewport.id===view.viewport.id);
  const old=decodeScreenshot(await readFile(historic.screenshot_path));
  if(!view.historical_html_equal||!view.historical_pixels_equal||hashBytes(html)!==historic.html_sha256||decoded.width!==old.width||decoded.height!==old.height||
   !Buffer.from(decoded.pixels).equals(Buffer.from(old.pixels)))throw Error('B0_HISTORICAL_DIFFERENCE');
  const other=receipt.captures[1-iteration].receipts.find((v:{label:string})=>v.label===view.label);
  const observable=(v:typeof view)=>({observation:v.view.observation,geometry:v.view.geometry,readability:v.view.readability,fonts:v.fonts,media:v.served_media_sha256});
  if(!other||other.html_sha256!==view.html_sha256||other.decoded_rgba_sha256!==view.decoded_rgba_sha256||inputSha256(observable(view))!==inputSha256(observable(other)))throw Error('B0_REPEATABILITY_CHANGED');
 }
}
for(const output of receipt.outputs) {
 if(!resolve(output.out).startsWith(resolve(`.tools/corrections/b0/${id}`)+'\\'))throw Error('B0_OUTPUT_SCOPE');
 const files=(await treeHashes(output.out)).filter(f=>!f.path.startsWith('.'));
 if(inputSha256(files)!==inputSha256(output.files))throw Error('B0_OUTPUT_CHANGED');
}
if(inputSha256(receipt.outputs[0].files)!==inputSha256(receipt.outputs[1].files))throw Error('B0_BUILD_DIFFERENCE');
const builds=await verifyJournal(`${directory}/journal.json`);
if(builds.steps.length!==2||builds.steps.some((step,index)=>step.id!==`build-${index===0?'a':'b'}`||step.status!=='PASS'))throw Error('B0_BUILD_JOURNAL_COVERAGE');
const journal=await verifyJournal(`docs/evidence/corrections/b0/${baseline}/journal.json`,true);
const preservation=await verifyProtectedFiles('docs/evidence/corrections/b0/pre/protected-files.json');
console.log(JSON.stringify({status:'B0_CONTROLLED_CAPTURE_VERIFIED',captures:32,repeatability_pairs:16,historical_match:true,
 protected_files:preservation.checked_files,baseline_passes:journal.steps.filter(s=>s.status==='PASS').length,
 legacy_environment_blocks:journal.steps.filter(s=>s.status==='BLOCKED_HISTORICAL_ENVIRONMENT').map(s=>s.id),human_approval:'NOT_COLLECTED',production_ready:false},null,2));
