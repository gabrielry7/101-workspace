import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import sharp from 'sharp';
import {newJournal,journalCommand,hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
import {verifyRuntime,controlledBrowserPath} from './lib/correction-runtime.ts';
import {prepareBrowserHarness} from './lib/correction-browser.ts';
import {loadB2Library} from './load-b2-library.ts';
import {b2RuntimePath} from './b2-runtime.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('Usage: b2-qa.ts <new-run-id>');
const directory=`docs/evidence/corrections/b2/${id}`,out=`.tools/corrections/b0/b2-qa/${id}`;
if(await access(directory).then(()=>true,()=>false)||await access(out).then(()=>true,()=>false))throw Error('QA_ALREADY_EXISTS');
await mkdir(directory,{recursive:true});
const runtime=await verifyRuntime(b2RuntimePath),harness=await prepareBrowserHarness(),journal=newJournal(`b2-${id}`),{library}=await loadB2Library();
if((await journalCommand(journal,directory,'build',['node_modules/astro/bin/astro.mjs','build','--outDir',resolve(out)])).status!=='PASS')throw Error('QA_BUILD_FAILED');
process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);
const browser=await harness.open(out),views:any[]=[],requests:string[]=[],exceptions:any[]=[],responses:any[]=[];
try{
 if(browser.version!==runtime.browser_version)throw Error('QA_BROWSER_MISMATCH');
 browser.on('Network.requestWillBeSent',e=>requests.push(String(e.request.url)));
 browser.on('Runtime.exceptionThrown',e=>exceptions.push(e));
 browser.on('Network.responseReceived',e=>responses.push({id:e.requestId,url:e.response.url,status:e.response.status,mime:e.response.mimeType}));
 await browser.call('Runtime.enable');
 await browser.call('Network.enable',{maxTotalBufferSize:33554432,maxResourceBufferSize:8388608,enableDurableMessages:true});
 const key=async(key:string,code:string,n:number)=>{for(const type of ['keyDown','keyUp'])await browser.call('Input.dispatchKeyEvent',{type,key,code,windowsVirtualKeyCode:n});};
 for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}]){
  await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
  for(const route of ['/b2/','/b2/pilot/','/b2/corpus/','/b2/providers/']){
   requests.length=0;exceptions.length=0;responses.length=0;await browser.navigate(route);
   await key('Tab','Tab',9);if(!await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0`))throw Error('QA_SKIP_FOCUS');
   await key('Enter','Enter',13);if(!await browser.evaluate(`location.hash==='#contenido'`))throw Error('QA_SKIP_NAVIGATION');
   let disclosure=true;
   if(await browser.evaluate(`Boolean(document.querySelector('summary'))`)){
    await browser.evaluate(`document.querySelector('summary').focus()`);await key(' ','Space',32);
    disclosure=await browser.evaluate(`document.querySelector('details').open`);if(!disclosure)throw Error('QA_DISCLOSURE');
   }
   // Inspect all content, including long literal reference notes, at both sizes.
   await browser.evaluate(`document.querySelectorAll('details').forEach(e=>e.open=true)`);
   const observed=await browser.evaluate(`(()=>{const root=document.querySelector('.review'),visible=Array.from(root.querySelectorAll('h1,h2,h3,p,li,summary,a,pre,dt,dd,code,img')).filter(e=>e.getClientRects().length&&e.getBoundingClientRect().width>0);return {
    lang:document.documentElement.lang,main:document.querySelectorAll('main').length,h1:document.querySelectorAll('h1').length,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
    overflow:visible.filter(e=>e.getBoundingClientRect().left<-.5||e.getBoundingClientRect().right>innerWidth+.5).map(e=>e.textContent.slice(0,100)),
    min_font_px:Math.min(...visible.filter(e=>e.tagName!=='IMG').map(e=>parseFloat(getComputedStyle(e).fontSize))),
    request_ids:Array.from(document.querySelectorAll('[data-b2-request]')).map(e=>e.dataset.b2Request),bindings:Array.from(document.querySelectorAll('[data-b2-binding]')).map(e=>e.dataset.b2Binding),
    references:Array.from(document.querySelectorAll('[data-reference-id]')).map(e=>({id:e.dataset.referenceId,scope:e.dataset.referenceScope})),providers:Array.from(document.querySelectorAll('[data-provider-id]')).map(e=>e.dataset.providerId),
    forms:document.forms.length,scripts:document.scripts.length,images:Array.from(document.images).map(i=>({src:i.currentSrc.replace(location.origin,''),decoded:i.complete&&i.naturalWidth>0,natural_width:i.naturalWidth,natural_height:i.naturalHeight,width:i.getBoundingClientRect().width,height:i.getBoundingClientRect().height,alt:i.alt})),
    figure:document.querySelector('figure')?{...document.querySelector('figure').dataset}:null,credit:document.querySelector('[data-credit]')?.textContent,context:document.querySelector('[data-context]')?.textContent,notice:document.querySelector('[data-notice]')?.textContent,
    documentary_gap:document.body.textContent.includes('Hueco documental bloqueado'),
    resources:performance.getEntriesByType('resource').map(e=>({path:e.name.replace(location.origin,''),bytes:e.encodedBodySize,duration_ms:e.duration})),
    text_sha_input:root.textContent,links:Array.from(root.querySelectorAll('a')).map(a=>a.getAttribute('href'))};})()`);
   if(observed.lang!=='es'||observed.main!==1||observed.h1!==1||observed.width>viewport.width||observed.overflow.length||observed.min_font_px<12||observed.forms||observed.scripts)throw Error(`QA_GEOMETRY:${JSON.stringify({route,viewport,observed})}`);
   if(route==='/b2/pilot/'){
    if(observed.request_ids.length!==library.requests.length||library.requests.some(r=>!observed.request_ids.includes(r.id))||library.bindings.some(b=>!observed.bindings.includes(b.id))||!observed.documentary_gap)throw Error('QA_BINDING_OR_GAP_LOST');
    if(observed.figure?.librarySha256!==library.library_sha256||observed.figure?.role!=='ATMOSPHERIC'||observed.credit!==library.manifest.usages[0]!.attribution_text||observed.context!==library.manifest.usages[0]!.generic_label||observed.notice!==library.manifest.usages[0]!.context_notices?.[0])throw Error('QA_MEDIA_CONTEXT_LOST');
    const image=observed.images[0],expected=`/media/b2/d255-19-${viewport.id==='mobile'?480:960}.webp`;
    if(observed.images.length!==1||!image.decoded||image.src!==expected||image.width>640||!image.alt)throw Error('QA_RESPONSIVE_MEDIA');
    const response=responses.find(r=>r.url.endsWith(expected));if(!response||response.status!==200)throw Error('QA_MEDIA_RESPONSE');
    const body=await browser.call('Network.getResponseBody',{requestId:response.id});
    const bytes=Buffer.from(body.body,body.base64Encoded?'base64':'utf8'),file=library.files.find(f=>f.path===`public${expected}`)!;
    if(hashBytes(bytes)!==file.sha256||bytes.length!==file.bytes||requests.some(r=>r.endsWith('.jpg')))throw Error('QA_SERVED_MEDIA_BYTES');
    observed.served_media={path:expected,bytes:bytes.length,sha256:hashBytes(bytes),mime:response.mime};
   }
   if(route==='/b2/corpus/'&&(observed.references.length!==21||observed.references.filter((r:any)=>r.scope==='GLOBAL_REPORTED').length!==18))throw Error('QA_CORPUS_LOSS');
   if(route==='/b2/providers/'&&observed.providers.length!==7)throw Error('QA_PROVIDER_LOSS');
   observed.text_sha256=hashBytes(observed.text_sha_input);delete observed.text_sha_input;
   await browser.evaluate(`document.querySelectorAll('details').forEach(e=>e.open=false);window.scrollTo(0,0)`);
   const label=`${route.split('/').filter(Boolean).at(-1)}-${viewport.id}`;
   const png=Buffer.from((await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'),html=await readFile(resolve(out,`.${route}index.html`));
   await writeFile(`${directory}/${label}.png`,png);
   if(viewport.id==='desktop')await writeFile(`${directory}/${label}.html`,html);
   const target=observed.links.find((href:string)=>href.startsWith('/'));
   await browser.evaluate(`Array.from(document.querySelectorAll('.review nav a')).find(a=>a.getAttribute('href')===${JSON.stringify(target)}).focus()`);await key('Enter','Enter',13);
   let navigation=false;for(let attempt=0;attempt<30;attempt++){navigation=await browser.evaluate(`location.pathname===${JSON.stringify(target)}`);if(navigation)break;await new Promise(r=>setTimeout(r,50));}
   if(!navigation||exceptions.length||requests.some(url=>!url.startsWith(browser.origin+'/')&&!url.startsWith('data:')))throw Error('QA_NETWORK_OR_NAVIGATION');
   views.push({label,route,viewport,observed,keyboard:{skip:true,disclosure,navigation},screenshot:{path:`${directory}/${label}.png`,sha256:hashBytes(png),rgba_sha256:hashBytes(await sharp(png).raw().toBuffer()),scope:'VIEWPORT_ONLY'},html_sha256:hashBytes(html),html_bytes:html.length,requests:requests.map(url=>url.replace(browser.origin,'<LOCAL>'))});
   console.log(`${label}: PASS`);
  }
 }
 const legacy=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8')),legacy_html=[];
 for(const group of legacy.originals)for(const view of group.views){const bytes=await readFile(resolve(out,`.${view.view.route}index.html`));if(hashBytes(bytes)!==view.html_sha256)throw Error('H8_HTML_CHANGED');legacy_html.push({route:view.view.route,sha256:hashBytes(bytes)});}
 const protection=await verifyProtectedFiles('docs/evidence/corrections/b2/pre/preservation.json');
 await writeFile(`${directory}/qa.json`,JSON.stringify({kind:'B2_ACTUAL_MEDIA_RENDER_QA',created_at:new Date().toISOString(),status:'TECHNICAL_PASS_HUMAN_REVIEW_PENDING',library_sha256:library.library_sha256,runtime_sha256:runtime.snapshot_sha256,browser:harness.provenance,views,legacy_html,protection,
 limitations:['Same-host laboratory, DPR1, no field-performance measurement or full accessibility certification','No final restaurant design or human aesthetic approval','Shared historical harness sends WebP as application/octet-stream; actual browser decode and byte hashes verified','One photo, two technical derivatives; no video/audio downloaded or inspected']},null,2)+'\n');
 console.log(`PASS ${views.length} views; ${legacy_html.length} historical HTML; ${protection.checked_files} protected files`);
}catch(error){await writeFile(`${directory}/failure.json`,JSON.stringify({error:String(error),completed:views.length},null,2)+'\n');throw error;}
finally{browser.close();delete process.env['H4_BROWSER_PATH'];}
