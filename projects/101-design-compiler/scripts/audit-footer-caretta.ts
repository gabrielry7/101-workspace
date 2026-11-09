import assert from 'node:assert/strict';
import { build } from 'astro';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, relative, sep } from 'node:path';
import { openLocalBrowser } from './lib/local-browser.ts';
import { carettaFooterBone, footerAnatomy } from '../src/bones/footer-caretta.ts';

// A focused harness compiles the actual workshop and component, not another renderer.
const directory = resolve('.tools/footer-caretta-20261105/audit');
await mkdir(resolve(directory, 'src/pages'), { recursive: true });
const source = relative(resolve(directory, 'src/pages'), resolve('src/pages/bones/footer-caretta.astro')).split(sep).join('/');
const component = relative(resolve(directory, 'src/pages'), resolve('src/components/bones/DirectoryFooter.astro')).split(sep).join('/');
const contract = relative(resolve(directory, 'src/pages'), resolve('src/bones/footer-caretta.ts')).split(sep).join('/');
await writeFile(resolve(directory, 'src/pages/index.astro'), `---\nimport Workshop from '${source}';\n---\n<Workshop />`);
// Compile compatibility routes from the actual application pages as well.
for (const route of ['bones/footer-caretta', 'bones/footers/caretta/index', 'bones/footers/caretta/instance']) {
  const page = resolve(directory, 'src/pages', route + '.astro');
  await mkdir(resolve(page, '..'), { recursive: true });
  const original = relative(resolve(page, '..'), resolve('src/pages', route + '.astro')).split(sep).join('/');
  await writeFile(page, `---\nimport Page from '${original}';\n---\n<Page />`);
}
await writeFile(resolve(directory, 'src/pages/bound.astro'), `---
import Footer from '${component}';
import { neutralFooter } from '${contract}';
const content = structuredClone(neutralFooter);
content.social = {...content.social, state: 'available', href: '/destination/'};
content.email = {...content.email, state: 'available', href: 'mailto:hello@example.com'};
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width"/><title>Vinculación sintética</title></head><body><Footer content={content}/></body></html>`);
await writeFile(resolve(directory, 'src/pages/destination.astro'), '<!doctype html><html lang="es"><title>Destino sintético</title><p>Destino de prueba local</p></html>');
await build({ root: directory, configFile: false, output: 'static', logLevel: 'error' });
const html = await readFile(resolve(directory, 'dist/index.html'), 'utf8');
assert.ok(!html.includes('<script'), 'Neutral bone requires no client scripts');
const browser = await openLocalBrowser(resolve(directory, 'dist'));
try {
  const results = [];
  for (const width of [360, 599, 600, 601, 768, 991, 992, 993, 1440]) {
    await browser.call('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
    await browser.navigate('/');
    const result = await browser.evaluate(`(() => {
      const footer = document.querySelector('footer');
      const elements = [...footer.querySelectorAll('[data-footer-part]')];
      const splitWords = [], clipped = [];
      const walker = document.createTreeWalker(footer, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        for (const match of node.textContent.matchAll(/\\S+/g)) {
          const range = document.createRange(); range.setStart(node, match.index); range.setEnd(node, match.index + match[0].length);
          const rects = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
          if (new Set(rects.map(r => Math.round(r.top))).size > 1) splitWords.push(match[0]);
          for (const r of rects) if (r.left < -1 || r.right > innerWidth + 1) clipped.push(match[0]);
        }
      }
      return { overflow: document.documentElement.scrollWidth > innerWidth, splitWords, clipped,
        parts: elements.map(e => e.dataset.footerPart), links: footer.querySelectorAll('a').length,
        upcoming: footer.querySelectorAll('[data-entry-state="upcoming"]').length,
        upcomingLinks: footer.querySelectorAll('[data-entry-state="upcoming"] a').length,
        cookiesDisabled: footer.querySelector('button').disabled,
        columns: getComputedStyle(footer.querySelector('.directory')).gridTemplateColumns.split(' ').length,
        text: footer.textContent, footerHeight: footer.getBoundingClientRect().height };
    })()`);
    assert.equal(result.overflow, false, `overflow ${width}`);
    assert.deepEqual(result.splitWords, [], `split words ${width}`);
    assert.deepEqual(result.clipped, [], `clipped ${width}`);
    assert.deepEqual([...result.parts].sort(), footerAnatomy().map(part => part.id).sort(), `anatomy ${width}`);
    assert.equal(result.links, 0); assert.equal(result.upcoming, 5); assert.equal(result.upcomingLinks, 0);
    assert.equal(result.cookiesDisabled, true);
    assert.equal(result.columns, width < 600 ? 2 : 4);
    assert.ok(!result.text.includes('Caretta'));
    const clip = await browser.evaluate(`(() => { const r=document.querySelector('footer').getBoundingClientRect(); return {x:r.left,y:r.top+scrollY,width:r.width,height:r.height,scale:1}; })()`);
    const shot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip });
    await writeFile(resolve(directory, `${width}.png`), Buffer.from(shot.data, 'base64'));
    results.push({ width, ...result, text: undefined });
  }
  // Explicit alternative system font, reduced motion and forced colours: same anatomy, no clipping.
  await browser.call('Emulation.setEmulatedMedia', { features: [
    { name: 'prefers-reduced-motion', value: 'reduce' }, { name: 'forced-colors', value: 'active' },
  ] });
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 360, height: 1000, deviceScaleFactor: 1, mobile: false });
  await browser.navigate('/');
  const fallback = await browser.evaluate(`(() => {
    const style=document.createElement('style'); style.textContent='* { font-family: Arial, sans-serif !important; }'; document.head.append(style);
    return { overflow: document.documentElement.scrollWidth > innerWidth,
      parts: document.querySelectorAll('footer [data-footer-part]').length,
      motion: getComputedStyle(document.querySelector('footer')).animationName,
      clipped: [...document.querySelectorAll('footer *')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.dataset.footerPart || e.tagName) };
  })()`);
  assert.equal(fallback.overflow, false); assert.deepEqual(fallback.clipped, []);
  assert.equal(fallback.parts, footerAnatomy().length); assert.equal(fallback.motion, 'none');
  const fallbackClip = await browser.evaluate(`(() => { const r=document.querySelector('footer').getBoundingClientRect(); return {x:r.left,y:r.top+scrollY,width:r.width,height:r.height,scale:1}; })()`);
  const fallbackShot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: fallbackClip });
  await writeFile(resolve(directory, '360-fallback.png'), Buffer.from(fallbackShot.data, 'base64'));
  await browser.call('Emulation.setScriptExecutionDisabled', { value: true });
  // Do not use navigate() here: its font/rAF readiness helper needs script execution.
  const loaded = new Promise<void>(done => browser.on('Page.loadEventFired', () => done()));
  await browser.call('Page.navigate', { url: `${browser.origin}/bound/` });
  await loaded;
  assert.equal(await browser.evaluate('document.querySelectorAll("footer a").length'), 2);
  await browser.evaluate('document.activeElement.blur()');
  await browser.call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  assert.equal(await browser.evaluate('document.activeElement.getAttribute("data-footer-part")'), 'social-1-text');
  await browser.call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  // CDP evaluates even when page scripts are disabled; wait for the native link navigation.
  for (let i = 0; i < 20; i++) {
    if ((await browser.evaluate('location.pathname')) === '/destination/') break;
    await new Promise(done => setTimeout(done, 50));
  }
  assert.equal(await browser.evaluate('location.pathname'), '/destination/');
  await browser.call('Emulation.setScriptExecutionDisabled', { value: false });
  const routes = ['/bones/footer-caretta/', '/bones/footers/caretta/', '/bones/footers/caretta/instance/'];
  for (const route of routes) {
    await browser.navigate(route);
    assert.equal(await browser.evaluate('document.querySelectorAll("footer [data-footer-part]").length'), footerAnatomy().length, route);
    assert.equal(await browser.evaluate('document.querySelectorAll("footer a, footer img, footer iframe, script").length'), 0, route);
    assert.equal(await browser.evaluate('document.querySelector("footer").textContent.includes("Caretta")'), false, route);
  }
  const report = { status: 'PASS', checkedAt: new Date().toISOString(), bone: carettaFooterBone, nativeBrowser: browser.version,
    results, fallback, routes, keyboardNativeLink: 'PASS', noClientScript: true, humanApproval: 'pending',
    limits: 'Reference desktop only. Responsive reflow proposed. No original media redistributed.' };
  await writeFile(resolve(directory, 'verification.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', viewports: results.length, parts: footerAnatomy().length, output: directory }));
} finally { browser.close(); }
