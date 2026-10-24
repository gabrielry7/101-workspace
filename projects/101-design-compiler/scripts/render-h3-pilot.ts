import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, extname, relative } from 'node:path';
import { loadMediaPilot } from './load-media-pilot.ts';
import { byteSha256 } from '../src/media/package.ts';

// Local browser QA only. No provider URL is opened or fetched by this script.
const pilot = await loadMediaPilot({ unsealed: true });
const route = '/h3-media-pilot/';
const html = await readFile(resolve('dist/h3-media-pilot/index.html'));
const root = resolve('dist');
const server = createServer(async (request, response) => {
  try {
    const path = decodeURIComponent(new URL(request.url ?? '/', 'http://localhost').pathname);
    const file = resolve(root, `.${path.endsWith('/') ? `${path}index.html` : path}`);
    if (relative(root, file).startsWith('..')) throw new Error('Outside dist');
    const body = await readFile(file);
    response.setHeader('Content-Type', ({ '.html': 'text/html; charset=utf-8', '.jpg': 'image/jpeg', '.css': 'text/css' } as Record<string, string>)[extname(file)] ?? 'application/octet-stream');
    response.end(body);
  } catch { response.statusCode = 404; response.end('Not found'); }
});
await new Promise<void>(done => server.listen(0, '127.0.0.1', done));
const address = server.address(); if (!address || typeof address === 'string') throw new Error('Local server unavailable');
const pageUrl = `http://127.0.0.1:${address.port}${route}`;
await mkdir(resolve('.tools/h3-render-profile'), { recursive: true });
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  `--user-data-dir=${resolve('.tools/h3-render-profile')}`, '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1', 'about:blank',
], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
let socket: WebSocket | undefined;
try {
  const debuggerUrl = await new Promise<string>((done, reject) => {
    let buffer = '';
    const timeout = setTimeout(() => reject(new Error('Local Edge debugging startup timeout')), 20000);
    browser.on('error', reject);
    browser.stderr.on('data', (data: Buffer) => {
      buffer += data.toString(); const match = buffer.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:\d+\/\S+)/);
      if (match?.[1]) { clearTimeout(timeout); done(match[1]); }
    });
  });
  const origin = new URL(debuggerUrl).origin.replace('ws:', 'http:');
  const version = await (await fetch(`${origin}/json/version`)).json() as { Browser: string };
  const target = await (await fetch(`${origin}/json/new?about:blank`, { method: 'PUT' })).json() as { webSocketDebuggerUrl: string };
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise<void>((done, reject) => { socket!.onopen = () => done(); socket!.onerror = () => reject(new Error('CDP connection failed')); });
  let sequence = 0;
  const pending = new Map<number, { done: (value: any) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>();
  const events = new Map<string, () => void>();
  socket.onmessage = event => {
    const message = JSON.parse(String(event.data));
    if (message.id) {
      const waiter = pending.get(message.id); if (!waiter) return;
      clearTimeout(waiter.timer); pending.delete(message.id);
      if (message.error) waiter.reject(new Error(JSON.stringify(message.error))); else waiter.done(message.result);
    } else if (message.method) events.get(message.method)?.();
  };
  const call = (method: string, params: Record<string, unknown> = {}): Promise<any> => new Promise((done, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 20000);
    pending.set(id, { done, reject, timer }); socket!.send(JSON.stringify({ id, method, params }));
  });
  await call('Page.enable');
  await call('Emulation.setDeviceMetricsOverride', { width: 1100, height: 1100, deviceScaleFactor: 1, mobile: false });
  const loaded = new Promise<void>((done, reject) => {
    const timer = setTimeout(() => reject(new Error('Pilot page load timeout')), 20000);
    events.set('Page.loadEventFired', () => { clearTimeout(timer); done(); });
  });
  await call('Page.navigate', { url: pageUrl }); await loaded;
  const evaluation = await call('Runtime.evaluate', { awaitPromise: true, returnByValue: true,
    expression: `(async () => {
      const figure = document.querySelector('figure'); const image = figure.querySelector('img');
      await image.decode(); await document.fonts.ready;
      const bounds = image.getBoundingClientRect();
      return { asset_id: figure.dataset.assetId, usage_id: figure.dataset.usageId,
        decoded: image.complete && image.naturalWidth > 0, natural_width: image.naturalWidth, natural_height: image.naturalHeight,
        displayed_width: bounds.width, displayed_height: bounds.height,
        visible: bounds.width > 0 && bounds.height > 0 && getComputedStyle(image).visibility === 'visible',
        alt: image.alt, caption: figure.querySelector('[data-context]').textContent.trim(),
        credit: figure.querySelector('[data-credit]').textContent.trim(),
        notices: [...figure.querySelectorAll('[data-notice]')].map(n => n.textContent.trim()),
        client_script_count: document.scripts.length, documentary_gap_visible: document.body.textContent.includes('Hueco documental bloqueado') };
    })()` });
  if (evaluation.exceptionDetails) throw new Error(JSON.stringify(evaluation.exceptionDetails));
  const observed = evaluation.result.value;
  const usage = pilot.output.manifest.usages[0]!, asset = pilot.output.manifest.assets[0]!;
  const served = new Uint8Array(await (await fetch(new URL(asset.uri, pageUrl))).arrayBuffer());
  if (!observed.decoded || !observed.visible || observed.usage_id !== usage.id || observed.asset_id !== asset.id
    || observed.natural_width !== asset.inspection.width || observed.natural_height !== asset.inspection.height
    || observed.caption !== usage.generic_label || observed.credit !== usage.attribution_text
    || !usage.context_notices?.every(n => observed.notices.includes(n)) || observed.client_script_count !== 0
    || !observed.documentary_gap_visible || byteSha256(served) !== asset.file_sha256) throw new Error('Pilot browser validation failed');
  const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await mkdir(resolve('docs/evidence/h3-pilot'), { recursive: true });
  await writeFile(resolve('docs/evidence/h3-pilot/render.html'), html);
  await writeFile(resolve('docs/evidence/h3-pilot/render.png'), Buffer.from(screenshot.data, 'base64'));
  const receipt = { route, browser: version.Browser, rendered_at: new Date().toISOString(),
    html_sha256: byteSha256(html), image: { ...observed, served_sha256: byteSha256(served) } };
  await writeFile(resolve('docs/evidence/h3-pilot/render-receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt));
} finally {
  socket?.close(); browser.kill(); server.closeAllConnections(); server.close();
}
