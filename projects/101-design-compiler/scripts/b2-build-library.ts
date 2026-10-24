import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {BusinessInputV1,BusinessProfileV1,CapabilityProfileV1,SitePlanV1} from '../src/contracts/v1/schemas.ts';
import {SiteRequirementsV1} from '../src/planner/contracts.ts';
import {MediaAssetV1,LicenseGrantV1} from '../src/media/contracts.ts';
import {buildMediaManifest,generateMediaNeeds,proposeUsage,unknownReview} from '../src/media/plan.ts';
import {functionMediaRequests,bindMediaFunction} from '../src/media/function-needs.ts';
import {MediaLibraryV1} from '../src/media/library-contracts.ts';
import {requirementCatalog} from '../src/requirements/catalog.ts';
import {humanReviewCatalog} from '../src/requirements/review-catalog.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {byteSha256} from '../src/media/package.ts';
// Explicit generation only. Verification/replay must never execute this writer.
if(!process.argv.includes('--build-reviewed-pilot'))throw Error('EXPLICIT_REVIEWED_BUILD_REQUIRED');
const output='data/media/library-v1/usda-pilot.json';if(await access(output).then(()=>true,()=>false))throw Error('LIBRARY_EXISTS');
const record=async(path:string)=>{const b=await readFile(path);return {path,bytes:b.length,sha256:byteSha256(b)};};
const base=JSON.parse(await readFile('data/derived/requirements-v1/restaurante.json','utf8')),p=base.planner;
const bundle={input:BusinessInputV1.parse(p.input),profile:BusinessProfileV1.parse(p.profile),capabilities:CapabilityProfileV1.parse(p.capabilities),plan:SitePlanV1.parse(p.plan)};
const requirements=SiteRequirementsV1.parse(p.requirements),acquisition=JSON.parse(await readFile('docs/evidence/corrections/b2/acquisition/receipt.json','utf8'));
const technical=JSON.parse(await readFile('docs/evidence/corrections/b2/technical-inspection.json','utf8')) as {files:{asset_id:string;path:string;sha256:string;bytes:number;width:number;height:number;codec:string;transformations:('RESIZE'|'TRANSCODE')[]}[]};
const evaluated_at=new Date().toISOString(),review=await record('docs/evidence/corrections/b2/legal-review.md'),inspection=await record('docs/evidence/corrections/b2/visual-review.md');
const context={client_id:'101-design-compiler-fixture-review',project_id:'b2-media-library-pilot',evaluated_at};
const verify=(reference:string,evidence_sha256:string)=>({status:'VERIFIED' as const,reference,reviewer:'Codex: byte-pinned official source and local-file assessment; not rights holder or legal certification',reviewed_at:evaluated_at,evidence_sha256});
const original=technical.files[0]!,rootId=original.asset_id;
const grant=LicenseGrantV1.parse({schema_version:'1.0.0',id:'b2-usda-d255-context-and-technical-derivatives',data_mode:'REAL',original_asset_id:rootId,original_sha256:original.sha256,
 provider:'USDA Agricultural Research Service',license_type:'OFFICIAL_PUBLIC_DOMAIN_DECLARATION; distinct narrowed B2 evaluation',holder:'USDA ARS identifies Steve Ausmus and public-domain status; no ownership claimed by compiler',purchaser:'NOT_PURCHASED: internal laboratory review',
 document:{reference:acquisition.documents[0].path,version:acquisition.documents[0].version,sha256:acquisition.documents[0].sha256},review:verify(review.path,acquisition.documents[0].sha256),
 client_ids:[context.client_id],project_ids:[context.project_id],scope_ids:[bundle.input.business_id],purposes:['generic:atmosphere'],pages:['/'],territories:['CO'],valid_from:evaluated_at,
 valid_until:new Date(Date.parse(evaluated_at)+30*86400000).toISOString(),revoked:false,commercial_web:'ALLOWED',multiple_clients:'DENIED',reuse:'DENIED',redistribution:'UNKNOWN',sublicensing:'UNKNOWN',exclusive:'DENIED',
 derivatives:'ALLOWED',transformations:['RESIZE','TRANSCODE'],automation:{search:'UNKNOWN',download:'ALLOWED'},
 ai:{classification:'UNKNOWN',embedding:'UNKNOWN',vision:'ALLOWED',editing:'DENIED',training:'UNKNOWN'},
 attribution:{required:true,text:'Photo by Steve Ausmus, USDA Agricultural Research Service.'},required_notices:['USDA ARS no respalda este fixture, producto, empresa ni posición.'],
 releases:{model:unknownReview(),property:unknownReview()},restrictions:['NO_PROVIDER_ENDORSEMENT'],retention_until:null,cost:null});
const assets=technical.files.map(f=>MediaAssetV1.parse({schema_version:'1.0.0',id:f.asset_id,data_mode:'REAL',kind:'image',uri:f.path.slice('public'.length),source:'USDA Agricultural Research Service',external_id:'D255-19',audio_track:'NONE',
 provenance:[...acquisition.documents.map((d:{official_url:string})=>({source:'USDA ARS',reference:d.official_url,recorded_at:acquisition.finished_at})),{source:'B2 reproducible derivation/inspection',reference:'docs/evidence/corrections/b2/technical-inspection.json',recorded_at:evaluated_at}],
 upstream_rights_status:null,upstream_document_ids:[],original_id:rootId,parent_id:f.asset_id===rootId?null:rootId,original_sha256:original.sha256,file_sha256:f.sha256,
 hash_review:verify('docs/evidence/corrections/b2/technical-inspection.json',f.sha256),transformations:f.transformations,restrictions:['NO_PROVIDER_ENDORSEMENT'],denied_purposes:[],documentary:null,
 relevance:[{purpose:'generic:atmosphere',scope_id:bundle.input.business_id,review:verify(inspection.path,f.sha256)}],
 inspection:{status:'REVIEWED',review:verify(inspection.path,f.sha256),width:f.width,height:f.height,duration_seconds:null,codec:f.codec,
  subject:'Pimientos rojos y follaje; contexto genérico, no oferta ni sede del negocio ficticio',findings:['Full pixel decode and measured metadata retained in technical inspection.','Local original and 480/960 WebP opened with view_image; inspected as contextual figures, no text overlay.','No claim of suitability for full-width hero or DPR > 1.'],quality:'PASS'},
 third_party:{model:'NOT_REQUIRED',property:'NOT_REQUIRED'}}));
const need=generateMediaNeeds(bundle.plan,requirements).find(n=>n.role==='ATMOSPHERIC');if(!need)throw Error('NO_ATMOSPHERIC_NEED');
const usages=assets.map(asset=>({...proposeUsage(need,asset,{...context,business_id:bundle.input.business_id},grant.id),
 attribution_text:grant.attribution.text,generic_label:'Imagen atmosférica de pimientos; no documenta este negocio ficticio ni sus platos.',endorsement_claimed:false,context_notices:grant.required_notices,
 automated_access:asset.parent_id?[]:['download'],ai_operations:['vision']}));
const {manifest,brief}=buildMediaManifest(bundle,requirements,{assets,grants:[grant],usages},context);
if(manifest.decisions.some(d=>d.status!=='ALLOWED'))throw Error(`B2_GATE_BLOCKED:${JSON.stringify(manifest.decisions)}`);
const operations=[{id:'acquire-original-D255-19',kind:'SINGLE_SELECTED_TRANSFER',asset_ids:[rootId],parent_asset_id:null,count:1,receipt_path:'docs/evidence/corrections/b2/acquisition/receipt.json'},
 ...assets.filter(a=>a.parent_id).map(a=>({id:`derive:${a.id}`,kind:'TECHNICAL_DERIVATION',asset_ids:[a.id],parent_asset_id:rootId,count:1,receipt_path:'docs/evidence/corrections/b2/technical-inspection.json'})),
 {id:'inspect-original-and-variants',kind:'LOCAL_VISUAL_INSPECTION',asset_ids:assets.map(a=>a.id),parent_asset_id:null,count:assets.length,receipt_path:inspection.path}];
const bindings=usages.map(u=>bindMediaFunction({id:`binding:${u.id}`,usage_id:u.id,capability_id:'identity',feature_id:'identity',scope_id:u.scope_id,page:u.page,module_id:u.module_id,subject_ids:u.subject_ids,
 acquisition_event_id:'acquire-original-D255-19',processing_event_ids:[...(u.asset_id===rootId?[]:[`derive:${u.asset_id}`]),'inspect-original-and-variants']},bundle,manifest));
const body={schema_version:'1.0.0',kind:'MEDIA_LIBRARY_SIDECAR',library_id:'b2-usda-single-photo-pilot-v1',catalog_sha256:requirementCatalog.catalog_sha256,review_catalog_sha256:humanReviewCatalog.catalog_sha256,
 manifest,brief,bindings,operations,requests:functionMediaRequests(bundle,manifest),files:technical.files.map(({asset_id,path,sha256,bytes})=>({asset_id,path,sha256,bytes})),
 documents:acquisition.documents.map((d:{path:string;sha256:string;bytes:number;official_url:string;version:string})=>({...d})),review,inspection,
 technical_inspection:await record('docs/evidence/corrections/b2/technical-inspection.json'),acquisition:await record('docs/evidence/corrections/b2/acquisition/receipt.json'),
 provider_policy:'USDA_ARS_SINGLE_SELECTED_PUBLIC_DOMAIN_PHOTO_V1',proof_boundary:'PINNED_SOURCE_REVIEW_NOT_FIXTURE_VERIFIED',human_design_approval:'NOT_COLLECTED'};
const library=MediaLibraryV1.parse({...body,library_sha256:inputSha256(body)});
await mkdir('data/media/library-v1',{recursive:true});await writeFile(output,JSON.stringify(library,null,2)+'\n');
console.log(JSON.stringify({path:output,review_seal:library.library_sha256,assets:assets.length,usages:usages.length,requests:library.requests.length}));
