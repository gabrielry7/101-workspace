import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { resolve, dirname, relative, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { build as astroBuild } from 'astro';

const project = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const source = resolve(project, process.env.LOCATION_MAP_OWNER || '.tools/bones-handoff-20261105/source');
const owner = resolve(source, 'packages/location-map');
const preview = resolve(project, '.tools/location-map-bones/preview');
const publicDir = resolve(preview, 'public');
const pinned = {
  'src/client.js': '58cb821219e4e93f123528974d57e4c122bb719c20879c9baf4fa6a56706d730',
  'src/contract.js': 'b8d175f3a6bea4820f2a5ac7dde12d87acf3fdbb5ec7d9197f6faf6d87ea2a6d',
  'src/map.css': '70d04612fbb30fe52a8e6b261951da36673705214d2a452a60acb886e8c0d34c',
  'LocationMap.astro': '38b4bb4de523a3031a1358d2737539ec7b8c7b2489fdac50b9937b28166e6eb6',
};
for (const [file, expected] of Object.entries(pinned)) {
  const bytes = await readFile(resolve(owner, file)).catch(() => { throw Error('PRIVATE_LOCATION_OWNER_MISSING: restore the pinned checkout; see docs/bones/location-map.md'); });
  if (createHash('sha256').update(bytes).digest('hex') !== expected) throw Error(`LOCATION_OWNER_DRIFT:${file}`);
}
const { build } = await import(pathToFileURL(resolve(owner, 'node_modules/esbuild/lib/main.js')).href);
const original = await import(pathToFileURL(resolve(owner, 'src/contract.js')).href);
const { fixtureLocationInput, fixtureLocation, fixtureLogo } = await import(pathToFileURL(resolve(project, 'src/bones/location-map-fixture.ts')).href);
original.locationInput(fixtureLocation); // Canonical validation before building the actual preview.
await mkdir(resolve(preview, 'src/pages'), { recursive: true });
await mkdir(publicDir, { recursive: true });
await build({ entryPoints: [resolve(project, 'src/bones/location-map-entry.js')], bundle: true,
  outfile: resolve(publicDir, 'location-runtime.js'), format: 'esm', target: 'es2022', minify: true,
  alias: { '@101/location-map/client': resolve(owner, 'src/client.js'), '@101/location-map/contract': resolve(owner, 'src/contract.js') },
  legalComments: 'eof' });
await build({ entryPoints: [resolve(project, 'src/bones/location-map-workshop.js')], bundle: true,
  outfile: resolve(publicDir, 'workshop.js'), format: 'esm', target: 'es2022', minify: true });
for (const name of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  await copyFile(resolve(owner, 'node_modules/maplibre-gl/dist', name), resolve(publicDir, name));
}
await copyFile(resolve(owner, 'node_modules/maplibre-gl/LICENSE.txt'), resolve(publicDir, 'MAPLIBRE-LICENSE.txt'));
await copyFile(resolve(owner, 'licenses/PMTILES-LICENSE.txt'), resolve(publicDir, 'PMTILES-LICENSE.txt'));
const fontDir = resolve(source, 'packages/gabo-review/public/studio-fonts');
await mkdir(resolve(publicDir, 'fonts'), { recursive: true });
for (const name of ['familjengrotesk.woff', 'bodonimoda.woff']) await copyFile(resolve(fontDir, name), resolve(publicDir, 'fonts', name));
// Retain the upstream font notices in this private build.
for (const name of ['familjengrotesk-OFL.txt', 'bodonimoda-OFL.txt']) await copyFile(resolve(fontDir, name), resolve(publicDir, 'fonts', name));
await writeFile(resolve(publicDir, 'fixture-logo.svg'), fixtureLogo);
await copyFile(resolve(project, 'tests/fixtures/location-map-google-browser.js'), resolve(publicDir, 'google-browser-test.js'));
const context = JSON.parse(await readFile(resolve(owner, 'demo/context.geojson'), 'utf8'));
const ids = ['synthetic/nearby-1', 'synthetic/nearby-2', 'synthetic/nearby-3'];
for (let i = 0; i < ids.length; i++) context.features.push({ type: 'Feature', properties: { kind: 'poi',
  osm_id: ids[i], name: `Otro negocio de prueba ${i + 1}` }, geometry: { type: 'Point', coordinates: [-75.425 + .0004 * (i + 1), 6.125 + .0003] } });
for (const feature of context.features.filter(item => item.properties.kind === 'road').slice(0, 2)) feature.properties.name = 'Calle de prueba';
await writeFile(resolve(publicDir, 'context.geojson'), JSON.stringify(context));
const basemap = { format: 'geojson', url: '/context.geojson', fontURL: '/fonts/familjengrotesk.woff',
  poiIDs: ids, attribution: 'Cartografía sintética de prueba · no representa calles reales' };
const pageImport = relative(resolve(preview, 'src/pages'), resolve(project, 'src/pages/bones/location-map.astro')).split(sep).join('/');
await writeFile(resolve(preview, 'src/pages/index.astro'), `---\nimport Workshop from '${pageImport}';\n---\n<Workshop runtimeURL="/location-runtime.js" originalURL="/original/" basemap={${JSON.stringify(basemap)}}/>`);
const componentImport = relative(resolve(preview, 'src/pages'), resolve(project, 'src/components/bones/SingleBusinessLocation.astro')).split(sep).join('/');
const boundLocation = structuredClone(fixtureLocation);
boundLocation.coordinate.purpose = 'owner_pin'; boundLocation.coordinate.source.kind = 'owner_confirmed';
boundLocation.coordinate.source.reference = 'synthetic:keyboard-link-test-not-real';
const boundInput = { ...fixtureLocationInput(), location: original.locationInput(boundLocation), directions: original.navigationLinks(original.locationInput(boundLocation)) };
await writeFile(resolve(preview, 'src/pages/bound.astro'), `---\nimport Location from '${componentImport}';\n---\n<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width"/><title>Prueba sintética de teclado</title><link rel="stylesheet" href="/location-runtime.css"/></head><body><p>Prueba sintética de enlaces. No visitar; ningún destino real está verificado.</p><Location id="bound-location" input={${JSON.stringify(boundInput)}} runtimeURL="/location-runtime.js" basemap={${JSON.stringify(basemap)}}/></body></html>`);
// Keep the original composition/CSS. Only replace its documented data slots and runtime binding.
await mkdir(resolve(publicDir, 'original'), { recursive: true });
const esc = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let html = await readFile(resolve(owner, 'demo/variants/direct.html'), 'utf8');
html = html.replaceAll('__BUSINESS_NAME__', esc(fixtureLocation.name)).replaceAll('__ADDRESS__', esc(fixtureLocation.address))
  .replaceAll('__NAVIGATION_LINKS__', '<p>Datos sintéticos · sin navegación real.</p>')
  .replace('../location-map.css', '/location-runtime.css').replace('../variant-runtime.js', '/original/runtime.js')
  .replace("../fonts/", '/fonts/');
await writeFile(resolve(publicDir, 'original/index.html'), html);
await writeFile(resolve(publicDir, 'original/runtime.js'), `import {owner} from '/location-runtime.js';\nowner.mountLocationMap(document.getElementById('map'),{location:${JSON.stringify(fixtureLocationInput().location)},basemap:${JSON.stringify(basemap)},workerURL:'/maplibre-gl-worker.mjs',detailsMode:'external',presentation:{zoom:16}});`);
await astroBuild({ root: preview, configFile: false, output: 'static', logLevel: 'error' });
await writeFile(resolve(preview, '../build-receipt.json'), JSON.stringify({ source: 'private pinned owner',
  pinned, synthetic: true, publication_allowed: false, providers_executed: ['maplibre'], google_live_verified: false }, null, 2));
console.log('Built private location workshop: .tools/location-map-bones/preview/dist; no paid requests.');
