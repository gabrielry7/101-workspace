import {readFile,readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import sharp from 'sharp';
import {FictionalMediaPackageV1} from './demo-contracts.ts';
import type {FictionalMediaPackage} from './demo-contracts.ts';
import {MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {readPackageFile,byteSha256} from './package.ts';
import {mp4Handlers,webmTracks} from './video-tracks.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {humanReviewCatalog} from '../requirements/review-catalog.ts';
export const REVIEWED_DEMO_PACKAGE_SHA256='970cc4a6bfbe7af3d8d1de15656fe532a97883963a3e81d9c9390dc07d57f425';
export type DemoPackageHandle={readonly package_sha256:string};
const trusted=new WeakMap<DemoPackageHandle,FictionalMediaPackage>();
export async function verifyDemoPackage(value:unknown,root=process.cwd()){
 const p=FictionalMediaPackageV1.safeParse(value);if(!p.success)return {success:false as const,codes:['DEMO_SCHEMA_INVALID']};
 const pack=p.data,{package_sha256,...body}=pack,codes:string[]=[];
 if(inputSha256(body)!==package_sha256)codes.push('DEMO_HASH_MISMATCH');
 if(package_sha256!==REVIEWED_DEMO_PACKAGE_SHA256)codes.push('DEMO_SOURCE_REVIEW_NOT_PINNED');
 if(codes.length)return {success:false as const,codes};
 try{
  for(const file of [...pack.files,...pack.evidence]){const b=await readPackageFile(file.path,root);if(b.length!==file.bytes||byteSha256(b)!==file.sha256)codes.push('DEMO_FILE_OR_EVIDENCE_CHANGED');}
  const base=JSON.parse((await readPackageFile('data/derived/requirements-v1/restaurante.json',root)).toString()).planner;
  if(inputSha256(base.plan)!==pack.scenario.site_plan_sha256||inputSha256(base.input)!==pack.scenario.input_sha256||base.input.business_id!==pack.scenario.business_id)codes.push('DEMO_FIXTURE_CONTEXT_CHANGED');
  for(const n of pack.needs){const m=base.plan.pages.flatMap((p:any)=>p.modules).find((m:any)=>m.id===n.target_module);
   if(!m||m.scope_id!==n.scope_id||m.capability_id!==n.target_capability||!humanReviewCatalog.features.some(f=>f.id===n.target_feature&&f.registry_references.includes(n.target_capability as any)))codes.push('DEMO_BINDING_MISMATCH');}
  if(new Set(pack.assets.map(a=>a.id)).size!==pack.assets.length||new Set(pack.usages.map(u=>u.id)).size!==pack.usages.length)codes.push('DEMO_DUPLICATE_IDS');
  for(const f of pack.files){const a=pack.assets.find(a=>a.id===f.asset_id);if(!a||a.file_sha256!==f.sha256)codes.push('DEMO_ASSET_FILE_MISMATCH');
   if(a?.kind==='image'){const b=await readPackageFile(f.path,root),m=await sharp(b).metadata();await sharp(b).raw().toBuffer();if(m.width!==a.inspection.width||m.height!==a.inspection.height||m.format!==a.inspection.codec)codes.push('DEMO_IMAGE_INSPECTION_MISMATCH');}
  }
  const proof=pack.silent_video,source=pack.files.find(f=>f.asset_id===proof.source_asset_id),render=pack.files.find(f=>f.asset_id===proof.render_asset_id);
  if(!source||!render||source.sha256!==proof.source_sha256||render.sha256!==proof.render_sha256||!mp4Handlers(await readPackageFile(source.path,root)).includes('soun')||
   inputSha256(webmTracks(await readPackageFile(render.path,root)))!==inputSha256([{type:1,codec:'V_VP8'}]))codes.push('SILENT_VIDEO_PROOF_MISMATCH');
  const receipt=JSON.parse((await readPackageFile(proof.receipt_path,root)).toString());
  if(receipt.source_sha256!==proof.source_sha256||receipt.output_sha256!==proof.render_sha256||receipt.source_frames_decoded!==receipt.output_frames_decoded||receipt.output_frames_decoded!==234||receipt.width!==640||receipt.height!==360)codes.push('VIDEO_DECODE_RECEIPT_MISMATCH');
  const exposed=(await readdir(resolve(root,'public/media/b2-fictional'))).sort(),allowed=pack.files.filter(f=>f.publication==='LOCAL_COMPOSITE_ONLY').map(f=>f.path.split('/').at(-1)!).sort();
  if(inputSha256(exposed)!==inputSha256(allowed))codes.push('UNADMITTED_FILE_IN_PRESENTATION_FOLDER');
 }catch{codes.push('PRIVATE_DEMO_PACKAGE_MISSING_OR_UNREADABLE');}
 if(codes.length)return {success:false as const,codes:[...new Set(codes)].sort()};
 const handle=Object.freeze({package_sha256});trusted.set(handle,structuredClone(pack));return {success:true as const,codes:[],handle};
}
export function demoPackageData(handle:DemoPackageHandle){const p=trusted.get(handle);if(!p)throw Error('DEMO_HANDLE_NOT_VERIFIED');return structuredClone(p);}
export function evaluateDemoUsage(handle:DemoPackageHandle,value:unknown,at:string){
 const p=trusted.get(handle);if(!p)throw Error('DEMO_HANDLE_NOT_VERIFIED');
 const parsed=MediaUsageV1.safeParse(value);if(!parsed.success)return {status:'BLOCKED' as const,codes:['DEMO_USAGE_SCHEMA_INVALID']};
 const u=parsed.data,a=p.assets.find(a=>a.id===u.asset_id),g=p.grants.find(g=>g.id===u.grant_id),n=p.needs.find(n=>n.id===u.need_id),registered=p.usages.find(v=>v.id===u.id);
 const gate=rightsGate(a,g,u,p.assets,at),codes=[...gate.codes];if(a)codes.push(...evaluateSuitability(a,u,at));
 if(!registered||inputSha256(registered)!==inputSha256(u))codes.push('DEMO_REGISTERED_USAGE_CHANGED');
 if(!n||n.target_module!==u.module_id||n.scope_id!==u.scope_id||n.purpose!==u.purpose||n.role!==u.role||u.subject_ids.length||u.representation!=='GENERIC_CONTEXT'||u.page!=='/b2/demo/')codes.push('DEMO_CONTEXT_MISMATCH');
 if(!p.files.some(f=>f.asset_id===u.asset_id&&f.publication==='LOCAL_COMPOSITE_ONLY'))codes.push('PRIVATE_SOURCE_NOT_RENDERABLE');
 // Associated B2 disposition, only for this verified silent derivative. H3's
 // default gate still blocks any lineage containing unreviewed video audio.
 const silent=u.asset_id===p.silent_video.render_asset_id&&a?.audio_track==='NONE'&&a.file_sha256===p.silent_video.render_sha256;
 const result=[...new Set(codes.filter(c=>!(silent&&c==='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED')))].sort();
 return {status:result.length?'BLOCKED' as const:'ALLOWED' as const,codes:result,audio_disposition:silent?'VERIFIED_SILENT_DERIVATIVE_ONLY':'STANDARD_H3_GATE'};
}
export async function loadDemoPackage(options:{evaluation_time?:string;root?:string}={}){
 const root=options.root??process.cwd(),raw=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/pixabay-fictional.json'),'utf8'));
 const result=await verifyDemoPackage(raw,root);if(!result.success)throw Error(`DEMO_PACKAGE_BLOCKED:${result.codes.join(',')}`);
 const data=demoPackageData(result.handle),at=options.evaluation_time??new Date().toISOString();
 if(data.usages.some(u=>evaluateDemoUsage(result.handle,u,at).status!=='ALLOWED'))throw Error('DEMO_CURRENT_USE_BLOCKED');
 return {handle:result.handle,pack:data,evaluated_at:at};
}
