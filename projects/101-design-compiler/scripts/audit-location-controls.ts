// Native browser audit with an explicitly labelled offline Google API double.
// Never reserves a trial load, obtains the real key or requests Google's SDK.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { openLocalBrowser } from './lib/local-browser.ts';

const folder = resolve('.tools/honorato-google-live');
const output = resolve(folder, 'controls-audit');
await mkdir(output, { recursive: true });
const budgetPath = resolve(folder, 'trial-budget.json');
const budgetBefore = await readFile(budgetPath, 'utf8');
const browser = await openLocalBrowser(resolve(folder, 'preview/dist'));
const external: string[] = [], exceptions: string[] = [];
browser.on('Network.requestWillBeSent', event => {
  const url = new URL(event.request.url);
  if (/^https?:$/.test(url.protocol) && url.hostname !== '127.0.0.1') external.push(url.origin);
});
await browser.call('Runtime.enable');
browser.on('Runtime.exceptionThrown', event => exceptions.push(event.exceptionDetails.text));
await browser.call('Page.addScriptToEvaluateOnNewDocument', { source: `
(() => {
  window.__offlineAudit = { maps:0, configurations:0 };
  const nativeFetch = window.fetch;
  window.fetch = async (input, options) => {
    const url = new URL(String(input), location.href);
    if (url.pathname === '/trial-status' && location.search.includes('offline-exhausted'))
      return new Response(JSON.stringify({ reserved:10,limit:10,remaining:0 }),{headers:{'Content-Type':'application/json'}});
    if (url.pathname !== '/trial-config') return nativeFetch(input, options);
    window.__offlineAudit.configurations++;
    return new Response(JSON.stringify({ google:{ enabled:true,apiKey:'OFFLINE_TEST_NOT_A_KEY',mapId:'offline-map',
      styleReview:{mapId:'offline-map',pois:'none',reference:'offline:controller-test',reviewedAt:'2026-11-09T00:00:00Z'}},
      budget:{reserved:10,limit:10,remaining:0} }), {headers:{'Content-Type':'application/json'}});
  };
  window.google = { maps:{
    importLibrary:async()=>({}),
    Map:class {
      constructor(canvas, options){
        this.canvas=canvas;this.options=options;window.__offlineAudit.maps++;
        canvas.style.position='relative';canvas.style.background='#e7e7e7';
        const label=document.createElement('span');label.textContent='DOBLE OFFLINE · sin cartografía de Google';
        label.style.cssText='position:absolute;left:12px;top:12px;color:#333;font:12px system-ui;max-width:85%';canvas.append(label);
      }
      setZoom(zoom){this.options.zoom=zoom} getZoom(){return this.options.zoom}
    },
    LatLng:class {constructor(lat,lng){this.lat=lat;this.lng=lng}},
    OverlayView:class {
      setMap(map){this.map=map}
      getProjection(){return this.map?{fromLatLngToContainerPixel:()=>({x:this.map.canvas.clientWidth/2,y:this.map.canvas.clientHeight/2})}:null}
    },
    marker:{AdvancedMarkerElement:class extends EventTarget {
      constructor(options){super();Object.assign(this,options);this.wrapper=document.createElement('div');
        this.wrapper.style.cssText='position:absolute;left:50%;top:50%;transform:translate(-50%,-100%)';options.map.canvas.append(this.wrapper)}
      append(child){this.wrapper.append(child)}
    }},
    event:{addListenerOnce(_m,_e,callback){queueMicrotask(callback)},clearInstanceListeners(){},trigger(){}},
  }};
  const append = HTMLHeadElement.prototype.append;
  HTMLHeadElement.prototype.append = function(...nodes){
    const script=nodes.find(node=>node.tagName==='SCRIPT'&&node.src.startsWith('https://maps.googleapis.com/maps/api/js'));
    if(script){queueMicrotask(()=>window[new URL(script.src).searchParams.get('callback')]());return}
    return append.apply(this,nodes);
  };
  addEventListener('DOMContentLoaded',()=>{const p=document.createElement('p');
    p.textContent='VERIFICACIÓN OFFLINE · proveedor simulado para no consumir cargas';
    p.style.cssText='padding:12px;margin:0;background:#fff3ca;color:#222;font:14px system-ui';document.body.prepend(p)});
})();` });
const pause = (ms: number) => new Promise(done => setTimeout(done, ms));
async function waitFor(expression: string) {
  for (let i=0;i<100;i++) { if (await browser.evaluate(expression)) return; await pause(100); }
  throw Error('Browser condition timed out: ' + expression);
}
const change = (name: string, value: unknown) => browser.evaluate(`(() => {
  const input=document.querySelector('[data-location-controls] form').elements.namedItem(${JSON.stringify(name)});
  if(input.type==='checkbox')input.checked=${JSON.stringify(value)};else input.value=${JSON.stringify(value)};
  input.dispatchEvent(new Event('input',{bubbles:true}));
})()`);
const state = () => browser.evaluate(`document.querySelector('[data-location-bone-config]').locationBone?.inspect()`);
const measure = () => browser.evaluate(`(() => {
  const section=document.getElementById('honorato-location'),host=section.querySelector('[data-location-bone-config]');
  const words=[];
  for(const el of section.querySelectorAll('h2,address,nav a')){
    const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode())for(const match of node.textContent.matchAll(/\\S+/g)){
      const range=document.createRange();range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
      const rects=[...range.getClientRects()].filter(r=>r.width&&r.height);
      if(new Set(rects.map(r=>Math.round(r.top))).size>1)words.push(match[0]);
    }
  }
  return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,words,
    skin:section.dataset.skin,variant:section.dataset.variant,background:getComputedStyle(section).backgroundColor,
    color:getComputedStyle(section).color,infoParent:section.querySelector('.location-bone__information').parentElement.className,
    sameCanvas:host.querySelector('.location-map__canvas')===window.__originalCanvas,
    sameController:host.locationBone===window.__originalController,height:host.querySelector('.location-map__canvas')?.getBoundingClientRect().height,
    maps:window.__offlineAudit.maps,configurations:window.__offlineAudit.configurations,info:host.locationBone?.inspect()};
})()`);
const screenshot = async (name: string) => {
  const result=await browser.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  await writeFile(resolve(output,name+'.png'),Buffer.from(result.data,'base64'));
};
try {
  await browser.call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await browser.call('Page.navigate',{url:'http://127.0.0.1:8780/'});
  await waitFor(`document.querySelector('[data-google-start]')?.disabled===false`);
  assert.deepEqual(await browser.evaluate('window.__offlineAudit'),{maps:0,configurations:0});
  await change('skin','ink');
  assert.equal(await browser.evaluate(`getComputedStyle(document.getElementById('honorato-location')).backgroundColor`),'rgb(32, 43, 44)');
  assert.equal(await readFile(budgetPath,'utf8'),budgetBefore);
  await screenshot('before-google-ink');
  await browser.evaluate(`document.querySelector('[data-google-start]').click()`);
  await waitFor(`document.querySelector('[data-location-bone-config]')?.locationBone?.inspect().marker_kind==='logo'`);
  const initial=await state();
  await browser.evaluate(`window.__originalController=document.querySelector('[data-location-bone-config]').locationBone;
    window.__originalCanvas=document.querySelector('.location-map__canvas')`);
  await change('zoom',17);assert.equal((await state()).camera_zoom,17);
  await change('mapHeight',520);assert.equal((await measure()).height,520);
  await change('pinPaper','#ffe0c0');await change('pinInk','#552211');
  await change('markerLabel',true);assert.equal((await state()).marker_label_visible,true);
  await change('markerLabel',false);assert.equal((await state()).marker_label_visible,false);
  await change('variant','editorial');
  await browser.evaluate(`document.querySelector('[data-controls-save]').click()`);
  const saved=await browser.evaluate(`JSON.parse(localStorage.getItem('101-location-controls-v1'))`);
  assert.equal(saved.skin,'ink');assert.equal(saved.variant,'editorial');
  assert.equal(JSON.stringify(saved).includes('apiKey'),false);
  await browser.evaluate(`document.querySelector('[data-controls-reset]').click()`);
  assert.equal((await measure()).skin,'neutral');assert.equal((await state()).camera_zoom,16);
  await browser.evaluate(`document.querySelector('[data-controls-restore]').click()`);
  assert.equal((await measure()).skin,'ink');assert.equal((await state()).camera_zoom,17);
  await browser.evaluate(`localStorage.setItem('101-location-controls-v1',JSON.stringify({apiKey:'invalid'}));document.querySelector('[data-controls-restore]').click()`);
  assert.equal((await measure()).skin,'ink');
  await browser.evaluate(`document.querySelector('[data-controls-reset]').click()`);
  const reports=[];
  for(const width of [1440,1201,1200,1101,1100,901,900,768,721,720,681,680,621,620,390]) {
    await browser.call('Emulation.setDeviceMetricsOverride',{width,height:1100,deviceScaleFactor:1,mobile:false});
    await change('skin','ink');
    for(const variant of ['direct','map-led','editorial']) {
      await change('variant',variant);await pause(80);
      const r=await measure();reports.push(r);
      if(r.overflow||r.words.length)await screenshot('failure-'+width+'-'+variant);
      assert.equal(r.overflow,false,`Overflow: ${width}/${variant}`);assert.deepEqual(r.words,[],`Word integrity: ${width}/${variant}`);
      assert.equal(r.sameCanvas,true);assert.equal(r.sameController,true);assert.equal(r.maps,1);
      assert.deepEqual(r.info.marker_coordinate,initial.marker_coordinate);
      assert.ok(r.info.marker_anchor_offset_px<=1);
    }
    if([1440,768,390].includes(width)) for(const skin of ['neutral','paper','ink']) {
      await change('variant','direct');await change('skin',skin);await pause(80);
      await screenshot(skin+'-'+width);
    }
  }
  await browser.evaluate(`document.getElementById('honorato-location').style.fontFamily='Arial,sans-serif';document.querySelector('select[name=skin]').focus()`);
  assert.equal(await browser.evaluate(`document.activeElement.name`),'skin');
  assert.equal((await measure()).overflow,false);
  assert.deepEqual(await browser.evaluate('window.__offlineAudit'),{maps:1,configurations:1});
  await browser.call('Page.navigate',{url:'http://127.0.0.1:8780/?offline-exhausted=1'});
  await waitFor(`document.querySelector('[data-trial-status]')?.textContent.includes('agotaron')`);
  await change('skin','ink');
  assert.equal(await browser.evaluate(`document.querySelector('[data-google-start]').disabled`),true);
  assert.deepEqual(await browser.evaluate('window.__offlineAudit'),{maps:0,configurations:0});
  assert.equal(await readFile(budgetPath,'utf8'),budgetBefore);
  assert.deepEqual(external,[]);assert.deepEqual(exceptions,[]);
  await writeFile(resolve(output,'report.json'),JSON.stringify({browser:browser.version,reports,saved,
    external,exceptions,offline_api_double:true,google_live_verified:false,real_reservations_consumed:0,
    no_provider_before_click:true,one_provider_for_all_changes:true,exhausted_state_controls_work:true,
    invalid_saved_configuration_rejected:true,keyboard_focus:true,human_approval:'pending'},null,2)+'\n');
  console.log('Controls passed: 45 responsive cases, three skins, persistence, marker label, same map, exhausted state; zero real Google loads.');
} finally { browser.close(); }
