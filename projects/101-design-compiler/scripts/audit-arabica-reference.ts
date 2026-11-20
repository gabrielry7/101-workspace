import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { openLocalBrowser } from './lib/local-browser.ts';
import { validateReferenceCatalogue, referenceVersion } from '../src/references/arabica-locations.js';

const live = process.argv.includes('--live');
const root = '.tools/arabica-locations-reference';
const catalogue = validateReferenceCatalogue(JSON.parse(await readFile(root + '/catalogue.json', 'utf8')));
const output = root + '/verification'; await mkdir(output, { recursive: true });
const checks: string[] = [];
const check = (condition: unknown, label: string) => { if (!condition) throw Error(label); checks.push(label); };
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const browser = await openLocalBrowser();
let googleScripts = 0;
browser.on('Network.requestWillBeSent', ({ request }) => {
  if (request.url.startsWith('https://maps.googleapis.com/maps/api/js?')) googleScripts++;
});
const sizes: number[] = [];
try {
  await browser.call('Network.setBlockedURLs', { urls: [] });
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await browser.call('Page.navigate', { url: 'http://127.0.0.1:8780/arabica/' }); await wait(1800);
  check(await browser.evaluate('!!window.arabicaReference'), 'private Astro reference boots');
  check(googleScripts === 0, 'opening the reference consumes zero Google loads');
  if (live) {
    await browser.evaluate("document.querySelector('[data-activate-map]').click()");
    for (let i = 0; i < 100; i++) {
      if (await browser.evaluate("window.arabicaReference.inspect().state === 'ready'")) break;
      await wait(250);
    }
    check(await browser.evaluate("window.arabicaReference.inspect().state === 'ready'"), 'Google renders real cartography');
    check(googleScripts === 1, 'one Google API initialization');
    await wait(1200);
  }
  async function screenshot(name: string) {
    const { data } = await browser.call('Page.captureScreenshot', { format: 'png' });
    await writeFile(`${output}/${live ? 'live' : 'layout'}-${name}.png`, Buffer.from(data, 'base64'));
  }
  await screenshot('world-1440');
  if (live) {
    for (const [name, destination] of [['Japan', 'japan'], ['Kyoto', 'japan/kyoto']]) {
      const pin = await browser.evaluate(`(()=>{const el=document.querySelector('.reference-map [title="${name}"]')||document.querySelector('.reference-map [aria-label="${name}"]');if(!el)return null;const r=el.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
      check(pin, `accessible real map pin: ${name}`);
      await browser.call('Input.dispatchMouseEvent', { type: 'mousePressed', x: pin.x, y: pin.y, button: 'left', clickCount: 1 });
      await browser.call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pin.x, y: pin.y, button: 'left', clickCount: 1 });
      await wait(900);
      check(await browser.evaluate(`window.arabicaReference.inspect().view === '${destination}'`), `real map pin opens ${destination}`);
    }
    await browser.evaluate("window.arabicaReference.navigate('world', true)");
  }
  for (const id of ['japan', 'japan/kyoto', 'united-kingdom', 'united-kingdom/london']) {
    await browser.evaluate(`(()=>{const link=document.querySelector('[data-directory-panel] [data-directory-target="${id}"]');if(link)link.click();else window.arabicaReference.navigate(${JSON.stringify(id)},true)})()`);
    await wait(live ? 1600 : 100);
    const state = await browser.evaluate('window.arabicaReference.inspect()');
    check(state.view === id, `navigation: ${id}`);
    if (live) {
      const page = catalogue.pages.find(page => page.id === id)!;
      check(state.mapInstances === 1 && state.markerCount === page.markers.length, `same instance and pins: ${id}`);
      check(state.markerCoordinates.every((p: any, i: number) => Math.abs(p.lng - page.markers[i].coordinates[0]) < 1e-8
        && Math.abs(p.lat - page.markers[i].coordinates[1]) < 1e-8), `geographic anchors: ${id}`);
    }
    await screenshot(id.replaceAll('/', '-'));
  }
  await browser.evaluate('history.back()'); await wait(200);
  check(await browser.evaluate("window.arabicaReference.inspect().view === 'united-kingdom'"), 'browser back restores country');
  await browser.evaluate('history.forward()'); await wait(200);
  check(await browser.evaluate("window.arabicaReference.inspect().view === 'united-kingdom/london'"), 'browser forward restores city');
  const matrix: any[] = [];
  for (const width of [360, 390, 559, 560, 561, 767, 768, 779, 780, 781, 1024, 1440]) {
    await browser.call('Emulation.setDeviceMetricsOverride', { width, height: width < 781 ? 844 : 1000, deviceScaleFactor: 1, mobile: width < 600 });
    await browser.evaluate("window.arabicaReference.navigate('world', true)"); await wait(live ? 500 : 100);
    const measured = await browser.evaluate(`(()=>{const m=document.querySelector('.reference-map').getBoundingClientRect(),p=document.querySelector('.reference-panel').getBoundingClientRect(),a=document.querySelector('.reference-map-area').getBoundingClientRect();return{overflow:document.documentElement.scrollWidth>innerWidth,areaY:a.y,map:{x:m.x,y:m.y,w:m.width,h:m.height},panel:{x:p.x,y:p.y,w:p.width,h:p.height}}})()`);
    check(!measured.overflow, `no document overflow at ${width}px`);
    if (width <= 780) {
      check(Math.abs(measured.map.y - measured.areaY) < 1, `mobile map starts at section top at ${width}px`);
      check(measured.panel.y >= measured.map.y + measured.map.h - 1, `map precedes list at ${width}px`);
    }
    matrix.push({ width, ...measured }); sizes.push(width);
    if ([390, 768, 1440].includes(width)) await screenshot(`world-${width}`);
  }
  await browser.call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await browser.evaluate("window.arabicaReference.navigate('japan/kyoto',true)");
  check(await browser.evaluate("getComputedStyle(document.querySelector('.reference-panel a')).transitionDuration === '0s'"), 'reduced motion removes transitions');
  await browser.evaluate("document.querySelector('.reference-panel a').focus()");
  check(await browser.evaluate("document.activeElement.matches('.reference-panel a')"), 'region links are keyboard focusable');
  await browser.evaluate("(()=>{const s=document.createElement('style');s.textContent='.arabica-reference *:not(.reference-icon){font-family:Arial!important}';document.head.append(s)})()");
  check(await browser.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'font fallback retains layout');
  await screenshot('font-fallback');
  if (live) check(googleScripts === 1, 'all navigation and viewport tests reuse one Google initialization');
  // Exercise failure handling through the explicit service seam, never through
  // an extra billable Google reservation or fake geographic screenshot.
  await browser.evaluate(`(async()=>{const {mountArabicaReference}=await import('/arabica/arabica-client.js');const old=document.querySelector('.arabica-reference'),copy=old.cloneNode(true);old.replaceWith(copy);window.failedReference=mountArabicaReference(copy,JSON.parse(document.getElementById('arabica-reference-input').textContent),{reserve:async()=>({ok:true,json:async()=>({google:{}})}),load:async()=>{throw Error('offline test')}});await window.failedReference.activate()})()`);
  check(await browser.evaluate("window.failedReference.inspect().state === 'unavailable' && document.querySelectorAll('.reference-panel a').length > 0"), 'provider failure retains the location navigation');
  await writeFile(output + '/audit.json', JSON.stringify({ version: referenceVersion, checkedAt: new Date().toISOString(),
    original: catalogue.source, reference_views: catalogue.pages.length, google_live_verified: live,
    google_api_initializations: googleScripts, matrix, checks, human_visual_approval: false }, null, 2));
  console.log(JSON.stringify({ passed: checks.length, google_live_verified: live, google_api_initializations: googleScripts, widths: sizes }));
} finally { browser.close(); }
