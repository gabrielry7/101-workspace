import { mkdir, writeFile } from 'node:fs/promises';
import { resolve, dirname, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build as astroBuild } from 'astro';
import { build } from 'esbuild';

const project = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const preview = resolve(project, '.tools/location-directory-bone/preview');
const pages = resolve(preview, 'src/pages');
await mkdir(resolve(pages, 'bones'), { recursive: true }); await mkdir(resolve(preview, 'public'), { recursive: true });
const pathFrom = (folder, path) => relative(folder, resolve(project, path)).split(sep).join('/');
await writeFile(resolve(pages, 'bones/location-directory.astro'), `---\nimport Workshop from '${pathFrom(resolve(pages, 'bones'), 'src/pages/bones/location-directory.astro')}';\n---\n<Workshop/>`);
await writeFile(resolve(pages, 'index.astro'), '<meta http-equiv="refresh" content="0;url=/bones/location-directory/"/><a href="/bones/location-directory/">Abrir hueso de ubicaciones</a>');
await writeFile(resolve(pages, 'multi.astro'), `---
import Directory from '${pathFrom(pages, 'src/components/bones/LocationDirectory.astro')}';
import {neutralLocationDirectory as content} from '${pathFrom(pages, 'src/bones/location-directory.ts')}';
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Dos instancias · prueba sintética</title></head><body><Directory id="directory-a" content={content}/><Directory id="directory-b" content={content}/></body></html>`);
await writeFile(resolve(pages, 'stress.astro'), `---
import Directory from '${pathFrom(pages, 'src/components/bones/LocationDirectory.astro')}';
import {neutralLocationDirectory} from '${pathFrom(pages, 'src/bones/location-directory.ts')}';
const content = structuredClone(neutralLocationDirectory);
content.title = 'Título de ubicaciones con varias palabras para comprobar su ajuste';
for (const view of content.views) {
  for (const item of [...view.entries, ...view.groups.flatMap(g=>g.items)]) item.label = 'Ubicación con un nombre largo y varias palabras';
  for (const card of view.cards) card.title = 'Nombre de un local con varias palabras para revisar';
}
---
<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Textos largos · prueba sintética</title></head><body><p>Datos sintéticos para revisión de ajuste.</p><Directory id="directory-stress" content={content}/></body></html>`);
await build({ entryPoints: [resolve(project, 'src/bones/location-directory-client.js')], bundle: true,
  outfile: resolve(preview, 'public/location-directory.js'), format: 'esm', target: 'es2022', minify: true });
await astroBuild({ root: preview, configFile: false, output: 'static', logLevel: 'error' });
console.log('Built location directory bone; no reference media or provider runtime.');
