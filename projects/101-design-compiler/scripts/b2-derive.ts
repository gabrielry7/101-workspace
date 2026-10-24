import {readFile,mkdir,writeFile,access} from 'node:fs/promises';
import sharp from 'sharp';
import {byteSha256} from '../src/media/package.ts';
if(!process.argv.includes('--reviewed-technical-derivatives'))throw Error('EXPLICIT_DERIVATION_REQUIRED');
const output='docs/evidence/corrections/b2/technical-inspection.json';
if(await access(output).then(()=>true,()=>false))throw Error('INSPECTION_RECEIPT_EXISTS');
const acquisition=JSON.parse(await readFile('docs/evidence/corrections/b2/acquisition/receipt.json','utf8'));
const original=await readFile(acquisition.file.deduplicated_path);if(byteSha256(original)!==acquisition.file.sha256)throw Error('ORIGINAL_HASH_MISMATCH');
const review=await readFile('docs/evidence/corrections/b2/legal-review.md');
const metadata=await sharp(original).metadata();await sharp(original).raw().toBuffer();
if(!metadata.width||!metadata.height||!metadata.format)throw Error('ORIGINAL_METADATA_MISSING');
await mkdir('public/media/b2',{recursive:true});
const files:{asset_id:string;path:string;sha256:string;bytes:number;width:number;height:number;codec:string;transformations:('RESIZE'|'TRANSCODE')[]}[]=[{asset_id:'b2-usda-d255-original',path:acquisition.file.deduplicated_path,sha256:byteSha256(original),bytes:original.length,width:metadata.width,height:metadata.height,codec:metadata.format,transformations:[]}];
for(const width of [480,960]){
 const path=`public/media/b2/d255-19-${width}.webp`,bytes=await sharp(original).resize({width,withoutEnlargement:true}).webp({quality:82,effort:6}).toBuffer();
 await writeFile(path,bytes);const meta=await sharp(bytes).metadata();await sharp(bytes).raw().toBuffer();
 if(!meta.width||!meta.height||!meta.format)throw Error('DERIVATIVE_METADATA_MISSING');
 files.push({asset_id:`b2-usda-d255-${width}`,path,sha256:byteSha256(bytes),bytes:bytes.length,width:meta.width,height:meta.height,codec:meta.format,transformations:['RESIZE','TRANSCODE']});
}
await writeFile(output,JSON.stringify({kind:'B2_TECHNICAL_DECODE_AND_DERIVATION',created_at:new Date().toISOString(),legal_review_sha256:byteSha256(review),
 tool:{sharp:sharp.versions.sharp,vips:sharp.versions.vips,webp:sharp.versions.webp},recipe:{widths:[480,960],fit:'proportional-no-crop',webp_quality:82,effort:6},
 files,visual_review:'PENDING_SEPARATE_REVIEW',limits:'Full pixel decode proves readability and measured dimensions; not beauty or business authenticity.'},null,2)+'\n');
console.log(JSON.stringify(files.map(f=>({path:f.path,bytes:f.bytes,width:f.width,height:f.height}))));
