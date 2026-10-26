import {readyPage,paintPage,openCaptureBrowser} from '../../tooling/claude-code/capture.mjs';
import {depthObserver} from '../../scripts/b3-depth-observer.ts';
import {auditDepthExperience} from '../../src/design/depth-experience-audit.ts';
import {loadB3DepthExperience} from '../../scripts/load-b3-depth-experience.ts';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [out,dir]=process.argv.slice(2),lab=await loadB3DepthExperience(),observer=await depthObserver();
await mkdir(dir,{recursive:true});let browser;const views=[],requests=[],exceptions=[];
const key=async(key,code,n)=>{await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:n});await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:n});};
try {
 for(const [width,height] of [[360,800],[390,844],[768,1024],[1024,768],[1440,1000]]) {
  browser=await openCaptureBrowser(out);
  browser.on('Network.requestWillBeSent',e=>requests.push(e.request.url));
  browser.on('Runtime.exceptionThrown',e=>exceptions.push(e));await browser.call('Runtime.enable');
  await browser.call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<=390});
  await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await readyPage(browser,'/b3/candidate-01/');
  const observed=await browser.evaluate(`(()=>{${observer};return observeDepthExperience()})()`);
  const audit=auditDepthExperience(observed,lab);
  await key('Tab','Tab',9);const skipFocused=await browser.evaluate(`document.activeElement.matches('.skip')`);
  const skipHref=await browser.evaluate(`document.activeElement.getAttribute('href')`);
  await key('Enter','Enter',13);const skipActivated=await browser.evaluate(`location.hash===${JSON.stringify(skipHref)}&&document.activeElement.id===${JSON.stringify(skipHref?.slice(1))}`);
  await browser.evaluate(`document.querySelector('.depth-navigation>summary').focus()`);await key(' ','Space',32);
  const navigationOpened=await browser.evaluate(`document.querySelector('.depth-navigation').open`);
  await key('Escape','Escape',27);const navigationClosed=await browser.evaluate(`!document.querySelector('.depth-navigation').open`);
  await browser.evaluate(`document.querySelectorAll('.journal-reading summary')[1].focus()`);await key(' ','Space',32);
  const disclosureOpened=await browser.evaluate(`document.querySelectorAll('.journal-reading')[1].open`);
  const expanded=await browser.evaluate(`(()=>{${observer};return observeDepthExperience()})()`);
  const expandedAudit=auditDepthExperience(expanded,lab);
  await browser.evaluate(`document.querySelectorAll('.journal-reading')[1].open=false;document.activeElement.blur();scrollTo(0,0)`);
  await paintPage(browser);
  const png=Buffer.from((await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:observed.geometry.height,scale:1}})).data,'base64');
  await writeFile(resolve(dir,`${width}.png`),png);
  const keyboard={skipFocused,skipActivated,navigationOpened,navigationClosed,disclosureOpened};
  views.push({viewport:{width,height},audit,expandedAudit,keyboard,observed,expanded,screenshot:{path:`${width}.png`,sha256:createHash('sha256').update(png).digest('hex')}});
  console.log(JSON.stringify({width,audit,expandedAudit,keyboard}));
  browser.close();
 }
 const result={createdAt:new Date().toISOString(),browser:browser.version,adapter:browser.adapter,views,requests,exceptions,pass:views.every(v=>v.audit.success&&v.expandedAudit.success&&Object.values(v.keyboard).every(Boolean))&&exceptions.length===0,limits:['Existing conservative source/computed-surface contrast audit, not full WCAG certification','Reduced-motion local warm renders; no cold-network Core Web Vitals measurement']};
 await writeFile(resolve(dir,'audit.json'),JSON.stringify(result,null,2)+'\n');if(!result.pass)process.exitCode=1;
}finally{browser.close();}
