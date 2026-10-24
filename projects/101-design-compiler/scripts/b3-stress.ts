import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {prepareBrowserHarness} from './lib/correction-browser.ts';
import {verifyRuntime,controlledBrowserPath} from './lib/correction-runtime.ts';
import {b2RuntimePath} from './b2-runtime.ts';
import {loadB3Lab} from './load-b3-lab.ts';
import {observeContextual,auditContextual} from '../src/design/contextual-audit.ts';
import {hashBytes} from './lib/correction-run.ts';
const id=process.argv[2];if(!/^[a-z0-9-]+$/.test(id??''))throw Error('NEW_STRESS_ID_REQUIRED');const directory=`docs/evidence/corrections/b3/${id}`;if(await access(directory).then(()=>true,()=>false))throw Error('STRESS_EXISTS');await mkdir(directory,{recursive:true});
const lab=await loadB3Lab(),runtime=await verifyRuntime(b2RuntimePath),h=await prepareBrowserHarness();process.env['H4_BROWSER_PATH']=controlledBrowserPath(runtime);const b=await h.open('.tools/corrections/b0/b3-qa/qa-08'),cases:any[]=[];
try{for(const d of lab.designs){await b.call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await b.call('Emulation.setScriptExecutionDisabled',{value:true});
 await b.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await b.call('Page.navigate',{url:b.origin+d.route});await new Promise(r=>setTimeout(r,250));
 for(let i=0;i<5;i++)await b.evaluate(`(async()=>{const i=document.images[${i}];i.scrollIntoView();await i.decode()})()`);const o=await b.evaluate(`(${observeContextual.toString()})()`),audit=auditContextual(o,lab.scenario,d,lab.media.review);
 const fallback=await b.evaluate(`({buttons_hidden:[...document.querySelectorAll('[data-demo-add],.demo-request,[data-menu-tools]')].every(e=>e.hidden),details:document.querySelectorAll('.dish-detail').length,scroll:getComputedStyle(document.documentElement).scrollBehavior})`);
 if(!audit.success||!fallback.buttons_hidden||fallback.details!==4||fallback.scroll!=='auto')throw Error(`B3_FALLBACK_FAILED:${d.id}`);cases.push({design:d.id,audit,fallback,scope:'JavaScript disabled + reduced motion; native details and content remain usable, enhancements hidden'});
 await b.call('Emulation.setScriptExecutionDisabled',{value:false});}
 // One representative shared component's expanded state, with all exact facts,
 // recipe/allergen/fiction notices and simulated table distribution visible.
 await b.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await b.call('Page.navigate',{url:b.origin+lab.designs[0]!.route});await new Promise(r=>setTimeout(r,250));
 for(let i=0;i<5;i++)await b.evaluate(`(async()=>{const i=document.images[${i}];i.scrollIntoView();await i.decode()})()`);
 await b.evaluate(`document.querySelectorAll('.dish-detail,.table-preview,.module-faqs details').forEach(d=>d.open=true);window.scrollTo(0,0)`);const expanded=await b.evaluate(`(${observeContextual.toString()})()`);
 if(!auditContextual(expanded,lab.scenario,lab.designs[0]!,lab.media.review).success)throw Error('B3_EXPANDED_FAILED');
 const png=Buffer.from((await b.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:expanded.geometry.height,scale:1}})).data,'base64');await writeFile(`${directory}/expanded-desktop.png`,png);
 const css=await readFile('src/design/contextual.css');await writeFile(`${directory}/stress.json`,JSON.stringify({kind:'B3_SHARED_FALLBACK_EXPANDED_QA',created_at:new Date().toISOString(),status:'PASS',context_sha256:lab.context_sha256,css_sha256:hashBytes(css),cases,expanded:{screenshot:`${directory}/expanded-desktop.png`,sha256:hashBytes(png),geometry:expanded.geometry},limits:['No real transactions or personal data','Not browser zoom, assistive technology or complete WCAG certification','Expanded screenshot is one shared component state, not an extra candidate or a new human vote']},null,2)+'\n');console.log('4 no-JS/reduced-motion views + expanded desktop: PASS');
}finally{b.close();delete process.env['H4_BROWSER_PATH'];}
