import {z} from 'zod';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {ExperienceMediaReviewV1,loadExperienceMedia,REVIEWED_EXPERIENCE_MEDIA_SHA256} from './experience-review.ts';
import {MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
export const RichExperienceMediaV1=ExperienceMediaReviewV1.extend({schema_version:z.literal('1.1.0'),kind:z.literal('B3_RICH_MEDIA_APPLICABILITY'),project_id:z.literal('b3-fictional-experience-rich'),routes:z.array(z.string()).length(44)});
export const REVIEWED_RICH_MEDIA_SHA256='5f114b66dab6e87092e87e5b942135e2a17922330f845f0393d2afcaefed567a';
type Review=z.infer<typeof RichExperienceMediaV1>;
const trusted=new WeakMap<object,Review>();
export function tryRichExperienceMediaData(handle:object){const r=trusted.get(handle);return r?structuredClone(r):null;}
export function evaluateRichExperienceUsage(handle:object,value:unknown,at:string){const r=trusted.get(handle);if(!r)throw Error('RICH_MEDIA_HANDLE_UNVERIFIED');const parsed=MediaUsageV1.safeParse(value);if(!parsed.success)return {status:'BLOCKED',codes:['RICH_USAGE_SCHEMA_INVALID']} as const;
 const u=parsed.data,a=r.assets.find(a=>a.id===u.asset_id),g=r.grants.find(g=>g.id===u.grant_id),registered=r.usages.find(v=>v.id===u.id);let codes=[...rightsGate(a,g,u,r.assets,at).codes,...(a?evaluateSuitability(a,u,at):['ASSET_MISSING'])];
 if(!registered||inputSha256(registered)!==inputSha256(u)||!r.routes.includes(u.page)||u.project_id!==r.project_id||u.client_id!==r.client_id||u.business_id!==r.business_id||u.role==='DOCUMENTARY'||u.representation!=='GENERIC_CONTEXT'||u.subject_ids.length)codes.push('RICH_USAGE_NOT_REGISTERED');
 if(a?.id==='b3-video-1280-silent'&&a.audio_track==='NONE'&&a.file_sha256==='15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1')codes=codes.filter(c=>c!=='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
 codes=[...new Set(codes)].sort();return {status:codes.length?'BLOCKED':'ALLOWED',codes} as const;
}
export async function verifyRichExperienceMedia(value:unknown,root=process.cwd(),at=new Date().toISOString()){
 const p=RichExperienceMediaV1.safeParse(value);if(!p.success)return {success:false as const,codes:['RICH_MEDIA_SCHEMA_INVALID']};const {review_sha256,...body}=p.data,r=p.data;
 if(review_sha256!==REVIEWED_RICH_MEDIA_SHA256||inputSha256(body)!==review_sha256||r.parent_review_sha256!==REVIEWED_EXPERIENCE_MEDIA_SHA256)return {success:false as const,codes:['RICH_MEDIA_NOT_PINNED']};
 try{const parent=await loadExperienceMedia(root,at);if(inputSha256(r.assets.map(a=>({id:a.id,sha:a.file_sha256})))!==inputSha256(parent.review.assets.map(a=>({id:a.id,sha:a.file_sha256}))))throw Error('ASSETS_CHANGED');for(const e of r.evidence)if(byteSha256(await readFile(resolve(root,e.path)))!==e.sha256)throw Error('EVIDENCE_CHANGED');}catch{return {success:false as const,codes:['RICH_MEDIA_EVIDENCE_INVALID']};}
 const handle=Object.freeze({review_sha256});trusted.set(handle,r);if(r.usages.some(u=>evaluateRichExperienceUsage(handle,u,at).status!=='ALLOWED')){trusted.delete(handle);return {success:false as const,codes:['RICH_CURRENT_USE_BLOCKED']};}return {success:true as const,codes:[],handle,review:structuredClone(r),evaluated_at:at};
}
export async function loadRichExperienceMedia(root=process.cwd(),at=new Date().toISOString()){const r=await verifyRichExperienceMedia(JSON.parse(await readFile(resolve(root,'data/media/demo-v1/b3-rich-experience-review.json'),'utf8')),root,at);if(!r.success)throw Error(r.codes.join(','));return r;}
