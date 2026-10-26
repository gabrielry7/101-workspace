// Reuses 101's existing static server and local Edge/CDP adapter.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
export async function openCaptureBrowser(output) {
  // Follow the existing correction-browser.ts overlay pattern. The historical
  // H4 server predates JS/video: octet-stream headers block B3 module scripts.
  // Keep frozen H4/H8 source bytes intact and overlay MIME support locally.
  const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
  const source=await readFile(resolve(root,'scripts/lib/local-browser.ts'),'utf8');
  const needle="'.jpg':'image/jpeg'";
  if(source.split(needle).length!==2)throw Error('Browser MIME overlay source changed');
  const adapted=source.replace(needle,needle+",'.js':'text/javascript','.mjs':'text/javascript','.mp4':'video/mp4','.webm':'video/webm','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml','.woff2':'font/woff2','.woff':'font/woff'");
  const sha=s=>createHash('sha256').update(s).digest('hex');
  const path=resolve(root,`.tools/claude-code/browser-${sha(adapted)}.ts`);await mkdir(dirname(path),{recursive:true});await writeFile(path,adapted);
  const {openLocalBrowser}=await import(pathToFileURL(path).href),browser=await openLocalBrowser(output);
  return {...browser,adapter:{source:'scripts/lib/local-browser.ts',sourceSha256:sha(source),overlaySha256:sha(adapted),change:'MIME types for existing B3 modules/media only; browser sandbox retained'}};
}
export async function readyPage(browser,route) {
  await browser.call('Page.bringToFront');
  await browser.call('Page.navigate',{url:browser.origin+route});
  for(let attempt=0;attempt<50;attempt++) {
    const ready=await browser.evaluate(`location.pathname===${JSON.stringify(route)}&&document.readyState==='complete'`);
    if(ready)break;
    if(attempt===49)throw Error('Page readiness timeout');
    await new Promise(done=>setTimeout(done,100));
  }
  // Bound readiness for B3 lazy images. Callers report unloaded image metrics.
  await browser.evaluate(`(async()=>{await Promise.race([Promise.allSettled([...document.images].map(i=>{i.loading='eager';return i.decode()})),new Promise(r=>setTimeout(r,5000))]);await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,5000))]);})()`);
}
export async function paintPage(browser) {
  // Full-page Edge captures can contain unpainted lazy-image tiles even after
  // decode. Reuse the established B3 practice: visit each image, then return.
  await browser.evaluate(`(async()=>{const frame=()=>Promise.race([new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))),new Promise(r=>setTimeout(r,1500))]);for(const image of document.images){image.scrollIntoView({block:'center'});await Promise.race([image.decode().catch(()=>{}),new Promise(r=>setTimeout(r,1500))]);await frame()}scrollTo(0,0);await frame()})()`);
}
async function main() {
const [output='dist',route='/b3/candidate-01/',destination='.tools/claude-code/baseline']=process.argv.slice(2);
if(!route.startsWith('/')||route.startsWith('//'))throw Error('Local route required');
await mkdir(destination,{recursive:true});
const browser=await openCaptureBrowser(output),views=[];
try {
  for(const [id,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
    await browser.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:id==='mobile'});
    await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    await readyPage(browser,route);
    await paintPage(browser);
    const metrics=await browser.evaluate(`({title:document.title,h1:[...document.querySelectorAll('h1')].map(x=>x.textContent),width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,links:[...document.querySelectorAll('a')].map(a=>({text:a.textContent.trim(),href:a.getAttribute('href')})),images:[...document.images].map(i=>({alt:i.alt,loaded:i.complete&&i.naturalWidth>0}))})`);
    // Native viewport screenshots avoid Edge's full-page mobile tile omission.
    const shot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    const path=resolve(destination,`${id}.png`);await writeFile(path,Buffer.from(shot.data,'base64'));
    const sections=[];
    for(const [label,offset] of [['journal',0],['journal-followup',height*.85]]){
      const top=await browser.evaluate(`(()=>{const e=document.querySelector('.community-journal');return e?e.getBoundingClientRect().top+scrollY:null})()`);
      if(top===null)continue;
      await browser.evaluate(`scrollTo(0,${top+offset});new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
      const image=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      const sectionPath=resolve(destination,`${id}-${label}.png`);await writeFile(sectionPath,Buffer.from(image.data,'base64'));
      sections.push({label,path:sectionPath,scrollY:await browser.evaluate('scrollY')});
    }
    views.push({id,viewport:{width,height},path,sections,metrics});
  }
  await writeFile(resolve(destination,'capture.json'),JSON.stringify({createdAt:new Date().toISOString(),output:resolve(output),route,browser:browser.version,adapter:browser.adapter,views},null,2)+'\n');
  console.log(JSON.stringify({destination,route,views:views.map(v=>({id:v.id,path:v.path,overflow:v.metrics.scrollWidth>v.metrics.width}))},null,2));
}finally{browser.close();}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await main();
