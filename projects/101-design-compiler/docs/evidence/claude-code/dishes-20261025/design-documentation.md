# Restaurant menu-to-detail extension — local evidence

Recorded 2026-10-25 from the finished isolated worktree `.tools/claude-worktrees/restaurant-dishes-20261025`. This is an ordinary extension of four established worlds: four traditional menu lists and sixteen static dish pages. It establishes no new identity, global token, or whole-system approval.

## Inheritance and comparison

| World | Incumbent visual system retained | Local application |
| --- | --- | --- |
| 01 | Bone paper, terracotta, Georgia display with sans-serif body | Printed ledger rows, serif dish names, dotted price leaders |
| 02 | Vermilion, Impact/Arial Narrow condensed display | Heavy rules, uppercase names, accent prices |
| 03 | Black, ember, Syne with DM Sans; existing desktop left rail | Dark list, ember actions/prices; narrower screens release uppercase and wrap the name above its price |
| 04 | Paper, plum, Bodoni Moda with DM Sans | Serif names, italic categories, restrained dividers |

The new styles consume incumbent `--paper`, `--ink`, `--muted`, `--line`, `--display`, `--action`, `--on-action`, `--accent-text`, `--mark`, and `--focus` variables. Menu names are approximately 1.25–2.25rem by world/viewport; detail titles use a responsive display scale, with a constrained container-based scale for 03. These are local component treatments, not a new normative type ramp.

Direct SHA-256 comparison against `.tools/claude-code/dish-resources-20261025/accepted/` found `experience-refinement.css`, `artistic-ember.css`, and `artistic-plate.css` byte-identical. That accepted snapshot does not contain the older `experience.css`, `rich-experience.css`, or `depth-experience.css`; no direct snapshot comparison is claimed for those files. `accepted.json` identifies the reviewed source selection. The output protection evidence below supplies the broader regression boundary.

## Local contracts

- `MenuCollection.astro` keeps semantic module, offering, fact and scope IDs, required flags, ordering, and existing search/category hooks. A category heading precedes each dish name; the name and “Ver plato” are ordinary links. Full facts live on the detail page.
- `DishDetail.astro` shows the bound name, category, price, description, photograph and labeled `dt`/`dd` ingredients, allergens, calories and currency. Values remain fictional bound data; the renderer invents no recipe or nutrition facts. Fiction notices and credits remain visible.
- `dish-routes.ts` accepts only candidates 01–04 and `pizza`, `pasta`, `salad`, `dessert`. `[dish].astro` validates offerings and statically emits `/b3/candidate-0N/carta/<dish>/`. Unknown paths are rejected. Breadcrumbs return to the menu; sibling links reach other dishes; “Elegir este plato” forwards the dish ID to the existing selection demonstration.
- `ExperienceComposition.astro` conditionally appends menu/detail CSS. Existing navigation and footer remain shared; dish navigation identifies the collection as its parent. Detail layouts stack on narrow screens and use two columns from 900px. Links retain visible focus and at least 44px targets; the main action is at least 48px.
- Images continue through the admitted media handle and `ContextualImage`; optional video comes only from `dishVideo()`. Video uses native controls, manual playback, `preload="none"`, a poster, and no source audio, with illustrative-media disclosure and attribution. The pinned media package contains 20 assets/48 usages. Local hover motion respects reduced-motion preference. No new client JavaScript, framework, or dependency was added.

## Recorded verification and limits

`final-audit/audit.json` passes 100/100 combinations: 20 routes at 360, 390, 768, 1024 and 1440px, with 40 final desktop/mobile contact sheets. `final-check-build.json` and `final-check.log` record successful checks/build: 322 checked files, zero errors/warnings/hints, 184 built pages. `protection-final.json` reports 164 other old HTML pages and 18 old client assets unchanged, four changed menus and sixteen new details. `navigation-smoke.json` passes native keyboard navigation/video playback, 20 preview URLs with exact output bytes, and unknown-path 404 checks.

The recorded test run passes 432/433; the sole failure is the unchanged historical H8 mismatch. The UI detector returned no findings on seven targets. The independent finish review examined first and final contact sheets and marked six requested fixes resolved: responsive 03 text, definition labels, optional prop typing, required metadata, category hierarchy, and Unicode icon removal in new components. Its SHIP verdict is limited to that reviewed flow/fix set. Geometry/contrast checks are not full WCAG certification; warm local playback is not cold mobile-network performance certification.

Root `PRODUCT.md`, `DESIGN.md`, and `.impeccable/design.json` are absent: a pre-existing documentation gap, left unrepaired within this narrow extension. No direction/quality-bar cards or approved generated composition exist for this code-led flow. No global system files were created or changed by this documentation pass, and no inherited defect or documentation gap is canonized as a future design rule.
