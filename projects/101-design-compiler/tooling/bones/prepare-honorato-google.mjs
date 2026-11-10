import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, relative, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { build as astroBuild } from 'astro';
import { bindLocationBone } from '../../src/bones/location-map.ts';

const project = fileURLToPath(new URL('../../', import.meta.url));
const source = resolve(project, process.env.LOCATION_MAP_OWNER || '.tools/bones-handoff-20261105/source');
const folder = resolve(project, '.tools/honorato-google-live');
const preview = resolve(folder, 'preview');
const publicDir = resolve(preview, 'public');
const ownerRoot = resolve(source, 'packages/location-map');
const owner = await import(pathToFileURL(resolve(ownerRoot, 'src/contract.js')).href);
const { build } = await import(pathToFileURL(resolve(ownerRoot, 'node_modules/esbuild/lib/main.js')).href);
const packetPath = resolve(source, 'artifacts/design-creative-20261028/business-packet.json');
const packetBytes = await readFile(packetPath);
const packet = JSON.parse(packetBytes.toString('utf8'));
let evidence;
try { evidence = JSON.parse(await readFile(resolve(folder, 'logo-evidence.json'), 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const input = bindLocationBone(owner, packet.location, evidence);
if (!owner.rendererEligibility(input.location, 'google_embed').render) throw Error('HONORATO_GOOGLE_LOCATION_NOT_ELIGIBLE');
if (input.location.business_id !== packet.business_id || input.location.location_id !== packet.location_id) throw Error('HONORATO_BINDING_MISMATCH');
await mkdir(resolve(preview, 'src/pages'), { recursive: true });
await mkdir(publicDir, { recursive: true });
await build({ entryPoints: [resolve(project, 'src/bones/location-map-entry.js')], bundle: true,
  outfile: resolve(publicDir, 'location-runtime.js'), format: 'esm', target: 'es2022', minify: true,
  alias: { '@101/location-map/client': resolve(ownerRoot, 'src/client.js'), '@101/location-map/contract': resolve(ownerRoot, 'src/contract.js') }, legalComments: 'eof' });
await build({ entryPoints: [resolve(project, 'tooling/bones/honorato-google-client.js')], bundle: true,
  outfile: resolve(publicDir, 'honorato-google-client.js'), format: 'esm', target: 'es2022', minify: true,
  external: ['/location-runtime.js'] });
if (input.marker.kind === 'logo') {
  if (!evidence.render_file) throw Error('LOGO_RENDER_FILE_REQUIRED');
  const bytes = await readFile(resolve(project, evidence.render_file));
  if (createHash('sha256').update(bytes).digest('hex') !== input.marker.sha256) throw Error('LOGO_RENDER_HASH_MISMATCH');
  const path = resolve(publicDir, '.' + input.marker.url);
  await mkdir(resolve(path, '..'), { recursive: true }); await writeFile(path, bytes);
}
const component = relative(resolve(preview, 'src/pages'), resolve(project, 'src/components/bones/SingleBusinessLocation.astro')).split(sep).join('/');
const controlsComponent = relative(resolve(preview, 'src/pages'), resolve(project, 'src/components/bones/LocationMapControls.astro')).split(sep).join('/');
await writeFile(resolve(preview, 'src/pages/index.astro'), `---
import Location from '${component}';
import Controls from '${controlsComponent}';
const input = ${JSON.stringify(input)};
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Honorato · prueba de Google Maps</title><link rel="stylesheet" href="/location-runtime.css"/></head>
<body><header class="operator"><h1>Honorato · taller del mapa</h1><p>Cambia la piel y los ajustes para ver el resultado al instante. Datos de la ficha conservada; la entrada exacta puede variar.</p>
<p data-trial-status role="status">Consultando las cargas disponibles de la prueba…</p><p data-trial-meter></p>
<button type="button" class="start-google" data-google-start disabled>Activar Google · usa 1 carga</button>
${input.marker.kind !== 'logo' ? '<p>Pin neutro: falta un logo de Honorato con permiso de uso registrado.</p>' : ''}
</header><main><div class="trial-workbench"><Controls target="honorato-location"/><div class="trial-preview"><Location id="honorato-location" input={input} provider="google_js" markerLabel={false}/></div></div><script type="module" src="/honorato-google-client.js" is:inline></script></main>
<style is:global>body{margin:0;background:#f5f5f3;color:#222;font:16px/1.5 system-ui,sans-serif}*{box-sizing:border-box}.operator,main{max-width:1500px;margin:0 auto;padding:28px}.operator h1{font-size:28px;font-weight:500}.operator p{max-width:85ch}main{padding-top:0}.location-bone{border:1px solid #aaa}.trial-workbench{display:grid;grid-template-columns:280px minmax(0,1fr);gap:24px;align-items:start}.trial-preview{min-width:0}.start-google{font:inherit;min-height:44px;padding:10px 16px;background:#222;color:#fff;border:1px solid #222}.start-google:disabled{background:#e5e5e5;color:#555;border-color:#aaa}.start-google:focus-visible{outline:3px solid #222;outline-offset:4px}@media(max-width:1100px){.trial-workbench{display:block}}@media(max-width:600px){.operator,main{padding:20px}}</style>
</body></html>`);
await astroBuild({ root: preview, configFile: false, output: 'static', logLevel: 'error' });
await writeFile(resolve(folder, 'build-receipt.json'), JSON.stringify({ source_packet_sha256: createHash('sha256').update(packetBytes).digest('hex'),
  business_id: packet.business_id, location_id: packet.location_id, publication_allowed: false,
  provider: 'google_js', marker: input.marker.kind, marker_reason: input.marker.reason, private_build: true,
  google_live_verified: false, marker_label_visible: false,
  operator_controls: true, google_starts_on_explicit_click: true,
  component: 'SingleBusinessLocation.astro' }, null, 2));
console.log('Built private Honorato consumer with the existing Astro component. No map loaded during build.');
