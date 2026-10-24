import { readFile,writeFile,mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { auditIndex } from '../src/audit/index.ts';
import { performance } from 'node:perf_hooks';
import { loadCohortLab,cohortPath } from './load-cohort-lab.ts';
import { openLocalBrowser } from './lib/local-browser.ts';
import { observePage } from '../src/composition/observe.ts';
import { measureRaster,measurePixels } from '../src/audit/raster.ts';
import { auditCandidate,chooseAcceptable,type BrowserView } from '../src/audit/evaluate.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { byteSha256 } from '../src/media/package.ts';
const state=await loadCohortLab(true),browser=await openLocalBrowser();
const policy={schema_version:'1.0.0',profile:'LAB',max_page_bytes:300000,max_requests:3,max_client_js_bytes:0,original_media_exception:false} as const;
const directory='docs/evidence/h7';await mkdir(directory,{recursive:true});
const receipts:any[]=[],indexReceipts:any[]=[],errors:any[]=[];const started=performance.now();
async function observe(mount:any,page:string,viewport:{id:string;width:number;height:number},fault?:'truth'|'rights'|'contrast'){
 await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
 await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 const route=cohortPath(mount.scenario,mount.candidate.plan.id,page);await browser.navigate(route);
 if(fault==='truth')await browser.evaluate(`document.querySelector('[data-fact-id]').textContent='Precio falso sembrado para prueba negativa'`);
 if(fault==='rights')await browser.evaluate(`const img=document.createElement('img');img.dataset.assetId='unknown-image';img.src='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';document.querySelector('.stage').append(img)`);
 if(fault==='contrast')await browser.evaluate(`document.querySelector('h1').style.color=getComputedStyle(document.querySelector('.lab')).backgroundColor`);
 const observed=await browser.evaluate(`(${observePage.toString()})()`) as ReturnType<typeof observePage>;
 await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
 await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
 const skip=await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0&&parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=3`);
 await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 const skipTarget=await browser.evaluate(`location.hash==='#contenido'`);
 await browser.evaluate(`document.querySelector('summary').focus()`);
 await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32});
 const disclosure=await browser.evaluate(`document.querySelector('details').open&&parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=3`);
 await browser.evaluate(`document.querySelector('details').open=false;document.activeElement.blur();window.scrollTo(0,0);new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
 const size=await browser.evaluate('({width:document.documentElement.clientWidth,height:document.documentElement.scrollHeight})');
 const shot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:size.width,height:size.height,scale:1}});
 const label=`${mount.id}-${viewport.id}${page==='/'?'':page.replaceAll('/','-')}${fault?`-seed-${fault}`:''}`;
 const png=Buffer.from(shot.data,'base64'),path=`${directory}/${label}.png`;await writeFile(path,png);
 const raster=await browser.evaluate(`(()=>{const measurePixels=${measurePixels.toString()};return (${measureRaster.toString()})(${JSON.stringify(shot.data)},${JSON.stringify(observed.geometry.image)})})()`);
 const html=await readFile(resolve('dist',`.${route}index.html`));
 const target=mount.candidate.plan.pages.find((p:{path:string})=>p.path!==page)!;
 await browser.evaluate(`Array.from(document.querySelectorAll('.site-nav a')).find(e=>e.dataset.route===${JSON.stringify(target.path)}).focus()`);
 await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 let navigation=false;for(let i=0;i<30;i++){navigation=await browser.evaluate(`location.pathname===${JSON.stringify(cohortPath(mount.scenario,mount.candidate.plan.id,target.path))}`);if(navigation)break;await new Promise(r=>setTimeout(r,50));}
 const view:BrowserView={...observed,mount_id:mount.id,requested_viewport:{width:viewport.width,height:viewport.height},route,screenshot_path:path,page_body_bytes:html.length+observed.resources.reduce((n,r)=>n+r.bytes,0),keyboard:{skip:skip&&skipTarget,disclosure,navigation},raster};
 const audit=auditCandidate(mount.candidate,mount.lab,view,policy,p=>cohortPath(mount.scenario,mount.candidate.plan.id,p));
 const expectedFail=mount.candidate.layout.measure==='fixed-wide'&&page==='/'||Boolean(fault);
 if(expectedFail?(audit.status!=='FAIL'):audit.status!=='LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW')errors.push({label,status:audit.status,codes:audit.issues.map(i=>i.code),expectedFail});
 const styles=await Promise.all(observed.resources.filter(r=>r.path.endsWith('.css')).map(async r=>({path:r.path,sha256:byteSha256(await readFile(resolve('dist',`.${r.path}`)))})));
 const served=null;
 const receipt={label,mount_id:mount.id,kind:fault?'SEEDED_DOM_DEFECT_TEST':mount.kind,seeded_fault:fault??null,candidate:mount.candidate,candidate_sha256:inputSha256(mount.candidate),
  viewport,semantic_page:page,html_sha256:byteSha256(html),styles,screenshot_sha256:byteSha256(png),served_media_sha256:served,view,audit};
 receipts.push(receipt);console.log(`${label}: ${audit.status}; ${audit.issues.map(i=>i.code).join(',')||'no issues'}; raster ${raster.sampled_pixels} pixels`);
 return receipt;
}
async function observeIndex(viewport:{id:string;width:number;height:number}){
 await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
 await browser.navigate('/h7/');
 const dom=await browser.evaluate(`({main_count:document.querySelectorAll('main').length,nested_main:!!document.querySelector('main main'),h1_count:document.querySelectorAll('h1').length,skip_target_id:document.querySelector('.skip').getAttribute('href').slice(1),skip_target_is_main:document.querySelector(document.querySelector('.skip').getAttribute('href'))?.tagName==='MAIN'})`);
 await browser.call('Accessibility.enable');const ax=await browser.call('Accessibility.getFullAXTree');const axMainCount=ax.nodes.filter((n:any)=>!n.ignored&&n.role?.value==='main').length;
 const key=async(key:string,code:string,value:number)=>{await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:value});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:value});};
 await key('Tab','Tab',9);const skipVisible=await browser.evaluate(`document.activeElement.matches('.skip')&&document.activeElement.getBoundingClientRect().top>=0&&parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=3`);
 await key('Enter','Enter',13);const skipActivated=await browser.evaluate(`location.hash==='#contenido'&&document.querySelector('#contenido').tagName==='MAIN'`);
 let href='';for(let i=0;i<30;i++){await key('Tab','Tab',9);href=await browser.evaluate(`document.activeElement.tagName==='A'?document.activeElement.getAttribute('href'):''`);if(href?.startsWith('/h7/'))break;}
 const reachable=Boolean(href?.startsWith('/h7/'));let activated=false;
 if(reachable){await key('Enter','Enter',13);for(let i=0;i<30;i++){activated=await browser.evaluate(`location.pathname===${JSON.stringify(href)}`);if(activated)break;await new Promise(r=>setTimeout(r,50));}}
 const observed={...dom,ax_main_count:axMainCount,skip_visible:skipVisible,skip_activated:skipActivated,link_reachable_by_tab:reachable,link_activated:activated,link_href:href??''};const audit=auditIndex(observed);if(audit.status==='FAIL')errors.push({index:viewport.id,codes:audit.codes});
 await browser.navigate('/h7/');const size=await browser.evaluate('({width:document.documentElement.clientWidth,height:document.documentElement.scrollHeight})');const shot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:size.width,height:size.height,scale:1}});const png=Buffer.from(shot.data,'base64');const path=`${directory}/index-${viewport.id}.png`;await writeFile(path,png);const html=await readFile('dist/h7/index.html');
 const styles=await browser.evaluate(`Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(e=>e.getAttribute('href'))`);const styleHashes=await Promise.all(styles.map(async(path:string)=>({path,sha256:byteSha256(await readFile(resolve('dist',`.${path}`)))})));
 indexReceipts.push({route:'/h7/',viewport,capture_size:size,observation:observed,ax_main_nodes:ax.nodes.filter((n:any)=>n.role?.value==='main'),audit,html_sha256:byteSha256(html),styles:styleHashes,screenshot_path:path,screenshot_sha256:byteSha256(png)});console.log(`index-${viewport.id}: ${audit.status}; DOM/AX main=${dom.main_count}/${axMainCount}; keyboard skip/navigation=${skipActivated}/${activated}`);
}
try{
 for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}])await observeIndex(viewport);
 for(const c of state.cases){if(!c.lab||!c.search)continue;for(const plan of c.search.finalists){const mount={id:`${c.scenario}-${plan.id}`,scenario:c.scenario,lab:c.lab,kind:'COHORT_FINALIST',candidate:{schema_version:'1.0.0',plan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}}};for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}])for(const p of plan.pages)await observe(mount,p.path,viewport);}}
 const negativeCase=state.cases.find(c=>c.scenario==='media-unknown')!;const negativePlan=negativeCase.search!.finalists[0]!;for(const fault of ['truth','rights','contrast'] as const)await observe({id:`media-unknown-${negativePlan.id}`,scenario:'media-unknown',lab:negativeCase.lab,kind:'SEEDED_DEFECT_TEST',candidate:{schema_version:'1.0.0',plan:negativePlan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}}},'/',{id:'mobile',width:390,height:844},fault);
 const selections=state.cases.filter(c=>c.lab&&c.search).map(c=>({scenario:c.scenario,selection:chooseAcceptable(c.search!.finalists.map(plan=>({candidate:receipts.find(r=>r.mount_id===`${c.scenario}-${plan.id}`).candidate,reports:receipts.filter(r=>r.mount_id===`${c.scenario}-${plan.id}`&&!r.seeded_fault).map(r=>r.audit)})))}));
 for(const s of selections)if(s.selection.finalists.length!==2)errors.push({scenario:s.scenario,error:'COVERAGE_SELECTION_FAILED'});
 await writeFile(`${directory}/run.json`,JSON.stringify({schema_version:'1.0.0',status:errors.length?'FAILED':'PASSED',errors,browser:browser.version,evaluated_at:new Date().toISOString(),policy,cohort_version:state.reservation.cohort_version,budget:state.budget,actual:{rendered_plans:new Set(receipts.filter(r=>!r.seeded_fault).map(r=>r.mount_id)).size,browser_views:receipts.length,index_browser_views:indexReceipts.length,wall_seconds:(performance.now()-started)/1000,provider_api_calls:0,new_spend:0,money_session:'NOT_MEASURED',tokens:'NOT_MEASURED'},receipts,index_receipts:indexReceipts,selections,human_preference:'NOT_COLLECTED',production_ready:false,beauty_calibration:'NOT_PERFORMED'},null,2)+'\n');
 if(errors.length)throw Error(`H7_BROWSER_FAIL:${JSON.stringify(errors)}`);
}finally{browser.close();}
