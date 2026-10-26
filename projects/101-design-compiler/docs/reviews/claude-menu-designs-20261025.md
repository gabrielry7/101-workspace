# Four distinct carta designs — 2026-10-25

Implemented with the real Claude Code CLI, session db3a7260-b3bd-4f75-b04a-28b7d2f09b20: three successful same-session exchanges (art direction, implementation, concrete visual correction). Codex owns the review. Retained isolated worktree: `C:/Users/gabri/101-design-compiler/.tools/claude-worktrees/restaurant-menus-20261025`; preview at http://127.0.0.1:4324/b3/. No commit, merge or push.

| Carta | Result | Preview |
|---|---|---|
| 01 WhiteInk | Printed menu, continuous photo strip, readable name/price rows | [Open](http://127.0.0.1:4324/b3/candidate-01/carta/) |
| 02 Vermilion | Newspaper lead and three secondary columns; compact mobile rows | [Open](http://127.0.0.1:4324/b3/candidate-02/carta/) |
| 03 Brasa | Wide cinematic images and Syne captions; full-word mobile titles with price below | [Open](http://127.0.0.1:4324/b3/candidate-03/carta/) |
| 04 Herbario | Centered specimen photographs, Bodoni names, quiet vertical rhythm | [Open](http://127.0.0.1:4324/b3/candidate-04/carta/) |

Official current menu research: [LUCA A La Carte](https://a.storyblok.com/f/285210/x/e504dadf0c/alc211026.pdf), [Osip tasting sheet](https://osiprestaurant.com/wp-content/uploads/2026/08/Tasting-A6-2.pdf), [Padella](https://www.padella.co/) information architecture and [ANG menu](https://restaurangang.se/menu/). LUCA and Osip PDF pages were downloaded, rasterized and visually reviewed, then supplied privately for internal Claude design analysis under the user's explicit request. Padella's local capture lacked CSS, so no visual conclusions came from that screenshot. KOL exposed no usable menu; Aponiente returned 403. No restaurant reference assets, logos, food copy, prices or policies entered runtime. Full research notes are in the evidence folder.

Existing shared Astro renderer remains. A single MenuCollection with four layout operators and one conditionally emitted raw stylesheet serve only the carta pages. ContextualModule, pedidos, JS bundles, media registry and all business facts stay unchanged. Reviewed accepted uncommitted source was explicitly selected and staged from restaurant-artistic-20261025; the new worktree initially started at HEAD. Main user work and unrelated dirty files were not copied or overwritten.

Verification: build 168 pages; Astro/TypeScript checks 317 files, zero errors/warnings/hints. Existing suite 429/430 passes; the sole unchanged historical H8 negative assertion expects LOCK_AUDIT_FILE_MISMATCH but receives LOCK_BROWSER_MISMATCH. It remains a failure and was not weakened. Final CSS-only correction was rebuilt successfully; no functional source changed after type/test checks.

Browser: all 20 route/viewport combinations at 360,390,768,1024,1440 pass content/module/fact preservation, original photo/alt binding, layout overflow, computed contrast/readability, target size, expanded details, filtering, empty/reset states, keyboard skip/navigation and query-linked selections. Four static no-JS checks preserve all dishes and native details with tools hidden. Zero external requests, HTTP errors or JS exceptions. Minimum audited text contrast 5.40. Additional explicit checks confirm no photo/text overlap or fragmented name words. The inherited generic audit initially missed actual photo overlap in 01 and broken mobile words in 03; Codex caught both visually and sent precise feedback, Claude corrected them, then the final captures were reviewed. Detector returned []. These are local computed/browser checks, not a full WCAG or cold-mobile-network certification.

Scope protection: exactly the four carta HTML files changed; all other 164 outputs are byte-identical to the approved version. All 18 existing _astro assets are byte-identical, including client JS. No new client code, fonts, media downloads or dependencies. HTML increases by approximately 15 KiB per carta for the conditional styles.

Evidence: [review receipt](../evidence/claude-code/menus-20261025/review.json), [final browser audit](../evidence/claude-code/menus-20261025/verification/final-audit.json), [screenshots](../evidence/claude-code/menus-20261025/captures/), source snapshots and genuine CLI prompts/responses. External reference screenshots remain private under .tools; only our own product captures are exported.
