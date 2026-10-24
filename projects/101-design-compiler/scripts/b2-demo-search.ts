import {access,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
// User-requested fictional restaurant package, five bounded searches, never build/replay.
if(!process.argv.includes('--requested-fictional-package'))throw Error('EXPLICIT_DEMO_REQUEST_REQUIRED');
const directory='docs/evidence/corrections/b2-demo/search',cache='.tools/b2-demo/cache';
if(await access(`${directory}/receipt.json`).then(()=>true,()=>false))throw Error('SEARCH_ALREADY_RECORDED');
process.loadEnvFile('.env');const key=process.env.PIXABAY_API_KEY?.trim();if(!key)throw Error('PRIVATE_KEY_MISSING');
const requests=[{id:'pizza',kind:'image',q:'pizza'},{id:'pasta',kind:'image',q:'pasta'},{id:'salad',kind:'image',q:'salad'},{id:'dessert',kind:'image',q:'tiramisu'},{id:'motion',kind:'video',q:'pizza'}];
await mkdir(directory,{recursive:true});await mkdir(cache,{recursive:true});const receipts=[];
for(const request of requests){
 const path=`${cache}/${request.id}.json`;
 if(await access(path).then(()=>true,()=>false))throw Error('CACHE_EXISTS_NO_REQUERY');
 const endpoint=request.kind==='video'?'https://pixabay.com/api/videos/':'https://pixabay.com/api/';
 const query={q:request.q,per_page:'3',page:'1',safesearch:'true',...(request.kind==='image'?{image_type:'photo',orientation:'horizontal'}:{video_type:'film'})};
 const url=new URL(endpoint);for(const [k,v] of Object.entries({...query,key}))url.searchParams.set(k,v);
 let response:Response;try{response=await fetch(url,{redirect:'error',signal:AbortSignal.timeout(30000)});}catch{throw Error('PIXABAY_SEARCH_FAILED_URL_REDACTED');}
 const bytes=Buffer.from(await response.arrayBuffer());if(bytes.includes(Buffer.from(key)))throw Error('SECRET_IN_RESPONSE_NOT_SAVED');
 if(!response.ok)throw Error(`PIXABAY_SEARCH_HTTP_${response.status}`);
 const body=JSON.parse(bytes.toString());await writeFile(path,bytes);
 const at=new Date().toISOString();const receipt={id:request.id,kind:request.kind,endpoint,query,at,cache_until:new Date(Date.parse(at)+86400000).toISOString(),private_cache:path,
  response_sha256:createHash('sha256').update(bytes).digest('hex'),response_bytes:bytes.length,hits:body.hits.length,
  rate_limit:Object.fromEntries(['X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset'].map(h=>[h,response.headers.get(h)]))};
 await writeFile(`${directory}/${request.id}.json`,JSON.stringify(receipt,null,2)+'\n');receipts.push(receipt);
 console.log(JSON.stringify({source:'Pixabay',query:request.id,candidates:body.hits.map((h:any)=>({id:h.id,page:h.pageURL,tags:h.tags,contributor:h.user,width:h.imageWidth,height:h.imageHeight,duration:h.duration,
  video:h.videos?Object.fromEntries(Object.entries(h.videos).map(([name,v]:[string,any])=>[name,{width:v.width,height:v.height,size:v.size}])):null}))}));
}
await writeFile(`${directory}/receipt.json`,JSON.stringify({kind:'B2_EXPLICIT_FICTIONAL_RESTAURANT_SEARCH',created_at:new Date().toISOString(),requests:receipts.length,media_downloads:0,queries:receipts,
 terms:'https://pixabay.com/api/docs/',policy:'Five specific searches for one fictional fixture. No pagination, bulk download, account changes or purchases. Raw responses private/24h, not published or replayed.'},null,2)+'\n');
