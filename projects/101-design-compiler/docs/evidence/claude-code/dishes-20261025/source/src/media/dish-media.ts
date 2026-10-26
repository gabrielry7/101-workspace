// Scoped addition for the 16 user-requested dish pages. Historical registries stay sealed.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
import {mp4Handlers,webmTracks} from './video-tracks.ts';
import {dishIds,isDishId,type DishId} from '../design/dish-routes.ts';
const PIN='3ef00cf620d6eec4ae04f844713e5c6f8fbebbe470be955ee28c613cf1931332';
const VIDEO_PINS:Record<string,string>={"b3-video-1280-silent":"15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1","dish-video-3510":"10a89fe1c4ed3fd61c0c0beb9751ff15b7436ee93f566d3dea17623dcf7f3510","dish-video-258562":"3dd435193da615cd4efebfd0f36aeeafe0a23c3a97886a200014f25c06271c44","dish-video-200157":"b63637332ba77bca42997a66511f0b52a220e743003b9d97df8d7371a8b5738b"};
type Review=Awaited<ReturnType<typeof readPackage>>;
const trusted=new WeakMap<object,Review>(),cache=new Map<string,Promise<Review>>();
async function readPackage(root:string){
 const raw=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/dish-details-20261025.json'),'utf8')),{review_sha256,...body}=raw;
 if(review_sha256!==PIN||inputSha256(body)!==PIN)throw Error('DISH_MEDIA_NOT_PINNED');
 const assets=MediaAssetV1.array().parse(body.assets),grants=LicenseGrantV1.array().parse(body.grants),usages=MediaUsageV1.array().parse(body.usages);
 if(byteSha256(await readFile(resolve(root,body.evidence.path)))!==body.evidence.sha256)throw Error('DISH_MEDIA_EVIDENCE_CHANGED');
 for(const file of body.files){const b=await readFile(resolve(root,file.path));if(b.length!==file.bytes||byteSha256(b)!==file.sha256)throw Error('DISH_MEDIA_BYTES_CHANGED');const a=assets.find(a=>a.id===file.asset_id);if(a?.kind==='video'&&!a.uri.startsWith('private:')){if(VIDEO_PINS[a.id]!==a.file_sha256)throw Error('DISH_VIDEO_NOT_PINNED');if(a.uri.endsWith('.mp4')?JSON.stringify(mp4Handlers(b))!=='["vide"]':JSON.stringify(webmTracks(b))!=='[{"type":1,"codec":"V_VP8"}]')throw Error('DISH_VIDEO_NOT_SILENT');}}
 const routes=['01','02','03','04'].flatMap(n=>dishIds.map(id=>`/b3/candidate-${n}/carta/${id}/`));
 if(JSON.stringify(body.routes)!==JSON.stringify(routes)||usages.some(u=>!routes.includes(u.page)))throw Error('DISH_ROUTE_SCOPE_CHANGED');
 return {review_sha256,assets,grants,usages,routes,policy:{credit_placement:'LINKED_CREDITS_PAGE' as const},video_choices:body.video_choices as Partial<Record<DishId,{asset_id:string;label:string}>>};
}
export function tryDishMediaData(handle:object){const r=trusted.get(handle);return r?structuredClone(r):null}
export function evaluateDishUsage(handle:object,value:unknown,at:string){
 const r=trusted.get(handle);if(!r)throw Error('DISH_MEDIA_HANDLE_UNVERIFIED');const parsed=MediaUsageV1.safeParse(value);if(!parsed.success)return {status:'BLOCKED',codes:['DISH_USAGE_SCHEMA_INVALID']} as const;
 const u=parsed.data,a=r.assets.find(a=>a.id===u.asset_id),g=r.grants.find(g=>g.id===u.grant_id),registered=r.usages.find(v=>v.id===u.id);let codes=[...rightsGate(a,g,u,r.assets,at).codes,...(a?evaluateSuitability(a,u,at):['ASSET_MISSING'])];
 if(a?.kind==='video'&&a.audio_track==='NONE'&&VIDEO_PINS[a.id]===a.file_sha256)codes=codes.filter(c=>c!=='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
 if(!registered||inputSha256(registered)!==inputSha256(u)||!r.routes.includes(u.page)||u.project_id!=='b3-dish-details-20261025'||u.role!=='ILLUSTRATIVE'||u.representation!=='GENERIC_CONTEXT'||u.subject_ids.length)codes.push('DISH_USAGE_NOT_REGISTERED');
 if(a?.uri.startsWith('private:'))codes.push('DISH_PRIVATE_ORIGINAL');codes=[...new Set(codes)].sort();return {status:codes.length?'BLOCKED':'ALLOWED',codes} as const;
}
export async function loadDishMedia(root=process.cwd(),at=new Date().toISOString()){
 const key=resolve(root);let p=cache.get(key);if(!p){p=readPackage(key);cache.set(key,p);p.catch(()=>cache.delete(key))}const review=await p,handle=Object.freeze({review_sha256:review.review_sha256});trusted.set(handle,review);
 if(review.usages.some(u=>evaluateDishUsage(handle,u,at).status!=='ALLOWED')){trusted.delete(handle);throw Error('DISH_MEDIA_USE_BLOCKED')}
 return {handle,review:structuredClone(review),evaluated_at:at};
}
export async function dishVideo(id:string,route:string,root=process.cwd(),at=new Date().toISOString()){
 if(!isDishId(id))throw Error('DISH_ID_INVALID');const p=await loadDishMedia(root,at),choice=p.review.video_choices[id];if(!choice)return null;
 const usage=p.review.usages.find(u=>u.page===route&&u.asset_id===choice.asset_id);if(!usage||evaluateDishUsage(p.handle,usage,at).status!=='ALLOWED')throw Error('DISH_VIDEO_UNREGISTERED_ROUTE');
 const asset=p.review.assets.find(a=>a.id===usage.asset_id)!,source=asset.provenance.find(p=>p.source.startsWith('Pixabay licensed'))!.reference,posterUse=p.review.usages.find(u=>u.page===route&&u.need_id===`b3-need:${id}`&&p.review.assets.find(a=>a.id===u.asset_id)?.inspection.width===1280);
 if(!posterUse)throw Error('DISH_POSTER_MISSING');const poster=p.review.assets.find(a=>a.id===posterUse.asset_id)!;
 return {asset,usage,source,poster:poster.uri,credit:usage.attribution_text,label:choice.label,review_sha256:p.review.review_sha256};
}
