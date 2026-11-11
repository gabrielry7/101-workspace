import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { resolve, dirname, relative, sep } from 'node:path';
import { createHash } from 'node:crypto';
import { bindLocationBone } from '../../src/bones/location-map.ts';

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const mapColors = {
  paper: '#faf6ee', land: '#f3e9dc', water: '#c6d7d4',
  road: '#fffdf8', roadOutline: '#bea58f', building: '#e2cfb8',
  ink: '#bf0000', pin: '#bf0000',
};

export async function prepareHonoratoOpenFreeMap({ project, source, preview, publicDir, owner, build }) {
  const work = resolve(project, '.tools/honorato-openfreemap');
  await mkdir(work, { recursive: true });
  const osmPath = resolve(work, 'complex-osm.json');
  const osmURL = 'https://www.openstreetmap.org/api/0.6/way/618065505/full.json';
  let osmBytes;
  try {
    osmBytes = await readFile(osmPath);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    const response = await fetch(osmURL, {
      signal: AbortSignal.timeout(15000),
      headers: { 'User-Agent': '101-design-compiler/0.4 (local cartography preview)' },
    });
    if (!response.ok) throw Error(`OSM_REFERENCE_UNAVAILABLE:${response.status}`);
    osmBytes = Buffer.from(await response.arrayBuffer());
    await writeFile(osmPath, osmBytes);
  }
  const { elements } = JSON.parse(osmBytes);
  const way = elements.find(element => element.type === 'way' && element.id === 618065505);
  if (way?.tags?.name !== 'Complex Llanogrande' || way.nodes.length < 4 || way.nodes[0] !== way.nodes.at(-1)) {
    throw Error('OSM_COMPLEX_REFERENCE_MISMATCH');
  }
  const nodes = new Map(elements.filter(element => element.type === 'node').map(node => [node.id, node]));
  const vertices = way.nodes.slice(0, -1).map(id => nodes.get(id));
  const mean = key => vertices.reduce((sum, node) => sum + node[key], 0) / vertices.length;
  const coordinate = {
    latitude: mean('lat'), longitude: mean('lon'), purpose: 'synthetic',
    source: { kind: 'osm', map_use: 'permitted', reference: 'https://www.openstreetmap.org/way/618065505',
      observed_at: (await stat(osmPath)).mtime.toISOString(), sha256: sha256(osmBytes) },
  };

  const packet = JSON.parse(await readFile(resolve(source, 'artifacts/design-creative-20261028/business-packet.json'), 'utf8'));
  const evidence = JSON.parse(await readFile(resolve(project, '.tools/honorato-google-live/logo-evidence.json'), 'utf8'));
  const input = bindLocationBone(owner, { ...packet.location, coordinate, publication_allowed: false }, evidence);
  if (input.marker.kind !== 'logo') throw Error(`HONORATO_LOGO_NOT_AVAILABLE:${input.marker.reason}`);
  if (!input.synthetic || input.directions.length || !owner.rendererEligibility(input.location).render) {
    throw Error('HONORATO_SAMPLE_BINDING_REQUIRED');
  }
  const logoBytes = await readFile(resolve(project, evidence.render_file));
  if (sha256(logoBytes) !== input.marker.sha256) throw Error('LOGO_RENDER_HASH_MISMATCH');
  const logoPath = resolve(publicDir, '.' + input.marker.url);
  await mkdir(dirname(logoPath), { recursive: true });
  await writeFile(logoPath, logoBytes);

  await writeFile(resolve(publicDir, 'openfreemap-empty.geojson'), '{"type":"FeatureCollection","features":[]}');
  const pageDir = resolve(preview, 'src/pages');
  const astroImport = path => relative(pageDir, resolve(project, path)).split(sep).join('/');
  await writeFile(resolve(pageDir, 'honorato.astro'), `---
import Location from '${astroImport('src/components/bones/SingleBusinessLocation.astro')}';
import Controls from '${astroImport('src/components/bones/LocationMapControls.astro')}';
const input = ${JSON.stringify(input)};
const colors = ${JSON.stringify(mapColors)};
const basemap = { format: 'openfreemap', url: '/openfreemap-empty.geojson', fontURL: '/fonts/familjengrotesk.woff', attribution: 'OpenFreeMap · OpenStreetMap' };
---
<!doctype html>
<html lang="es"><head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex,nofollow"/>
  <title>Honorato en OpenFreeMap</title><link rel="icon" href="data:,"/><link rel="stylesheet" href="/location-runtime.css"/>
</head><body>
  <main class="honorato-preview" aria-label="Vista previa del mapa de Honorato">
    <p class="preview-note"><strong>Vista previa en OpenFreeMap.</strong> Pin de muestra en Ciudadela Complex. La ubicación exacta del local está por confirmar.</p>
    <Location id="honorato-open-map" input={input} skin="paper" runtimeURL="/location-runtime.js" basemap={basemap} mapColors={colors} markerLabel={false}/>
    <Controls target="honorato-open-map" initiallyOpen={false} note="Ajusta la sección, el zoom y el pin. El mapa mantiene su paleta de Honorato."/>
  </main>
  <script is:inline type="module" src="/honorato-openfreemap-controls.js"></script>
</body></html>
<style is:global>
  @font-face { font-family: Familjen; src: url('/fonts/familjengrotesk.woff') format('woff'); font-display: swap; }
  body { margin: 0; background: #faf6ee; color: #201c1b; font: 16px/1.5 Familjen, system-ui, sans-serif; }
  .honorato-preview { max-width: 1392px; margin: 0 auto; padding: clamp(20px, 4vw, 56px); }
  .preview-note { margin: 0 0 18px; font-size: .875rem; max-width: 72ch; }
  .preview-note strong { color: #bf0000; }
  #honorato-open-map { border: 1px solid var(--section-line); margin-bottom: 24px; }
  #honorato-open-map[data-skin="paper"] { --section-paper: #fffaf1; --section-ink: #201c1b; --section-line: #d4b7a5; --section-accent: #bf0000; font-family: Familjen, system-ui, sans-serif; }
  #honorato-open-map[data-skin="paper"] h2 { color: var(--section-accent); font-weight: 650; }
  #honorato-open-map [data-location-part="directions"],
  #honorato-open-map [data-map-state="degraded"] .location-map__canvas { display: none; }
  #honorato-open-map .single-business-marker__frame path { stroke-width: 2.6; }
  @media (forced-colors: active) {
    #honorato-open-map[data-skin="paper"] { --section-paper: Canvas; --section-ink: CanvasText; --section-line: CanvasText; --section-accent: Highlight; }
  }
</style>`);
  const controls = resolve(project, 'src/bones/location-map-controls.js');
  await build({
    stdin: {
      contents: `import { mountLocationControls } from ${JSON.stringify(controls)};
const section = document.getElementById('honorato-open-map');
const panel = document.querySelector('[data-location-controls]');
mountLocationControls(panel, section, { storageKey: '101-honorato-openfreemap-controls-v1',
  initial: { skin: 'paper', pinPaper: ${JSON.stringify(mapColors.paper)}, pinInk: ${JSON.stringify(mapColors.ink)} } });`,
      resolveDir: project,
    },
    bundle: true, format: 'esm', target: 'es2022',
    outfile: resolve(publicDir, 'honorato-openfreemap-controls.js'),
  });
  await writeFile(resolve(work, 'honorato-build-receipt.json'), JSON.stringify({
    provider: 'openfreemap', source: coordinate.source, sample_pin: true, publication_allowed: false,
    palette_basis: 'Honorato website red and black, Studio cream, adapted map surfaces', mapColors,
  }, null, 2) + '\n');
}
