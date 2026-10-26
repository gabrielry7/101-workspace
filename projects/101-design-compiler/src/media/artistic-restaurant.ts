import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
import {mp4Handlers,webmTracks} from './video-tracks.ts';
const PIN='041b95f7b9d6b142a532706a6940ef86b9e9bba38231c8172f8d0cfe26a741d3';
type ArtisticPackage=Awaited<ReturnType<typeof readPackage>>;
const cache=new Map<string,Promise<ArtisticPackage>>();
async function readPackage(root:string){
 const raw=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/artistic-20261025.json'),'utf8')), {review_sha256,...body}=raw;
 if(review_sha256!==PIN||inputSha256(body)!==PIN)throw Error('ART_MEDIA_NOT_PINNED');
 const assets=MediaAssetV1.array().parse(body.assets),grants=LicenseGrantV1.array().parse(body.grants),usages=MediaUsageV1.array().parse(body.usages);
 if(byteSha256(await readFile(resolve(root,body.evidence.path)))!==body.evidence.sha256)throw Error('ART_MEDIA_EVIDENCE_CHANGED');
 for(const file of body.files){const bytes=await readFile(resolve(root,file.path));if(byteSha256(bytes)!==file.sha256||bytes.length!==file.bytes)throw Error('ART_MEDIA_BYTES_CHANGED');if(file.asset_id==='art-120734-render'&&JSON.stringify(mp4Handlers(bytes))!=='["vide"]')throw Error('ART_VIDEO_NOT_SILENT');if(file.asset_id==='art-267-render'&&JSON.stringify(webmTracks(bytes))!=='[{"type":1,"codec":"V_VP8"}]')throw Error('ART_VIDEO_NOT_SILENT');}
 return {assets,grants,usages,review_sha256,choices:body.choices as {id:number|string;label:string;kind:string;contributor:string;page:string}[]};
}
export async function loadArtisticRestaurantMedia(root=process.cwd()){
 const key=resolve(root);let pending=cache.get(key);if(!pending){pending=readPackage(key);cache.set(key,pending);pending.catch(()=>cache.delete(key));}return pending;
}
export async function artisticMedia(id:number|string,route:string,at=new Date().toISOString(),root=process.cwd()){
 const p=await loadArtisticRestaurantMedia(root),uses=p.usages.filter(u=>u.page===route&&u.need_id===`art:${id}`);
 if(!uses.length)throw Error('ART_MEDIA_UNREGISTERED_ROUTE');
 const assets=uses.map(u=>{const a=p.assets.find(a=>a.id===u.asset_id)!,g=p.grants.find(g=>g.id===u.grant_id);let codes=[...rightsGate(a,g,u,p.assets,at).codes,...evaluateSuitability(a,u,at)];
  // Same narrow precedent as the existing B3 silent-video review: only the pinned
  // video-only remux may discard the inherited audio-review code. No source audio
  // is rendered; every other gate, lineage, time, byte and usage check remains.
  if(a.id==='art-120734-render'&&a.file_sha256==='2f56e75f8f89a57300b18453cdde8bb07ee6436d5a1d571282e018443f19303e'&&a.audio_track==='NONE')codes=codes.filter(c=>c!=='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
  if(a.id==='art-267-render'&&a.file_sha256==='098fa5ca01deade66fc80cf573c949101fbe8ae402e4b512e2dac142e01adc6f'&&a.audio_track==='NONE')codes=codes.filter(c=>c!=='VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED');
  if(codes.length||a.uri.startsWith('private:'))throw Error('ART_MEDIA_USE_BLOCKED:'+codes.join(','));return a;
 });return {assets,uses,review_sha256:p.review_sha256};
}
