import sharp from 'sharp';
import {MediaUsageV1} from './contracts.ts';
import type {FixtureBundle} from '../contracts/v1/schemas.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {MediaLibraryV1} from './library-contracts.ts';
import type {MediaLibrary} from './library-contracts.ts';
import {readPackageFile,byteSha256} from './package.ts';
import {validateMediaManifest} from './plan.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {functionMediaRequests,bindMediaFunction} from './function-needs.ts';
import {requirementCatalog} from '../requirements/catalog.ts';
import {humanReviewCatalog} from '../requirements/review-catalog.ts';

// Trust anchor for this ONE source-reviewed package, not a fixture-supplied
// VERIFIED flag, provider-wide license or generic document classifier.
export const B2_REVIEWED_LIBRARY_SHA256='56149318785d0990032e2b902aab01ad15879d1924f4e423c2e2c382eb6a1e45';
export type VerifiedLibrary={readonly library_sha256:string};
const verified=new WeakMap<VerifiedLibrary,{library:MediaLibrary;bundle:FixtureBundle}>();
export async function verifyMediaLibrary(value:unknown,bundle:FixtureBundle,requirements:unknown,root=process.cwd()) {
 const parsed=MediaLibraryV1.safeParse(value);if(!parsed.success)return {success:false as const,codes:['LIBRARY_SCHEMA_INVALID']};
 const library=parsed.data,{library_sha256,...body}=library,codes:string[]=[];
 if(inputSha256(body)!==library_sha256)codes.push('LIBRARY_HASH_MISMATCH');
 if(library_sha256!==B2_REVIEWED_LIBRARY_SHA256)codes.push('SOURCE_REVIEW_SEAL_MISMATCH');
 if(library.catalog_sha256!==requirementCatalog.catalog_sha256||library.review_catalog_sha256!==humanReviewCatalog.catalog_sha256)codes.push('LIBRARY_CATALOG_MISMATCH');
 if(codes.length)return {success:false as const,codes};
 try {
  for(const file of [...library.files,...library.documents,library.review,library.inspection,library.technical_inspection,library.acquisition]){
   const bytes=await readPackageFile(file.path,root);if(bytes.length!==file.bytes||byteSha256(bytes)!==file.sha256)codes.push('LIBRARY_FILE_OR_DOCUMENT_HASH_MISMATCH');
  }
  const source=await readPackageFile(library.documents[0]!.path,root),policy=await readPackageFile(library.documents[1]!.path,root);
  if(library.documents.length!==2||library.documents[0]!.official_url!=='https://www.ars.usda.gov/oc/images/photos/featuredphoto/mar23/bell-peppers/'||
   library.documents[1]!.official_url!=='https://www.ars.usda.gov/oc/images/copyright/'||!source.toString().includes('Copyright free, public domain image')||
   !source.toString().includes('Photo by Steve Ausmus, USDA/ARS')||!source.toString().includes('/ARSUserFiles/oc/images/photos/300dpi/kesa/D255-19.jpg')||
   !policy.toString().includes('infer or imply ARS endorsement'))codes.push('OFFICIAL_SOURCE_CORROBORATION_MISSING');
  const technical=JSON.parse((await readPackageFile(library.technical_inspection.path,root)).toString()) as {legal_review_sha256:string;files:{asset_id:string;sha256:string;width:number;height:number;codec:string}[]};
  if(technical.legal_review_sha256!==library.review.sha256)codes.push('PROCESSING_PERMISSION_REVIEW_MISMATCH');
  for(const file of library.files){
   const asset=library.manifest.assets.find(a=>a.id===file.asset_id),receipt=technical.files.find(f=>f.asset_id===file.asset_id),bytes=await readPackageFile(file.path,root);
   const metadata=await sharp(bytes).metadata();await sharp(bytes).raw().toBuffer();
   if(!asset||asset.data_mode!=='REAL'||asset.file_sha256!==file.sha256||`public${asset.uri}`!==file.path||!receipt||receipt.sha256!==file.sha256||
    metadata.width!==asset.inspection.width||metadata.height!==asset.inspection.height||metadata.format!==asset.inspection.codec||
    metadata.width!==receipt.width||metadata.height!==receipt.height)codes.push('ACTUAL_INSPECTION_MISMATCH');
  }
  const context={client_id:library.manifest.client_id,project_id:library.manifest.project_id,evaluated_at:library.manifest.evaluated_at};
  if(!validateMediaManifest(library.manifest,library.brief,bundle,requirements,context).success)codes.push('LIBRARY_MANIFEST_MISMATCH');
  if(inputSha256(library.requests)!==inputSha256(functionMediaRequests(bundle,library.manifest)))codes.push('LIBRARY_REQUESTS_MISMATCH');
  if(new Set(library.bindings.map(b=>b.id)).size!==library.bindings.length||new Set(library.bindings.map(b=>b.usage_id)).size!==library.bindings.length||
   library.manifest.usages.some(u=>!library.bindings.some(b=>b.usage_id===u.id)))codes.push('LIBRARY_BINDING_COVERAGE_MISMATCH');
  for(const b of library.bindings)bindMediaFunction(b,bundle,library.manifest);
  const transfers=library.operations.filter(e=>e.kind==='SINGLE_SELECTED_TRANSFER');
  const rootAsset=library.manifest.assets.find(a=>!a.parent_id);
  const acquisition=JSON.parse((await readPackageFile(library.acquisition.path,root)).toString());
  const rootFile=library.files.find(f=>f.asset_id===rootAsset?.id);
  if(acquisition.kind!=='B2_SINGLE_SELECTED_ACQUISITION'||acquisition.file?.source_url!=='https://www.ars.usda.gov/ARSUserFiles/oc/images/photos/300dpi/kesa/D255-19.jpg'||
   acquisition.file?.sha256!==rootAsset?.original_sha256||acquisition.file?.sha256!==rootFile?.sha256||acquisition.file?.bytes!==rootFile?.bytes||
   acquisition.file?.deduplicated_path!==rootFile?.path)codes.push('ACQUISITION_SOURCE_OR_BYTES_MISMATCH');
  if(transfers.length!==1||transfers[0]!.count!==1||transfers[0]!.asset_ids.length!==1||transfers[0]!.asset_ids[0]!==rootAsset?.id||transfers[0]!.receipt_path!==library.acquisition.path)codes.push('ACQUISITION_OPERATION_MISMATCH');
  for(const b of library.bindings){
   const usage=library.manifest.usages.find(u=>u.id===b.usage_id)!,asset=library.manifest.assets.find(a=>a.id===usage.asset_id)!;
   if(b.acquisition_event_id!==transfers[0]?.id||b.processing_event_ids.some(id=>!library.operations.some(e=>e.id===id&&e.asset_ids.includes(asset.id)))||
    (asset.parent_id&&usage.automated_access.length)||(!asset.parent_id&&inputSha256(usage.automated_access)!==inputSha256(['download'])))codes.push('PROCESSING_EVENT_BINDING_MISMATCH');
  }
 }catch{codes.push('LIBRARY_EVIDENCE_READ_FAILED');}
 if(codes.length)return {success:false as const,codes:[...new Set(codes)].sort()};
 const handle=Object.freeze({library_sha256});verified.set(handle,{library:structuredClone(library),bundle:structuredClone(bundle)});
 return {success:true as const,codes:[],handle};
}
function state(handle:VerifiedLibrary){const s=verified.get(handle);if(!s)throw Error('LIBRARY_HANDLE_NOT_VERIFIED');return s;}
export function libraryData(handle:VerifiedLibrary){return structuredClone(state(handle).library);}
export function evaluateLibraryUsage(handle:VerifiedLibrary,value:unknown,evaluated_at:string){
 const {library,bundle}=state(handle),u=MediaUsageV1.safeParse(value);if(!u.success)return {status:'BLOCKED' as const,codes:['USAGE_SCHEMA_INVALID']};
 const usage=u.data,asset=library.manifest.assets.find(a=>a.id===usage.asset_id),grant=library.manifest.grants.find(g=>g.id===usage.grant_id);
 const gate=rightsGate(asset,grant,usage,library.manifest.assets,evaluated_at),codes=[...gate.codes];
 if(asset)codes.push(...evaluateSuitability(asset,usage,evaluated_at));
 const registered=library.manifest.usages.find(u=>u.id===usage.id),binding=library.bindings.find(b=>b.usage_id===usage.id);
 if(!registered||registered.asset_id!==usage.asset_id||!binding)codes.push('USAGE_NOT_REGISTERED');
 else {try{bindMediaFunction(binding,bundle,{...library.manifest,usages:library.manifest.usages.map(u=>u.id===usage.id?usage:u)});}catch{codes.push('FUNCTION_MEDIA_BINDING_MISMATCH');}}
 if(usage.business_id!==library.manifest.business_id)codes.push('USAGE_BUSINESS_MISMATCH');
 if(registered&&inputSha256(usage)!==inputSha256(registered))codes.push('REGISTERED_USAGE_CHANGED');
 if(registered&&(inputSha256(usage.automated_access)!==inputSha256(registered.automated_access)||inputSha256(usage.ai_operations)!==inputSha256(registered.ai_operations)))codes.push('PROCESSING_HISTORY_MISMATCH');
 if(usage.transformations.length)codes.push('UNINSPECTED_TRANSFORMED_USAGE');
 return {status:codes.length?'BLOCKED' as const:'ALLOWED' as const,codes:[...new Set(codes)].sort()};
}
export function attachmentState(handle:VerifiedLibrary,capability_id:string,scope_id:string,evaluated_at:string){
 const {library}=state(handle),bindings=library.bindings.filter(b=>b.capability_id===capability_id&&b.scope_id===scope_id);
 const evaluations=bindings.map(b=>({binding:b,usage:library.manifest.usages.find(u=>u.id===b.usage_id)!,decision:evaluateLibraryUsage(handle,library.manifest.usages.find(u=>u.id===b.usage_id),evaluated_at)}));
 const card=requirementCatalog.cards.find(c=>c.id===capability_id),admissible=evaluations.filter(e=>!card?.media_roles.length||card.media_roles.includes(e.usage.role));
 const objectives=library.requests.filter(r=>r.source==='MASTER_CATALOG'&&r.capability_id===capability_id&&r.scope_id===scope_id);
 const covered=completeSubjectCoverage(objectives,admissible.filter(e=>e.decision.status==='ALLOWED').map(e=>e.usage));
 const codes=[...new Set([...evaluations.flatMap(e=>e.decision.codes),...(evaluations.length&&!admissible.length?['CATALOG_ROLE_NOT_COVERED']:[]),
  ...(!covered?['INCOMPLETE_SUBJECT_OR_USE_COVERAGE']:[])])].sort();
 return {explicit_use:bindings.length>0,authorized_use_exists:evaluations.some(e=>e.decision.status==='ALLOWED'),
  condition_active:admissible.length===evaluations.length&&completeMediaCoverage(admissible.map(e=>e.decision))&&(!card?.media_roles.length||covered),evaluations,codes};
}
export function completeMediaCoverage(decisions:{status:'ALLOWED'|'BLOCKED';codes:string[]}[]){return decisions.length>0&&decisions.every(d=>d.status==='ALLOWED'&&d.codes.length===0);}
export function completeSubjectCoverage(requests:{subject_status:'EXACT'|'SUBJECT_PENDING';subject_ids:string[]}[],usages:{subject_ids:string[]}[]){
 return requests.every(r=>r.subject_status==='EXACT'&&r.subject_ids.every(id=>usages.some(u=>u.subject_ids.includes(id))));
}
