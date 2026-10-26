---
name: "Eight restaurant operators - preliminary local collection"
description: "Source-derived record for proposed operators 05-08; original four are read-only references."
colors:
  market-paper: "#f6f7f1"
  market-ink: "#17211c"
  market-muted: "#4a5750"
  market-line: "#d3d8cc"
  market-control: "#6b7a70"
  market-accent: "#1e4d3a"
  market-accent-text: "#1e4d3a"
  market-mark: "#e8a317"
  market-action: "#1e4d3a"
  market-on-action: "#f6f7f1"
  market-surface: "#e9eee3"
  market-focus: "#1e4d3a"
  market-footer-bg: "#14352a"
  market-footer-ink: "#f6f7f1"
  market-footer-muted: "#d6e0d6"
  marea-paper: "#eef5f3"
  marea-ink: "#0b2b3a"
  marea-muted: "#3f5a66"
  marea-line: "#c3d6d3"
  marea-control: "#5f7f86"
  marea-accent: "#0e5f66"
  marea-accent-text: "#0e5f66"
  marea-mark: "#f2c9a5"
  marea-action: "#0b2b3a"
  marea-on-action: "#eef5f3"
  marea-surface: "#e0ece9"
  marea-focus: "#0e5f66"
  marea-footer-bg: "#0b2b3a"
  marea-footer-ink: "#eef5f3"
  marea-footer-muted: "#c9dcdd"
  riso-paper: "#f3eedf"
  riso-ink: "#14183a"
  riso-muted: "#3e4570"
  riso-line: "#b9b49f"
  riso-control: "#5a5f8a"
  riso-accent: "#1d3fbb"
  riso-accent-text: "#1d3fbb"
  riso-mark: "#ffd21f"
  riso-action: "#1d3fbb"
  riso-on-action: "#fff"
  riso-surface: "#fbe27a"
  riso-focus: "#1d3fbb"
  riso-footer-bg: "#1d3fbb"
  riso-footer-ink: "#fff"
  riso-footer-muted: "#dce3ff"
  indice-paper: "#e9ece4"
  indice-ink: "#101410"
  indice-muted: "#444b44"
  indice-line: "#bfc5b8"
  indice-control: "#6a7367"
  indice-accent: "#3a5200"
  indice-accent-text: "#3a5200"
  indice-mark: "#c6f432"
  indice-action: "#101410"
  indice-on-action: "#c6f432"
  indice-surface: "#dde2d4"
  indice-focus: "#101410"
  indice-footer-bg: "#101410"
  indice-footer-ink: "#e9ece4"
  indice-footer-muted: "#c5ccbd"
typography:
  market-display:
    fontFamily: "DM Sans, system-ui, sans-serif"
    fontSize: "clamp(2.5rem,6.5vw,5rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-.025em"
  marea-display:
    fontFamily: "Bodoni Moda, Georgia, serif"
    fontSize: "clamp(2.75rem,7vw,5.5rem)"
    fontWeight: 400
    lineHeight: .98
    letterSpacing: "-.015em"
  riso-display:
    fontFamily: "Bodoni Moda, Georgia, serif"
    fontSize: "clamp(3rem,13vw,8rem)"
    fontWeight: 900
    lineHeight: .85
    letterSpacing: "-.03em"
  indice-display:
    fontFamily: "Syne, system-ui, sans-serif"
    fontSize: "clamp(1.875rem,6vw,4.25rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-.02em"
  body:
    fontFamily: "DM Sans, system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.5
  menu-name:
    fontFamily: "DM Sans, system-ui, sans-serif"
    fontSize: "1.1875rem"
    lineHeight: 1.2
  note:
    fontFamily: "DM Sans, system-ui, sans-serif"
    fontSize: ".875rem"
    lineHeight: 1.5
rounded:
  square: "0"
  market-photo: "14px"
  market-chip: "999px"
  marea-arch: "50% 50% 0 0/32% 32% 0 0"
spacing:
  home-gutter: "clamp(1.25rem,4vw,3.5rem)"
  action-gap: ".75rem"
  action-inset: "0 1.5rem"
  menu-row: ".75rem 0 .5rem"
  selection-panel: "2rem"
components:
  market-button-primary:
    backgroundColor: "{colors.market-action}"
    textColor: "{colors.market-on-action}"
    rounded: "{rounded.square}"
    padding: "{spacing.action-inset}"
  marea-button-primary:
    backgroundColor: "{colors.marea-action}"
    textColor: "{colors.marea-on-action}"
    rounded: "{rounded.square}"
    padding: "{spacing.action-inset}"
  riso-button-primary:
    backgroundColor: "{colors.riso-action}"
    textColor: "{colors.riso-on-action}"
    rounded: "{rounded.square}"
    padding: "{spacing.action-inset}"
  indice-button-primary:
    backgroundColor: "{colors.indice-action}"
    textColor: "{colors.indice-on-action}"
    rounded: "{rounded.square}"
    padding: "{spacing.action-inset}"
---

# Design System: Eight restaurant operators - preliminary local collection

## Overview

**Creative North Star: "One menu, four additional entry compositions"**

Local source record of four proposed operators in an eight-option restaurant laboratory; not a globally approved product system. Original 01-04 remain PRELIMINARY_ACCEPTED and read-only. Mercado/Marea are general; Riso/Índice artistic. New 05-08 remain AWAITING_HUMAN_REVIEW. Independent SHIP means ready for preliminary user review only.

Counter, arch, poster and index compositions present the same fictional restaurant and forty-dish journey through the existing shared Astro renderer. The descriptive north star records no new user vote or creative approval.

**Key Characteristics:**
- Four distinct entry compositions over shared semantic modules.
- Ordinary text menu, complete dish facts and local demonstration selection.
- Licensed atmosphere separated from dish evidence; missing media stays missing.

## Colors

Frontmatter preserves each scoped CSS role and hexadecimal value. Never combine the four namespaces into another palette.

### Primary
- **Mercado:** pine actions/accent/focus; marigold mark.
- **Marea:** teal accent/focus, navy actions, sand category fields.
- **Riso:** blue action/display/category bands; yellow poster/mark.
- **Índice:** olive readable accents, charcoal action, lime mark/action text.

### Neutral
Paper, ink, muted, line, control, surface and footer roles retain their source assignments. Marea also uses literal white tile text; Riso alternate rows use `rgb(255 210 31 / .28)`. These are observed treatments, not extra approved palettes.

**The Scoped Palette Rule.** An operator changes presentation; it does not rewrite facts or grant media rights.

## Typography

Home display roles are in frontmatter. All bodies/menu names use self-hosted DM Sans. Variable weight declarations: DM Sans 100-1000; upright Bodoni Moda 400-900 (Marea 400 display, Riso 900); Syne 400-800 (Índice 800). No explicit font-variation-settings is authored. Packet fvar checks confirm these ranges; original fonts/OFL remain frozen.

Menu names are 1.1875rem/1.2, weights Mercado/Marea/Riso/Índice 700/600/700/700. Prices use tabular numerals: DM Sans 1.0625rem at 700/800 for Mercado/Índice; Bodoni 1.25rem at 500/900 for Marea/Riso. Descriptions are 1rem/1.5 up to 46ch; general paragraphs cap at 65ch; notes are .875rem/1.5. Shared taglines retain the existing display-family/important-declaration cascade.

**The Container Reading Rule.** Size the wide Syne face from its actual column: section headings use clamp(1.375rem,9cqi,4.5rem), selection clamp(1rem,6cqi,2rem), and dish names clamp(1.25rem,7cqi,3.25rem). Preserve whole words with normal word-break and no hyphenation.

Shared text-only detail names otherwise use `clamp(1.75rem,11cqi,4rem)`. Compact carta titles at <=760px use the higher-specificity shared `clamp(2.25rem,11vw,2.75rem)` override, rather than the home display ramp.

## Layout

Home gutter is the fluid frontmatter inset; interiors center within 1680px with `clamp(1.25rem,6vw,6rem)` side padding. Header height is 88px desktop/76px mobile; native disclosure navigation has bounded scrolling and stacks at <=760px while quick links hide.

- **Mercado:** 1:1.1 split counter, 4:3 photo, category chips. Stacks <=760px. Only full-width carta gains two columns at >=960px; pedidos remains one catalogue column.
- **Marea:** 1.1:.9 bottom-aligned hero, 3:4 arch capped 36rem; stacks <=760px with arch capped 26rem. Four category columns become two <=960px. Carta stays single-column, max 52rem.
- **Riso:** opposing poster words and three atmosphere plates. At <=760px plates stack, lose rotations, and change from 3:4 to 4:3 photos.
- **Índice:** category word/count plus `clamp(5rem,16vw,12rem)` thumbnail column, reduced to 4.5rem <=480px. Long labels wrap between words; images remain visible on touch/no-JS.

Order layout is 1.5:1 with 4rem gap; <=760px it stacks with selection first/static. Desktop selection sticks at 6.5rem. Expanded names scroll within `min(40vh,20rem)`. Category navigation becomes wrapping links >=600px; menu leaders hide <=480px. Dish facts gain an 8rem label column >=600px; text-only detail layout becomes 5:6 heading/fact columns >=900px.

## Elevation & Depth

Flat color, rules and photographs establish depth; no new card-shadow system. Inherited navigation overlay retains `0 60px 100px #0005`. Marea's second category row uses `inset 0 0 0 2px currentColor`. Riso rotations/blends apply to atmosphere, never dish media.

## Shapes

Square controls/panels dominate. Mercado's photo/chips and Marea's arch use frontmatter radii. Riso uses thick blue dividers/yellow headline backing; Índice straight rules and lime title underlay. These remain operator-specific, not universal corner rules.

## Components

**Actions/fields/navigation:** home actions have 48px minimum height and 2px borders; ghosts are transparent with ink borders, hover underlines. Catalogue controls/category links have 44px minimum height. Focus is 3px with 3px catalogue/dish offset or inherited 4px shared offset. Native skip link, details navigation, breadcrumbs and current-page state persist. Mercado chips hover marigold; Marea tile names underline; Índice rows turn lime on hover/focus-within and restore thumbnail color. Action color transitions .2s ease-out and media filter/transform .35s ease-out occur only under no-preference motion.

**Menu and selection:** forty ordinary text rows in eight groups of five, each with name, price, description and real dish link. Native category/dish links survive no-JS; search/filter/reset and local selection enhance them. State 0 shows empty count/status, state 1 updates count/list/demo total, state 40 keeps every name reachable in the bounded expanded list. Native selection details starts closed; clear restores empty. `?plato=` preserves offering IDs. No order/payment is sent.

**Routes/facts/media:** eleven business routes per operator, including home, carta, pedidos, reservas, historia, visita, preguntas, diario, opiniones, contacto and creditos; plus forty dish details. Detail facts hold ingredients, allergens, fictional calories and currency. The synthetic forty-offering projection preserves original fact IDs and base content; it does not replace source business truth. Only the original four dish media bindings remain admitted; thirty-six new dishes stay text-only. Riso's three licensed overprinted photos and Índice's thumbnails are explicitly atmosphere. Optional dish video is native, manual, muted, playsinline and preload none, with poster/credits; original dish images remain untreated. Pinned route/usage grants, trusted handles, rights/suitability and byte/silence checks remain mandatory.

## Do's and Don'ts

### Do:
- **Do** keep each operator palette and display role scoped to its own routes.
- **Do** preserve whole-word reading, visible keyboard focus, native details and the forty-dish journey.
- **Do** preserve fictional labels, linked credits and media permission checks.
- **Do** use the existing shared renderer and semantic business modules.

### Don't:
- **Don't** treat this local record or reviewer SHIP as human approval or a production Design Lock.
- **Don't** copy atmosphere imagery into dish records or assign the original four dish assets to the new thirty-six.
- **Don't** turn inherited eyebrows, kickers or shared module ordinals into rules for future surfaces.
- **Don't** open a ninth operator before the roadmap's consolidation and authorized-data work.

Not canonized: inherited eyebrows/kickers and shared-module ordinals. Pre-existing missing global PRODUCT.md, DESIGN.md and design.json remain unrepaired. The roadmap freezes aesthetic expansion and prioritizes consolidation, authorized upstream facts, capabilities/media edge cases, traceable generation/review and pilot evidence.
