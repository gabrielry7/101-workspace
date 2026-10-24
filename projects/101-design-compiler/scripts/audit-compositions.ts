import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadCompositionLab } from './load-composition-lab.ts';
import { compositions, previewPath } from '../src/composition/registry.ts';
import { observePage } from '../src/composition/observe.ts';
import { auditRender } from '../src/composition/audit.ts';
import { byteSha256 } from '../src/media/package.ts';
import { openLocalBrowser } from './lib/local-browser.ts';

const lab=await loadCompositionLab(), browser=await openLocalBrowser();
const directory='docs/evidence/h4';await mkdir(directory,{recursive:true});
const receipts:unknown[]=[]; const errors:unknown[]=[];
const requests:string[]=[];browser.on('Network.requestWillBeSent',p=>requests.push(p.request.url));
const failures:unknown[]=[];browser.on('Runtime.exceptionThrown',p=>failures.push(p));await browser.call('Runtime.enable');
try {
  for(const c of compositions) for(const viewport of [{id:'desktop',width:1280,height:900},{id:'mobile',width:390,height:844}]) for(const page of lab.content.pages){
    const route=previewPath(c.id,page.path),label=`${c.id}-${viewport.id}${page.path==='/'?'':'-offering'}`;
    requests.length=0;failures.length=0;
    await browser.call('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.id==='mobile'});
    await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    await browser.navigate(route);
    const observed=await browser.evaluate(`(${observePage.toString()})()`) as ReturnType<typeof observePage>;
    const bindings=auditRender(observed.observation,lab,c.id,page.path);
    const codes=[...bindings.codes];
    if(observed.geometry.overflow.length||observed.geometry.document_width>viewport.width)codes.push('OVERFLOW');
    if(observed.readability.some(r=>r.contrast<4.5||r.font_px<12))codes.push('CONTRAST_OR_LEGIBILITY');
    if(observed.geometry.modules.some(m=>!m.visible))codes.push('MODULE_HIDDEN');
    if(observed.animated_elements||!observed.reduced_motion)codes.push('MOTION_POLICY');
    if(observed.resources.some(r=>!r.local)||requests.some(url=>!url.startsWith(browser.origin)))codes.push('EXTERNAL_RESOURCE');
    if(failures.length)codes.push('BROWSER_EXCEPTION');
    // Keyboard operation, focus ring, native disclosure and local route navigation.
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    const skip=await browser.evaluate(`({focused:document.activeElement.matches('.skip'),top:document.activeElement.getBoundingClientRect().top,outline:getComputedStyle(document.activeElement).outlineWidth})`);
    if(!skip.focused||skip.top<0||parseFloat(skip.outline)<3)codes.push('KEYBOARD_SKIP_FAILURE');
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    const skipTarget=await browser.evaluate(`location.hash === '#contenido'`);if(!skipTarget)codes.push('SKIP_TARGET_FAILURE');
    await browser.evaluate(`document.querySelector('summary').focus()`);
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32});
    await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32});
    await browser.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
    const disclosure=await browser.evaluate(`({open:document.querySelector('details').open,focus:getComputedStyle(document.activeElement).outlineWidth,diagnostics:[...document.querySelectorAll('[data-diagnostic-index]')].every(e=>e.getBoundingClientRect().height>0),links:[...document.querySelectorAll('.lab a,summary')].filter(e=>e.getClientRects().length).map(e=>({label:e.textContent.trim(),height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width}))})`);
    if(!disclosure.open||!disclosure.diagnostics||parseFloat(disclosure.focus)<3||disclosure.links.some((l:{height:number;width:number})=>l.height<44||l.width<24))codes.push('DISCLOSURE_OR_TOUCH_FAILURE');
    const ax=await browser.call('Accessibility.getFullAXTree');
    const landmarks=ax.nodes.filter((n:any)=>!n.ignored&&['main','navigation','heading','image','link'].includes(n.role?.value)).map((n:any)=>({role:n.role.value,name:n.name?.value??''}));
    if(!landmarks.some((n:{role:string})=>n.role==='main')||!landmarks.some((n:{role:string;name:string})=>n.role==='navigation'&&n.name==='Páginas del fixture'))codes.push('AX_LANDMARK_FAILURE');
    await browser.evaluate(`document.querySelector('details').open=false;document.activeElement.blur();window.scrollTo(0,0)`);
    await browser.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
    const closedSize=await browser.evaluate('({width:document.documentElement.clientWidth,height:document.documentElement.scrollHeight})');
    const shot=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:closedSize.width,height:closedSize.height,scale:1}});
    const png=Buffer.from(shot.data,'base64');await writeFile(`${directory}/${label}.png`,png);
    const html=await readFile(resolve('dist',`.${route}index.html`));
    const cssPaths=observed.resources.filter(r=>r.type==='link'&&r.path.endsWith('.css')).map(r=>r.path);
    const styles=await Promise.all(cssPaths.map(async path=>({path,sha256:byteSha256(await readFile(resolve('dist',`.${path}`)))})));
    const mediaBytes=observed.observation.media.length?new Uint8Array(await(await fetch(browser.origin+lab.media.asset.uri)).arrayBuffer()):null;
    if(mediaBytes&&byteSha256(mediaBytes)!==lab.media.asset.file_sha256)codes.push('SERVED_MEDIA_HASH_MISMATCH');
    const targetPage=lab.content.pages.find(p=>p.path!==page.path)!;
    await browser.evaluate(`Array.from(document.querySelectorAll('.site-nav a')).find(e=>e.dataset.route===${JSON.stringify(targetPage.path)}).focus()`);
    // Enter invokes the actual anchor. Check the destination DOM and status, not only href.
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    let reached=false;
    for(let attempt=0;attempt<30;attempt++){
      reached=await browser.evaluate(`location.pathname===${JSON.stringify(previewPath(c.id,targetPage.path))} && document.querySelector('.lab')?.dataset.semanticPage===${JSON.stringify(targetPage.path)}`);
      if(reached)break;await new Promise(done=>setTimeout(done,50));
    }
    if(!reached)codes.push('KEYBOARD_NAVIGATION_FAILURE');
    const receipt={label,variant:c.id,semantic_page:page.path,route,viewport,html_sha256:byteSha256(html),styles,
      screenshot_path:`${directory}/${label}.png`,screenshot_sha256:byteSha256(png),
      original_sha256:mediaBytes?byteSha256(mediaBytes):null,page_body_bytes:html.length+observed.resources.reduce((n,r)=>n+r.bytes,0),
      ...observed,keyboard:{skip,skip_target:skipTarget,disclosure,local_navigation:reached},accessibility:landmarks,
      status:codes.length?'FAILED':'PASSED',codes};
    receipts.push(receipt);if(codes.length)errors.push({label,codes});
    console.log(`${label}: ${codes.length?codes.join(','):'PASSED'}; image ${observed.geometry.image?.width??0}px; body ${receipt.page_body_bytes} bytes`);
  }
  // Narrow viewport / 200% text enlargement stress, without changing business content.
  const stress=[];
  for(const c of compositions){
    await browser.call('Emulation.setDeviceMetricsOverride',{width:320,height:844,deviceScaleFactor:1,mobile:true});
    await browser.navigate(previewPath(c.id,'/'));
    await browser.evaluate(`document.querySelectorAll('.lab h1,.lab p,.lab a,.lab summary,.lab-header').forEach(e=>e.style.fontSize=(parseFloat(getComputedStyle(e).fontSize)*2)+'px')`);
    const observed=await browser.evaluate(`(${observePage.toString()})()`) as ReturnType<typeof observePage>;
    const codes=observed.geometry.overflow.length||observed.geometry.document_width>320?['TEXT_200_OVERFLOW']:[];
    stress.push({variant:c.id,width:320,text_scale:2,geometry:observed.geometry,status:codes.length?'FAILED':'PASSED',codes});if(codes.length)errors.push({variant:c.id,codes});
  }
  await writeFile(`${directory}/browser-audit.json`,JSON.stringify({schema_version:'1.0.0',browser:browser.version,evaluated_at:new Date().toISOString(),client_id:lab.client_id,project_id:lab.project_id,content_sha256:lab.content.content_sha256,plan_sha256:lab.content.plan_sha256,manifest_sha256:lab.manifest_sha256,receipts,stress,status:errors.length?'FAILED':'PASSED',errors},null,2)+'\n');
  if(errors.length)throw new Error(`H4_BROWSER_AUDIT_FAILED:${JSON.stringify(errors)}`);
} finally { browser.close(); }
