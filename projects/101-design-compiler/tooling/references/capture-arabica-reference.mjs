import { mkdir, readFile, writeFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { openLocalBrowser } from '../../scripts/lib/local-browser.ts';
import { parseArabicaReference } from './parse-arabica-reference.mjs';

// Local review only: restore public reference observations into ignored files.
const root = '.tools/arabica-locations-reference/';
const offline = process.argv.includes('--offline');
let observedAt = new Date().toISOString();
try { observedAt = (await stat(root + 'reference/world-desktop.json')).mtime.toISOString(); } catch {}
await mkdir(root + 'pages', { recursive: true });
await mkdir(root + 'reference', { recursive: true });
const assets = [
  ['avenir-roman.woff2', 'https://arabica.com/wp-content/themes/arabica/css/webfonts/326276_1_0.woff2'],
  ['avenir-heavy.woff2', 'https://arabica.com/wp-content/themes/arabica/css/webfonts/326276_0_0.woff2'],
  ['arabica-icons.woff', 'https://arabica.com/wp-content/themes/arabica/fonts/arabica-icons.woff?h315i7'],
];
const assetEvidence = [];
for (const [name, url] of assets) {
  let bytes;
  try { bytes = await readFile(root + 'reference/' + name); } catch (error) {
    if (error.code !== 'ENOENT' || offline) throw error;
    const response = await fetch(url, { signal: AbortSignal.timeout(25000) });
    if (!response.ok) throw Error('REFERENCE_FONT_UNAVAILABLE');
    bytes = Buffer.from(await response.arrayBuffer()); await writeFile(root + 'reference/' + name, bytes);
  }
  assetEvidence.push({ name, source: url, sha256: createHash('sha256').update(bytes).digest('hex'),
    scope: 'private-reference-only', publication_allowed: false });
}
await writeFile(root + 'reference/assets.json', JSON.stringify(assetEvidence, null, 2));
const browser = await openLocalBrowser();
try {
  await browser.call('Network.setBlockedURLs', { urls: [] });
  await browser.call('Page.navigate', { url: offline ? 'about:blank' : 'https://arabica.com/en/locations/' });
  await new Promise(r => setTimeout(r, 2500));
  await browser.evaluate(`window.__parseReference = ${parseArabicaReference.toString()}`);
  const seen = new Set(), pages = [], queue = ['https://arabica.com/en/locations/'];
  while (queue.length) {
    const batch = queue.splice(0, 3).filter(url => {
      const path = new URL(url).pathname.replace(/\/$/, '');
      if (seen.has(path)) return false;
      if (seen.size >= 180 || !/^\/en\/locations(?:\/[a-z0-9-]+){0,2}$/.test(path)) throw Error('REFERENCE_CAPTURE_BOUND');
      seen.add(path); return true;
    });
    const results = await Promise.allSettled(batch.map(async url => {
      const id = new URL(url).pathname.replace(/^\/en\/locations\/?/, '').replace(/\/$/, '') || 'world';
      const file = root + 'pages/' + id.replaceAll('/', '__') + '.html';
      let html;
      try { html = await readFile(file, 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (!html && id === 'world') {
        try { html = JSON.parse(await readFile(root + 'reference/world-desktop.json', 'utf8')).html; } catch {}
      }
      if (!html && offline) throw Error('OFFLINE_REFERENCE_PAGE_MISSING:' + id);
      if (!html) html = await browser.evaluate(`fetch(${JSON.stringify(url)}, {signal:AbortSignal.timeout(15000)}).then(r=>{if(!r.ok)throw Error('SOURCE_'+r.status);return r.text()})`);
      const page = await browser.evaluate(`window.__parseReference(${JSON.stringify(html)}, ${JSON.stringify(url)})`);
      page.sha256 = createHash('sha256').update(html).digest('hex');
      await writeFile(file, html);
      return page;
    }));
    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.status === 'rejected') throw new Error(`REFERENCE_CAPTURE_FAILED:${batch[i]}`, { cause: result.reason });
      const page = result.value; pages.push(page);
      if (page.level !== 'city') queue.push(...page.links.map(link => link.url));
      console.log(page.id, page.links.length, page.markers.length, page.cards.length);
    }
    await writeFile(root + 'catalogue.json', JSON.stringify({ schema: '101-arabica-reference-v1',
      observedAt, processedAt: new Date().toISOString(), referenceOnly: true, publicationAllowed: false,
      source: 'https://arabica.com/en/locations/', pages }, null, 2));
  }
  console.log('COMPLETE', pages.length);
} finally { browser.close(); }
