import {readFile,readdir,unlink} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
if(!process.argv.includes('--expired-only'))throw Error('EXPIRED_ONLY_REQUIRED');
const root=resolve('.tools/b2-demo/cache'),folder='docs/evidence/corrections/b2-demo/search';
let removed=0,retained=0;
for(const name of await readdir(folder)){
 if(!name.endsWith('.json')||name==='receipt.json')continue;
 const receipt=JSON.parse(await readFile(`${folder}/${name}`,'utf8'));if(!receipt.private_cache||!receipt.cache_until)continue;
 const path=resolve(receipt.private_cache);if(dirname(path)!==root)throw Error('OUTSIDE_PRIVATE_CACHE');
 if(Date.now()<Date.parse(receipt.cache_until)){retained++;continue;}
 await unlink(path).then(()=>removed++,error=>{if(error.code!=='ENOENT')throw error;});
}
console.log(JSON.stringify({removed,retained,provider_requests:0,policy:'Only six private expired query responses; no media/evidence deletion or automatic requery'}));
