import {mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import sharp from 'sharp';
import {verifyRuntime,controlledBrowserPath} from './lib/correction-runtime.ts';
import {b2RuntimePath} from './b2-runtime.ts';
import {prepareBrowserHarness} from './lib/correction-browser.ts';
import {newJournal,journalCommand,hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
import {loadDemoPackage} from '../src/media/demo-package.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('NEW_QA_ID_REQUIRED');
const directory=`docs/evidence/corrections/b2-demo/${id}`,out=`.tools/corrections/b0/b2-demo-qa/${id}`;
if(await access(directory).then(()=>true,()=>false))throw Error('QA_ALREADY_EXISTS');await mkdir(directory,{recursive:true});
const runtime=await verifyRuntime(b2RuntimePath),harness=await prepareBrowserHarness(),{pack}=await loadDemoPackage();
if((await journalCommand(newJournal(`b2-demo-${id}`),directory,'build',['node_modules/astro/bin/astro.mjs','build','--outDir',resolve(out)])).status!=='PASS')throw Error('DEMO_QA_BUILD_FAILED');
process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);const browser=await harness.open(out),views:any[]=[],requests:string[]=[],responses:any[]=[],exceptions:any[]=[];
try{
 await browser.call('Runtime.enable');await browser.call('Network.enable',{maxTotalBufferSize:33554432,maxResourceBufferSize:8388608,enableDurableMessages:true});
 browser.on('Network.requestWillBeSent',e=>requests.push(e.request.url));browser.on('Network.responseReceived',e=>responses.push({id:e.requestId,url:e.response.url,status:e.response.status}));browser.on('Runtime.exceptionThrown',e=>exceptions.push(e));
 const key=async(key:string,code:string,n:number)=>{for(const type of ['keyDown','keyUp'])await browser.call('Input.dispatchKeyEvent',{type,key,code,windowsVirtualKeyCode:n});};
 for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}]){
  await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
  requests.length=0;responses.length=0;exceptions.length=0;
  // Browser harness navigate() waits for all images; first visit local blank so
  // lazy images are inspected by deliberate scrolling rather than eager loading.
  await browser.call('Page.navigate',{url:browser.origin+'/b2/demo/'});
  for(let i=0;i<100;i++){if(await browser.evaluate(`document.readyState==='complete'&&Boolean(document.querySelector('[data-demo-package]'))`))break;await new Promise(r=>setTimeout(r,50));}
  await browser.evaluate(`document.fonts.ready`);
  const initial=await browser.evaluate(`({video_bytes:performance.getEntriesByType('resource').filter(e=>e.name.endsWith('.webm')).reduce((n,e)=>n+e.encodedBodySize,0),autoplay:document.querySelector('video').autoplay,preload:document.querySelector('video').preload,loaded_images:[...document.images].filter(i=>i.complete&&i.naturalWidth).length})`);
  if(initial.video_bytes||initial.autoplay||initial.preload!=='none'||requests.some(r=>r.endsWith('.webm')))throw Error('VIDEO_LOADED_BEFORE_INTERACTION');
  await key('Tab','Tab',9);if(!await browser.evaluate(`document.activeElement.matches('.skip')`))throw Error('SKIP_FOCUS_FAILED');await key('Enter','Enter',13);
  if(!await browser.evaluate(`location.hash==='#contenido'`))throw Error('SKIP_TARGET_FAILED');
  for(let i=0;i<4;i++)await browser.evaluate(`(async()=>{const i=document.images[${i}];i.scrollIntoView();await i.decode();})()`);
  await browser.evaluate(`document.querySelector('video').scrollIntoView()`);
  const played=await browser.call('Runtime.evaluate',{expression:`(async()=>{const v=document.querySelector('video');await v.play();await new Promise(r=>setTimeout(r,700));const advanced=v.currentTime>0;v.pause();await new Promise((r,j)=>{v.addEventListener('seeked',r,{once:true});v.addEventListener('error',()=>j(Error('VIDEO_DECODE')),{once:true});v.currentTime=.5;});await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return {advanced,current_time:v.currentTime,duration:v.duration,width:v.videoWidth,height:v.videoHeight,paused:v.paused,error:v.error?.code??null};})()`,awaitPromise:true,returnByValue:true,userGesture:true});
  if(played.exceptionDetails||!played.result.value.advanced||played.result.value.error)throw Error('ACTUAL_VIDEO_PLAYBACK_FAILED');
  const observed=await browser.evaluate(`(()=>{const root=document.querySelector('.demo-preview'),visible=[...root.querySelectorAll('h1,h2,h3,p,a,img,video')].filter(e=>e.getClientRects().length);return {lang:document.documentElement.lang,main:document.querySelectorAll('main').length,h1:document.querySelectorAll('h1').length,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,overflow:visible.filter(e=>e.getBoundingClientRect().left<-.5||e.getBoundingClientRect().right>innerWidth+.5).map(e=>e.tagName),min_font_px:Math.min(...visible.filter(e=>!['IMG','VIDEO'].includes(e.tagName)).map(e=>parseFloat(getComputedStyle(e).fontSize))),images:[...document.images].map(i=>({src:i.currentSrc.replace(location.origin,''),decoded:i.complete&&i.naturalWidth>0,width:i.getBoundingClientRect().width,height:i.getBoundingClientRect().height,loading:i.loading,alt:i.alt})),needs:[...root.querySelectorAll('[data-demo-need]')].map(e=>e.dataset.demoNeed),usage_ids:[...root.querySelectorAll('[data-demo-usage]')].flatMap(e=>[...e.dataset.demoUsage.split(' '),...(e.dataset.demoPosterUsage?[e.dataset.demoPosterUsage]:[])]),disclosure:document.querySelector('[data-demo-disclosure]').textContent,notice:document.querySelector('[data-provider-notice]').textContent,credits:[...root.querySelectorAll('.credit')].map(e=>e.textContent),forms:document.forms.length,scripts:document.scripts.length,text:root.textContent,links:[...root.querySelectorAll('a')].map(a=>a.getAttribute('href'))};})()`);
  if(observed.lang!=='es'||observed.main!==1||observed.h1!==1||observed.width>viewport.width||observed.overflow.length||observed.min_font_px<14||observed.forms||observed.scripts||observed.images.length!==4||observed.images.some((i:any)=>!i.decoded||!i.alt))throw Error(`DEMO_GEOMETRY_OR_ACCESSIBILITY_FAILED:${JSON.stringify(observed)}`);
  if(pack.usages.some(u=>!observed.usage_ids.includes(u.id))||observed.disclosure!==pack.usages[0]!.generic_label||observed.notice!==pack.usages[0]!.context_notices?.[0])throw Error('DEMO_CONTEXT_OR_BINDINGS_LOST');
  const served=[];for(const path of [...new Set(observed.images.map((i:any)=>i.src))] as string[]){const r=responses.find(r=>r.url.endsWith(path));if(!r||r.status!==200)throw Error('IMAGE_NOT_SERVED');
   const body=await browser.call('Network.getResponseBody',{requestId:r.id}),b=Buffer.from(body.body,body.base64Encoded?'base64':'utf8'),f=pack.files.find(f=>f.path===`public${path}`);if(!f||hashBytes(b)!==f.sha256)throw Error('SERVED_IMAGE_BYTES_MISMATCH');served.push({path,bytes:b.length,sha256:hashBytes(b)});}
  const videoPath='/media/b2-fictional/149678-silent-640.webm',r=responses.find(r=>r.url.endsWith(videoPath));if(!r)throw Error('VIDEO_RESPONSE_MISSING');
  const vb=await browser.call('Network.getResponseBody',{requestId:r.id}),vbytes=Buffer.from(vb.body,vb.base64Encoded?'base64':'utf8');if(hashBytes(vbytes)!==pack.silent_video.render_sha256)throw Error('VIDEO_SERVED_BYTES_MISMATCH');
  served.push({path:videoPath,bytes:vbytes.length,sha256:hashBytes(vbytes)});
  observed.text_sha256=hashBytes(observed.text);delete observed.text;
  await browser.evaluate(`window.scrollTo(0,0)`);
  const png=Buffer.from((await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:viewport.width,height:observed.height,scale:1}})).data,'base64'),html=await readFile(resolve(out,'b2/demo/index.html'));
  await writeFile(`${directory}/${viewport.id}.png`,png);if(viewport.id==='desktop')await writeFile(`${directory}/demo.html`,html);
  await browser.evaluate(`document.querySelector('nav a').focus()`);await key('Enter','Enter',13);if(!await browser.evaluate(`location.hash==='#carta'`))throw Error('DEMO_NAVIGATION_FAILED');
  const nativeIcon=(r:string)=>r.startsWith('data:image/svg+xml;base64,');
  if(exceptions.length||requests.some(r=>!r.startsWith(browser.origin+'/')&&!nativeIcon(r))||requests.some(r=>/\.jpg(?:\?|$)|\.mp4(?:\?|$)/.test(r)))throw Error(`UNEXPECTED_NETWORK_OR_SOURCE_EXPOSURE:${JSON.stringify({exceptions,requests})}`);
  views.push({viewport,initial,playback:played.result.value,observed,served,screenshot:{path:`${directory}/${viewport.id}.png`,sha256:hashBytes(png),rgba_sha256:hashBytes(await sharp(png).raw().toBuffer()),scope:'FULL_PAGE'},html_sha256:hashBytes(html),html_bytes:html.length,requests:requests.map(r=>nativeIcon(r)?`<BROWSER_CONTROL_DATA_SVG:${hashBytes(r)}>`:r.replace(browser.origin,'<LOCAL>'))});console.log(`${viewport.id}: PASS`);
 }
 const legacy=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8'));let legacyCount=0;for(const group of legacy.originals)for(const v of group.views){if(hashBytes(await readFile(resolve(out,`.${v.view.route}index.html`)))!==v.html_sha256)throw Error('H8_HTML_CHANGED');legacyCount++;}
 await writeFile(`${directory}/qa.json`,JSON.stringify({kind:'FICTIONAL_PIXABAY_MEDIA_BROWSER_QA',created_at:new Date().toISOString(),package_sha256:pack.package_sha256,runtime_sha256:runtime.snapshot_sha256,status:'TECHNICAL_PASS_HUMAN_PENDING',browser:harness.provenance,views,historical_html:legacyCount,protection:await verifyProtectedFiles('docs/evidence/corrections/b2-demo/pre/preservation.json'),limits:['Local controlled Edge154/current B2 fonts, not WCAG/field performance certification','Video 4.45MB only on user interaction; no audio rights claimed for source','Media retained in private package outside Git; full-page composite screenshots are evidence, not downloadable stock assets','No B3 grammar, live business, backend or aesthetic approval']},null,2)+'\n');
}catch(error){await writeFile(`${directory}/failure.json`,JSON.stringify({error:String(error),views_completed:views.length},null,2)+'\n');throw error;}
finally{browser.close();delete process.env['H4_BROWSER_PATH'];}
