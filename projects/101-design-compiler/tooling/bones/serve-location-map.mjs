import http from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import { resolve, relative, isAbsolute, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = await realpath(fileURLToPath(new URL('../../.tools/location-map-bones/preview/dist/', import.meta.url)));
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.geojson': 'application/geo+json', '.svg': 'image/svg+xml', '.woff': 'font/woff', '.png': 'image/png' };
const server = http.createServer(async (req, res) => {
  try {
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = await realpath(resolve(root, '.' + path + (path.endsWith('/') ? 'index.html' : '')));
    const rel = relative(root, file); if (rel.startsWith('..') || isAbsolute(rel)) throw Error('OUTSIDE_ROOT');
    const data = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch { res.writeHead(404); res.end('Not found'); }
});
server.listen(8777, '127.0.0.1', () => console.log('Location bones: http://127.0.0.1:8777/'));
process.on('SIGINT', () => server.close()); process.on('SIGTERM', () => server.close());
