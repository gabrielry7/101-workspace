import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { resolve, dirname, relative, sep } from 'node:path';
import { createHash } from 'node:crypto';
import { bindLocationBone } from '../../src/bones/location-map.ts';
import { locationEditorDefaults } from '../../src/bones/location-map-editor.ts';

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
  const editor = locationEditorDefaults(mapColors);
  const astroImport = path => relative(pageDir, resolve(project, path)).split(sep).join('/');
  await writeFile(resolve(pageDir, 'honorato.astro'), `---
import Location from '${astroImport('src/components/bones/SingleBusinessLocation.astro')}';
import Controls from '${astroImport('src/components/bones/LocationMapControls.astro')}';
const input = ${JSON.stringify(input)};
const colors = ${JSON.stringify(mapColors)};
const editor = ${JSON.stringify(editor)};
const basemap = { format: 'openfreemap', url: '/openfreemap-empty.geojson', fontURL: '/fonts/familjengrotesk.woff',
  alternateFontURL: '/fonts/bodonimoda.woff', attribution: 'OpenFreeMap · OpenStreetMap' };
---
<!doctype html>
<html lang="es"><head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex,nofollow"/>
  <title>Honorato en OpenFreeMap</title><link rel="icon" href="data:,"/><link rel="stylesheet" href="/location-runtime.css"/>
</head><body>
  <main class="honorato-preview" aria-label="Vista previa del mapa de Honorato">
    <p class="preview-note"><strong>Vista previa en OpenFreeMap.</strong> Pin de muestra en Ciudadela Complex. La ubicación exacta del local está por confirmar.</p>
    <a class="edit-link" href="#honorato-open-map-controls">Editar mapa</a>
    <Location id="honorato-open-map" input={input} skin="paper" runtimeURL="/location-runtime.js" basemap={basemap} mapColors={colors} markerLabel={false}/>
    <Controls target="honorato-open-map" note="" editor={editor}/>
  </main>
  <script is:inline type="module" src="/honorato-openfreemap-controls.js"></script>
</body></html>
<style is:global>
  @font-face { font-family: Familjen; src: url('/fonts/familjengrotesk.woff') format('woff'); font-display: swap; }
  body { margin: 0; background: #faf6ee; color: #201c1b; font: 16px/1.5 Familjen, system-ui, sans-serif; }
  .honorato-preview { max-width: 1392px; margin: 0 auto; padding: clamp(20px, 4vw, 56px); }
  .preview-note { margin: 0 0 12px; font-size: .875rem; max-width: 72ch; }
  .preview-note strong { color: #bf0000; }
  .edit-link { display: inline-block; margin-bottom: 12px; padding: 4px 0; color: inherit; text-underline-offset: 3px; }
  #honorato-open-map { border: 1px solid var(--section-line); margin-bottom: 24px; }
  #honorato-open-map[data-skin="paper"] { --section-paper: #fffaf1; --section-ink: #201c1b; --section-line: #d4b7a5; --section-accent: #bf0000; font-family: Familjen, system-ui, sans-serif; }
  #honorato-open-map[data-skin="paper"] h2 { color: var(--section-accent); font-weight: 650; }
  #honorato-open-map [data-location-part="directions"],
  #honorato-open-map [data-map-state="degraded"] .location-map__canvas,
  #honorato-open-map[data-hide-map-zoom] .maplibregl-ctrl-top-right,
  #honorato-open-map[data-hide-pin-logo] .single-business-marker__logo { display: none; }
  #honorato-open-map[data-hide-pin-logo] .single-business-marker__frame circle { visibility: visible; }
  #honorato-open-map .single-business-marker,
  #honorato-open-map .single-business-marker__visual {
    width: calc(64px * var(--editor-pin-scale, 1));
    height: calc(80px * var(--editor-pin-scale, 1));
  }
  #honorato-open-map .single-business-marker__frame { width: 100%; height: 100%; }
  #honorato-open-map .single-business-marker__frame circle { r: var(--editor-pin-dot-radius, 7px); }
  #honorato-open-map .single-business-marker__frame path { stroke-width: var(--editor-pin-stroke, 2.6); }
  #honorato-open-map .single-business-marker__logo {
    left: 50%; top: 40%; width: var(--editor-logo-scale, 68.75%); height: calc(var(--editor-logo-scale, 68.75%) * .8);
    transform: translate(-50%, -50%);
  }
  #honorato-open-map .location-map__marker-label { font-size: var(--editor-label-size, 14px); }
  #honorato-open-map[data-editor-font="familjen"] { font-family: Familjen, system-ui, sans-serif; }
  #honorato-open-map[data-editor-font="georgia"] { font-family: Georgia, serif; }
  #honorato-open-map[data-editor-font="system"] { font-family: system-ui, sans-serif; }
  #honorato-open-map h2 { font-size: calc(clamp(2rem, 4vw, 4.5rem) * var(--editor-title-scale, 1)); }
  #honorato-open-map[data-skin="neutral"] h2 { font-size: calc(1em * var(--editor-title-scale, 1)); }
  @media (forced-colors: none) {
    #honorato-open-map { background: var(--editor-section-paper, var(--section-paper)); border-color: var(--editor-section-line, var(--section-line)); }
    #honorato-open-map, #honorato-open-map .location-map { color: var(--editor-section-ink, var(--section-ink)); }
    #honorato-open-map h2 { color: var(--editor-section-accent, currentColor); }
    #honorato-open-map[data-skin="paper"] h2 { color: var(--editor-section-accent, var(--section-accent)); }
    #honorato-open-map .single-business-marker__frame circle { fill: var(--editor-pin-dot, currentColor); }
    #honorato-open-map .location-map__marker-label {
      background: var(--editor-label-paper, var(--map-paper));
      color: var(--editor-label-ink, var(--map-ink));
      border-color: var(--editor-label-line, var(--map-ink));
    }
  }
  @media (forced-colors: active) {
    #honorato-open-map[data-skin="paper"] { --section-paper: Canvas; --section-ink: CanvasText; --section-line: CanvasText; --section-accent: Highlight; }
  }
  @media (min-width: 1200px) {
    .honorato-preview { display: grid; grid-template-columns: minmax(0, 1fr) 310px; gap: 16px 24px; align-items: start; }
    .preview-note { grid-column: 1 / -1; margin: 0; }
    .edit-link { display: none; }
    #honorato-open-map-controls { position: sticky; top: 20px; max-height: calc(100dvh - 40px); overflow-y: auto; box-sizing: border-box; }
  }
</style>`);
  const controls = resolve(project, 'src/bones/location-map-controls.js');
  await build({
    stdin: {
      contents: `import { mountLocationControls } from ${JSON.stringify(controls)};
const section = document.getElementById('honorato-open-map');
const panel = document.querySelector('[data-location-controls]');
mountLocationControls(panel, section, { storageKey: '101-honorato-openfreemap-controls-v1',
  editor: ${JSON.stringify(editor)},
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
