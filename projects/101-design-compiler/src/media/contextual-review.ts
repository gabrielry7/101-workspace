import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {z} from 'zod';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {loadDemoPackage,REVIEWED_DEMO_PACKAGE_SHA256} from './demo-package.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256,readPackageFile} from './package.ts';
const sha=z.string().regex(/^[a-f0-9]{64}$/);
export const ContextualMediaReviewV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('B3_ASSOCIATED_MEDIA_REVIEW'),review_sha256:sha,
 parent_package_sha256:sha,input_sha256:sha,plan_sha256:sha,evaluated_at:z.iso.datetime(),business_id:z.string(),client_id:z.string(),project_id:z.string(),
 routes:z.array(z.string()).length(4),assets:z.array(MediaAssetV1),grants:z.array(LicenseGrantV1),usages:z.array(MediaUsageV1),
 evidence:z.array(z.strictObject({path:z.string(),sha256:sha})).min(2),
 policy:z.strictObject({crop:z.literal(false),source_audio:z.literal(false),documentary:z.literal(false),public_stock_redistribution:z.literal(false),human_approval:z.literal('NOT_COLLECTED')})});
export const REVIEWED_B3_MEDIA_SHA256='794ee55ea5d168c93d3943b2299f0a9464b6a24d23bfb043e0d296b22d67608d';
type Review=z.infer<typeof ContextualMediaReviewV1>;
export type ContextualMediaHandle={readonly review_sha256:string};
const trusted=new WeakMap<ContextualMediaHandle,Review>();
export async function verifyContextualMediaReview(value:unknown,root=process.cwd(),at=new Date().toISOString()){
 const p=ContextualMediaReviewV1.safeParse(value);if(!p.success)return {success:false as const,codes:['B3_MEDIA_SCHEMA_INVALID']};
 const {review_sha256,...body}=p.data,codes:string[]=[];
 if(review_sha256!==REVIEWED_B3_MEDIA_SHA256||inputSha256(body)!==review_sha256||body.parent_package_sha256!==REVIEWED_DEMO_PACKAGE_SHA256)codes.push('B3_MEDIA_REVIEW_NOT_PINNED');
 if(codes.length)return {success:false as const,codes};
 try{const {pack}=await loadDemoPackage({root,evaluation_time:at});
  for(const evidence of body.evidence)if(byteSha256(await readPackageFile(evidence.path,root))!==evidence.sha256)codes.push('B3_MEDIA_EVIDENCE_CHANGED');
  const scenario=JSON.parse((await readPackageFile('fixtures/corrections/b3/la-mesa.json',root)).toString());
  if(inputSha256(scenario.input)!==body.input_sha256||inputSha256(scenario.planner.plan)!==body.plan_sha256||scenario.input.business_id!==body.business_id)codes.push('B3_MEDIA_SCENARIO_CHANGED');
  if(inputSha256(body.assets.map(a=>({id:a.id,file:a.file_sha256,original:a.original_sha256})))!==inputSha256(pack.assets.map(a=>({id:a.id,file:a.file_sha256,original:a.original_sha256}))))codes.push('B3_MEDIA_BYTES_CONTEXT_CHANGED');
 }catch{codes.push('B3_PARENT_OR_EVIDENCE_BLOCKED');}
 if(codes.length)return {success:false as const,codes};const handle=Object.freeze({review_sha256});trusted.set(handle,p.data);
 return {success:true as const,codes:[],handle};
}
export function contextualMediaData(h:ContextualMediaHandle){const r=trusted.get(h);if(!r)throw Error('B3_MEDIA_HANDLE_NOT_VERIFIED');return structuredClone(r);}
export function evaluateContextualUsage(h:ContextualMediaHandle,value:unknown,at:string){
 const review=trusted.get(h);if(!review)throw Error('B3_MEDIA_HANDLE_NOT_VERIFIED');const parsed=MediaUsageV1.safeParse(value);if(!parsed.success)return {status:'BLOCKED' as const,codes:['B3_USAGE_SCHEMA_INVALID']};
 const u=parsed.data,a=review.assets.find(a=>a.id===u.asset_id),g=review.grants.find(g=>g.id===u.grant_id),registered=review.usages.find(v=>v.id===u.id);
 const codes=[...rightsGate(a,g,u,review.assets,at).codes,...(a?evaluateSuitability(a,u,at):['ASSET_MISSING'])];
 if(!registered||inputSha256(registered)!==inputSha256(u))codes.push('B3_REGISTERED_USAGE_CHANGED');
 if(u.client_id!==review.client_id||u.project_id!==review.project_id||u.business_id!==review.business_id||!review.routes.includes(u.page)||u.role==='DOCUMENTARY'||u.representation!=='GENERIC_CONTEXT'||u.subject_ids.length||u.transformations.length)codes.push('B3_USAGE_CONTEXT_MISMATCH');
 const silent=a?.id==='pixabay-149678-silent'&&a.audio_track==='NONE'&&a.file_sha256==='d49c312d1db0515b802ce668206cbf4ded1670ea3b537f0dfbf1a058563d353b';
 const final=[...new Set(codes.filter(c=>!(silent&&c==='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED')))].sort();return {status:final.length?'BLOCKED' as const:'ALLOWED' as const,codes:final};
}
export async function loadContextualMedia(root=process.cwd(),at=new Date().toISOString()){
 const r=await verifyContextualMediaReview(JSON.parse(await readFile(resolve(root,'data/media/demo-v1/b3-usage-review.json'),'utf8')),root,at);
 if(!r.success)throw Error(`B3_MEDIA_BLOCKED:${r.codes.join(',')}`);const review=contextualMediaData(r.handle);
 if(review.usages.some(u=>evaluateContextualUsage(r.handle,u,at).status!=='ALLOWED'))throw Error('B3_CURRENT_USE_BLOCKED');return {handle:r.handle,review,evaluated_at:at};
}
