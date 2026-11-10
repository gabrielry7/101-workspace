import http from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import { resolve, relative, isAbsolute, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { reserveTrialLoad } from './google-trial-budget.mjs';
import { googleConfiguration } from '../../src/bones/location-map-google.js';

const project = fileURLToPath(new URL('../../', import.meta.url));
const folder = resolve(project, '.tools/honorato-google-live');
const root = await realpath(resolve(folder, 'preview/dist'));
const cloud = JSON.parse(await readFile(resolve(folder, 'cloud-state.json'), 'utf8'));
const google = googleConfiguration(JSON.parse(await readFile(resolve(folder, 'browser-config.json'), 'utf8')));
if (!google || cloud.budget_usd !== 1 || cloud.max_initializations !== 10 || cloud.daily_maps_limit !== 10) {
  throw Error('VERIFIED_BOUNDED_GOOGLE_TRIAL_REQUIRED');
}
const origins = new Set(['http://127.0.0.1:8780', 'http://localhost:8780']);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.avif': 'image/avif' };
const server = http.createServer(async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  try {
    if (!['127.0.0.1:8780', 'localhost:8780'].includes(req.headers.host)) {
      res.writeHead(403); res.end('Local trial only'); return;
    }
    const path = decodeURIComponent(new URL(req.url, 'http://127.0.0.1:8780').pathname);
    if (path === '/trial-status' && req.method === 'GET') {
      const budget = JSON.parse(await readFile(resolve(folder, 'trial-budget.json'), 'utf8'));
      if (budget.schema !== '101-google-trial-budget-v1' || budget.limit !== 10
        || !Number.isInteger(budget.reserved) || budget.reserved < 0 || budget.reserved > 10) {
        res.writeHead(503); res.end('Trial status unavailable'); return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ reserved: budget.reserved, limit: 10, remaining: 10 - budget.reserved })); return;
    }
    if (path === '/trial-config') {
      if (req.method !== 'POST' || req.headers.origin && !origins.has(req.headers.origin)
        || req.headers['sec-fetch-site'] === 'cross-site') {
        res.writeHead(403); res.end('Local request required'); return;
      }
      let budget;
      try { budget = reserveTrialLoad(resolve(folder, 'trial-budget.json'), 10); }
      catch (error) {
        res.writeHead(error.message === 'TRIAL_BUDGET_EXHAUSTED' ? 429 : 503);
        res.end('Trial initialization unavailable'); return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ google, budget })); return;
    }
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    const file = await realpath(resolve(root, '.' + path + (path.endsWith('/') ? 'index.html' : '')));
    const rel = relative(root, file);
    if (rel.startsWith('..') || isAbsolute(rel)) throw Error('OUTSIDE_ROOT');
    const bytes = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : bytes);
  } catch { res.writeHead(404); res.end('Not found'); }
});
server.listen(8780, '127.0.0.1', () => console.log('Honorato Google trial: http://127.0.0.1:8780/ (10 initializations maximum)'));
process.on('SIGINT', () => server.close());
process.on('SIGTERM', () => server.close());
