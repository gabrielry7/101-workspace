# Honorato concepts — portable review

Three complete Honorato proposals, the working catalogue, and the component/skill
map. All required photographs, logo, fonts and browser code are included.
Viewing needs only **Node18 or newer**. No npm install, account, API key, model call
or original archive restoration is required.

From this repository root:

```sh
node projects/honorato-studio-preview/serve.mjs
```

Open **http://127.0.0.1:4335/studio/**. Keep the command running. Ctrl+C stops it.
The server binds only to this computer. If that port is busy, set `PORT=4336`
(PowerShell: `$env:PORT=4336`) and rerun.

For a separate checkout that preserves your current work:

```sh
git clone --depth 1 --filter=blob:none --sparse --branch codex/honorato-studio-preview-20261028 https://github.com/gabrielry7/101-workspace.git honorato-concepts
cd honorato-concepts
git sparse-checkout set projects/honorato-studio-preview
node projects/honorato-studio-preview/serve.mjs
```

## What to inspect

- **A su ritmo:** Impeccable-adapted photographic process direction.
- **Carta abierta:** Taste-adapted product/menu-led direction.
- **Dentro del obrador:** Meng To-adapted people/editorial direction.
- Open **Why these pages?** and **Why these photographs?** in the gallery.
- Try each menu's search, category filter, empty/reset state and product detail.
- Open `/studio/map/` for the standardized capabilities/component map.

Owl guided information architecture; Emil informed small interaction feedback and
reduced motion; Jakub informed actual independent image review. These are adapted
methods, not a claim that every listed skill or external component was executed.
The menu uses Gabo's real catalogue client with twelve observed Honorato products.
Prices/current availability remain unknown. This is a review proposal, not the
business's live website, an ordering service or an owner-approved direction.

The gallery reveals methods; it is not a blinded comparison. Record Gabo's own
comments as his feedback. Do not invent Thomas's preferences or turn observations
into approval. The earlier laboratory and vote store are not part of this bundle.

## Agent instructions

1. Run `node serve.mjs --verify` inside this project, then start `node serve.mjs`.
2. Open the gallery and all three concepts on desktop and phone widths. Actually
   view rendered images when reporting visual findings; saving a screenshot alone
   is not inspection.
3. Keep Gabo's feedback separate from agent critique and Thomas's feedback.
4. Preserve `provenance.json` and the original branch before editing. Do not
   regenerate sites or download the full historical archive just to preview them.

## Optional source edits

The selected Astro source is included under `src/`; generated business inputs
are included under `src/data/`, and assets under `public/`. This project is isolated
from the larger compiler and requires **Node22.12+** to rebuild:

```sh
npm ci
npm run dev
```

Or `npm run build` followed by `node serve.mjs`. Build reseals the local output and
labels it a local rebuild; it does not inherit the original image-review result.
There are no package hooks that call paid models. Business evidence, contact
destinations and publication uncertainty must survive design edits.

`provenance.json` identifies the original source commit/build, selected upstream
versions, asset provenance and portability changes. `preview-files.json` binds
every served file to its SHA-256 hash. Source license notices and font OFL files
are retained. Photographs/branding belong to their source owners; inclusion in
this review bundle is not a general stock-media license or business endorsement.
