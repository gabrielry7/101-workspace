// Separate pinned companion for explicitly admitted new engine routes.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
import {mp4Handlers,webmTracks} from './video-tracks.ts';
import {isDishId,type DishId} from '../design/dish-routes.ts';
const PIN='61e270572e27fd51121d3ec295a66b35854ed60a5cd51e269faf8708740a3ae6';
const VIDEO_PINS:Record<string,string>={"pixabay-149678-silent":"d49c312d1db0515b802ce668206cbf4ded1670ea3b537f0dfbf1a058563d353b","art-120734-render":"2f56e75f8f89a57300b18453cdde8bb07ee6436d5a1d571282e018443f19303e","art-267-render":"098fa5ca01deade66fc80cf573c949101fbe8ae402e4b512e2dac142e01adc6f","b3-video-1280-silent":"15d8a7edce609b9a48eea6815cd7d1a275610e3bbce9a8488b86ad1548d252c1","dish-video-3510":"10a89fe1c4ed3fd61c0c0beb9751ff15b7436ee93f566d3dea17623dcf7f3510","dish-video-258562":"3dd435193da615cd4efebfd0f36aeeafe0a23c3a97886a200014f25c06271c44","dish-video-200157":"b63637332ba77bca42997a66511f0b52a220e743003b9d97df8d7371a8b5738b"};
type Review=Awaited<ReturnType<typeof readPackage>>;
const trusted=new WeakMap<object,Review>(),cache=new Map<string,Promise<Review>>();
async function readPackage(root:string){
 const raw=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/engines8-20261025.json'),'utf8')),{review_sha256,...body}=raw;
 if(review_sha256!==PIN||inputSha256(body)!==PIN)throw Error('ENGINE_MEDIA_NOT_PINNED');
 const assets=MediaAssetV1.array().parse(body.assets),grants=LicenseGrantV1.array().parse(body.grants),usages=MediaUsageV1.array().parse(body.usages);
 if(byteSha256(await readFile(resolve(root,body.evidence.path)))!==body.evidence.sha256)throw Error('ENGINE_MEDIA_EVIDENCE_CHANGED');
 for(const file of body.files){const b=await readFile(resolve(root,file.path));if(b.length!==file.bytes||byteSha256(b)!==file.sha256)throw Error('ENGINE_MEDIA_BYTES_CHANGED');const a=assets.find(a=>a.id===file.asset_id);if(a?.kind==='video'&&!a.uri.startsWith('private:')){if(VIDEO_PINS[a.id]!==a.file_sha256)throw Error('ENGINE_VIDEO_NOT_PINNED');if(a.uri.endsWith('.mp4')?JSON.stringify(mp4Handlers(b))!=='["vide"]':JSON.stringify(webmTracks(b))!=='[{"type":1,"codec":"V_VP8"}]')throw Error('ENGINE_VIDEO_NOT_SILENT');}}
 const routes=body.routes as string[];if(routes.length!==60||routes.some(r=>!/^\/b3\/candidate-0[5-8]\/(?:$|(?:carta|pedidos|reservas|historia|visita|preguntas|diario|opiniones|contacto|creditos)\/$|carta\/(?:pizza|pasta|salad|dessert)\/$)/.test(r))||usages.some(u=>!routes.includes(u.page)))throw Error('ENGINE_ROUTE_SCOPE_CHANGED');
 return {review_sha256,assets,grants,usages,routes,policy:{credit_placement:'LINKED_CREDITS_PAGE' as const},video_choices:body.video_choices as Partial<Record<DishId,{asset_id:string;label:string}>>};
}
export function tryEngineMediaData(handle:object){const r=trusted.get(handle);return r?structuredClone(r):null}
export function evaluateEngineUsage(handle:object,value:unknown,at:string){
 const r=trusted.get(handle);if(!r)throw Error('ENGINE_MEDIA_HANDLE_UNVERIFIED');const parsed=MediaUsageV1.safeParse(value);if(!parsed.success)return {status:'BLOCKED',codes:['ENGINE_USAGE_SCHEMA_INVALID']} as const;
 const u=parsed.data,a=r.assets.find(a=>a.id===u.asset_id),g=r.grants.find(g=>g.id===u.grant_id),registered=r.usages.find(v=>v.id===u.id);let codes=[...rightsGate(a,g,u,r.assets,at).codes,...(a?evaluateSuitability(a,u,at):['ASSET_MISSING'])];
 if(a?.kind==='video'&&a.audio_track==='NONE'&&VIDEO_PINS[a.id]===a.file_sha256)codes=codes.filter(c=>c!=='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
 if(!registered||inputSha256(registered)!==inputSha256(u)||!r.routes.includes(u.page)||u.project_id!=='b3-engines8-20261025'||!['ILLUSTRATIVE','ATMOSPHERIC'].includes(u.role)||u.representation!=='GENERIC_CONTEXT'||u.subject_ids.length)codes.push('ENGINE_USAGE_NOT_REGISTERED');
 if(a?.uri.startsWith('private:'))codes.push('ENGINE_PRIVATE_ORIGINAL');codes=[...new Set(codes)].sort();return {status:codes.length?'BLOCKED':'ALLOWED',codes} as const;
}
// One coherent build-time evaluation, with explicit-time evaluations isolated in
// their own cache. Cache no decision across a changed package/root or timestamp.
const buildAt=new Date().toISOString(),evaluations=new Map<string,Promise<{handle:Readonly<{review_sha256:string}>;review:Review;evaluated_at:string}>>();
export async function loadEngineMedia(root=process.cwd(),at=buildAt){
 const key=resolve(root),evaluationKey=JSON.stringify([key,at]);let evaluated=evaluations.get(evaluationKey);
 if(!evaluated){evaluated=(async()=>{let p=cache.get(key);if(!p){p=readPackage(key);cache.set(key,p);p.catch(()=>cache.delete(key))}const review=await p,handle=Object.freeze({review_sha256:review.review_sha256});trusted.set(handle,review);
 if(review.usages.some(u=>evaluateEngineUsage(handle,u,at).status!=='ALLOWED')){trusted.delete(handle);throw Error('ENGINE_MEDIA_USE_BLOCKED')}
 return{handle,review,evaluated_at:at}})();evaluations.set(evaluationKey,evaluated);evaluated.catch(()=>evaluations.delete(evaluationKey))}
 const p=await evaluated;return{...p,review:structuredClone(p.review)};
}
export async function engineDishVideo(id:string,route:string,root=process.cwd(),at=buildAt){
 if(!isDishId(id))throw Error('ENGINE_ID_INVALID');const p=await loadEngineMedia(root,at),choice=p.review.video_choices[id];if(!choice)return null;
 const usage=p.review.usages.find(u=>u.page===route&&u.asset_id===choice.asset_id);if(!usage||evaluateEngineUsage(p.handle,usage,at).status!=='ALLOWED')throw Error('ENGINE_VIDEO_UNREGISTERED_ROUTE');
 const asset=p.review.assets.find(a=>a.id===usage.asset_id)!,source=asset.provenance.find(p=>p.source.startsWith('Pixabay licensed'))!.reference,posterUse=p.review.usages.find(u=>u.page===route&&u.need_id===`b3-need:${id}`&&p.review.assets.find(a=>a.id===u.asset_id)?.inspection.width===1280);
 if(!posterUse)throw Error('ENGINE_POSTER_MISSING');const poster=p.review.assets.find(a=>a.id===posterUse.asset_id)!;
 return {asset,usage,source,poster:poster.uri,credit:usage.attribution_text,label:choice.label,review_sha256:p.review.review_sha256};
}
