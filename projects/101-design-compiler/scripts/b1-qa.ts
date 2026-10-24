import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {performance} from 'node:perf_hooks';
import {newJournal,journalCommand,hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
import {verifyRuntime,controlledBrowserPath} from './lib/correction-runtime.ts';
import {prepareBrowserHarness} from './lib/correction-browser.ts';
import {loadB1Fixtures} from './lib/b1-fixtures.ts';
import {observeInspector} from '../src/requirements/observe.ts';
import {decodeScreenshot} from '../src/audit/png.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {FunctionalDiagnosticV1} from '../src/requirements/contracts.ts';
import {requirementCatalog} from '../src/requirements/catalog.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('Usage: b1-qa.ts <new-run-id>');
const directory=`docs/evidence/corrections/b1/${id}`,out=`.tools/corrections/b0/b1-qa/${id}`,started=performance.now();
if(await access(directory).then(()=>true,()=>false)||await access(out).then(()=>true,()=>false))throw Error('B1_QA_RUN_EXISTS');await mkdir(directory,{recursive:true});
const journal=newJournal(`b1-${id}`),runtime=await verifyRuntime(),harness=await prepareBrowserHarness(),fixtures=await loadB1Fixtures();
await writeFile(`${directory}/browser-harness.ts.txt`,harness.adapted);
const views:{label:string;route:string;viewport:{id:string;width:number;height:number};state:string;observed:ReturnType<typeof observeInspector>;
 html_path:string;html_sha256:string;screenshot_path:string;screenshot_sha256:string;rgba_sha256:string;capture_size:{width:number;height:number};full_page:boolean;
 keyboard:{skip:boolean;disclosure:boolean;navigation:boolean};requests:string[];browser_exceptions:unknown[];page_bytes:number;wall_seconds:number}[]=[];
const routes=['/b1/','/b1/catalogo/',...fixtures.map(f=>`/b1/${f.scenario}/`)];
let browser:Awaited<ReturnType<typeof harness.open>>|undefined;
try {
 const build=await journalCommand(journal,directory,'build',['node_modules/astro/bin/astro.mjs','build','--outDir',resolve(out)]);if(build.status!=='PASS')throw Error('B1_QA_BUILD_FAILED');
 process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);browser=await harness.open(out);if(browser.version!==runtime.browser_version)throw Error('B1_BROWSER_VERSION');
 const requests:string[]=[],exceptions:unknown[]=[];browser.on('Network.requestWillBeSent',e=>requests.push(String(e.request.url)));browser.on('Runtime.exceptionThrown',e=>exceptions.push(e));await browser.call('Runtime.enable');
 for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}]) {
  await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
  await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  for(const route of routes)for(const state of route==='/b1/restaurante/'?['default','reservation-expanded']:['default']) {
   const viewStart=performance.now();requests.length=0;exceptions.length=0;await browser.navigate(route);
   const key=async(key:string,code:string,n:number)=>{await browser!.call('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:n});await browser!.call('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:n});};
   await key('Tab','Tab',9);const focused=await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0`) as boolean;
   await key('Enter','Enter',13);const skip=focused&&await browser.evaluate(`location.hash==='#contenido'`) as boolean;
   let disclosure=true;
   const hasDetails=await browser.evaluate(`!!document.querySelector('.b1 details summary')`) as boolean;
   if(hasDetails){await browser.evaluate(`document.querySelector('.b1 details summary').focus()`);await key(' ','Space',32);disclosure=await browser.evaluate(`document.querySelector('.b1 details').open`) as boolean;
    await browser.evaluate(`document.querySelector('.b1 details').open=false;document.activeElement.blur()`);}
   if(state==='reservation-expanded')await browser.evaluate(`(()=>{const card=Array.from(document.querySelectorAll('[data-goal-card]')).find(e=>e.dataset.capabilityId==='reservation'&&e.dataset.scopeId!==${JSON.stringify(fixtures.find(f=>f.scenario==='restaurante')!.input.business_id)});card.querySelector('[data-level-id="connected_confirmation"]').open=true;})()`);
   await browser.evaluate(`window.scrollTo(0,0);document.activeElement.blur();new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
   const observed=await browser.evaluate(`(${observeInspector.toString()})()`) as ReturnType<typeof observeInspector>;
   if(observed.lang!=='es'||observed.main_count!==1||observed.h1_count!==1||observed.document.width>viewport.width||observed.overflow.length||
    observed.forms||observed.buttons||observed.scripts||observed.media||observed.resources.some(r=>!r.local)||observed.readability.some(r=>r.font_px<12||r.contrast<4.5)||!skip||!disclosure) {
    await writeFile(`${directory}/failed-view.json`,JSON.stringify({route,viewport,state,observed,requests,exceptions},null,2)+'\n');throw Error('B1_INSPECTOR_GATE_FAILED');
   }
   if(observed.root.b1Page==='case') {
    const scenario=route.split('/')[2]!,data=JSON.parse(await readFile(`data/derived/requirements-v1/${scenario}.json`,'utf8')),diagnostic=FunctionalDiagnosticV1.parse(data.diagnostic);
    const expected=diagnostic.entries.map(e=>({scope_id:e.scope_id,capability_id:e.capability_id,relevance:e.relevance,emitted:String(e.emitted_in_plan)}));
    const expectedFields=diagnostic.entries.flatMap(e=>e.levels.flatMap(l=>l.requirements.map(r=>({scope_id:e.scope_id,capability_id:e.capability_id,level_id:l.level_id,requirement_id:r.requirement_id,status:r.status,owner:r.owner}))));
    const ordered=(a:unknown[])=>[...a].sort((a,b)=>inputSha256(a).localeCompare(inputSha256(b)));
    if(observed.root.diagnosticSha256!==diagnostic.diagnostic_sha256||inputSha256(ordered(observed.goals))!==inputSha256(ordered(expected))||
     inputSha256(ordered(observed.fields))!==inputSha256(ordered(expectedFields)))throw Error('B1_RENDER_BINDING_LOSS');
   }
   if(observed.root.b1Page==='catalog'&&(observed.catalog_cards.length!==47||new Set(observed.catalog_cards).size!==47||observed.root.catalogSha256!==requirementCatalog.catalog_sha256))throw Error('B1_RENDER_CATALOG_LOSS');
   const size={width:observed.document.client_width,height:Math.min(observed.document.height,Math.floor(19000000/observed.document.client_width))};
   const shot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:size.width,height:size.height,scale:1}});
   const png=Buffer.from(shot.data,'base64'),decoded=decodeScreenshot(png),label=`${route.split('/').filter(Boolean).join('-')}-${viewport.id}-${state}`;
   const screenshot_path=`${directory}/${label}.png`,html_path=`${directory}/${label}.html`,html=await readFile(resolve(out,`.${route}index.html`));
   await writeFile(screenshot_path,png);await writeFile(html_path,html);
   const target=await browser.evaluate(`document.querySelector('.b1-nav a').getAttribute('href')`) as string;
   await browser.evaluate(`document.querySelector('.b1-nav a').focus()`);await key('Enter','Enter',13);let navigation=false;
   for(let attempt=0;attempt<30;attempt++){navigation=await browser.evaluate(`location.pathname===${JSON.stringify(target)}`) as boolean;if(navigation)break;await new Promise(r=>setTimeout(r,50));}
   if(!navigation||exceptions.length||requests.some(url=>!url.startsWith(browser!.origin+'/')&&!url.startsWith('data:')))throw Error('B1_NAVIGATION_OR_NETWORK_FAILED');
   views.push({label,route,viewport,state,observed,html_path,html_sha256:hashBytes(html),screenshot_path,screenshot_sha256:hashBytes(png),rgba_sha256:hashBytes(decoded.pixels),capture_size:size,
    full_page:size.height===observed.document.height,keyboard:{skip,disclosure,navigation},requests:requests.map(u=>u.replace(browser!.origin,'<LOCAL>')),browser_exceptions:[...exceptions],
    page_bytes:html.length+observed.resources.reduce((sum,r)=>sum+r.bytes,0),wall_seconds:(performance.now()-viewStart)/1000});
   await writeFile(`${directory}/partial.json`,JSON.stringify({views},null,2)+'\n');console.log(`${label}: PASS; ${observed.goals.length} functions, ${observed.fields.length} data requirements retained`);
  }
 }
 const history=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8')),legacy_html=[];
 for(const group of history.originals)for(const view of group.views){const html=await readFile(resolve(out,`.${view.view.route}index.html`));
  if(hashBytes(html)!==view.html_sha256)throw Error('B1_LEGACY_HTML_CHANGED');legacy_html.push({route:view.view.route,viewport:view.viewport.id,sha256:hashBytes(html)});}
 const preservation=await verifyProtectedFiles('docs/evidence/corrections/b1/pre/preservation.json');await verifyRuntime();
 const receipt={schema_version:'1.0.0',kind:'B1_INSPECTOR_BROWSER_QA',status:'LAB_INSPECTOR_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW',created_at:new Date().toISOString(),runtime_sha256:runtime.snapshot_sha256,
  catalog_sha256:requirementCatalog.catalog_sha256,browser_harness:harness.provenance,views,legacy_html,preservation,
  metering:{wall_seconds:(performance.now()-started)/1000,human_work_seconds:null,session_tokens:null,total_cost:null,currency:null,provider_operations:'NOT_INVOKED_BY_THIS_RECIPE'},
  limitations:['B0 copied browser sandbox exception: fixed local test pages only','DOM/keyboard/contrast checks are not a complete WCAG audit','Diagnostic inspector, not final website aesthetic approval','Legacy HTML equivalence, no new H8 rollback/global verifier approval'],production_ready:false};
 await writeFile(`${directory}/qa.json`,JSON.stringify(receipt,null,2)+'\n');console.log(`B1 QA PASS ${views.length} views; legacy HTML ${legacy_html.length}`);
}catch(error){await writeFile(`${directory}/failure.json`,JSON.stringify({status:'FAIL',error:String(error),wall_seconds:(performance.now()-started)/1000,views_completed:views.length,human_work_seconds:null,total_cost:null},null,2)+'\n');throw error;}
finally{browser?.close();delete process.env['H4_BROWSER_PATH'];}
