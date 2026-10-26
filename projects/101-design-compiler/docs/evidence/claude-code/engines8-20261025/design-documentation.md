# Local design documentation - eight restaurant operators

Scope: source-derived preliminary collection, recorded 2026-10-25. No UI, source, media, global persistence, integration, merge or push is performed. Exactly eight registry operators: 01 WhiteInk, 02 Vermilion, 03 Brasa and 04 Herbario retain PRELIMINARY_ACCEPTED; 05 Mercado / 06 Marea are general, 07 Riso / 08 Índice artistic, all four AWAITING_HUMAN_REVIEW. Original palettes/assets are inherited read-only references, deliberately not re-extracted as a new global system.

Independent finish disposition is SHIP for preliminary user review, with no remaining material fixes in that bounded scope. It is not a user selection, approved comp, production lock or universal-sector validation. Source wins over intended direction; documentation adds no authority to the four proposals.

The local [DESIGN.md](design-system/DESIGN.md) contains actual four-namespace color tokens, display/menu/body type roles, declared variable-font ranges, container-aware long-heading rules, responsive layout and interaction components. The [sidecar](design-system/.impeccable/design.json) extends it with motion, breakpoints, inherited shadow exceptions and ten self-contained representative visual snippets. Snippet text is demonstration-only and snippets do not implement business behavior. Its eight-step OKLCH ramps are synthesized panel previews from the actual colors, never additional approved CSS tokens or contrast recommendations. Primitives remain owned by DESIGN.md frontmatter.

The forty-row catalogue is a separate synthetic projection: four original offerings are structured clones, thirty-six new offerings have explicit fictional facts and stable IDs, eight categories contain five dishes each, and the original base content hash is checked. Menu rows expose name/description/price; details carry ingredients/allergens/calories/currency and related links. It does not overwrite source business facts. Every operator exposes all eleven business routes (including home) plus forty detail routes. Native links/category details survive no-JS; enhanced local selection includes empty, one and forty-item states with a clear action and bounded expanded scrolling. Facts, identity and query offering IDs are shared across the skins.

Media remains a separate pinned companion, not a source of dish facts. Only the original four dish bindings admit image/optional manual silent video; the other thirty-six stay text-only. Atmosphere images carry explicit non-documentary labels; only those images receive Riso overprint or Índice grayscale/color state. `engine-media.ts` binds unforgeable handles to registered route/usage, rights and suitability decisions; validates bytes, evidence, silent tracks and explicit evaluation time; and fails closed. The companion reports 76 assets, 128 scoped grants and 1,780 registered usages; permission expiry is not renewed by this documentation. Its review pin is `61e270572e27fd51121d3ec295a66b35854ed60a5cd51e269faf8708740a3ae6`.

Evidence index (existing parent receipts; no audit or detector rerun):
- `review-packet.md` and `independent-review.md`: bounded direction, actual final SHIP disposition and detailed fidelity matrix.
- `final-review/{05,06,07,08}-{home,carta,pedidos,detail,story}-{390,1440}.png`, eight `*-surfaces-*-sheet.png`, and `captures.json`: forty native top-zero primary views.
- `final-audit/audit.json`: 256 catalogue/detail views at 360/390/768/1024/1440, including 160 new detail fact sets; `*-pedidos-{mobile,desktop}-expanded40.png`, active/empty captures and menu/detail sheets cover selection and lower sections.
- `final-pages/audit.json` and eight `*-pages-{390,1440}-sheet.png`: 144 other business-page views at 360/390/768/1440. Together the two audits cover 400 views; these are local geometry/contrast checks, not complete WCAG or field-performance certification.
- `navigation-smoke.json`: keyboard category -> dish -> selection -> clear, query/no-JS behavior, 168 preview URLs and 404 negatives.
- `protection-final.json`: 327 protected old HTML outputs and historical assets unchanged, only comparison index allowed to differ. This carries the old-four freeze; documentation does not reseal it.
- `final-check.log`, `final-build.log`, `final-test.log`, `performance.json`: checker zero issues, 532 built pages; suite 437/438 due to historical H8 expecting LOCK_AUDIT_FILE_MISMATCH and receiving LOCK_BROWSER_MISMATCH. Full suite is not green. Static budget is passed; no new dependency files, external scripts or autoplay. `detector.json=[]` is the single completed detector result.

Not canonized: inherited eyebrows/kickers or shared-module ordinals. They remain in unchanged business modules and are not durable operator rules. No new source defect is legitimized as a token. Pre-existing global PRODUCT.md, DESIGN.md and .impeccable/design.json remain missing and unmodified.

The roadmap `docs/roadmap-next-steps-20261025.md` freezes aesthetic expansion at eight. Next priorities are reviewed consolidation preserving dirty user work, authorized upstream facts, capability/media edge cases, traceable generation/review and a measured pilot. Those are planned work, not current integration claims.

## Observed source and media hashes

Paths below are relative to `.tools/claude-worktrees/restaurant-engines8-20261025`; SHA-256 is over existing bytes. The files were read only during this documentation pass.

| Path | SHA-256 |
|---|---|
| `src/components/composition/StyleEngineSite.astro` | `7a273383c2b8db1a4950fbf586e0a864c6a74568c6d797c4d626574c27e366e1` |
| `src/design/style-engines.ts` | `f2d83ee2c36e3fae0dd8067562092a2213c78e2e49d3d2bb738d6745edc62be9` |
| `src/design/engine-base.css` | `004d0b7a0438ab42b027d77e109879dc6a4f816d218dbd2b082f0ff262ac404d` |
| `src/design/engine-market.css` | `96ea780e274776959f5099da76952bc16bf9b98df5eafb77ea477ea2ea5daf0a` |
| `src/design/engine-marea.css` | `f8dfb2cc70e382d1e38fceb9e3fc33eb0df9102f0ac640eb3796c2e8b391a42f` |
| `src/design/engine-riso.css` | `528d39c31abb7df607bdf09a0630304b479ae1d3473dddb397ed75da518aeca6` |
| `src/design/engine-indice.css` | `91ad3e35afd5ee90d18151f2934afce7d82ce6c0a836d6c198a9137024e194cb` |
| `src/design/catalogue.css` | `e07db240732333c2d268779acc8832427acdbf90ea954c81c8bc81d65c748bdd` |
| `src/design/dish-detail.css` | `ca5dcc051efeaefbe16946f9ce0ab76620c3cd7a213cc0cf98435357182aab7e` |
| `src/design/restaurant-catalogue.ts` | `a8afc132011242a921a9e0aa72257ac172799ff62e6051489123ac6fb5a31e26` |
| `src/components/composition/MenuCollection.astro` | `1095776d1ee2ad2b3c65a51bc6e8b4b5afe535c94eae9176eb901af9193ee206` |
| `src/components/composition/CatalogueSelection.astro` | `de1f126bb9302a7120b3a87ee2acca41ff61f48e4e66867d9e122453ad8e8843` |
| `src/components/composition/DishDetail.astro` | `1bc6895ecd0baa747cf4f14477acfdef4e7c23c3f0ef6a2d0441af31c39c01cb` |
| `src/media/engine-media.ts` | `8f8da9f75d8ba3132c19812c2e6cc6075382943c3a84639ca54234183614d75d` |
| `data/content/demo-catalogue-40.json` | `cab5d68e110b85754c43f41d6526272befb252ab9c0fc59a5cf3e4c033364be4` |
| `data/media/demo-v1/engines8-20261025.json` | `8135df753c3bfc11f1cf5c1059be2e3d59641ae685227b1676d6cea320deb079` |
| `public/fonts/b3-artistic/bodonimoda.woff` | `3ac63a7baa08bb7af148929baf5288b31bc2b3c3a14763ab0ca6541b8ab33ae3` |
| `public/fonts/b3-artistic/dmsans.woff` | `d137b1c03916ead1adf9d604a6a020f4716a5a367fb09cc53e645f412922a173` |
| `public/fonts/b3-artistic/syne.woff` | `db4c864d91aaa1b709d97cafebf862a28b7893747b030885436454cbe7813301` |

Documentation verification: YAML contains the actual source color-role assignments for all four new operators; JSON schemaVersion is 2, it has no duplicated primitive token group, and all component examples are self-contained visual excerpts. Source/media hashes were rechecked after writing and matched.
