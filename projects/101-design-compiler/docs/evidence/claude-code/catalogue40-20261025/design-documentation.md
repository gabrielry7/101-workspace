# Forty-dish catalogue — incumbent-system comparison

The request, “Haz de cuenta que no solo son 4 platos sino 40 platos,” is implemented as an ordinary scale extension within the four existing restaurant worlds. This note records the delivered extension; it does not establish a new identity or replace a project design system.

## Preserved visual systems

Compared the current renderer with the accepted source snapshot in `../catalogue40-resources-20261025/accepted/` and its `accepted.json` manifest. The accepted `experience-refinement.css`, `artistic-ember.css`, and `artistic-plate.css` are byte-identical to the worktree versions. Base typography/navigation was also sampled in `experience.css` and `depth-experience.css`.

| World | Incumbent palette and type | Extension expression and navigation |
| --- | --- | --- |
| 01 | Bone paper `#fbf8f2`, ink `#1d1a16`, terracotta `#a5461c`; Georgia display, Arial body | Ledger rows, serif dish names and prices; existing header and navigation retained. |
| 02 | Warm white `#fffbf7`, ink `#2a1511`, vermilion `#b8231a`; Impact/Arial Narrow display, Arial body | Front-page rows, condensed uppercase names and heavier rules; existing masthead navigation retained. |
| 03 | Black `#0b0908`, warm ink `#efe6d8`, ember `#ff6a2b`; Syne display, DM Sans body | Framed, emphatic rows; existing desktop rail and responsive navigation retained. Narrow text-only detail headings use mixed case and column-relative sizing. |
| 04 | Paper `#f3ece0`, plum ink `#2a1020`, wine `#7a1631`; Bodoni Moda display, DM Sans body | Plate-style rows with italic category titles and wine rules; existing centred masthead retained. |

The catalogue inherits existing color, action, focus, surface and display tokens. Its scoped stylesheet adds density, wrapping and responsive behavior; it does not introduce a replacement palette, font family or navigation system. Rows and controls retain flat surfaces, square corners and world-specific rules.

## Extension contracts

- `data/content/demo-catalogue-40.json` and `src/design/restaurant-catalogue.ts` project 40 unique synthetic offerings in eight categories of five. The sealed scenario and original four offerings/facts remain intact. Catalogue SHA-256: `6ee760fadbf0fbfeaf57ac6d37ad0cc41dff93f6ca6e5f9bedd045228bc8f338`.
- Shared `MenuCollection`, `DishDetail`, `CatalogueSelection`, `ExperienceComposition` and artistic pages produce 160 dish pages and a 40-item local selection in the existing Astro renderer. No framework, generator, backend or purchase flow was added.
- Original dishes retain their 16 scoped media routes and pins. The other 36 offerings use text-only detail pages, with explicit fictional ingredient, allergen and calorie disclosures. Existing original-dish videos remain manual native controls, without autoplay or audio, with `preload="none"`; credits and media gates remain operative.
- Category navigation uses native details/anchors: folded on mobile and open on desktop with enhancement. All 40 dishes and their full details remain browsable without JavaScript. Search, filtering and selection require enhancement.
- `catalogue-client.js` is conditionally loaded and uses isolated `data-cat-*` hooks. The compact selection counter mirrors the single legacy selection state. Its native panel defaults closed on narrow layouts and open where space permits; the 40-name list has bounded scrolling. Both `#seleccion` and `#cat-seleccion` open the panel. Detail links return to their category hash, offer three related dishes from that category, and accept new dish IDs in selection queries.

## Verification boundary

`final-audit/audit.json` records 256 rendered checks and 160 complete static fact checks passing before the final scoped summary-span visibility fix. After that fix, `summary-audit/audit.json` passes 60 states (0/1/40 selections, four worlds, five widths), covering painted labels, typography, contrast, overflow and bounded lists; 24 panel captures were refreshed. The fix explicitly restores only the two compact-summary spans hidden by a legacy selector.

`final-check.log` reports 326 files with zero errors, warnings or hints; the release build produces 328 pages. `protection-release.json` confirms 160 unrelated old HTML pages and all 18 old client assets unchanged. `navigation-smoke.json` passes native keyboard/category/detail/selection/clear flows in all worlds; 168 preview URLs serve exact final bytes with HTTP 200, and unknown profile/dish URLs return 404. Full tests: 435/436, with the sole historical H8 mismatch remaining. The earlier detector result was empty; it was not rerun after the final specific span rule.

Four real Claude CLI calls used Claude session `989dd842-6113-46ea-997e-390cd9ede2dc`. Independent review issues were resolved, including the final hidden summary labels, and the final reviewer verdict was SHIP.

Pre-existing documentation drift is not canonized or repaired: `PRODUCT.md`, `DESIGN.md` and the design sidecar are absent. No global documents or identity rules were created for this bounded extension. Existing decorative kickers/glyph conventions are not promoted into new design-system requirements.
