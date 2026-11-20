import http from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import { resolve, relative, isAbsolute, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
const project = fileURLToPath(new URL('../../', import.meta.url));
const root = await realpath(resolve(project, '.tools/location-directory-bone/preview/dist'));
const baseline = resolve(project, '.tools/arabica-locations-reference/before-bone-0.1.1');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.woff': 'font/woff', '.woff2': 'font/woff2' };
const server = http.createServer(async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  try {
    if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    const path = decodeURIComponent(new URL(req.url, 'http://127.0.0.1:8779').pathname);
    // Optional retained reference is for private layout comparison; this static
    // server has no Google configuration or initialization endpoint.
    const folder = path.startsWith('/arabica/') ? await realpath(baseline) : root;
    const file = await realpath(resolve(folder, '.' + path + (path.endsWith('/') ? 'index.html' : '')));
    const rel = relative(folder, file); if (rel.startsWith('..') || isAbsolute(rel)) throw Error('OUTSIDE_ROOT');
    const bytes = await readFile(file); res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : bytes);
  } catch { res.writeHead(404); res.end('Not found'); }
});
server.listen(8779, '127.0.0.1', () => console.log('Location directory bone: http://127.0.0.1:8779/bones/location-directory/'));
process.on('SIGINT', () => server.close()); process.on('SIGTERM', () => server.close());
