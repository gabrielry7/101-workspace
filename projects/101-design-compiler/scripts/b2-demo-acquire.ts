import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import sharp from 'sharp';
if(!process.argv.includes('--selected-demo-files'))throw Error('EXPLICIT_SELECTION_REQUIRED');
const directory='docs/evidence/corrections/b2-demo',privateRoot='.tools/b2-demo';
if(await access(`${directory}/acquisition.json`).then(()=>true,()=>false))throw Error('ACQUISITION_ALREADY_EXISTS');
const selections=[{query:'pizza',id:4991789,label:'Pizza de ejemplo'},{query:'pasta',id:3547078,label:'Pasta de ejemplo'},{query:'salad',id:5904093,label:'Ensalada de ejemplo'},{query:'dessert',id:7030032,label:'Postre de ejemplo'},{query:'motion',id:136431,label:'Escena culinaria de ejemplo'}];
const sha=(b:Uint8Array)=>createHash('sha256').update(b).digest('hex');
await mkdir(`${privateRoot}/originals`,{recursive:true});await mkdir('public/media/b2-fictional',{recursive:true});
const files=[];
for(const selection of selections){
 const receipt=JSON.parse(await readFile(`${directory}/search/${selection.query}.json`,'utf8'));
 if(Date.now()>Date.parse(receipt.cache_until))throw Error('SEARCH_CACHE_EXPIRED_NO_AUTOMATIC_REQUERY');
 const cached=await readFile(receipt.private_cache);if(sha(cached)!==receipt.response_sha256)throw Error('CACHE_HASH_MISMATCH');
 const hit=JSON.parse(cached.toString()).hits.find((h:any)=>h.id===selection.id);if(!hit)throw Error('SELECTED_FILE_NOT_IN_RESPONSE');
 const video=selection.query==='motion',rendition=video?hit.videos.medium:null;
 const selectedUrl=video?rendition.url:hit.largeImageURL;let url=new URL(selectedUrl),response:Response|undefined;
 for(let redirects=0;redirects<4;redirects++){
  if(url.protocol!=='https:'||!['pixabay.com','cdn.pixabay.com'].includes(url.hostname))throw Error('NON_PROVIDER_DOWNLOAD_HOST');
  try{response=await fetch(url,{redirect:'manual',signal:AbortSignal.timeout(45000)});}catch{throw Error('DOWNLOAD_FAILED_URL_NOT_LOGGED');}
  if(response.status>=300&&response.status<400){const location=response.headers.get('location');if(!location)throw Error('REDIRECT_WITHOUT_LOCATION');url=new URL(location,url);continue;}break;
 }
 if(!response?.ok)throw Error(`PROVIDER_DOWNLOAD_HTTP_${response?.status}`);
 const bytes=Buffer.from(await response.arrayBuffer());if(bytes.length>15*1024*1024)throw Error('SELECTED_RESOURCE_TOO_LARGE');
 const path=`${privateRoot}/originals/${selection.id}.${video?'mp4':'jpg'}`;await writeFile(path,bytes);
 let derivatives:any[]=[],metadata:any=null;
 if(!video){metadata=await sharp(bytes).metadata();await sharp(bytes).raw().toBuffer();
  for(const width of [640,1280]){const derived=await sharp(bytes).resize({width,withoutEnlargement:true}).webp({quality:84,effort:6}).toBuffer(),m=await sharp(derived).metadata(),p=`public/media/b2-fictional/${selection.id}-${width}.webp`;await writeFile(p,derived);derivatives.push({path:p,sha256:sha(derived),bytes:derived.length,width:m.width,height:m.height,codec:m.format,operations:['RESIZE','TRANSCODE']});}
 }else{const p=`public/media/b2-fictional/${selection.id}.mp4`;await writeFile(p,bytes);derivatives=[{path:p,sha256:sha(bytes),bytes:bytes.length,operations:[]}];}
 files.push({provider:'Pixabay',id:selection.id,label:selection.label,kind:video?'video':'image',source_page:hit.pageURL,contributor:hit.user,
  acquired_at:new Date().toISOString(),source_url_private_record:`${privateRoot}/source-${selection.id}.json`,source_host:url.hostname,
  original_received:{path,sha256:sha(bytes),bytes:bytes.length,origin:'PROVIDER_RENDITION_NOT_CAMERA_ORIGINAL'},
  decoded_image:metadata?{width:metadata.width,height:metadata.height,codec:metadata.format}:null,
  video_metadata:'PENDING_LOCAL_CONTAINER_AND_BROWSER_INSPECTION',derivatives,search_receipt:`${directory}/search/${selection.query}.json`});
 await writeFile(`${privateRoot}/source-${selection.id}.json`,JSON.stringify({source_url:selectedUrl,final_url:url.href,source_page:hit.pageURL,contributor:hit.user,acquired_at:new Date().toISOString()},null,2)+'\n');
 console.log(JSON.stringify({source:'Pixabay',id:selection.id,kind:video?'video':'image',bytes:bytes.length,sha256:sha(bytes),image:metadata?{width:metadata.width,height:metadata.height}:null}));
}
await writeFile(`${directory}/acquisition.json`,JSON.stringify({kind:'B2_FICTIONAL_PACKAGE_SELECTED_TRANSFERS',created_at:new Date().toISOString(),files,
 selection:'Four specific food photographs and one short culinary clip selected for an explicitly fictional restaurant scenario, not a catalog.',
 license_sources:['https://pixabay.com/service/terms/','https://pixabay.com/api/docs/'],authorization:'User explicitly requested images/videos via existing API for fictional trials; bounded selections, no purchase or new account.',
 status:'OBTAINED_NOT_YET_ADMITTED_OR_PRESENTED',private_originals:true,standalone_redistribution:false},null,2)+'\n');
