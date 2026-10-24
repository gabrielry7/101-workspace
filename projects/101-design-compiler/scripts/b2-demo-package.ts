import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import sharp from 'sharp';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from '../src/media/contracts.ts';
import {FictionalMediaPackageV1} from '../src/media/demo-contracts.ts';
import {unknownReview} from '../src/media/plan.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {byteSha256} from '../src/media/package.ts';
import {mp4Handlers,webmTracks} from '../src/media/video-tracks.ts';
if(!process.argv.includes('--reviewed-fictional-package'))throw Error('EXPLICIT_REVIEWED_PACKAGE_REQUIRED');
const path='data/media/demo-v1/pixabay-fictional.json';if(await access(path).then(()=>true,()=>false))throw Error('PACKAGE_EXISTS');
const data=JSON.parse(await readFile('data/derived/requirements-v1/restaurante.json','utf8')).planner,old=JSON.parse(await readFile('data/media/library-v1/usda-pilot.json','utf8'));
const candidates=(await Promise.all(['acquisition.json','acquisition-alternatives.json','acquisition-final-candidates.json'].map(async p=>JSON.parse(await readFile(`docs/evidence/corrections/b2-demo/${p}`,'utf8')).files))).flat();
const selected=[{id:4991789,slot:'pizza',label:'Pizza · ejemplo',date:'2020-04-02'},{id:3547078,slot:'pasta',label:'Pasta · ejemplo',date:'2018-07-19'},{id:791891,slot:'salad',label:'Ensalada · ejemplo',date:'2015-06-01'},{id:1971552,slot:'dessert',label:'Postre · ejemplo',date:'2017-01-11'},{id:149678,slot:'motion',label:'Una escena de cocina',date:'2023-02-07'}];
const record=async(path:string)=>{const b=await readFile(path);return {path,sha256:byteSha256(b),bytes:b.length};};
const evaluated_at=new Date().toISOString(),legal=await record('docs/evidence/corrections/b2-demo/legal-review.md'),videoReceipt=await record('docs/evidence/corrections/b2-demo/video-derivation-640.json');
const video=JSON.parse(await readFile(videoReceipt.path,'utf8')),sourceVideo=candidates.find(c=>c.id===149678);
const sourceVideoMetadata=JSON.parse(await readFile('docs/evidence/corrections/b2-demo/source-video-metadata.json','utf8'));
if(!mp4Handlers(await readFile(sourceVideo.original_received.path)).includes('soun')||JSON.stringify(webmTracks(await readFile(video.output)))!==JSON.stringify([{type:1,codec:'V_VP8'}]))throw Error('VIDEO_DISPOSITION_MISMATCH');
const scenario={id:'b2-fictional-restaurant-v1',title:'La Mesa · restaurante ficticio',mode:'SYNTHETIC_DEMO',business_id:data.input.business_id,scope_id:data.input.business_id,
 site_plan_sha256:inputSha256(data.plan),input_sha256:inputSha256(data.input),client_id:'101-design-compiler-fixture-review',project_id:'b2-fictional-pixabay-demo',real_business_evidence:false};
const verify=(reference:string,sha:string)=>({status:'VERIFIED',reference,reviewer:'Codex: pinned official policy applicability and actual-file assessment; not rights holder',reviewed_at:evaluated_at,evidence_sha256:sha});
const contextLabel='Restaurante ficticio · imágenes y vídeo ilustrativos de Pixabay. No representan una empresa ni sus productos reales.';
const notice='Pixabay y sus autores no respaldan este escenario.';
const assets:any[]=[],grants:any[]=[],usages:any[]=[],needs:any[]=[],files:any[]=[],sources:any[]=[];
for(const choice of selected){
 const c=candidates.find(c=>c.id===choice.id),motion=choice.slot==='motion',module=data.plan.pages.flatMap((p:any)=>p.modules).find((m:any)=>m.capability_id===(motion?'identity':'menu'));
 const need={id:`demo-need:${choice.slot}`,label:choice.label,placement:motion?'MOTION':'CARD',scope_id:module.scope_id,purpose:`fictional:${choice.slot}`,role:motion?'ATMOSPHERIC':'ILLUSTRATIVE',target_module:module.id,target_capability:module.capability_id,target_feature:motion?'identity':'offer_detail',
 source_need_ids:old.manifest.needs.filter((n:any)=>n.module_id===module.id).map((n:any)=>n.id),satisfies_documentary_need:false};needs.push(need);
 const rootId=`pixabay-${choice.id}-received`,credit=`${c.contributor} / Pixabay`,grantId=`license:${choice.id}`,rootFile=c.original_received;
 const license=choice.date<'2019-01-09'?'CC0_1_0_BY_TERMS_SECTION_4':'PIXABAY_CONTENT_LICENSE';
 sources.push({asset_id:rootId,provider_id:choice.id,page:motion?'https://pixabay.com/videos/pizza-peperonni-cheese-italian-149678/':c.source_page,contributor:c.contributor,published_date:choice.date,license,terms_version:'2024-11-18',camera_original:'NOT_OBTAINED',ai_generated:'NOT_REPORTED'});
 grants.push(LicenseGrantV1.parse({schema_version:'1.0.0',id:grantId,data_mode:'REAL',original_asset_id:rootId,original_sha256:rootFile.sha256,provider:'Pixabay',license_type:license,
 holder:`Provider lists ${c.contributor}; no ownership asserted by compiler`,purchaser:'User existing Pixabay API account; free selected resources',document:{reference:legal.path,sha256:legal.sha256,version:'Pixabay Terms 2024-11-18, applicable per-file source dates; local applicability review'},review:verify(legal.path,legal.sha256),
 client_ids:[scenario.client_id],project_ids:[scenario.project_id],scope_ids:[module.scope_id],purposes:[need.purpose],pages:['/b2/demo/'],territories:['CO'],valid_from:evaluated_at,valid_until:new Date(Date.parse(evaluated_at)+30*86400000).toISOString(),revoked:false,
 commercial_web:'ALLOWED',multiple_clients:'DENIED',reuse:'DENIED',redistribution:'DENIED',sublicensing:'UNKNOWN',exclusive:'DENIED',derivatives:'ALLOWED',transformations:['RESIZE','TRANSCODE'],automation:{search:'ALLOWED',download:'ALLOWED'},
 ai:{classification:'UNKNOWN',embedding:'UNKNOWN',vision:'ALLOWED',editing:'DENIED',training:'DENIED'},attribution:{required:true,text:credit},required_notices:[notice],releases:{model:unknownReview(),property:unknownReview()},restrictions:['NO_PROVIDER_ENDORSEMENT'],retention_until:null,cost:null}));
 const specs=[{id:rootId,...rootFile,publication:'PRIVATE_SOURCE',operations:[],width:c.decoded_image?.width??sourceVideoMetadata.width,height:c.decoded_image?.height??sourceVideoMetadata.height,codec:motion?sourceVideoMetadata.fourcc:c.decoded_image.codec,audio:motion?'PRESENT':'NONE'},
  ...(motion?[{id:`pixabay-${choice.id}-silent`,path:video.output,sha256:video.output_sha256,bytes:video.output_bytes,publication:'LOCAL_COMPOSITE_ONLY',operations:['RESIZE','TRANSCODE'],width:video.width,height:video.height,codec:'vp8',audio:'NONE'}]:c.derivatives.map((d:any)=>({id:`pixabay-${choice.id}-${d.width}`, ...d,publication:'LOCAL_COMPOSITE_ONLY',audio:'NONE'})))];
 for(const f of specs){const actual=await record(f.path);if(actual.sha256!==f.sha256||actual.bytes!==f.bytes)throw Error('FILE_BYTES_CHANGED');
  if(!motion){const m=await sharp(await readFile(f.path)).metadata();await sharp(await readFile(f.path)).raw().toBuffer();if(m.width!==f.width||m.height!==f.height)throw Error('MEASURED_DIMENSIONS_CHANGED');}
  files.push({asset_id:f.id,...actual,publication:f.publication});
  const root=f.id===rootId;
  const asset=MediaAssetV1.parse({schema_version:'1.0.0',id:f.id,data_mode:'REAL',kind:motion?'video':'image',uri:root?`private:${f.path}`:f.path.slice('public'.length),source:'Pixabay',external_id:String(choice.id),audio_track:f.audio,
   provenance:[{source:'Pixabay licensed provider rendition; not camera original',reference:c.source_page,recorded_at:c.acquired_at},{source:'B2 fictional usage review',reference:legal.path,recorded_at:evaluated_at}],upstream_rights_status:null,upstream_document_ids:[],
   original_id:rootId,parent_id:root?null:rootId,original_sha256:rootFile.sha256,file_sha256:f.sha256,hash_review:verify(f.path,f.sha256),transformations:f.operations,restrictions:['NO_PROVIDER_ENDORSEMENT'],denied_purposes:[],documentary:null,
   relevance:[{purpose:need.purpose,scope_id:module.scope_id,review:verify(f.path,f.sha256)}],inspection:{status:'REVIEWED',review:verify(f.path,f.sha256),width:f.width,height:f.height,duration_seconds:motion?video.duration_from_frames:null,codec:f.codec,subject:choice.label,
    findings:[motion?'234 frames decoded; 1-second samples reviewed, pizza/cutter; output track verified separately.':'Original and local resized files visually reviewed and fully decoded; no identifying people or marks observed.','Fictional illustration only; not recipe, allergen, factual business or human design approval.'],quality:'PASS'},third_party:{model:'NOT_REQUIRED',property:'NOT_REQUIRED'}});assets.push(asset);
  if(!root)usages.push(MediaUsageV1.parse({schema_version:'1.0.0',id:`demo-use:${f.id}`,need_id:need.id,asset_id:asset.id,grant_id:grantId,client_id:scenario.client_id,project_id:scenario.project_id,business_id:scenario.business_id,scope_id:module.scope_id,page:'/b2/demo/',module_id:module.id,purpose:need.purpose,role:need.role,representation:'GENERIC_CONTEXT',subject_ids:[],transformations:[],territory:'CO',attribution_text:credit,generic_label:contextLabel,endorsement_claimed:false,context_notices:[notice],ai_operations:['vision'],automated_access:[]}));
 }
}
// The poster is a separate use, scope and purpose, not an implicit reuse of the
// menu photograph in the identity module.
const identity=data.plan.pages.flatMap((p:any)=>p.modules).find((m:any)=>m.capability_id==='identity'),posterPurpose='fictional:poster';
needs.push({id:'demo-need:poster',label:'Portada ilustrativa del vídeo',placement:'POSTER',scope_id:identity.scope_id,purpose:posterPurpose,role:'ATMOSPHERIC',target_module:identity.id,target_capability:'identity',target_feature:'identity',source_need_ids:old.manifest.needs.filter((n:any)=>n.module_id===identity.id).map((n:any)=>n.id),satisfies_documentary_need:false});
const posterAsset=assets.find(a=>a.id==='pixabay-4991789-640'),posterGrant=grants.find(g=>g.id==='license:4991789');posterGrant.scope_ids.push(identity.scope_id);posterGrant.purposes.push(posterPurpose);
for(const asset of assets.filter(a=>a.original_id===posterAsset.original_id))asset.relevance.push({purpose:posterPurpose,scope_id:identity.scope_id,review:verify(files.find(f=>f.asset_id===asset.id).path,asset.file_sha256)});
usages.push(MediaUsageV1.parse({...usages.find(u=>u.asset_id===posterAsset.id),id:'demo-use:poster',need_id:'demo-need:poster',scope_id:identity.scope_id,module_id:identity.id,purpose:posterPurpose,role:'ATMOSPHERIC'}));
const body={schema_version:'1.0.0',kind:'FICTIONAL_MEDIA_PACKAGE',scenario,evaluated_at,needs,assets,grants,usages,files,sources,evidence:[legal,videoReceipt,await record('docs/evidence/corrections/b2-demo/current-container.json'),await record('docs/evidence/corrections/b2-demo/source-video-metadata.json'),await record('docs/evidence/corrections/b2-demo/acquisition.json'),await record('docs/evidence/corrections/b2-demo/acquisition-alternatives.json'),await record('docs/evidence/corrections/b2-demo/acquisition-final-candidates.json')],
 silent_video:{source_asset_id:'pixabay-149678-received',render_asset_id:'pixabay-149678-silent',source_sha256:sourceVideo.original_received.sha256,render_sha256:video.output_sha256,method:'PIXEL_ONLY_TRANSCODE',receipt_path:videoReceipt.path,source_audio:'PRESENT',render_audio:'NONE'},human_aesthetic_approval:'NOT_COLLECTED',public_stock_redistribution:false};
const result=FictionalMediaPackageV1.parse({...body,package_sha256:inputSha256(body)});await mkdir('data/media/demo-v1',{recursive:true});await writeFile(path,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({path,sha256:result.package_sha256,files:files.length,usages:usages.length}));
