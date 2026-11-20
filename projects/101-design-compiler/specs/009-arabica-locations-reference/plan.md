# Technical plan

Reuse Astro and its current dependency versions; isolate a scoped private build
with the pattern of `tooling/bones/prepare-location-map.mjs`. Reuse `loadGoogleMaps`
and the existing bounded local trial server. Apply the reference's inline Google
style without changing the Honorato cloud style. The single-business bone owns one destination;
do not change that contract to accommodate this independent reference study.
The reference component is not a second production renderer or a new service.

Own source: `src/components/references/ArabicaLocations.astro`, reference-specific
CSS/client/data helpers, a bounded preparation script and native-browser audit.
Extract only the location hierarchy and public observations into ignored local
input. Retain original reference HTML/CSS/media privately with provenance; never
run retained third-party scripts or transfer their API keys to the reproduction.

Match measured original layout and private fonts. Local reference assets remain
separate from the repository's original approved templates and Honorato preview.
Map controls and geographic rendering use the chosen provider's real instance;
avoid screenshots as the working map or fake route/detail actions.

Verify pure input/navigation logic meaningfully, build only this scoped Astro
entry, and inspect real cartography and hierarchy in Chromium using
`scripts/lib/local-browser.ts`. Test mobile/tablet/desktop, 559/560/561 and
779/780/781 boundaries as applicable, font fallback, reduced motion, blocked
provider and history. Save screenshots privately; commit a non-sensitive receipt.

Constitution check: specification precedes implementation; reuse existing stack,
protect unrelated Caretta files and restricted references, label this study's
authority, retain accessibility and avoid claiming human visual approval.
