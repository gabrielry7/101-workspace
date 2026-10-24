// Local-only discovery. This script makes no network requests or uploads.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, dirname, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const out = resolve(root, '.superdesign');
const hashes = {};
async function read(path) {
  const absolute = resolve(root, path);
  if (!absolute.startsWith(root + sep) || /(^|[\\/])\.env(?:\.|$)/.test(path)) throw Error('CONTEXT_PATH_REJECTED');
  const bytes = await readFile(absolute);
  hashes[path] = createHash('sha256').update(bytes).digest('hex');
  return bytes.toString('utf8');
}
async function dump(paths) {
  const parts = [];
  for (const path of paths) parts.push(`## ${path}\n\n\`\`\`${path.endsWith('.astro') ? 'astro' : path.endsWith('.css') ? 'css' : 'typescript'}\n${await read(path)}\n\`\`\`\n`);
  return parts.join('\n');
}
const entry = 'src/pages/b3/[candidate].astro';
const imports = new Map();
async function trace(path) {
  if (imports.has(path)) return;
  const code = await read(path);
  const children = [];
  imports.set(path, children);
  for (const match of code.matchAll(/(?:\bfrom\s*|\bimport\s*\(?\s*)['"]([^'"]+)['"]/g)) {
    if (!match[1].startsWith('.')) continue;
    const target = relative(root, resolve(root, dirname(path), match[1].split('?')[0])).split(sep).join('/');
    if (/\.(?:astro|ts|css|mjs|js|json)$/.test(target)) {
      children.push(target);
      await trace(target);
    }
  }
}
await trace(entry);
const expanded = new Set();
function tree(path, depth = 0) {
  const line = `${'  '.repeat(depth)}- ${path}`;
  if (expanded.has(path)) return `${line} (already traced)\n`;
  expanded.add(path);
  return line + '\n' + (imports.get(path) ?? []).map(p => tree(p, depth + 1)).join('');
}
const css = ['src/design/experience.css', 'src/design/rich-experience.css', 'src/design/depth-experience.css', 'src/design/experience-refinement.css'];
const docs = {
  'components.md': '# Shared B3 components\n\nAstro primitives; no third-party component library. Full local source, not an upload list.\n\n' + await dump(['src/components/composition/ContextualImage.astro', 'src/components/composition/ExperienceFeatures.astro', 'src/components/composition/CommunitySections.astro']),
  'layouts.md': '# Shared shell and composition\n\nExperienceComposition selects the actual home branch when page.kind is home. Navigation and footer remain shared across all four profiles.\n\n' + await dump(['src/layouts/Foundation.astro', 'src/components/composition/ExperienceComposition.astro', 'src/components/composition/ExperienceNavigation.astro']),
  'routes.md': '# Routes\n\nAstro static routes. Four profiles, eleven destinations each. Initial target: /b3/candidate-01/.\n\n' + await dump([entry, 'src/pages/b3/[candidate]/[page].astro', 'src/design/rich-experience-contracts.ts', 'src/design/experience-contracts.ts']),
  'theme.md': '# Current candidate-01 tokens\n\nAstro 7.3.7; vanilla CSS; no Tailwind or React. WhiteInk / Classic / Immersive / Journal. Paper #fff; ink #181818; line #d0d0cb; muted #50504c. Display Georgia, Times New Roman, serif; body Arial, Helvetica, sans-serif. Base 16px / 1.5. Gutter clamp(1.25rem,4vw,4rem); section space clamp(3rem,7vw,7rem). Main responsive breakpoint 760px, extra guard 380px. Full-width cover film; dark legibility overlay; reduced-motion behavior is intentional. No invented font files or logo image: brand is the current text wordmark.\n\n## Full stylesheet sources\n\n' + await dump(css),
  'pages.md': '# Home dependency tree\n\nRecursively traced local imports, including gates and pure logic. This discovery inventory is NOT the remote payload. Never upload every dependency. Four profiles use the same entry and shared renderer; target candidate-01 has the home branch.\n\n```text\n' + tree(entry) + '```\n',
  'extractable-components.md': '# Existing reusable components\n\n## ExperienceNavigation\n- Source: src/components/composition/ExperienceNavigation.astro\n- Category: layout\n- Props: root, name, kind. Keep the current target name and destinations.\n- Current structure: text wordmark, Carta/Reservas quick links, grouped native disclosure navigation.\n\n## ExperienceComposition footer\n- Source: src/components/composition/ExperienceComposition.astro\n- Category: layout (embedded shared footer, not a separate source file)\n- Props for extraction: root and active page only.\n- Hardcoded invariants: links, fictional-media disclosure and Pixabay non-endorsement.\n\n## ContextualImage\n- Source: src/components/composition/ContextualImage.astro\n- Category: basic\n- Local rights gate and picture/srcset output. Keep gate in 101; do not substitute a remote rendering implementation.\n'
};
await mkdir(resolve(out, 'init'), {recursive: true});
for (const [name, body] of Object.entries(docs)) await writeFile(resolve(out, 'init', name), body);
const system = `# 101 B3 — La mesa abierta\n\nExisting UI refinement, not a new restaurant site. Target /b3/candidate-01/. User liked its elegant identity, Georgia typography and white/ink palette. Preserve them.\n\nThe initial scene is a full-width background film, text wordmark/navigation over it, title La Mesa, tagline Cocina para quedarse un rato., and two links to dedicated carta and reservas pages. Below: house introduction + four-route directory, four editorial stories, two fictional opinions, contact/social examples, and shared footer. Preserve the approved copy, destinations and disclosures; do not fabricate a real restaurant or operational booking/order/social service.\n\nUse ONLY the fonts, colors, spacing, and component styles defined in the design system and attached actual CSS. No new fonts, colors, stock downloads, images, facts, logos or commercial functions. Explore hierarchy, spacing, proportional image fields and editorial rhythm. Root content/plan/media hashes must remain preserved when porting an approved idea back to 101.\n\nAll media are illustrative, not documentary. Existing B3 permissions do not authorize training, AI editing, standalone redistribution or publishing a new provider asset library. Keep private originals/keys out of all context. Resolve hosted-service media treatment before any image/screenshot upload.\n\nThe mandatory existing-UI reproduction precedes a scoped variation. A local snapshot or successful CLI install is not a remote draft. No remote IDs until returned by the provider. No generation before authenticated preflight and verified applicable cost/budget. User reviews drafts before implementation.\n`;
await writeFile(resolve(out, 'design-system.md'), system);
await writeFile(resolve(out, 'init', 'source-fingerprints.json'), JSON.stringify({schemaVersion: 1, target: '/b3/candidate-01/', sourceFiles: hashes, uploads: []}, null, 2) + '\n');
console.log(JSON.stringify({status: 'LOCAL_CONTEXT_READY', target: '/b3/candidate-01/', initFiles: Object.keys(docs), tracedFiles: imports.size, uploadedFiles: 0}));
