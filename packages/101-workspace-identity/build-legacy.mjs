// Generate the shared font distribution for existing non-React staff pages.
import {readFile, writeFile, copyFile, mkdir} from 'node:fs/promises';
const output = new URL('../../projects/101_restaurant_commerce_v4/src/world_model/restaurant_commerce/web/workspace/assets/', import.meta.url);
await mkdir(output, {recursive:true});
const face = await readFile(new URL('./typography.css', import.meta.url), 'utf8');
const tokens = await readFile(new URL('./tokens.css', import.meta.url), 'utf8');
await writeFile(new URL('101-ui-font.css', output), face + tokens + '\nbody,h1,h2,h3,h4,h5,h6,button,input,select,textarea{font-family:var(--wm-font);font-synthesis:none}\n');
for (const name of ['inter-latin-wght-normal.woff2','INTER-LICENSE.txt']) {
  await copyFile(new URL(name, import.meta.url), new URL(name, output));
}
