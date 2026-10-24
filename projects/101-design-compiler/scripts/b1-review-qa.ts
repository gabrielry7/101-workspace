import {access,mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {newJournal,journalCommand,hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
import {verifyRuntime,controlledBrowserPath} from './lib/correction-runtime.ts';
import {prepareBrowserHarness} from './lib/correction-browser.ts';
import {humanReviewCatalog as catalog,reviewFeaturesForProfile} from '../src/requirements/review-catalog.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('Usage: b1-review-qa.ts <new-run-id>');
const directory=`docs/evidence/corrections/b1/${id}`,out=`.tools/corrections/b0/b1-review-qa/${id}`;
if(await access(directory).then(()=>true,()=>false)||await access(out).then(()=>true,()=>false))throw Error('REVIEW_QA_ALREADY_EXISTS');
await mkdir(directory,{recursive:true});
const runtime=await verifyRuntime(),harness=await prepareBrowserHarness(),journal=newJournal(`b1-${id}`);
await writeFile(`${directory}/catalog.json`,JSON.stringify(catalog,null,2)+'\n');
const build=await journalCommand(journal,directory,'build',['node_modules/astro/bin/astro.mjs','build','--outDir',resolve(out)]);
if(build.status!=='PASS')throw Error('REVIEW_QA_BUILD_FAILED');
process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);
const browser=await harness.open(out),views:unknown[]=[],requests:string[]=[],exceptions:unknown[]=[];
try {
 if(browser.version!==runtime.browser_version)throw Error('REVIEW_QA_BROWSER_VERSION');
 browser.on('Network.requestWillBeSent',e=>requests.push(String(e.request.url)));browser.on('Runtime.exceptionThrown',e=>exceptions.push(e));await browser.call('Runtime.enable');
 const key=async(key:string,code:string,n:number)=>{for(const type of ['keyDown','keyUp'])await browser.call('Input.dispatchKeyEvent',{type,key,code,windowsVirtualKeyCode:n});};
 const routes=['/b1/revision/',...catalog.profiles.map(p=>`/b1/revision/${p.archetype_id}/`)];
 for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}]){
  await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
  for(const route of routes)for(const state of route.endsWith('/food_hospitality/')?['default','table-expanded']:['default']){
   requests.length=0;exceptions.length=0;await browser.navigate(route);
   await key('Tab','Tab',9);const skipFocused=await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0`);
   await key('Enter','Enter',13);if(!skipFocused||!await browser.evaluate(`location.hash==='#contenido'`))throw Error('REVIEW_QA_SKIP');
   let keyboardDisclosure=true;
   if(state==='table-expanded'){
    await browser.evaluate(`document.querySelector('#function-table_map > details > summary').focus()`);await key(' ','Space',32);
    keyboardDisclosure=await browser.evaluate(`document.querySelector('#function-table_map > details').open`);if(!keyboardDisclosure)throw Error('REVIEW_QA_DISCLOSURE');
   }
   const observed=await browser.evaluate(`(()=>{const root=document.querySelector('.review'),els=Array.from(root.querySelectorAll('h1,h2,h3,h4,p,li,summary,a')),visible=els.filter(e=>e.getClientRects().length&&e.getBoundingClientRect().width>0);return {
    lang:document.documentElement.lang,main:document.querySelectorAll('main').length,h1:document.querySelectorAll('h1').length,
    root:{...root.dataset},width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
    overflow:visible.filter(e=>e.getBoundingClientRect().left<-.5||e.getBoundingClientRect().right>innerWidth+.5).map(e=>e.textContent.slice(0,100)),
    min_font_px:Math.min(...visible.map(e=>parseFloat(getComputedStyle(e).fontSize))),
    feature_ids:Array.from(document.querySelectorAll('[data-review-feature]')).map(e=>e.dataset.reviewFeature),
    data_ids:Array.from(document.querySelectorAll('[data-review-data-id]')).map(e=>e.dataset.reviewDataId),
    data_bindings:Array.from(document.querySelectorAll('[data-review-data-id]')).map(e=>({id:e.dataset.reviewDataId,owner:e.dataset.reviewOwner,scope:e.dataset.reviewScope})),
    forms:document.forms.length,scripts:document.scripts.length,media:document.querySelectorAll('img,video,audio').length,
    links:Array.from(root.querySelectorAll('a')).map(e=>e.getAttribute('href')),notice:document.querySelector('.notice').textContent};})()`);
   if(observed.lang!=='es'||observed.main!==1||observed.h1!==1||observed.width>viewport.width||observed.overflow.length||observed.min_font_px<12||observed.forms||observed.scripts||observed.media)throw Error(`REVIEW_QA_GEOMETRY:${JSON.stringify({route,viewport,observed})}`);
   const profile=catalog.profiles.find(p=>route.endsWith(`/${p.archetype_id}/`));
   if(profile){const entries=reviewFeaturesForProfile(profile.archetype_id);
    if(observed.root.reviewCatalogSha256!==catalog.catalog_sha256||JSON.stringify([...observed.feature_ids].sort())!==JSON.stringify(entries.map(e=>e.feature.id).sort())||
     JSON.stringify([...observed.data_ids].sort())!==JSON.stringify(entries.flatMap(e=>e.feature.business_data.map(d=>d.id)).sort()))throw Error('REVIEW_QA_BINDING_LOSS');
    const ordered=(bindings:{id:string;owner:string;scope:string}[])=>bindings.toSorted((a,b)=>a.id.localeCompare(b.id));
    const expectedBindings=entries.flatMap(e=>e.feature.business_data.map(d=>({id:d.id,owner:d.owner,scope:d.scope})));
    if(JSON.stringify(ordered(observed.data_bindings))!==JSON.stringify(ordered(expectedBindings)))throw Error('REVIEW_QA_DATA_SCOPE_OR_OWNER_LOSS');
   }else if(catalog.profiles.some(p=>!observed.links.includes(`/b1/revision/${p.archetype_id}/`)))throw Error('REVIEW_QA_PROFILE_LINK_LOSS');
   const label=`review-${profile?.archetype_id??'index'}-${viewport.id}-${state}`;
   await browser.evaluate(state==='table-expanded'?`window.scrollTo(0,document.querySelector('#function-table_map').getBoundingClientRect().top+scrollY-12)`:`window.scrollTo(0,0)`);
   const png=Buffer.from((await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'),html=await readFile(resolve(out,`.${route}index.html`));
   await writeFile(`${directory}/${label}.png`,png);
   if(viewport.id==='desktop'&&state==='default')await writeFile(`${directory}/${label}.html`,html);
   const target=observed.links.find((href:string)=>href.startsWith('/'));
   await browser.evaluate(`Array.from(document.querySelectorAll('.review nav a')).find(a=>a.getAttribute('href')===${JSON.stringify(target)}).focus()`);await key('Enter','Enter',13);
   let navigation=false;for(let attempt=0;attempt<30;attempt++){navigation=await browser.evaluate(`location.pathname===${JSON.stringify(target)}`);if(navigation)break;await new Promise(r=>setTimeout(r,50));}
   if(!navigation||exceptions.length||requests.some(url=>!url.startsWith(browser.origin+'/')&&!url.startsWith('data:')))throw Error('REVIEW_QA_NAVIGATION_OR_NETWORK');
   views.push({label,route,state,viewport,observed,keyboard:{skip:true,disclosure:keyboardDisclosure,navigation},screenshot:{path:`${directory}/${label}.png`,sha256:hashBytes(png),scope:'VIEWPORT_ONLY'},html_sha256:hashBytes(html),html_bytes:html.length,requests:requests.map(url=>url.replace(browser.origin,'<LOCAL>'))});
   console.log(`${label}: PASS`);
  }
 }
 const legacy=JSON.parse(await readFile('docs/evidence/h8/run.json','utf8')),legacy_html=[];
 for(const group of legacy.originals)for(const view of group.views){const html=await readFile(resolve(out,`.${view.view.route}index.html`));if(hashBytes(html)!==view.html_sha256)throw Error('REVIEW_QA_H8_HTML_CHANGED');legacy_html.push({route:view.view.route,sha256:hashBytes(html)});}
 const preservation=await verifyProtectedFiles('docs/evidence/corrections/b1/pre/preservation.json');
 await writeFile(`${directory}/qa.json`,JSON.stringify({kind:'B1_HUMAN_REVIEW_SUPPLEMENT_QA',created_at:new Date().toISOString(),status:'TECHNICAL_PASS_HUMAN_REVIEW_PENDING',catalog_sha256:catalog.catalog_sha256,runtime_sha256:runtime.snapshot_sha256,browser:harness.provenance,views,legacy_html,preservation,limitations:['Viewport screenshots, not full-page aesthetic approval','No final restaurant demo, real business evaluation, operations or new media','Not a full accessibility or field performance audit']},null,2)+'\n');
 console.log(`PASS ${views.length} views; ${legacy_html.length} historical HTML; ${preservation.checked_files} protected files`);
}catch(error){await writeFile(`${directory}/failure.json`,JSON.stringify({error:String(error),completed:views.length},null,2)+'\n');throw error;}
finally{browser.close();delete process.env['H4_BROWSER_PATH'];}
