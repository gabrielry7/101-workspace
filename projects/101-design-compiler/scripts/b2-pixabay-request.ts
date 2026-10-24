import {access,mkdir,writeFile,readFile,unlink} from 'node:fs/promises';
import {createHash} from 'node:crypto';
// One human-requested search. Never imported by build, tests, verification or replay.
const directory='docs/evidence/corrections/b2/pixabay';
const privateCache='.tools/b2-pixabay-cache/response.json';
if(process.argv.includes('--purge-expired-cache')){
 const receipt=JSON.parse(await readFile(`${directory}/receipt.json`,'utf8'));
 if(Date.now()<Date.parse(receipt.cache_until))throw Error('CACHE_24H_WINDOW_NOT_FINISHED');
 if(await access(privateCache).then(()=>true,()=>false))await unlink(privateCache);
 console.log('EXPIRED_PRIVATE_CACHE_PURGED_NO_PROVIDER_REQUEST');
 process.exit(0);
}
if(!process.argv.includes('--single-human-request'))throw Error('EXPLICIT_HUMAN_REQUEST_REQUIRED');
if(await access(`${directory}/receipt.json`).then(()=>true,()=>false))throw Error('REQUEST_ALREADY_RECORDED_USE_CACHE');
process.loadEnvFile('.env');const key=process.env.PIXABAY_API_KEY?.trim();if(!key)throw Error('PRIVATE_KEY_MISSING');
const query={q:'red bell peppers',image_type:'photo',category:'food',safesearch:'true',per_page:'3',page:'1'};
const url=new URL('https://pixabay.com/api/');for(const [k,v] of Object.entries({...query,key}))url.searchParams.set(k,v);
const started_at=new Date().toISOString();let response:Response;
try{response=await fetch(url,{redirect:'error',signal:AbortSignal.timeout(30000)});}catch{throw Error('PIXABAY_REQUEST_FAILED_NO_URL_LOGGED');}
const bytes=Buffer.from(await response.arrayBuffer());if(bytes.includes(Buffer.from(key)))throw Error('SECRET_IN_RESPONSE_NOT_PERSISTED');
const sha256=createHash('sha256').update(bytes).digest('hex');
await mkdir(directory,{recursive:true});
const ok=response.ok;let hits:number|null=null;
if(ok){const body=JSON.parse(bytes.toString());hits=Array.isArray(body.hits)?body.hits.length:null;await mkdir('.tools/b2-pixabay-cache',{recursive:true});await writeFile(privateCache,bytes);}
const receipt={schema_version:'1.0.0',kind:'B2_SINGLE_HUMAN_SEARCH',started_at,finished_at:new Date().toISOString(),
 endpoint:'https://pixabay.com/api/',query,credential_source:'.env:PIXABAY_API_KEY (value omitted)',http_status:response.status,
 response_sha256:sha256,response_bytes:bytes.length,response_path:null,private_cache_path:ok?privateCache:null,hits,
 rate_limit:Object.fromEntries(['X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset'].map(k=>[k,response.headers.get(k)])),
 cache_until:new Date(Date.parse(started_at)+86400000).toISOString(),cache_policy:'PRIVATE_24H_NOT_PUBLISHED_NOT_REPLAYED_PURGE_AFTER_EXPIRY',requests:1,media_downloads:0,
 decision:ok?'AUTHENTICATED_SEARCH_ONLY_NO_ASSET_AUTHORIZED':'ACCESS_FAILED_NO_ASSET_AUTHORIZED',
 terms:['https://pixabay.com/api/docs/','https://pixabay.com/service/terms/'],
 boundaries:['No account changes, purchases, retries, pagination, catalog automation or media downloads','Search metadata is not inspected pixels, source rights evidence, model release or commercial permission','No API key or authenticated URL persisted','Raw result is private temporary cache, excluded from Git; no public redistribution or permanent image URL display']};
await writeFile(`${directory}/receipt.json`,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({http_status:response.status,hits,media_downloads:0,receipt:`${directory}/receipt.json`}));
if(!ok)process.exitCode=1;
