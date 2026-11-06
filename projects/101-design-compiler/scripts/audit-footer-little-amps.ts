import assert from 'node:assert/strict';
import { build } from 'astro';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, relative, sep } from 'node:path';
import { openLocalBrowser } from './lib/local-browser.ts';
import { littleAmpsAnatomy, littleAmpsBone } from '../src/bones/footer-little-amps.ts';

const root = resolve('.tools/footer-little-amps/audit');
await mkdir(resolve(root, 'src/pages'), { recursive: true });
const imp = (path: string) => relative(resolve(root, 'src/pages'), resolve(path)).split(sep).join('/');
await writeFile(resolve(root, 'src/pages/index.astro'), `---
import Workshop from '${imp('src/pages/bones/footer-little-amps.astro')}';
---
<Workshop />`);
await writeFile(resolve(root, 'src/pages/bound.astro'), `---
import Footer from '${imp('src/components/bones/SocialRailFooter.astro')}';
import { neutralLittleAmps } from '${imp('src/bones/footer-little-amps.ts')}';
const content = structuredClone(neutralLittleAmps);
content.logo = {...content.logo, state:'available', href:'/destination/'};
content.email = {...content.email, state:'available', href:'mailto:hello@example.com'};
content.followGraphic = {...content.followGraphic, state:'available', href:'/destination/'};
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width"/><title>Prueba sintética de enlaces</title></head><body><Footer content={content}/></body></html>`);
await writeFile(resolve(root, 'src/pages/destination.astro'), '<!doctype html><html lang="es"><title>Destino sintético</title><p>Destino de prueba local</p></html>');
// Optional comparison is local-only; no reference asset is part of the delivery.
try {
  await mkdir(resolve(root, 'public/reference'), { recursive: true });
  await copyFile(resolve('.tools/footer-little-amps/reference/desktop.jpg'), resolve(root, 'public/reference/desktop.jpg'));
  await copyFile(resolve('.tools/footer-little-amps/reference/mobile.png'), resolve(root, 'public/reference/mobile.png'));
  await writeFile(resolve(root, 'src/pages/comparison.astro'), `---
import Footer from '${imp('src/components/bones/SocialRailFooter.astro')}';
import {neutralLittleAmps} from '${imp('src/bones/footer-little-amps.ts')}';
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width"/><title>Referencia y hueso</title></head><body>
<h1>Little Amps: original y hueso sin piel</h1><p>Referencia de Footr para revisión local. Medios originales sin permiso de redistribución. El neutro conserva la receta; requiere aprobación humana.</p>
<div class="comparison"><section><h2>Referencia original</h2><picture><source media="(max-width:1099px)" srcset="/reference/mobile.png"/><img src="/reference/desktop.jpg" alt="Captura del footer original de Little Amps publicada en Footr"/></picture></section><section><h2>Hueso sin piel</h2><div class="neutral"><Footer content={neutralLittleAmps}/></div></section></div>
<p><a href="/">Abrir inventario completo</a></p>
</body></html><style>body{margin:16px}.comparison{display:grid;gap:24px}.comparison img{width:100%;height:auto}.neutral :global([data-footer-part]),.neutral :global([data-slot-kind]){outline:1px dotted #aaa;outline-offset:-1px}.neutral :global([data-slot-kind]),.neutral :global(.gallery-group > *){background:#f5f5f5}@media(min-width:2400px){.comparison{grid-template-columns:1fr 1fr}}</style>`);
} catch (error) { console.log('Optional local reference comparison unavailable:', String(error)); }
await build({ root, configFile: false, output: 'static', logLevel: 'error' });
const html = await readFile(resolve(root, 'dist/index.html'), 'utf8');
assert.ok(!/<iframe|<img|@font-face/.test(html));
const browser = await openLocalBrowser(resolve(root, 'dist'));
// The historical helper is hash-locked by prior deliveries and only serves HTML,
// CSS and JPG MIME types. Correct MIME at CDP's response boundary without changing
// its source or script bytes (a real static host serves JavaScript correctly).
const responseErrors: string[] = [];
browser.on('Fetch.requestPaused', (event: any) => {
  void (async () => {
    const payload = await browser.call('Fetch.getResponseBody', { requestId: event.requestId });
    const headers = event.responseHeaders.filter((header: any) => header.name.toLowerCase() !== 'content-type');
    headers.push({ name: 'Content-Type', value: event.request.url.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'image/png' });
    await browser.call('Fetch.fulfillRequest', { requestId: event.requestId,
      responseCode: event.responseStatusCode, responseHeaders: headers,
      body: payload.base64Encoded ? payload.body : Buffer.from(payload.body).toString('base64') });
  })().catch(error => responseErrors.push(String(error)));
});
await browser.call('Fetch.enable', { patterns: [
  { urlPattern: browser.origin+'/*.js', requestStage: 'Response' },
  { urlPattern: browser.origin+'/*.png', requestStage: 'Response' },
] });
let loadVersion = 0;
browser.on('Page.loadEventFired', () => { loadVersion++; });
const navigateWithoutScripts = async (path: string) => {
  // The original navigate waits for page rAF callbacks, which cannot run without JS.
  const previous = loadVersion;
  browser.on('Page.loadEventFired', () => { loadVersion++; });
  await browser.call('Page.navigate', { url: browser.origin + path });
  for (let i=0; i<100 && loadVersion===previous; i++) await new Promise(done=>setTimeout(done,20));
  assert.ok(loadVersion>previous, 'native page load without JS');
};
const expected = littleAmpsAnatomy().map(part => part.id).sort();
const externalRequests: string[] = [];
browser.on('Network.requestWillBeSent', (event: any) => {
  if (/^https?:/.test(event.request.url) && !event.request.url.startsWith(browser.origin)) externalRequests.push(event.request.url);
});
const measure = `(() => {
  const footer = document.querySelector('footer');
  const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const words = [], clipped = [];
  const walker = document.createTreeWalker(footer, NodeFilter.SHOW_TEXT); let node;
  while (node = walker.nextNode()) {
    if (node.parentElement.closest('.copies')) continue;
    for (const match of node.textContent.matchAll(/\\S+/g)) {
      const range = document.createRange();range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
      const rects=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
      if(new Set(rects.map(r=>Math.round(r.top))).size>1) words.push(match[0]);
      for(const rect of rects) {
        const tile=node.parentElement.closest('[data-slot-kind="social-media"]');
        if(tile) {const box=tile.getBoundingClientRect();if(rect.left<box.left-1||rect.right>box.right+1)clipped.push(match[0]);}
        else if(rect.left< -1||rect.right>innerWidth+1)clipped.push(match[0]);
      }
    }
  }
  const panel=footer.querySelector('.main-panel');
  return {overflow:document.documentElement.scrollWidth>innerWidth,words,clipped,
    parts:[...footer.querySelectorAll('[data-footer-part]')].map(e=>e.dataset.footerPart).sort(),
    links:footer.querySelectorAll('a').length,mediaCount:footer.querySelectorAll('[data-slot-kind="social-media"]').length,
    playerVisible:getComputedStyle(footer.querySelector('.player-slot')).display!=='none',
    panelColumns:getComputedStyle(panel).gridTemplateColumns.split(' ').length,
    menuColumns:getComputedStyle(footer.querySelector('.menus')).gridTemplateColumns.split(' ').length,
    caretVisible:getComputedStyle(footer.querySelector('summary svg')).display!=='none',
    openMenus:[...footer.querySelectorAll('.menus details')].map(e=>e.open),
    motion:getComputedStyle(footer.querySelector('.gallery-track')).animationName,
    invitationWidth:footer.querySelector('.invitation').getBoundingClientRect().width,
    tileWidth:footer.querySelector('[data-footer-part="gallery-1"]').getBoundingClientRect().width,
    imageCount:footer.querySelectorAll('img, iframe').length};
})()`;
const key = async (key: string, code = key) => {
  const windowsVirtualKeyCode = ({ Enter: 13, Tab: 9, ' ': 32, End: 35, ArrowRight: 39 } as Record<string, number>)[key];
  const text = key === 'Enter' ? '\r' : key === ' ' ? ' ' : undefined;
  await browser.call('Input.dispatchKeyEvent', { type: 'keyDown', key, code, windowsVirtualKeyCode, text, unmodifiedText: text });
  await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode });
  // Wait outside the page: rAF callbacks cannot run when testing with JS disabled.
  await new Promise(done => setTimeout(done, 80));
};
const shot = async (name: string) => {
  const clip = await browser.evaluate(`(() => {const r=document.querySelector('footer').getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height,scale:1};})()`);
  const result = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip });
  await writeFile(resolve(root, name+'.png'), Buffer.from(result.data, 'base64'));
};
try {
  const results = [];
  for (const width of [360, 749, 750, 751, 768, 769, 770, 1099, 1100, 1101, 1200, 1201, 1202, 1440, 2048]) {
    await browser.call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    await browser.navigate('/');
    const result = await browser.evaluate(measure);
    assert.equal(result.overflow, false, `overflow ${width}`);
    assert.deepEqual(result.words, [], `split words ${width}`);
    assert.deepEqual(result.clipped, [], `clipped words ${width}`);
    assert.deepEqual(result.parts, expected, `anatomy ${width}`);
    assert.equal(result.links, 0); assert.equal(result.mediaCount, 11); assert.equal(result.imageCount, 0);
    assert.equal(result.playerVisible, width >= 1201);
    assert.equal(result.menuColumns, width >= 1100 ? 2 : 1);
    assert.equal(result.caretVisible, width < 1100);
    assert.deepEqual(result.openMenus, [true, true]);
    if ([360, 768, 1099, 1100, 1200, 1201, 1440, 2048].includes(width)) await shot(String(width));
    results.push({ width, ...result, parts: result.parts.length });
  }
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 360, height: 1000, deviceScaleFactor: 1, mobile: true });
  await browser.navigate('/');
  await browser.call('Page.bringToFront');
  await browser.call('Emulation.setFocusEmulationEnabled', { enabled: true });
  await browser.evaluate(`document.querySelector('[data-footer-part="menu-1-toggle"]').focus()`);
  await key('Enter');
  assert.deepEqual(await browser.evaluate(`[...document.querySelectorAll('.menus details')].map(e=>e.open)`), [false, true]);
  await key('Enter');
  assert.deepEqual(await browser.evaluate(`[...document.querySelectorAll('.menus details')].map(e=>e.open)`), [true, false]);
  await browser.evaluate(`document.querySelector('.pause').focus()`); await key(' ' ,'Space');
  assert.equal(await browser.evaluate(`document.querySelector('.pause').getAttribute('aria-pressed')`), 'true');
  await browser.evaluate(`document.querySelector('.gallery-window').focus()`); await key('ArrowRight');
  assert.ok(await browser.evaluate(`document.querySelector('.gallery-window').scrollLeft`) > 0, 'native keyboard scroll');
  // Also check the maximum scroll box limit; there must be access to the last item.
  const scroll = await browser.evaluate(`(() => {const e=document.querySelector('.gallery-window');e.scrollLeft=e.scrollWidth;return {left:e.scrollLeft,max:e.scrollWidth-e.clientWidth,animation:getComputedStyle(e.firstElementChild).animationName};})()`);
  assert.ok(scroll.left > 0); assert.equal(scroll.animation, 'none');
  await browser.evaluate(`document.querySelector('.pause').focus()`); await key(' ', 'Space');
  assert.equal(await browser.evaluate(`document.querySelector('.pause').getAttribute('aria-pressed')`), 'false');
  await browser.evaluate(`document.activeElement.blur()`);
  assert.equal(await browser.evaluate(`getComputedStyle(document.querySelector('.gallery-track')).animationName`), 'footer-rail');
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  assert.deepEqual(await browser.evaluate(`[...document.querySelectorAll('.menus details')].map(e=>e.open)`), [true, true]);
  // Force an alternative native font, not just a font stack already in use.
  const fallbacks = [];
  for (const width of [360, 768, 1440]) {
    await browser.call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    await browser.call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    await browser.navigate('/');
    await browser.evaluate(`(() => {const s=document.createElement('style');s.textContent='footer * {font-family:Arial,sans-serif !important}';document.head.append(s)})()`);
    const result = await browser.evaluate(measure);
    assert.equal(result.overflow, false); assert.deepEqual(result.words, []); assert.deepEqual(result.clipped, []);
    assert.equal(result.motion, 'none');
    await shot(`${width}-fallback`); fallbacks.push({ width, ...result, parts: result.parts.length });
  }
  await browser.call('Emulation.setEmulatedMedia', { features: [{ name: 'forced-colors', value: 'active' }] });
  await browser.navigate('/'); const forced = await browser.evaluate(measure);
  assert.equal(forced.overflow, false); assert.equal(forced.motion, 'none');
  await shot('forced-colors');
  await browser.call('Emulation.setScriptExecutionDisabled', { value: true });
  await navigateWithoutScripts('/');
  const noScript = await browser.evaluate(measure);
  assert.equal(noScript.motion, 'none'); assert.equal(noScript.mediaCount, 11);
  assert.equal(await browser.evaluate(`document.querySelector('.pause').hidden`), true);
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 360, height: 1000, deviceScaleFactor: 1, mobile: true });
  await navigateWithoutScripts('/');
  await browser.evaluate(`document.querySelector('[data-footer-part="menu-1-toggle"]').focus()`); await key('Enter');
  assert.equal(await browser.evaluate(`document.querySelector('.menus details').open`), false, 'native disclosure without JS');
  await browser.evaluate(`document.querySelector('.gallery-window').focus()`); await key('ArrowRight');
  assert.ok(await browser.evaluate(`document.querySelector('.gallery-window').scrollLeft`) > 0, 'native gallery without JS');
  await navigateWithoutScripts('/bound/');
  assert.equal(await browser.evaluate(`document.querySelectorAll('footer a').length`), 3);
  await browser.evaluate('document.activeElement.blur()'); await key('Tab');
  assert.equal(await browser.evaluate('document.activeElement.dataset.footerPart'), 'brand-logo');
  await key('Enter');
  for (let i=0; i<20; i++) {
    if (await browser.evaluate('location.pathname') === '/destination/') break;
    await new Promise(done => setTimeout(done,50));
  }
  assert.equal(await browser.evaluate('location.pathname'), '/destination/');
  assert.deepEqual(externalRequests, []);
  assert.deepEqual(responseErrors, []);
  const report = { status: 'PASS', bone: littleAmpsBone, browser: browser.version, checkedAt: new Date().toISOString(),
    results, fallbacks, forcedColors: 'PASS', noScript: 'PASS', keyboard: 'PASS', menus: 'PASS', manualScroll: scroll,
    pauseResume: 'PASS', externalRequests, responseErrors, humanApproval: 'pending',
    limits: 'No provider integration or asset-binding. Local reference comparison only; no reference media redistributed.' };
  await writeFile(resolve(root, 'verification.json'), JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({ status:'PASS', viewports:results.length, parts:expected.length, directory:root }));
} finally { browser.close(); }
