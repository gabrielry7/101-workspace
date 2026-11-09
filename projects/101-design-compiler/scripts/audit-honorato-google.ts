// Explicitly invoked live check: reserves ONE of the ten authorized map loads.
// Private inputs, browser evidence and screenshots stay under ignored .tools/.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { openLocalBrowser } from './lib/local-browser.ts';

if (!process.argv.includes('--live')) throw Error('LIVE_TRIAL_REQUIRED: use --live; consumes one reserved load');
const folder = resolve('.tools/honorato-google-live');
const cloud = JSON.parse(await readFile(resolve(folder, 'cloud-state.json'), 'utf8'));
assert.equal(cloud.budget_usd, 1);
assert.equal(cloud.max_initializations, 10);
assert.equal(cloud.daily_maps_limit, 10);
const reservationBefore = JSON.parse(await readFile(resolve(folder, 'trial-budget.json'), 'utf8')).reserved;
assert.ok(reservationBefore < 10, 'Trial has no remaining map loads');
const browser = await openLocalBrowser(resolve(folder, 'preview/dist'));
const consoleErrors: string[] = [], exceptions: string[] = [];
const redact = (value: string) => value.replace(/AIza[A-Za-z0-9_-]+/g, '[REDACTED]')
  .replace(/([?&](?:key|access_token|token)=)[^&\s]+/gi, '$1[REDACTED]');
const pause = (ms: number) => new Promise(done => setTimeout(done, ms));
const inspect = () => browser.evaluate(`document.querySelector('[data-location-bone-config]').locationBone?.inspect()`);
const snapshot = async (name: string) => {
  const result = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(resolve(folder, name + '.png'), Buffer.from(result.data, 'base64'));
};
try {
  await browser.call('Runtime.enable');
  browser.on('Runtime.consoleAPICalled', event => {
    if (event.type === 'error') consoleErrors.push(redact(event.args.map((v: any) => v.value ?? v.description ?? '').join(' ')));
  });
  browser.on('Runtime.exceptionThrown', event => exceptions.push(redact(event.exceptionDetails.text)));
  await browser.call('Network.setBlockedURLs', { urls: [] });
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await browser.call('Page.navigate', { url: 'http://127.0.0.1:8780/' });
  let first;
  for (let i = 0; i < 160; i++) {
    first = await inspect();
    if (first && ['ready', 'degraded', 'fallback'].includes(first.state)) break;
    await pause(250);
  }
  assert.equal(first?.state, 'ready', first?.reason);
  assert.equal(first.provider, 'google_js');
  await pause(1200);
  const checkPosition = (info: any) => {
    assert.deepEqual(info.marker_coordinate, first.marker_coordinate);
    assert.deepEqual(info.expected_coordinate, first.expected_coordinate);
    assert.ok(info.marker_anchor_offset_px !== null && info.marker_anchor_offset_px <= 1);
    assert.equal(info.publication_allowed, false);
  };
  const viewports = [];
  for (const width of [1440, 901, 900, 768, 621, 620, 390]) {
    await browser.call('Emulation.setDeviceMetricsOverride', { width, height: 1100, deviceScaleFactor: 1, mobile: false });
    await pause(650);
    const info = await inspect(); checkPosition(info);
    const overflow = await browser.evaluate('document.documentElement.scrollWidth > innerWidth');
    assert.equal(overflow, false, `Overflow at ${width}`);
    viewports.push({ width, overflow, anchor_offset_px: info.marker_anchor_offset_px });
    await snapshot('live-' + width);
  }
  await browser.evaluate(`document.body.style.fontFamily = 'Georgia, serif'`);
  await pause(300);
  assert.equal(await browser.evaluate('document.documentElement.scrollWidth > innerWidth'), false);
  await snapshot('live-font-fallback');
  await browser.evaluate(`document.body.style.fontFamily = ''`);
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await pause(500);
  await browser.evaluate(`document.querySelector('[data-location-bone-config]').locationBone.setPresentation({zoom:17})`);
  await pause(900);
  const zoom = await inspect(); checkPosition(zoom);
  await snapshot('live-zoom17');
  const position = () => browser.evaluate(`(() => {const r=document.querySelector('.single-business-marker').getBoundingClientRect();return {x:r.x,y:r.y};})()`);
  const markerBefore = await position();
  const canvas = await browser.evaluate(`(() => {const r=document.querySelector('.location-map__canvas').getBoundingClientRect();return {x:r.x,y:r.y};})()`);
  const x = canvas.x + 110, y = canvas.y + 100;
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await browser.call('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1, buttons: 1 });
  for (let i = 1; i <= 10; i++) {
    await browser.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: x + i * 10, y: y + i * 4, button: 'left', buttons: 1 });
    await pause(30);
  }
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: x + 100, y: y + 40, button: 'left', clickCount: 1, buttons: 0 });
  await pause(900);
  const pan = await inspect(); checkPosition(pan);
  const markerAfter = await position();
  assert.ok(Math.hypot(markerAfter.x - markerBefore.x, markerAfter.y - markerBefore.y) > 10, 'Real pan must move marker on screen');
  await snapshot('live-pan');
  await browser.evaluate(`document.querySelector('.location-bone nav a').focus()`);
  assert.equal(await browser.evaluate(`document.activeElement.matches('.location-bone nav a')`), true);
  assert.equal(exceptions.length, 0);
  const reservationAfter = JSON.parse(await readFile(resolve(folder, 'trial-budget.json'), 'utf8')).reserved;
  assert.equal(reservationAfter, reservationBefore + 1, 'Resizing, zoom and pan must reuse the same map');
  await writeFile(resolve(folder, 'browser-extended-report.json'), JSON.stringify({
    browser: browser.version, provider: first.provider, viewports, zoom, pan,
    markerBefore, markerAfter, consoleErrors, exceptions, font_fallback_overflow: false,
    keyboard_directions_focus: true, agent_map_initializations: 1,
    reservations_after: reservationAfter, visual_review: 'pending-agent-review', human_approval: 'pending',
  }, null, 2) + '\n');
  console.log(JSON.stringify({ google_live: true, viewports: viewports.length, pan: true, zoom: true,
    reservations: reservationAfter, consoleErrors, exceptions, screenshots: 'private .tools/honorato-google-live' }));
} finally { browser.close(); }
