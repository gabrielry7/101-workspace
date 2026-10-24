// Post-capture verification recipe. Run from repository root with Node 24 and
// --experimental-strip-types. Reads captured bytes and never repairs receipts.
import {readFile,writeFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const fromRoot=path=>import(pathToFileURL(resolve(path)).href);
const {hashBytes,workspacePath,verifyProtectedFiles}=await fromRoot('scripts/lib/correction-run.ts');
const {verifyJournal}=await fromRoot('scripts/lib/correction-evidence.ts');
const {decodeScreenshot}=await fromRoot('src/audit/png.ts');
const {humanReviewCatalog:catalog,reviewFeaturesForProfile}=await fromRoot('src/requirements/review-catalog.ts');
const {validateHumanReviewCatalog}=await fromRoot('src/requirements/review-contracts.ts');
const output='docs/evidence/corrections/b1/human-review-reproduction/comparison.json';
if(await access(output).then(()=>true,()=>false))throw Error('RECEIPT_EXISTS');
const paths=['docs/evidence/corrections/b1/human-review-browser-delivery','docs/evidence/corrections/b1/human-review-clean-pinned-browser'];
const receipts=[],pins=[];
for(const path of paths){
 const qa=JSON.parse(await readFile(`${path}/qa.json`,'utf8'));
 assert.equal(qa.status,'TECHNICAL_PASS_HUMAN_REVIEW_PENDING');assert.equal(qa.catalog_sha256,catalog.catalog_sha256);assert.equal(qa.views.length,32);
 const saved=validateHumanReviewCatalog(JSON.parse(await readFile(`${path}/catalog.json`,'utf8')));assert.deepEqual(saved,catalog);
 assert.equal(new Set(qa.views.map(v=>v.label)).size,32);
 for(const view of qa.views){
  assert(view.observed.width<=view.viewport.width);assert.equal(view.observed.overflow.length,0);
  assert(view.keyboard.skip&&view.keyboard.disclosure&&view.keyboard.navigation);assert.equal(view.observed.forms+view.observed.scripts+view.observed.media,0);
  const profile=view.observed.root.reviewProfile;
  const ids=profile?reviewFeaturesForProfile(profile).map(e=>e.feature.id):[];assert.deepEqual([...view.observed.feature_ids].sort(),ids.sort());
  const png=await readFile(workspacePath(process.cwd(),view.screenshot.path));assert.equal(hashBytes(png),view.screenshot.sha256);
  const html=await readFile(`${path}/review-${profile??'index'}-desktop-default.html`);assert.equal(hashBytes(html),view.html_sha256);
  pins.push({receipt:path,label:view.label,png_sha256:hashBytes(png),rgba_sha256:hashBytes(decodeScreenshot(png).pixels),html_sha256:hashBytes(html)});
 }
 assert.equal(qa.legacy_html.length,16);assert.equal(qa.preservation.checked_files,1330);receipts.push(qa);
}
const pairs=receipts[0].views.map(a=>{
 const b=receipts[1].views.find(b=>b.label===a.label);assert(b);assert.deepEqual(a.observed,b.observed);assert.equal(a.html_sha256,b.html_sha256);
 const pa=pins.find(p=>p.receipt===paths[0]&&p.label===a.label),pb=pins.find(p=>p.receipt===paths[1]&&p.label===a.label);
 assert.equal(pa.rgba_sha256,pb.rgba_sha256);return {label:a.label,html:'IDENTICAL',rgba:'IDENTICAL',observed:'IDENTICAL'};
});
const journals=[];
for(const path of ['human-review-final-scope','human-review-clean-pinned']){
 const journal=await verifyJournal(`docs/evidence/corrections/b1/${path}/journal.json`);assert.equal(journal.steps.length,19);
 journals.push({path,steps:journal.steps.map(s=>({id:s.id,status:s.status}))});
}
await writeFile(output,JSON.stringify({kind:'B1_HUMAN_REVIEW_REPRODUCTION_COMPARISON',status:'PASS',created_at:new Date().toISOString(),
 source_tree:'a4d85dcff7257e1761dfcd1aced1c3d98b8df58a',catalog_sha256:catalog.catalog_sha256,paths,pairs,pins,journals,
 preservation:await verifyProtectedFiles('docs/evidence/corrections/b1/pre/preservation.json'),scope:'SAME_HOST_VERIFIED_RUNTIME_DECLARED_BYTE_PIN_OVERLAYS'},null,2)+'\n');
console.log(`PASS: ${pairs.length} HTML/RGBA/DOM pairs; ${pins.length} screenshots; 2 checked journals; original protected bytes retained`);
