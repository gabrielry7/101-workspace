import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { openLocalBrowser } from './lib/local-browser.ts';

const output = resolve('.tools/location-map-bones/audit');
await mkdir(output, { recursive: true });
const browser = await openLocalBrowser('.tools/location-map-bones/preview/dist');
const errors: string[] = [], network: string[] = [];
await browser.call('Runtime.enable');
browser.on('Runtime.exceptionThrown', (event: any) => console.log('Browser exception:',event.exceptionDetails.exception?.description||event.exceptionDetails.text));
const types: Record<string, string> = { '.js':'text/javascript', '.mjs':'text/javascript', '.svg':'image/svg+xml',
  '.woff':'font/woff', '.geojson':'application/geo+json', '.json':'application/json' };
browser.on('Fetch.requestPaused', (event: any) => {
  void (async () => {
    const type = types[extname(new URL(event.request.url).pathname)];
    if (!type) { await browser.call('Fetch.continueRequest', { requestId:event.requestId }); return; }
    const result = await browser.call('Fetch.getResponseBody', { requestId:event.requestId });
    const headers = event.responseHeaders.filter((header: any) => header.name.toLowerCase() !== 'content-type');
    headers.push({ name:'Content-Type', value:type });
    await browser.call('Fetch.fulfillRequest', { requestId:event.requestId, responseCode:event.responseStatusCode,
      responseHeaders:headers, body:result.base64Encoded ? result.body : Buffer.from(result.body).toString('base64') });
  })().catch(error => errors.push(String(error)));
});
browser.on('Network.requestWillBeSent', (event: any) => {
  if (/^https?:/.test(event.request.url) && !event.request.url.startsWith(browser.origin)) network.push(new URL(event.request.url).origin);
});
await browser.call('Fetch.enable', { patterns:[{urlPattern:browser.origin+'/*',requestStage:'Response'}] });
async function settle() {
  for (let i=0;i<150;i++) {
    const done = await browser.evaluate(`(() => {const m=document.querySelector('#comparison-brand [data-location-bone-config]');return !!m?.locationBone&&['ready','fallback','degraded'].includes(m.dataset.mapState)})()`);
    if (done) break;
    await new Promise(done=>setTimeout(done,100));
  }
}
async function capture(name: string) {
  const data = await browser.call('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
  await writeFile(resolve(output,name+'.png'),Buffer.from(data.data,'base64'));
}
const measure = `(() => {
  const words=[], clipped=[];
  for(const heading of document.querySelectorAll('h1,h2,h3,address,.location-map__marker-label')) {
    if(!heading.getClientRects().length||getComputedStyle(heading).visibility==='hidden'||heading.closest('details:not([open])'))continue;
    const walker=document.createTreeWalker(heading,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()) for(const match of node.textContent.matchAll(/\\S+/g)) {
      const range=document.createRange();range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
      const rects=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
      if(new Set(rects.map(r=>Math.round(r.top))).size>1)words.push(match[0]);
      if(rects.some(r=>r.left< -1||r.right>innerWidth+1))clipped.push(match[0]);
    }
  }
  return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,words,clipped,
    maps:[...document.querySelectorAll('[data-location-bone-config]')].map(el=>{
      const pin=el.querySelector('[data-location-part="marker-pin"]');
      const logo=el.querySelector('[data-location-part="brand-logo-slot"]');
      const p=pin?.getBoundingClientRect(),l=logo?.getBoundingClientRect();
      return {id:el.closest('section').id,...el.locationBone?.inspect(),pinPresent:!!pin,
        logoInsidePin:!l||!!p&&l.left>=p.left&&l.right<=p.right&&l.top>=p.top&&l.bottom<=p.top+p.width,
        neutralTitle:el.closest('section').dataset.skin!=='neutral'||getComputedStyle(el.closest('section').querySelector('h2')).fontSize===getComputedStyle(el.closest('section')).fontSize};
    })};
})()`;
const reports: any[] = [];
try {
  await browser.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await browser.navigate('/'); await settle();
  const first = await browser.evaluate(measure);
  console.log(JSON.stringify({width:first.width,overflow:first.overflow,maps:first.maps.map((m:any)=>({id:m.id,state:m.state,marker:m.marker_kind,offset:m.marker_anchor_offset_px}))},null,2));
  await capture('desktop-initial');
  if (process.argv.includes('--reference')) {
    await browser.evaluate("document.querySelector('#comparison details').open=true;document.querySelector('#comparison details').scrollIntoView()");
    for(let i=0;i<120;i++) {
      const reference=await browser.evaluate("document.querySelector('#comparison iframe')?.contentDocument?.getElementById('map')?.dataset.mapState");
      if(reference==='ready')break;await new Promise(done=>setTimeout(done,100));
    }
    console.log('Original state:',await browser.evaluate("({state:document.querySelector('#comparison iframe')?.contentDocument?.getElementById('map')?.dataset.mapState,resources:document.querySelector('#comparison iframe')?.contentWindow?.performance.getEntriesByType('resource').map(e=>e.name)})"));
    await capture('original-thomas-1440');
  } else if (process.argv.includes('--keyboard')) {
    await browser.navigate('/bound/');
    await browser.evaluate('new Promise(r=>setTimeout(r,4000))');
    await browser.call('Page.bringToFront');
    console.log(JSON.stringify(await browser.evaluate(`(() => {const root=document.querySelector('[data-location-bone-config]');const marker=document.querySelector('.single-business-marker');marker?.focus();return {state:root?.dataset.mapState,reason:root?.dataset.mapReason,error:root?.locationBone?.inspect().map_error,active:document.activeElement?.tagName,markerStyle:marker&&getComputedStyle(marker).visibility}})()`),null,2));
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    console.log(JSON.stringify(await browser.evaluate('({active:document.activeElement?.tagName,app:document.activeElement?.dataset.mapApp})')));
  } else if (process.argv.includes('--smoke')) {
    await writeFile(resolve(output,'smoke.json'),JSON.stringify({first,network,errors},null,2));
  } else {
    assert.equal(first.maps.find((m:any)=>m.id==='comparison-brand').state,'ready');
    assert.ok(await browser.evaluate("document.getElementById('variants').compareDocumentPosition(document.getElementById('comparison')) & Node.DOCUMENT_POSITION_FOLLOWING"));
    assert.ok(await browser.evaluate("document.getElementById('google').textContent.includes('por configurar')"));
    const cloudStyle=await browser.evaluate("fetch('/google-no-pois.style.json').then(r=>r.json())");
    assert.equal(cloudStyle.styles.find((item:any)=>item.id==='pointOfInterest').label.visible,false);
    for(const width of [360,619,620,621,679,680,681,719,720,721,768,899,900,901,1200,1201,1440]) {
      await browser.call('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
      await browser.evaluate('new Promise(r=>setTimeout(r,120))');
      const result=await browser.evaluate(measure);reports.push(result);
      if(result.clipped.length||result.words.length||result.overflow) {
        await capture('failure-'+width);
        console.log(JSON.stringify(await browser.evaluate(`([...document.querySelectorAll('.location-map__marker-label')].map(el=>({id:el.closest('.location-bone')?.id,box:el.getBoundingClientRect().toJSON(),state:el.closest('[data-map-state]')?.dataset.mapState,visibility:getComputedStyle(el).visibility})))`)));
      }
      assert.equal(result.overflow,false,`overflow at ${width}`);
      assert.deepEqual(result.words,[],`split words at ${width}`);
      assert.deepEqual(result.clipped,[],`clipping at ${width}`);
      for(const map of result.maps.filter((m:any)=>m.state==='ready')) {
        assert.deepEqual(map.rendered_poi_ids,[]);
        assert.equal(map.pinPresent,true,`missing pin ${map.id} at ${width}`);
        assert.equal(map.logoInsidePin,true,`logo outside pin ${map.id} at ${width}`);
        assert.equal(map.neutralTitle,true,`brand title styling on neutral ${map.id}`);
        if(map.marker_anchor_offset_px!==null&&!map.id.startsWith('state-')) assert.ok(map.marker_anchor_offset_px<=1,`anchor ${map.id} at ${width}: ${map.marker_anchor_offset_px}`);
      }
      for(const id of ['variant-direct','variant-map-led','variant-editorial']) {
        assert.equal(result.maps.find((m:any)=>m.id===id).marker_kind,'logo',`neutral logo slot ${id}`);
      }
      if([360,768,1440].includes(width))await capture('workshop-'+width);
      if([360,768,1440].includes(width)) {
        for(const id of ['comparison-brand','variant-direct','variant-map-led','variant-editorial']) {
          await browser.evaluate(`document.getElementById('${id}').scrollIntoView({block:'start'});new Promise(r=>setTimeout(r,200))`);
          await capture(id+'-'+width);
        }
        await browser.evaluate('scrollTo(0,0)');
      }
    }
    const before=await browser.evaluate("document.querySelector('#comparison-brand [data-location-bone-config]').locationBone.inspect()");
    await browser.evaluate("document.querySelector('[data-workshop-pan]').click();document.querySelector('[data-workshop-zoom]').click();document.querySelector('[data-workshop-skin=ink]').click()");
    await browser.evaluate('new Promise(r=>setTimeout(r,500))');
    const after=await browser.evaluate("document.querySelector('#comparison-brand [data-location-bone-config]').locationBone.inspect()");
    assert.deepEqual(after.marker_coordinate,before.marker_coordinate);assert.deepEqual(after.rendered_poi_ids,[]);
    assert.ok(after.marker_anchor_offset_px<=1);assert.equal(after.marker_kind,'logo');
    const rejects=await browser.evaluate(`(() => {const m=document.querySelector('#comparison-brand [data-location-bone-config]').locationBone;try{m.setPresentation({pois:{mode:'all'}});return false}catch{return true}})()`);
    assert.ok(rejects);
    await browser.evaluate("document.querySelector('[data-workshop-save]').click();document.querySelector('[data-workshop-skin=neutral]').click();document.querySelector('[data-workshop-restore]').click()");
    assert.equal(await browser.evaluate("document.getElementById('comparison-brand').dataset.skin"),'ink');
    await browser.evaluate("document.querySelector('[data-workshop-skin=paper]').click();document.querySelectorAll('details').forEach(el=>el.open=true)");
    await browser.evaluate('new Promise(r=>setTimeout(r,500))');
    const states=await browser.evaluate(measure);
    assert.equal(states.maps.find((m:any)=>m.id==='state-broken-logo').marker_kind,'pin');
    assert.equal(states.maps.find((m:any)=>m.id==='state-broken-logo').logo_reason,'LOGO_LOAD_FAILED');
    assert.equal(states.maps.find((m:any)=>m.id==='state-no-coordinate').business_pin_plotted,false);
    assert.equal(states.maps.find((m:any)=>m.id==='state-google').state,'fallback');
    await browser.call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    await browser.evaluate("document.querySelector('#comparison-brand').scrollIntoView()");
    await capture('brand-reduced-motion');
    await browser.call('Emulation.setEmulatedMedia',{features:[{name:'forced-colors',value:'active'}]});
    await capture('forced-colors');
    await browser.call('Emulation.setEmulatedMedia',{features:[]});
    await browser.evaluate("document.querySelectorAll('.location-bone').forEach(el=>el.style.fontFamily='serif')");
    const fallback=await browser.evaluate(measure);assert.deepEqual(fallback.words,[]);assert.equal(fallback.overflow,false);
    await browser.call('Emulation.setScriptExecutionDisabled',{value:true});
    let loaded=false;browser.on('Page.loadEventFired',()=>{loaded=true;});
    await browser.call('Page.navigate',{url:browser.origin+'/'});
    for(let i=0;i<100&&!loaded;i++)await new Promise(done=>setTimeout(done,30));
    assert.ok(loaded);await capture('without-javascript');
    await browser.call('Emulation.setScriptExecutionDisabled',{value:false});
    const ssr=await browser.evaluate("({address:document.querySelector('#comparison-brand address')?.textContent,placeholder:!!document.querySelector('#comparison-brand .location-bone__placeholder')})");
    assert.ok(ssr.address&&ssr.placeholder);
    await browser.navigate('/');await settle();
    await browser.evaluate("document.querySelector('#comparison details').open=true;document.querySelector('#comparison details').scrollIntoView()");
    for(let i=0;i<120;i++) {
      if(await browser.evaluate("document.querySelector('#comparison iframe')?.contentDocument?.getElementById('map')?.dataset.mapState==='ready'"))break;
      await new Promise(done=>setTimeout(done,100));
    }
    await capture('original-thomas-1440');
    await browser.evaluate("document.querySelector('#comparison details').open=false");
    const google=await browser.evaluate(`(async()=>{const {runGoogleChecks}=await import('/google-browser-test.js');const config=JSON.parse(document.querySelector('#comparison-brand [data-location-bone-config]').dataset.locationBoneConfig);return runGoogleChecks(config)})()`);
    await browser.navigate('/bound/');
    for(let i=0;i<150;i++) { if(await browser.evaluate("document.querySelector('[data-location-bone-config]')?.dataset.mapState==='ready'"))break;await new Promise(done=>setTimeout(done,50)); }
    await browser.evaluate("document.querySelector('.single-business-marker').focus()");
    await browser.call('Page.bringToFront');
    await browser.call('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    await browser.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    assert.equal(await browser.evaluate("document.activeElement?.dataset.mapApp"),'google');
    const keyboard={markerActivationFocusesGoogle:true};
    assert.deepEqual(network,[]);assert.deepEqual(errors,[]);
    await writeFile(resolve(output,'report.json'),JSON.stringify({browser:browser.version,widths:reports,states,before,after,ssr,google,keyboard,network,errors,
      google_live_verified:false,human_approval:false},null,2));
    console.log('Location native browser checks passed.');
  }
} finally { browser.close(); }
