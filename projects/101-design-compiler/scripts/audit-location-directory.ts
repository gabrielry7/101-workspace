import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { openLocalBrowser } from './lib/local-browser.ts';
import { locationDirectoryAnatomy, neutralLocationDirectory } from '../src/bones/location-directory.ts';

// Run against the two existing private local servers. Never activate Google.
const out = '.tools/location-directory-bone/verification';
await mkdir(out, { recursive: true });
const ledgerPaths = ['.tools/arabica-locations-reference/trial-budget.json', '.tools/honorato-google-live/trial-budget.json'];
const ledgersBefore = await Promise.all(ledgerPaths.map(p => readFile(p, 'utf8')));
const b = await openLocalBrowser();
const checks: string[] = [], external: string[] = [], errors: string[] = [];
const matrix: any[] = [], comparisons: any[] = [];
const check = (condition: unknown, name: string) => { assert.ok(condition, name); checks.push(name); console.log('PASS', name); };
const wait = (ms = 80) => new Promise(r => setTimeout(r, ms));
async function until(expression: string) {
  for (let i = 0; i < 80; i++) { if (await b.evaluate(expression)) return; await wait(50); }
  throw Error('Browser did not settle: ' + expression);
}
async function visit(path: string, port = 8779, boot = true) {
  await b.call('Page.navigate', { url: `http://127.0.0.1:${port}${path}` });
  await until("document.readyState === 'complete'");
  await b.evaluate('document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');
  if (boot) await until(port === 8780 || path.startsWith('/arabica/') ? '!!window.arabicaReference' : "!!document.querySelector('[data-directory-view]')");
}
async function viewport(width: number) {
  await b.call('Emulation.setDeviceMetricsOverride', { width, height: width < 781 ? 844 : 1000, deviceScaleFactor: 1, mobile: false });
  await b.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
}
async function screenshot(name: string) {
  const s = await b.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(`${out}/${name}.png`, Buffer.from(s.data, 'base64'));
}
const state = () => b.evaluate("document.querySelector('.location-directory').dataset.directoryView");
const select = (id: string) => b.evaluate(`void document.querySelector('[data-directory-panel] a[data-directory-target="${id}"]').click()`);
const fitExpression = `(()=>{
 const root=document.querySelector('.location-directory'), map=root.querySelector('.ld-map').getBoundingClientRect(), panel=root.querySelector('.ld-panel').getBoundingClientRect();
 const broken=[]; const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()) {const node=walker.currentNode;if(!node.parentElement.closest('.ld-title,.ld-panel-heading,.ld-panel a,.ld-card h3'))continue;
 for(const match of node.textContent.matchAll(/[\\p{L}\\p{N}]+/gu)){const r=document.createRange();r.setStart(node,match.index);r.setEnd(node,match.index+match[0].length);const lines=[...r.getClientRects()].filter(r=>r.width>0&&r.height>0);if(new Set(lines.map(r=>Math.round(r.y))).size>1)broken.push(match[0]);}}
 return {overflow:document.documentElement.scrollWidth>innerWidth,broken,map:map.toJSON(),panel:panel.toJSON()};})()`;

try {
  await b.call('Runtime.enable');
  b.on('Runtime.exceptionThrown', p => errors.push(p.exceptionDetails.text));
  b.on('Network.requestWillBeSent', ({ request }) => {
    if (/^https?:/.test(request.url) && !/^http:\/\/(127\.0\.0\.1|localhost):/.test(request.url)) external.push(request.url.split('?')[0]);
  });
  await viewport(1440); await visit('/bones/location-directory/');
  check(await state() === 'overview', 'neutral component boots without provider');
  await b.evaluate("window.retainedMap=document.querySelector('[data-directory-map]');window.directoryEvents=[];document.querySelector('.location-directory').addEventListener('directory:viewchange',e=>window.directoryEvents.push(e.detail.viewId))");
  await select('region-1'); check(await state() === 'region-1', 'region link selects area');
  await select('region-1/city-1'); check(await state() === 'region-1/city-1', 'city link selects locality');
  check(await b.evaluate("document.querySelector('[aria-current=location]').dataset.directoryTarget==='region-1/city-1'"), 'active location is exposed');
  await b.evaluate('history.back()'); await until("document.querySelector('.location-directory').dataset.directoryView==='region-1'");
  await b.evaluate('history.forward()'); await until("document.querySelector('.location-directory').dataset.directoryView==='region-1/city-1'");
  checks.push('browser back and forward restore hierarchy');
  await b.evaluate("void document.querySelector('[data-directory-map]').dispatchEvent(new MouseEvent('click',{bubbles:true}))");
  check(await state() === 'region-1/city-1', 'map background click does not reset navigation');
  await b.evaluate("void document.querySelector('.location-directory').dispatchEvent(new CustomEvent('directory:select',{detail:{viewId:'region-1/city-2'}}))");
  check(await state() === 'region-1/city-2', 'provider selection event uses shared navigation');
  check(await b.evaluate("window.retainedMap===document.querySelector('[data-directory-map]') && window.directoryEvents.includes('region-1/city-2')"), 'map node survives navigation and emits view changes');
  await b.evaluate("void document.querySelector('[data-directory-part$=\":back\"]').click()");
  check(await state() === 'region-1', 'back action selects actual parent');
  await b.evaluate("void document.querySelector('[data-directory-panel] a').focus()");
  await b.call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await b.call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  check(await state() === 'region-1/city-1' && await b.evaluate("document.activeElement.matches('[data-directory-panel] a')"), 'keyboard selection restores useful focus');
  await visit('/bones/location-directory/?view=region-3');
  check(await b.evaluate("document.querySelector('[data-directory-part=\"region-3:empty\"]').textContent.includes('Sin entradas') && document.querySelector('[data-directory-part$=\":back\"]')!==null"), 'empty area has honest state and usable return');
  await visit('/bones/location-directory/?view=not-a-view');
  check(await state() === 'overview', 'unknown route falls back to overview');
  const anatomy = new Set(locationDirectoryAnatomy(neutralLocationDirectory).map(p => p.id));
  for (const view of neutralLocationDirectory.views) {
    await b.evaluate(`void document.querySelector('.location-directory').dispatchEvent(new CustomEvent('directory:select',{detail:{viewId:${JSON.stringify(view.id)}}}))`);
    const parts = await b.evaluate("[...document.querySelectorAll('[data-directory-part]')].map(e=>e.dataset.directoryPart)");
    check(parts.every((part: string) => anatomy.has(part)) && new Set(parts).size === parts.length, `unique canonical anatomy: ${view.id}`);
  }
  await visit('/bones/location-directory/');
  for (const width of [360,390,430,431,559,560,561,768,779,780,781,1000,1001,1024,1440]) {
    await viewport(width);
    const m = await b.evaluate(fitExpression);
    check(!m.overflow && !m.broken.length, `whole words and no document overflow: ${width}px`);
    check(width <= 780 ? m.panel.y >= m.map.bottom - 1 && Math.abs(m.map.height - 300) < 1 : m.panel.y === m.map.y && m.panel.x > m.map.x, `composition: ${width}px`);
    matrix.push({width,...m});
    if ([390,768,1440].includes(width)) await screenshot(`neutral-${width}`);
  }
  await viewport(390);
  const initialCard = await b.evaluate("document.querySelector('.ld-card-track').scrollLeft");
  await b.evaluate("document.querySelectorAll('.ld-card-dots button')[1].click()");
  await wait(600);
  check(await b.evaluate("document.querySelector('.ld-card-track').scrollLeft") > initialCard && await b.evaluate("document.querySelectorAll('.ld-card-dots button')[1].hasAttribute('aria-current')"), 'mobile pagination scrolls actual rail');
  await b.evaluate("document.querySelector('.ld-card-track').scrollIntoView({block:'center'})");
  const track = await b.evaluate("document.querySelector('.ld-card-track').getBoundingClientRect().toJSON()");
  await b.call('Input.synthesizeScrollGesture', { x: track.x + track.width / 2, y: track.y + 50, xDistance: -220, yDistance: 0, gestureSourceType: 'touch' });
  check(await b.evaluate("document.querySelector('.ld-card-track').scrollLeft") > initialCard && await state() === 'overview', 'native touch scroll leaves directory selection intact');
  await b.call('Emulation.setEmulatedMedia', { features: [{name:'prefers-reduced-motion',value:'reduce'}] });
  check(await b.evaluate("getComputedStyle(document.querySelector('.ld-card')).animationName==='none'"), 'reduced motion is retained');
  await b.call('Emulation.setEmulatedMedia', { features: [{name:'forced-colors',value:'active'}] });
  check(await b.evaluate("getComputedStyle(document.querySelector('.ld-panel')).color!==getComputedStyle(document.querySelector('.ld-panel')).backgroundColor"), 'native forced colours keep text visible');
  await b.call('Emulation.setEmulatedMedia', { features: [] });
  await visit('/stress/');
  await b.evaluate("void document.head.appendChild(Object.assign(document.createElement('style'),{textContent:'.location-directory{font-family:Arial,sans-serif!important}'}))");
  for (const width of [360,390,768,779,780,781,1024,1440]) {
    await viewport(width); const m=await b.evaluate(fitExpression);
    check(!m.overflow && !m.broken.length, `long labels and fallback font: ${width}px`);
  }
  await viewport(390); await screenshot('long-labels-font-fallback');
  await visit('/multi/');
  await b.evaluate("void document.querySelector('#directory-a a[data-directory-target=region-1]').click()");
  await b.evaluate("void document.querySelector('#directory-b a[data-directory-target=region-2]').click()");
  check(await b.evaluate("document.querySelector('#directory-a').dataset.directoryView==='region-1' && document.querySelector('#directory-b').dataset.directoryView==='region-2' && new URL(location.href).searchParams.get('location-directory-a')==='region-1' && new URL(location.href).searchParams.get('location-directory-b')==='region-2'"), 'instances preserve independent view and URL parameters');
  await b.evaluate('history.back()');
  await until("document.querySelector('#directory-b').dataset.directoryView==='overview'");
  check(await b.evaluate("document.querySelector('#directory-a').dataset.directoryView==='region-1'"), 'history restores only changed instance');
  await b.call('Emulation.setScriptExecutionDisabled', { value: true });
  let loadedWithoutScript = false;
  b.on('Page.loadEventFired', () => { loadedWithoutScript = true; });
  await b.call('Page.navigate', { url: 'http://127.0.0.1:8779/bones/location-directory/' });
  for (let i=0; i<80 && !loadedWithoutScript; i++) await wait(50);
  assert.ok(loadedWithoutScript, 'no-JavaScript document loaded');
  // Re-enable CDP evaluation after the document was parsed with JS disabled.
  // Existing module scripts are not executed retroactively.
  await b.call('Emulation.setScriptExecutionDisabled', { value: false });
  check(await b.evaluate("document.querySelector('.ld-nojs').getBoundingClientRect().height>0 && document.querySelectorAll('.ld-nojs details').length===7"), 'no-JavaScript native data fallback is visible');
  check(external.length === 0, 'neutral navigation, controls and fallbacks request no external services');
  // Inactive original and shared reference: compare geometry, not Google imagery.
  const rectExpression = `(()=>{window.scrollTo(0,0);return Object.fromEntries(['.reference-title','.reference-map','.reference-panel','.reference-cards','.reference-card img'].map(s=>{const e=document.querySelector(s);return[s,e?e.getBoundingClientRect().toJSON():null]}))})()`;
  for (const width of [390,1440]) for (const view of ['world','japan','japan/kyoto']) {
    await viewport(width); const path='/arabica/?view='+encodeURIComponent(view);
    await visit(path); const before=await b.evaluate(rectExpression);
    await visit(path,8780); const after=await b.evaluate(rectExpression);
    for (const selector of Object.keys(before)) {
      if (!before[selector] && !after[selector]) continue;
      check(!!before[selector] && !!after[selector] && ['x','y','width','height'].every(k=>Math.abs(before[selector][k]-after[selector][k])<1), `reference geometry retained: ${width}/${view}/${selector}`);
    }
    comparisons.push({width,view,before,after});
    if(view==='world')await screenshot(`reference-shared-${width}`);
  }
  check(external.length === 0, 'reference comparison activates zero provider requests');
  check(errors.length === 0, 'no browser runtime exceptions');
  const ledgersAfter=await Promise.all(ledgerPaths.map(p=>readFile(p,'utf8')));
  check(JSON.stringify(ledgersAfter)===JSON.stringify(ledgersBefore), 'both persistent trial ledgers remain unchanged');
  await writeFile(`${out}/audit.json`,JSON.stringify({schema:'101-location-directory-verification-v1',checkedAt:new Date().toISOString(),browser:b.version,bone:'location.directory-map-hierarchy@0.1.0',checks,matrix,comparisons,external_requests:external,errors,google_initializations:0,google_live_verified_this_delivery:false,human_visual_approval:false},null,2));
  console.log(JSON.stringify({passed:checks.length,external_requests:external.length,google_initializations:0,widths:matrix.map(r=>r.width)}));
} finally { b.close(); }
