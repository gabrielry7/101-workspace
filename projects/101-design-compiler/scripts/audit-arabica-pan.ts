import { mkdir, writeFile } from 'node:fs/promises';
import { openLocalBrowser } from './lib/local-browser.ts';

if (!process.argv.includes('--live')) throw Error('Use --live only within the authorized Google trial budget.');
const browser = await openLocalBrowser();
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const checks: string[] = [];
const check = (condition: unknown, name: string) => { if (!condition) throw Error(name); checks.push(name); };
const read = (expression: string) => browser.evaluate(`document.querySelector('iframe').contentWindow.eval(${JSON.stringify(expression)})`);
const camera = () => read('window.arabicaReference.inspect().camera');
const moved = (a: any, b: any) => Math.abs(a.center.lat - b.center.lat) + Math.abs(a.center.lng - b.center.lng) > .01;
let apiLoads = 0;
browser.on('Network.requestWillBeSent', ({ request }) => { if (request.url.startsWith('https://maps.googleapis.com/maps/api/js?')) apiLoads++; });
const output = '.tools/arabica-locations-reference/verification';
await mkdir(output, { recursive: true });
try {
  await browser.call('Network.setBlockedURLs', { urls: [] });
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await browser.call('Page.navigate', { url: 'http://127.0.0.1:8780/arabica/' }); await wait(1000);
  await browser.evaluate(`(()=>{const frame=document.createElement('iframe');frame.src='/arabica/';frame.style.cssText='position:fixed;inset:0;width:100%;height:100%;border:0';document.body.replaceChildren(frame)})()`);
  await wait(1600); await read("document.querySelector('[data-activate-map]').click()");
  for (let i = 0; i < 100; i++) { if (await read("window.arabicaReference.inspect().state === 'ready'")) break; await wait(250); }
  check(await read("window.arabicaReference.inspect().state === 'ready'"), 'real Google map loads inside iframe');
  check(await read("window.arabicaReference.inspect().gestureHandling === 'greedy'"), 'gestures explicitly enabled in embedded preview');
  await wait(800);
  const mouseBefore = await camera();
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 1000, y: 470 }); await wait(650);
  await browser.call('Input.dispatchMouseEvent', { type: 'mousePressed', x: 1000, y: 470, button: 'left', buttons: 1, clickCount: 1 }); await wait(120);
  for (let i = 1; i <= 12; i++) { await browser.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 1000 + i * 15, y: 470 + i * 4, button: 'left', buttons: 1 }); await wait(35); }
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 1180, y: 518, button: 'left', buttons: 0, clickCount: 1 }); await wait(1200);
  const mouseAfter = await camera(); check(moved(mouseBefore, mouseAfter), 'actual mouse drag moves geographic centre');
  const first = await browser.call('Page.captureScreenshot', { format: 'png' }); await writeFile(output + '/pan-mouse.png', Buffer.from(first.data, 'base64'));
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseWheel', x: 1000, y: 470, deltaY: -220, deltaX: 0 }); await wait(1200);
  const wheelAfter = await camera(); check(wheelAfter.zoom > mouseAfter.zoom, 'mouse wheel zooms the map');
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1100, height: 1000, deviceScaleFactor: 1, mobile: false }); await wait(700);
  const resized = await camera();
  check(Math.abs(resized.center.lat - wheelAfter.center.lat) < .00001 && Math.abs(resized.center.lng - wheelAfter.center.lng) < .00001
    && resized.zoom === wheelAfter.zoom, 'resize preserves manual pan and zoom');
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await browser.call('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 }); await wait(800);
  const touchBefore = await camera();
  await browser.call('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 280, y: 250, id: 0 }] }); await wait(120);
  for (let i = 1; i <= 12; i++) { await browser.call('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 280 - i * 8, y: 250 + i * 6, id: 0 }] }); await wait(35); }
  await browser.call('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await wait(1200);
  const touchAfter = await camera(); check(moved(touchBefore, touchAfter), 'single-finger drag moves the map inside iframe');
  check(await read('scrollY === 0'), 'map drag does not scroll the surrounding page');
  const shot = await browser.call('Page.captureScreenshot', { format: 'png' }); await writeFile(output + '/pan-touch.png', Buffer.from(shot.data, 'base64'));
  await browser.call('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 150, y: 710, id: 0 }] });
  for (let i = 1; i <= 10; i++) { await browser.call('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 150, y: 710 - i * 14, id: 0 }] }); await wait(35); }
  await browser.call('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await wait(500);
  check(await read('scrollY > 0'), 'touch outside the map still scrolls the page');
  await read("window.arabicaReference.navigate('japan',true)"); await wait(500);
  check(await read("window.arabicaReference.inspect().view === 'japan' && window.arabicaReference.inspect().camera.zoom === 4"), 'choosing a country still applies its reference framing');
  check(apiLoads === 1 && await read('window.arabicaReference.inspect().mapInstances === 1'), 'all gesture checks reuse one Google initialization');
  const report = { version: '0.1.1', checkedAt: new Date().toISOString(), google_live_verified: true,
    google_api_initializations: apiLoads, embedded_preview: true, checks,
    mouse: { before: mouseBefore, after: mouseAfter }, touch: { before: touchBefore, after: touchAfter }, resize: resized };
  await writeFile(output + '/pan-audit.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ passed: checks.length, google_api_initializations: apiLoads }));
} finally { browser.close(); }
