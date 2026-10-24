import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve,relative,isAbsolute,sep} from 'node:path';
import {loadB2Library} from '../scripts/load-b2-library.ts';
import {verifyMediaLibrary,libraryData,evaluateLibraryUsage,attachmentState,completeMediaCoverage,completeSubjectCoverage} from '../src/media/library.ts';
import {bindMediaFunction} from '../src/media/function-needs.ts';
import {humanReviewCatalog} from '../src/requirements/review-catalog.ts';
import {compileReferenceCorpus} from '../src/media/reference-corpus.ts';
import {diagnoseBoundMedia} from '../src/requirements/media-diagnostic.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const sealed=JSON.parse(await readFile('data/media/library-v1/usda-pilot.json','utf8'));
const pilot=await loadB2Library({evaluation_time:sealed.manifest.evaluated_at}),{handle,library,bundle,requirements,diagnostic}=pilot,at=library.manifest.evaluated_at;
const usage=library.manifest.usages[0]!;
test('real source-reviewed package is verified from bytes, includes lineage and preserves documentary gaps',()=>{
 assert.equal(library.manifest.assets.length,3);assert.equal(new Set(library.manifest.assets.map(a=>a.original_id)).size,1);
 assert(library.manifest.assets.every(a=>a.documentary===null));
 assert(library.brief.gaps.some(g=>g.need.role==='DOCUMENTARY'));
 assert(library.requests.some(n=>n.source==='MASTER_CATALOG'&&n.subject_status==='SUBJECT_PENDING'));
 assert(library.requests.some(n=>n.source==='SEMANTIC_PLAN'&&n.status==='AUTHORIZED'));
 assert.equal(evaluateLibraryUsage(handle,usage,at).status,'ALLOWED');
 assert.equal(library.operations.filter(e=>e.kind==='SINGLE_SELECTED_TRANSFER').length,1);
 assert.equal(library.manifest.usages.filter(u=>u.automated_access.includes('download')).length,1);
 assert(library.bindings.every(b=>b.acquisition_event_id==='acquire-original-D255-19'));
 for(const request of library.requests.filter(r=>r.feature_id!==null))assert(humanReviewCatalog.features.some(f=>f.id===request.feature_id&&f.registry_references.includes(request.capability_id)),'Aspirational feature must actually refer to capability');
});
test('one allowed usage cannot mask another blocked usage or incomplete coverage at the same function/scope',()=>{
 const good=evaluateLibraryUsage(handle,usage,at),bad=evaluateLibraryUsage(handle,{...usage,attribution_text:null},at);
 assert.equal(completeMediaCoverage([good,bad]),false);assert.equal(completeMediaCoverage([good]),true);assert.equal(completeMediaCoverage([]),false);
 assert.equal(completeMediaCoverage([{status:'ALLOWED',codes:['INSPECTION_PENDING']}]),false);
 const needs=[{subject_status:'EXACT' as const,subject_ids:['dish-1']},{subject_status:'EXACT' as const,subject_ids:['dish-2']}];
 assert.equal(completeSubjectCoverage(needs,[{subject_ids:['dish-1']}]),false);
 assert.equal(completeSubjectCoverage(needs,[{subject_ids:['dish-1']},{subject_ids:['dish-2']}]),true);
});
test('serialized handle and self-created VERIFIED review cannot become trusted evidence, even resealed',async()=>{
 assert.throws(()=>libraryData(JSON.parse(JSON.stringify(handle))),/NOT_VERIFIED/);
 const forged=structuredClone(library);forged.manifest.grants[0]!.client_ids.push('another-client');
 const {library_sha256:_,...body}=forged;forged.library_sha256=inputSha256(body);
 const denied=await verifyMediaLibrary(forged,bundle,requirements);assert.equal(denied.success,false);assert(denied.codes.includes('SOURCE_REVIEW_SEAL_MISMATCH'));
 const snapshot=libraryData(handle);snapshot.manifest.grants[0]!.commercial_web='DENIED';assert.equal(evaluateLibraryUsage(handle,usage,at).status,'ALLOWED');
});
test('client, project, purpose, page, branch, territory and misleading subject are checked for each attempted use',()=>{
 for(const [field,value,code] of [['client_id','other','CLIENT_NOT_ALLOWED'],['project_id','other','PROJECT_NOT_ALLOWED'],['purpose','document:menu','PURPOSE_NOT_ALLOWED'],
  ['page','/other','PAGE_NOT_ALLOWED'],['scope_id',bundle.input.locations[0]!.id,'SCOPE_NOT_ALLOWED'],['territory','US','TERRITORY_NOT_ALLOWED']] as const){
  const result=evaluateLibraryUsage(handle,{...usage,[field]:value},at);assert.equal(result.status,'BLOCKED');assert(result.codes.includes(code),`${field}: ${result.codes}`);
 }
 const misleading=evaluateLibraryUsage(handle,{...usage,role:'DOCUMENTARY',representation:'BUSINESS_EVIDENCE',subject_ids:[bundle.input.offerings[0]!.id]},at);
 assert.equal(misleading.status,'BLOCKED');assert(misleading.codes.includes('MISLEADING_BUSINESS_REPRESENTATION'));
});
test('credit, notice, unknown automation/AI, internal review expiry and uninspected transformations block use',()=>{
 const cases=[{edit:{grant_id:null},code:'RIGHTS_UNKNOWN'},{edit:{attribution_text:null},code:'ATTRIBUTION_REQUIRED'},{edit:{context_notices:[]},code:'REQUIRED_NOTICE_MISSING'},
  {edit:{automated_access:['search']},code:'AUTOMATION_NOT_ALLOWED'},{edit:{ai_operations:['embedding']},code:'AI_PROCESSING_NOT_ALLOWED'},
  {edit:{transformations:['CROP']},code:'TRANSFORMATION_NOT_ALLOWED'},{edit:{transformations:['RESIZE']},code:'UNINSPECTED_TRANSFORMED_USAGE'}];
 for(const c of cases){const result=evaluateLibraryUsage(handle,{...usage,...c.edit},at);assert.equal(result.status,'BLOCKED');assert(result.codes.includes(c.code),result.codes.join(','));}
 const expired=evaluateLibraryUsage(handle,usage,library.manifest.grants[0]!.valid_until!);assert.equal(expired.status,'BLOCKED');assert(expired.codes.includes('RIGHTS_EXPIRED'));
});
test('bindings reject another function, feature, page, branch, subject and module',()=>{
 const b=library.bindings[0]!;
 for(const mutation of [{capability_id:'menu'},{feature_id:'offer_detail'},{page:'/other'},{scope_id:bundle.input.locations[0]!.id},{subject_ids:['other-dish']},{module_id:'other-module'}]){
  assert.throws(()=>bindMediaFunction({...b,...mutation},bundle,library.manifest),/FUNCTION_MEDIA_BINDING_MISMATCH/);
 }
});
test('B1 overlay leaves unrelated optional media inactive and cannot use atmosphere to complete documentary roles',()=>{
 const before=inputSha256(diagnostic),overlay=diagnoseBoundMedia(diagnostic,handle,at);
 assert.equal(inputSha256(diagnostic),before);assert.equal(overlay.operational_integrations,'NOT_CONNECTED');
 assert(overlay.entries.filter(e=>e.capability_id==='opening_hours').every(e=>e.status==='NOT_REQUIRED_BY_CONDITION'&&!e.condition_active));
 assert(overlay.entries.filter(e=>e.capability_id==='identity').every(e=>e.status!=='SATISFIED'&&e.codes.includes('CATALOG_ROLE_NOT_COVERED')));
 assert.equal(attachmentState(handle,'identity',bundle.input.business_id,at).authorized_use_exists,true);
 assert.equal(attachmentState(handle,'identity',bundle.input.business_id,at).condition_active,false,'atmosphere is not documentary coverage');
 assert.equal(attachmentState(handle,'menu',bundle.input.locations[0]!.id,at).condition_active,false);
 assert.equal(attachmentState(handle,'identity',bundle.input.business_id,library.manifest.grants[0]!.valid_until!).condition_active,false);
 const forged=structuredClone(diagnostic);forged.business_input_sha256='0'.repeat(64);assert.throws(()=>diagnoseBoundMedia(forged,handle,at),/CONTEXT_MISMATCH/);
});
test('the same loader used by the route/figure blocks a future build after internal review expiry',async()=>{
 await assert.rejects(loadB2Library({evaluation_time:library.manifest.grants[0]!.valid_until!}),/B2_LIBRARY_USE_NOT_CURRENTLY_ALLOWED.*RIGHTS_EXPIRED/);
});
test('registered use identity includes full context, need and label, not just operation flags',()=>{
 for(const mutation of [{generic_label:'Nuestro plato real'},{need_id:'some-other-need'},{representation:'BUSINESS_EVIDENCE'}]){
  const denied=evaluateLibraryUsage(handle,{...usage,...mutation},at);assert.equal(denied.status,'BLOCKED');assert(denied.codes.includes('REGISTERED_USAGE_CHANGED'));
 }
});
test('missing evidence or changed real bytes cannot be replaced by fixture metadata',async()=>{
 const root=await mkdtemp(resolve(tmpdir(),'101-b2-negative-'));
 try{
  for(const f of [...library.files,...library.documents,library.review,library.inspection,library.technical_inspection,library.acquisition]){
   const p=resolve(root,f.path);await mkdir(resolve(p,'..'),{recursive:true});await writeFile(p,await readFile(f.path));
  }
  await writeFile(resolve(root,library.files[1]!.path),'not the inspected derivative');
  const result=await verifyMediaLibrary(library,bundle,requirements,root);assert.equal(result.success,false);assert(result.codes.includes('LIBRARY_FILE_OR_DOCUMENT_HASH_MISMATCH'));
 }finally{const rel=relative(resolve(tmpdir()),root);if(isAbsolute(rel)||rel.startsWith('..')||!rel.startsWith('101-b2-negative-')||rel.includes(sep))throw Error('UNSAFE_TEMP_CLEANUP');await rm(root,{recursive:true,force:true});}
});
test('all 21 reported references retain literal sections and partial approvals, never new votes or asset permission',async()=>{
 const bytes=await readFile('data/reference/design/101_referencias_aprobadas_completas_v01.md'),source=bytes.toString(),corpus=compileReferenceCorpus(bytes);
 assert.equal(corpus.references.length,21);assert.equal(corpus.references.filter(r=>r.approved_scope==='GLOBAL_REPORTED').length,18);
 for(const r of corpus.references){assert(source.includes(r.source_section_literal));assert.equal((r.source_section_literal.match(/^### /gm)??[]).length,1);
  assert.equal(r.inspected_at,null);assert.deepEqual(r.new_observations,[]);assert.equal(r.asset_reuse,'NOT_AUTHORIZED_BY_REFERENCE');}
 assert.equal(corpus.references[11]!.approved_scope,'SPECIFIC_PAGE_ONLY');assert.equal(corpus.references[12]!.approved_scope,'STORYTELLING_ONLY');assert.equal(corpus.references[20]!.approved_scope,'DROPDOWN_ONLY');
 assert(corpus.references[13]!.negative_or_limit_lines.some(s=>s.includes('escritorio')));assert(corpus.negative_references_section_literal.includes('Othership'));
 assert(!corpus.references[0]!.source_section_literal.includes('Central Restaurante\r\n\r\n-'));
});
