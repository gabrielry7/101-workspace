import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
import {openLocalBrowser} from './lib/local-browser.ts';

const output=resolve('docs/evidence/bones/footer-001');
await mkdir(output+'/captures',{recursive:true});
const browser=await openLocalBrowser('dist-footer-bones');
const errors: unknown[]=[];
browser.on('Runtime.exceptionThrown',event=>errors.push(event));
const evidence: any[]=[];
const pause='new Promise(r=>setTimeout(r,60))';
try{
  await browser.call('Runtime.enable');
  const viewport=async(width:number,height=1000)=>browser.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
  const screenshot=async(name:string,width:number,height:number)=>{
    const result=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height,scale:1}});
    await writeFile(output+'/captures/'+name+'.png',Buffer.from(result.data,'base64'));
  };
  const inspect=await readFile(new URL('./footer-inspection.js',import.meta.url),'utf8');
  for(const width of [1440,768,991,992,993,600,601,360]){
    await viewport(1700,1100);
    await browser.navigate('/bones/footers/caretta/');
    const report=await browser.evaluate('(async()=>{for(let i=0;i<80;i++){if(window.footerBoneWorkbench?.getReport())return window.footerBoneWorkbench.setWidth('+width+');await '+pause+';}throw Error("Workshop not ready");})()');
    assert.equal(report.coverage.footer_bounds.width,width);
    assert.equal(report.shared_inspector.available,true);
    const m=report.coverage.metrics;
    assert.ok(Math.abs(m.text_line_boxes.percent+m.without_text.percent-100)<=.02);
    assert.ok(Math.abs(m.occupied_layout.percent+m.free_layout.percent-100)<=.02);
    assert.ok(Object.values(m).every((v:any)=>v.percent>=0&&v.percent<=100));
    assert.equal(report.coverage.viewport.height,Math.ceil(report.coverage.footer_bounds.height));
    const filename='measurements-'+width;
    await writeFile(output+'/'+filename+'.json',JSON.stringify(report,null,2)+'\n');
    if(width===1440){
      await browser.evaluate('document.getElementById("toggle-guides").click()');
      assert.equal(await browser.evaluate('!!document.querySelector("iframe").contentDocument.querySelector("[data-101-design-overlay]")'),true);
      await screenshot('workshop-1440',1700,1100);
    }
    await viewport(width,1000);
    await browser.navigate('/bones/footers/caretta/instance/');
    const stats=await browser.evaluate(inspect);
    assert.equal(stats.overflow,false,'horizontal overflow at '+width);
    assert.deepEqual(stats.brokenWords,[],'word breaks at '+width);
    assert.equal(stats.groups,4);assert.equal(stats.soon,5);
    assert.equal(stats.cookieDisabled,true);
    assert.ok(stats.links.every((l:any)=>l.name&&/^(https?:|mailto:)/.test(l.href)));
    assert.equal(stats.inspectorLoaded,false);
    if(width>=992)assert.deepEqual(stats.regions,[274,448,84]);
    await screenshot('neutral-'+width,width,Math.ceil(stats.height));
    evidence.push({width,height:stats.height,groups:stats.groups,soon:stats.soon,overflow:stats.overflow,broken_words:stats.brokenWords,measurements:filename+'.json'});
  }
  // Font fallback remains in the actual component, with the same real copy.
  await browser.evaluate('document.querySelector(".bone-footer").style.setProperty("--bf-font","UnavailableFooterFont, monospace")');
  const fallback=await browser.evaluate(inspect);
  assert.equal(fallback.overflow,false);assert.deepEqual(fallback.brokenWords,[]);
  await screenshot('fallback-360',360,Math.ceil(fallback.height));
  await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  assert.equal(await browser.evaluate('document.getAnimations().length'),0);
  await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
  await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
  assert.equal(await browser.evaluate('document.activeElement.tagName'),'A');
  await browser.call('Emulation.setScriptExecutionDisabled',{value:true});
  const noJsLoaded=new Promise<void>(done=>browser.on('Page.loadEventFired',()=>done()));
  await browser.call('Page.navigate',{url:browser.origin+'/bones/footers/caretta/instance/'});
  await noJsLoaded;
  const noJsDocument=await browser.call('DOM.getDocument');
  const noJsGroups=await browser.call('DOM.querySelectorAll',{nodeId:noJsDocument.root.nodeId,selector:'[data-footer-part=group]'});
  assert.equal(noJsGroups.nodeIds.length,4);
  await browser.call('Emulation.setScriptExecutionDisabled',{value:false});
  await browser.navigate('/bones/footers/caretta/event-instance/');
  const cookieEvent=await browser.evaluate('(()=>{let received=0;document.addEventListener("101:footer-cookie-settings",()=>received++);const b=document.querySelector("[data-footer-cookie]");b.click();return {received,disabled:b.disabled};})()');
  assert.deepEqual(cookieEvent,{received:1,disabled:false});
  // Simulate an unprepared checkout without changing the real inspector owner.
  await browser.call('Network.setBlockedURLs',{urls:['https://*','*/__bone-tools/*']});
  await viewport(1440,1000);
  await browser.navigate('/bones/footers/caretta/');
  const unavailable=await browser.evaluate('(async()=>{for(let i=0;i<80;i++){const r=window.footerBoneWorkbench?.getReport();if(r)return r;await '+pause+';}throw Error("Missing inspector fallback failed");})()');
  assert.equal(unavailable.shared_inspector.available,false);
  assert.ok(unavailable.coverage.metrics.text_line_boxes.percent>0);
  assert.equal(errors.length,0,JSON.stringify(errors));
  await writeFile(output+'/verification.json',JSON.stringify({
    schema:'101-footer-verification-v1',verified_at:new Date().toISOString(),browser:browser.version,
    bone:'footer.directory-watermark@0.1.0',cases:evidence,
    checks:{font_fallback:true,reduced_motion:true,keyboard:true,no_js:true,cookie_event_contract:true,inspector_absence:true,operator_guides:true,customer_inspector_absent:true,page_exceptions:errors.length},
    build_scope:'same Astro installation, byte-identical staged bones source; no alternate renderer',
    full_project_build:'blocked by preserved legacy B3 media package; no gates resealed',
    human_visual_approval:'pending',
  },null,2)+'\n');
  console.log(JSON.stringify({status:'passed',cases:evidence,checks:'fallback, keyboard, reduced motion, no-JS, cookie event, optional shared inspector',human_approval:'pending'}));
}finally{browser.close();}
