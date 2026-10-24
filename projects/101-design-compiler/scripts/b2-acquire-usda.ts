import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {createHash} from 'node:crypto';
// Explicit one-photo operator command, never invoked by build/test/replay.
if(!process.argv.includes('--single-selected-transfer'))throw Error('EXPLICIT_SINGLE_TRANSFER_REQUIRED');
const directory='docs/evidence/corrections/b2/acquisition',temporary='.tools/b2-acquisition';
if(await access(`${directory}/receipt.json`).then(()=>true,()=>false))throw Error('ACQUISITION_ALREADY_RECORDED');
await mkdir(directory,{recursive:true});await mkdir(temporary,{recursive:true});
const sha=(bytes:Uint8Array)=>createHash('sha256').update(bytes).digest('hex'),started_at=new Date().toISOString();
const get=async(url:string,max:number)=>{
 const r=await fetch(url,{redirect:'error',signal:AbortSignal.timeout(30000)});if(!r.ok)throw Error(`OFFICIAL_FETCH_HTTP_${r.status}`);
 const bytes=new Uint8Array(await r.arrayBuffer());if(bytes.length>max)throw Error('OFFICIAL_FETCH_TOO_LARGE');return bytes;
};
const sources=[['asset-page','https://www.ars.usda.gov/oc/images/photos/featuredphoto/mar23/bell-peppers/'],['policy','https://www.ars.usda.gov/oc/images/copyright/']] as const;
const documents=[];for(const [name,official_url] of sources){const bytes=await get(official_url,500000),path=`${directory}/${name}.html`;
 await writeFile(path,bytes);documents.push({path,official_url,sha256:sha(bytes),bytes:bytes.length,version:'Official unnumbered page; byte snapshot on acquisition date; no numbered legal version'});}
const page=await readFile(documents[0]!.path,'utf8'),policy=await readFile(documents[1]!.path,'utf8');
if(!page.includes('Copyright free, public domain image')||!page.includes('Photo by Steve Ausmus, USDA/ARS')||!page.includes('/ARSUserFiles/oc/images/photos/300dpi/kesa/D255-19.jpg')||!policy.includes('copyright-free, public domain')||!policy.includes('infer or imply ARS endorsement'))throw Error('PERMISSION_CORROBORATION_MISSING');
const source_url='https://www.ars.usda.gov/ARSUserFiles/oc/images/photos/300dpi/kesa/D255-19.jpg',bytes=await get(source_url,5000000),hash=sha(bytes);
await writeFile(`${temporary}/selected-D255-19.jpg`,bytes);
const deduplicated_path='public/media/h3-pilot/usda-ars-d255-19.jpg';
if(hash!=='ffdb883d56a41ba9a03a51fb7d1bdf8f0b9e30d3946eda180b750620a17c3715'||sha(await readFile(deduplicated_path))!==hash)throw Error('ORIGINAL_CHANGED_QUARANTINE_REQUIRED');
await writeFile(`${directory}/receipt.json`,JSON.stringify({schema_version:'1.0.0',kind:'B2_SINGLE_SELECTED_ACQUISITION',started_at,finished_at:new Date().toISOString(),
 selection:'One official photo selected by agent after official-site search/page/policy review for generic atmosphere; no catalog crawler or provider search API.',documents,
 file:{source_url,sha256:hash,bytes:bytes.length,deduplicated_path},method:'Two fixed official page GETs and one linked original GET; subsequent replay is offline.',new_purchase:false,cost_amount:null,
 cost_note:'Official complimentary source; no payment, total platform cost unknown',limits:'No general API/crawler/AI-training permission inferred; no documentary business evidence'},null,2)+'\n');
console.log(`Single selected acquisition PASS; ${bytes.length} bytes; ${hash}`);
