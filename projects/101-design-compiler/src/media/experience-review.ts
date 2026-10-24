import {z} from 'zod';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {loadContextualMedia,REVIEWED_B3_MEDIA_SHA256} from './contextual-review.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {videoOnlyMp4} from './remux-video.ts';
import {mp4Handlers} from './video-tracks.ts';
const sha=z.string().regex(/^[a-f0-9]{64}$/);
export const ExperienceMediaReviewV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('B3_MULTIPAGE_MEDIA_APPLICABILITY'),review_sha256:sha,
 parent_review_sha256:sha,evaluated_at:z.iso.datetime(),client_id:z.string(),project_id:z.literal('b3-fictional-experience'),business_id:z.string(),
 routes:z.array(z.string()).length(32),assets:z.array(MediaAssetV1),grants:z.array(LicenseGrantV1),usages:z.array(MediaUsageV1),
 evidence:z.array(z.strictObject({path:z.string(),sha256:sha})).min(3),
 policy:z.strictObject({credit_placement:z.literal('LINKED_CREDITS_PAGE'),crop:z.literal(true),autoplay:z.literal('MUTED_BACKGROUND_WITH_PAUSE_AND_STATIC_FALLBACK'),audio:z.literal(false),documentary:z.literal(false),human_approval:z.literal('NOT_COLLECTED')})});
export const REVIEWED_EXPERIENCE_MEDIA_SHA256='378c4506d9e403498a20a66392adb671cf40a910c1ed007a29cd5db601ad0d06';
type Review=z.infer<typeof ExperienceMediaReviewV1>;
export type ExperienceMediaHandle={readonly review_sha256:string};
const trusted=new WeakMap<ExperienceMediaHandle,Review>();
export function tryExperienceMediaData(h:ExperienceMediaHandle){const v=trusted.get(h);return v?structuredClone(v):null;}
export function evaluateExperienceUsage(h:ExperienceMediaHandle,value:unknown,at:string){const r=trusted.get(h);if(!r)throw Error('EXPERIENCE_MEDIA_HANDLE_UNVERIFIED');const p=MediaUsageV1.safeParse(value);if(!p.success)return {status:'BLOCKED',codes:['EXPERIENCE_USAGE_SCHEMA_INVALID']} as const;const u=p.data,a=r.assets.find(a=>a.id===u.asset_id),g=r.grants.find(g=>g.id===u.grant_id),registered=r.usages.find(v=>v.id===u.id);
 const codes=[...rightsGate(a,g,u,r.assets,at).codes,...(a?evaluateSuitability(a,u,at):['ASSET_MISSING'])];
 if(!registered||inputSha256(registered)!==inputSha256(u)||!r.routes.includes(u.page)||u.project_id!==r.project_id||u.client_id!==r.client_id||u.business_id!==r.business_id||u.role==='DOCUMENTARY'||u.representation!=='GENERIC_CONTEXT'||u.subject_ids.length)codes.push('EXPERIENCE_USE_NOT_REGISTERED');
 const silent=a?.id==='b3-video-1280-silent'&&a.audio_track==='NONE'&&a.file_sha256==='15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1';
 const final=[...new Set(codes.filter(c=>!(silent&&c==='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED')))].sort();return {status:final.length?'BLOCKED':'ALLOWED',codes:final} as const;
}
export async function verifyExperienceMedia(value:unknown,root=process.cwd(),at=new Date().toISOString()){
 const p=ExperienceMediaReviewV1.safeParse(value);if(!p.success)return {success:false as const,codes:['EXPERIENCE_MEDIA_SCHEMA_INVALID']};const r=p.data,{review_sha256,...body}=r;
 if(review_sha256!==REVIEWED_EXPERIENCE_MEDIA_SHA256||inputSha256(body)!==review_sha256||r.parent_review_sha256!==REVIEWED_B3_MEDIA_SHA256)return {success:false as const,codes:['EXPERIENCE_MEDIA_NOT_PINNED']};
 try{const parent=await loadContextualMedia(root,at);
  for(const e of r.evidence)if(byteSha256(await readFile(resolve(root,e.path)))!==e.sha256)throw Error('EVIDENCE_CHANGED');
  if(inputSha256(r.assets.filter(a=>a.id!=='b3-video-1280-silent').map(a=>({id:a.id,sha:a.file_sha256})))!==inputSha256(parent.review.assets.map(a=>({id:a.id,sha:a.file_sha256}))))throw Error('PARENT_ASSETS_CHANGED');
  const source=await readFile(resolve(root,'.tools/b2-demo/originals/149678.mp4')),derived=await readFile(resolve(root,'public/media/b3-experience/149678-silent-1280.mp4')),remux=videoOnlyMp4(source),decode=JSON.parse(await readFile(resolve(root,'docs/evidence/corrections/b3/experience-media-01/decode.json'),'utf8'));
  if(byteSha256(derived)!=='15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1'||byteSha256(remux.output)!==byteSha256(derived)||JSON.stringify(mp4Handlers(derived))!=='["vide"]'||decode.output_sha256!==byteSha256(derived)||decode.decoded_frames!==234||!decode.all_decoded_pixels_identical)throw Error('VIDEO_INSPECTION_CHANGED');
 }catch{return {success:false as const,codes:['EXPERIENCE_MEDIA_EVIDENCE_OR_BYTES_CHANGED']};}
 const handle=Object.freeze({review_sha256});trusted.set(handle,r);if(r.usages.some(u=>evaluateExperienceUsage(handle,u,at).status!=='ALLOWED')){trusted.delete(handle);return {success:false as const,codes:['EXPERIENCE_CURRENT_USE_BLOCKED']};}return {success:true as const,codes:[],handle,review:structuredClone(r),evaluated_at:at};
}
export async function loadExperienceMedia(root=process.cwd(),at=new Date().toISOString()){const r=await verifyExperienceMedia(JSON.parse(await readFile(resolve(root,'data/media/demo-v1/b3-experience-review.json'),'utf8')),root,at);if(!r.success)throw Error(r.codes.join(','));return r;}
