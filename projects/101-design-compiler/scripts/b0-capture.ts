import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { performance } from 'node:perf_hooks';
import { prepareBrowserHarness } from './lib/correction-browser.ts';
import { verifyRuntime, controlledBrowserPath } from './lib/correction-runtime.ts';
import { newJournal, journalCommand, hashBytes, treeHashes, verifyProtectedFiles } from './lib/correction-run.ts';
import { DesignLockV1, type DesignLock } from '../src/lock/contracts.ts';
import { validateLock } from '../src/lock/validate.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { observePage } from '../src/composition/observe.ts';
import { auditCandidate, type BrowserView } from '../src/audit/evaluate.ts';
import { decodeScreenshot } from '../src/audit/png.ts';
import { measurePixels } from '../src/audit/raster.ts';
import type { GeneralCompositionLab } from '../src/composition/lab.ts';

const id = process.argv[2];
if (!id || !/^[a-z0-9-]+$/.test(id)) throw Error('Usage: b0-capture.ts <new-run-id>');
const directory = `docs/evidence/corrections/b0/${id}`;
if (await access(directory).then(()=>true,()=>false)) throw Error('B0_RUN_ALREADY_EXISTS');
await mkdir(directory,{recursive:true});
const started=performance.now(),journal=newJournal(id),runtime=await verifyRuntime();
const recipePaths=['scripts/b0-capture.ts','scripts/lib/correction-run.ts','scripts/lib/correction-runtime.ts','scripts/lib/correction-browser.ts'];
const recipe=await Promise.all(recipePaths.map(async path=>({path,sha256:hashBytes(await readFile(path))})));
const harness=await prepareBrowserHarness();
await writeFile(`${directory}/browser-harness.ts.txt`,harness.adapted);
const locks=await Promise.all(['pilot-flow','pilot-rail','hybrid-no-media'].map(async name=>{
 const lock=DesignLockV1.parse(JSON.parse(await readFile(`fixtures/locks/h8/${name}.json`,'utf8')));
 if(!validateLock(lock).success)throw Error('B0_INVALID_LEGACY_LOCK');
 return lock;
}));
const oldRun=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8'));
const policy={schema_version:'1.0.0',profile:'LAB',max_page_bytes:2500000,max_requests:3,max_client_js_bytes:0,original_media_exception:true} as const;
const routeFor=(lock:DesignLock,path:string)=>`/${lock.mount.kind}/${lock.mount.id}${path==='/'?'/':`${path}/`}`;
const publicFiles=async(out:string)=>(await treeHashes(out)).filter(f=>!f.path.startsWith('.'));

async function capture(out:string,iteration:string) {
 process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);
 const browser=await harness.open(out),receipts=[];
 const requests:string[]=[],blocked:string[]=[],exceptions:unknown[]=[];
 browser.on('Network.requestWillBeSent',event=>requests.push(String(event.request.url)));
 browser.on('Runtime.exceptionThrown',event=>exceptions.push(event));
 browser.on('Fetch.requestPaused',event=>{
  const url=String(event.request.url);
  const allowed=url.startsWith(browser.origin+'/')||url.startsWith('data:');
  if(!allowed)blocked.push(url.replace(/\?.*$/,'?[REMOVED]'));
  void browser.call(allowed?'Fetch.continueRequest':'Fetch.failRequest',allowed?{requestId:event.requestId}:{requestId:event.requestId,errorReason:'BlockedByClient'}).catch(error=>exceptions.push(String(error)));
 });
 try {
  if(browser.version!==runtime.browser_version)throw Error('B0_CONTROLLED_BROWSER_VERSION_MISMATCH');
  await browser.call('Runtime.enable');
  await browser.call('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
  for(const lock of locks) for(const viewport of lock.environment.viewports) {
   await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
   await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
   for(const page of lock.resolved_plan.pages) {
    const viewStarted=performance.now(),route=routeFor(lock,page.path);requests.length=0;blocked.length=0;exceptions.length=0;
    await browser.navigate(route);
    const observed=await browser.evaluate(`(${observePage.toString()})()`) as ReturnType<typeof observePage>;
    const key=async(value:string,code:string,n:number)=>{await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:value,code,windowsVirtualKeyCode:n});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:value,code,windowsVirtualKeyCode:n});};
    await key('Tab','Tab',9);const skip=await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0`) as boolean;
    await key('Enter','Enter',13);const activated=await browser.evaluate(`location.hash==='#contenido'`) as boolean;
    await browser.evaluate(`document.querySelector('summary').focus()`);await key(' ','Space',32);
    const disclosure=await browser.evaluate(`document.querySelector('details').open`) as boolean;
    await browser.evaluate(`document.querySelector('details').open=false;document.activeElement.blur();window.scrollTo(0,0);new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
    await browser.call('DOM.enable');await browser.call('CSS.enable');
    const dom=await browser.call('DOM.getDocument'),heading=await browser.call('DOM.querySelector',{nodeId:dom.root.nodeId,selector:'.lab h1'});
    const fonts=await browser.call('CSS.getPlatformFontsForNode',{nodeId:heading.nodeId});
    const size=await browser.evaluate('({width:document.documentElement.clientWidth,height:document.documentElement.scrollHeight})') as {width:number;height:number};
    const screenshot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:size.width,height:size.height,scale:1}});
    const png=Buffer.from(screenshot.data,'base64'),label=`${lock.id}-${viewport.id}${page.path==='/'?'':page.path.replaceAll('/','-')}`;
    const screenshot_path=`${directory}/${iteration}-${label}.png`;await writeFile(screenshot_path,png);
    const decoded=decodeScreenshot(png),raster=measurePixels(decoded.pixels,decoded.width,decoded.height,observed.geometry.image);
    const htmlPath=`${directory}/${iteration}-${label}.html`,html=await readFile(resolve(out,`.${route}index.html`));await writeFile(htmlPath,html);
    let navigation=false;
    const target=lock.resolved_plan.pages.find(p=>p.path!==page.path)!;
    await browser.evaluate(`window.scrollTo(0,0);Array.from(document.querySelectorAll('.site-nav a')).find(e=>e.dataset.route===${JSON.stringify(target.path)}).focus()`);
    await key('Enter','Enter',13);
    for(let attempt=0;attempt<40;attempt++) {
     navigation=await browser.evaluate(`location.pathname===${JSON.stringify(routeFor(lock,target.path))}`) as boolean;
     if(navigation)break;await new Promise(done=>setTimeout(done,50));
    }
    const lab=lock.lab as GeneralCompositionLab;
    const served_media_sha256=lab.media&&page.path===lab.media.usage.page?hashBytes(new Uint8Array(await(await fetch(browser.origin+lab.media.asset.uri)).arrayBuffer())):null;
    if(served_media_sha256&&served_media_sha256!==lab.media!.asset.file_sha256)throw Error('B0_SERVED_MEDIA_CHANGED');
    const view:BrowserView={...observed,route,mount_id:lock.mount.id,requested_viewport:{width:viewport.width,height:viewport.height},
     screenshot_path,page_body_bytes:html.length+observed.resources.reduce((sum,r)=>sum+r.bytes,0),keyboard:{skip:skip&&activated,disclosure,navigation},raster};
    const candidate={schema_version:'1.0.0',plan:lock.resolved_plan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}} as const;
    const audit=auditCandidate(candidate,lab,view,policy,p=>routeFor(lock,p));
    if(audit.status!=='LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW'||blocked.length||exceptions.length||requests.some(url=>!url.startsWith(browser.origin+'/')&&!url.startsWith('data:'))) {
     await writeFile(`${directory}/failed-view.json`,JSON.stringify({label,audit,blocked,exceptions,requests},null,2)+'\n');
     throw Error(`B0_CAPTURE_FAILED:${label}:${audit.issues.map(i=>i.code)}`);
    }
    const reference=oldRun.originals.find((g:{label:string})=>g.label===`${lock.id}-original`).views.find((v:{semantic_page:string;viewport:{id:string}})=>v.semantic_page===page.path&&v.viewport.id===viewport.id);
    const originalPng=decodeScreenshot(await readFile(reference.screenshot_path));
    const historical_pixels_equal=originalPng.width===decoded.width&&originalPng.height===decoded.height&&Buffer.from(originalPng.pixels).equals(Buffer.from(decoded.pixels));
    receipts.push({label,lock_id:lock.id,lock_sha256:lock.lock_sha256,semantic_page:page.path,route,viewport,
     html_path:htmlPath,html_sha256:hashBytes(html),screenshot_path,screenshot_sha256:hashBytes(png),capture_size:size,
     decoded_rgba_sha256:hashBytes(decoded.pixels),fonts:fonts.fonts,view,audit,served_media_sha256,
     historical_html_equal:hashBytes(html)===reference.html_sha256,historical_pixels_equal,
     page_requests:requests.map(url=>url.replace(browser.origin,'<LOCAL>')),blocked_requests:[...blocked],browser_exceptions:[...exceptions],wall_seconds:(performance.now()-viewStarted)/1000});
    console.log(`${iteration}:${label}: ${audit.status}, historical pixels ${historical_pixels_equal}`);
    await writeFile(`${directory}/partial-${iteration}.json`,JSON.stringify({browser:browser.version,receipts},null,2)+'\n');
   }
  }
  return {browser:browser.version,receipts};
 } finally {browser.close();delete process.env['H4_BROWSER_PATH'];}
}
const outputs:{iteration:string;out:string;files:Awaited<ReturnType<typeof publicFiles>>}[]=[],captures:Awaited<ReturnType<typeof capture>>[]=[];
try {
for(const iteration of ['a','b']) {
 const out=`.tools/corrections/b0/${id}/build-${iteration}`;
 if(await access(out).then(()=>true,()=>false))throw Error('B0_BUILD_DIRECTORY_ALREADY_EXISTS');
 const result=await journalCommand(journal,directory,`build-${iteration}`,['node_modules/astro/bin/astro.mjs','build','--outDir',resolve(out)]);
 if(result.status!=='PASS')throw Error('B0_BUILD_FAILED');
 outputs.push({iteration,out,files:await publicFiles(out)});
 captures.push(await capture(out,iteration));
 await verifyRuntime();
}
const comparisons=captures[0]!.receipts.map((left,index)=>{
 const right=captures[1]!.receipts[index]!;
 const observable=(receipt:typeof left)=>({observation:receipt.view.observation,geometry:receipt.view.geometry,readability:receipt.view.readability,fonts:receipt.fonts,media:receipt.served_media_sha256});
 return {label:left.label,html_equal:left.html_sha256===right.html_sha256,pixels_equal:left.decoded_rgba_sha256===right.decoded_rgba_sha256,
  functional_equal:inputSha256(observable(left))===inputSha256(observable(right))};
});
const outputs_equal=inputSha256(outputs[0]!.files)===inputSha256(outputs[1]!.files);
if(!outputs_equal||comparisons.length!==16||comparisons.some(c=>!c.html_equal||!c.pixels_equal||!c.functional_equal))throw Error('B0_REPEATABILITY_FAILED');
for(const item of recipe)if(hashBytes(await readFile(item.path))!==item.sha256)throw Error('B0_CAPTURE_RECIPE_DRIFT');
const preservation=await verifyProtectedFiles('docs/evidence/corrections/b0/pre/protected-files.json');
const receipt={schema_version:'1.0.0',kind:'B0_CONTROLLED_CAPTURE',status:'CONTROLLED_SAME_HOST_REPEATABILITY_PASS',created_at:new Date().toISOString(),
 runtime_sha256:runtime.snapshot_sha256,recipe,browser_harness:harness.provenance,outputs,captures,comparisons,outputs_equal,preservation,
 historical_comparison_status:captures.every(group=>group.receipts.every(r=>r.historical_html_equal&&r.historical_pixels_equal))?'MATCHED':'DIFFERENCES_OBSERVED',
 limitations:['Same Windows/OS/fonts/dependencies guarded before/after; not cross-machine equivalence','Copied Windows Edge needs sandbox disabled; fixed local test pages only, no browsing providers','Existing synthetic sparse fixtures, not final aesthetic approval','No complete H8 historical verifier override or reseal','Browser page requests only; not all background OS traffic'],
 metering:{wall_seconds:(performance.now()-started)/1000,human_work_seconds:null,session_tokens:null,session_cost:null,total_cost:null,currency:null,
  provider_operations:'NOT_INVOKED_BY_THIS_RECIPE',human_approval:'NOT_COLLECTED'},production_ready:false};
await writeFile(`${directory}/capture.json`,JSON.stringify(receipt,null,2)+'\n');
console.log(`B0 controlled repeatability PASS: 32 views, 16 pairs; historical ${receipt.historical_comparison_status}. No human acceptance.`);
} catch(error) {
 await writeFile(`${directory}/failure.json`,JSON.stringify({status:'FAIL',error:String(error),created_at:new Date().toISOString(),recipe,
  runtime_sha256:runtime.snapshot_sha256,browser_harness:harness.provenance,machine_wall_seconds:(performance.now()-started)/1000,
  human_work_seconds:null,total_cost:null,session_tokens:null,human_approval:'NOT_COLLECTED'},null,2)+'\n');
 throw error;
}
