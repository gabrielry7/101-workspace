// Task-scoped companion to the pinned historical package, using the same contracts and gates.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
import {rightsGate,evaluateSuitability} from './gate.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {byteSha256} from './package.ts';
const PIN='658c2a2405a9a4cd718531de1b06c213aaa0569e5b4f1b5a293017eb42f7d731';
export async function loadOptionalRestaurantMedia(root=process.cwd(),at=new Date().toISOString()){
 const raw=JSON.parse(await readFile(resolve(root,'data/media/demo-v1/claude-optional-20261024.json'),'utf8'));const {review_sha256,...body}=raw;
 if(review_sha256!==PIN||inputSha256(body)!==PIN)throw Error('OPTIONAL_MEDIA_NOT_PINNED');
 const assets=MediaAssetV1.array().parse(body.assets),grants=LicenseGrantV1.array().parse(body.grants),usages=MediaUsageV1.array().parse(body.usages);
 if(byteSha256(await readFile(resolve(root,body.evidence.path)))!==body.evidence.sha256)throw Error('OPTIONAL_MEDIA_EVIDENCE_CHANGED');
 for(const f of body.files){const bytes=await readFile(resolve(root,f.path));if(bytes.length!==f.bytes||byteSha256(bytes)!==f.sha256)throw Error('OPTIONAL_MEDIA_BYTES_CHANGED');}
 for(const u of usages){const a=assets.find(a=>a.id===u.asset_id),g=grants.find(g=>g.id===u.grant_id);if(!a||rightsGate(a,g,u,assets,at).status!=='ALLOWED'||evaluateSuitability(a,u,at).length)throw Error('OPTIONAL_MEDIA_USE_BLOCKED');}
 return {assets,grants,usages,choices:body.choices as {id:number;kind:string;slug:string}[],review_sha256};
}
export async function optionalRestaurantImage(id:number,route:string){const media=await loadOptionalRestaurantMedia();const uses=media.usages.filter(u=>u.page===route&&media.assets.find(a=>a.id===u.asset_id)?.external_id===String(id));if(!uses.length)throw Error('OPTIONAL_MEDIA_UNREGISTERED_ROUTE');return {assets:uses.map(u=>media.assets.find(a=>a.id===u.asset_id)!),uses,review_sha256:media.review_sha256};}
