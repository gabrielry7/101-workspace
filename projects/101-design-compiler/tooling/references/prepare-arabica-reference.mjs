import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { dirname, resolve, relative, sep, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { build as astroBuild } from 'astro';
import { build } from 'esbuild';
import { validateReferenceCatalogue } from '../../src/references/arabica-locations.js';

const project = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const work = resolve(project, '.tools/arabica-locations-reference');
const preview = resolve(work, 'preview');
const assets = resolve(preview, 'public/arabica/assets');
await mkdir(assets, { recursive: true });
const catalogue = validateReferenceCatalogue(JSON.parse(await readFile(resolve(work, 'catalogue.json'), 'utf8')));
for (const name of ['avenir-roman.woff2', 'avenir-heavy.woff2', 'arabica-icons.woff']) {
  await copyFile(resolve(work, 'reference', name), resolve(assets, name));
}
const urls = new Set(catalogue.pages.flatMap(page => page.markers.map(pin => pin.icon)));
// Only the reference images visible in the acceptance cases need retained local copies.
for (const page of catalogue.pages.filter(page => ['world', 'japan/kyoto', 'united-kingdom/london'].includes(page.id))) {
  for (const card of page.cards) urls.add(card.image);
}
const assetMap = new Map();
const queue = [...urls];
async function worker() {
  while (queue.length) {
    const url = queue.shift(), source = new URL(url);
    if (source.origin !== 'https://arabica.com' || !source.pathname.includes('/wp-content/')) throw Error('REFERENCE_ASSET_ORIGIN');
    const extension = extname(source.pathname).toLowerCase();
    if (!['.png', '.jpg', '.jpeg', '.webp'].includes(extension)) throw Error('REFERENCE_ASSET_TYPE');
    const name = createHash('sha256').update(url).digest('hex').slice(0, 20) + extension;
    const file = resolve(assets, name);
    try { await readFile(file); } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      const response = await fetch(url, { signal: AbortSignal.timeout(25000) });
      if (!response.ok) throw Error(`REFERENCE_ASSET_UNAVAILABLE:${source.pathname}:${response.status}`);
      await writeFile(file, Buffer.from(await response.arrayBuffer()));
    }
    assetMap.set(url, '/arabica/assets/' + name);
  }
}
await Promise.all([worker(), worker(), worker()]);
for (const page of catalogue.pages) {
  for (const pin of page.markers) pin.icon = assetMap.get(pin.icon);
  for (const card of page.cards) card.image = assetMap.get(card.image) || card.image;
}
await writeFile(resolve(work, 'prepared-catalogue.json'), JSON.stringify(catalogue));
await mkdir(resolve(preview, 'src/pages'), { recursive: true });
const localImport = path => relative(resolve(preview, 'src/pages'), resolve(project, path)).split(sep).join('/');
await writeFile(resolve(preview, 'src/pages/arabica.astro'), `---
import Reference from '${localImport('src/components/references/ArabicaLocations.astro')}';
import catalogue from '${localImport('.tools/arabica-locations-reference/prepared-catalogue.json')}';
---
<!doctype html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><meta name="robots" content="noindex,nofollow"/><link rel="icon" href="data:,"/><title>% Arabica · Locations · private reference</title></head><body><Reference catalogue={catalogue}/></body></html>`);
await build({ entryPoints: [resolve(project, 'src/references/arabica-locations-client.js')], bundle: true,
  outfile: resolve(preview, 'public/arabica/arabica-client.js'), format: 'esm', target: 'es2022', minify: true });
await astroBuild({ root: preview, configFile: false, output: 'static', build: { assets: 'arabica/_astro' }, logLevel: 'error' });
await writeFile(resolve(work, 'build-receipt.json'), JSON.stringify({ version: '0.1.1',
  reference: catalogue.source, observed_at: catalogue.observedAt, pages: catalogue.pages.length,
  retained_assets: assetMap.size + 3, publication_allowed: false, google_initializations: 0,
  map_provider: 'google', authorization: 'existing bounded trial; activation required' }, null, 2));
console.log(`Built private % Arabica reference (${catalogue.pages.length} views), no Google loads consumed.`);
