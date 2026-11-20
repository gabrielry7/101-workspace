# % Arabica locations · private reference reproduction

Date: 2026-11-17. Version: 0.1.1, visual review pending.
User requests a faithful copy of https://arabica.com/en/locations/ first;
conversion into section bones is explicitly deferred.

## Outcome and scope

Reproduce the locations section in a private local Astro preview: restrained
header, title, monochrome map, floating region list and counts, numbered country
and city pins, coming-opening pins, back navigation and the reference's new-store
cards. Preserve its world → country → city navigation, camera framing, spacing,
type, colours, map controls and responsive map/list ordering. Branch-detail links
may open the original official page; reproducing shop, checkout, entire branch
pages and the rest of the brand website is outside this section's scope.

- R1: Inspect the actual reference at desktop/mobile and country/city levels;
  retain dated source evidence privately. Do not infer unobserved interactions.
- R2: Recreate the observed composition and typography, including the 560 px and
  780 px responsive transitions, using the existing Astro application.
- R3: All retained regions/countries/cities work through the hierarchy, including
  markers, counts, explicit back links and browser back/forward. Keep reference
  facts and opening states as dated source observations, not new business claims.
- R4: Use one map instance, neutral cartography, geographic marker anchoring,
  visible map attribution and usable zoom/pan. Preserve scroll-wheel behaviour.
  The original uses Google Maps; the user selected the same provider for this
  copy and deferred provider binding for the future bone. No
  third-party key may be reused and the existing paid-trial cap may not be reset.
  Preserve Honorato's existing ledger and the cloud daily quota. The user
  explicitly authorized ten additional reference loads on 2026-11-19, with the
  same US$1 total ceiling and ten-load daily quota. Retain a separate private
  reference ledger and the permission record; never reset either ledger.
- R5: Keyboard navigation, focus, reduced motion, font fallback and a useful
  map-unavailable state retain the region/city/branch navigation.
- R6: Original media/fonts/snapshots and their local build stay under ignored
  `.tools/arabica-locations-reference/`; no public deployment or redistribution.
  Commit and push only own implementation, tooling, spec and verification summary.
- R7 (user correction): Real mouse drag, wheel zoom and one-finger touch must
  move the map inside an embedded preview as well. Preserve the user's camera
  across layout resizing; reframe only when choosing another location. Page
  scrolling remains possible outside the map. Verify with actual input events.

## Acceptance scenarios

1. Open world view at 1440×1000 and 390×844; compare original and copy natively.
2. Select Japan → Kyoto and United Kingdom → London using panel and map pins;
   verify corresponding groups, branches, camera and back/history behaviour.
3. Compare both sides of breakpoints, tablet and a narrow viewport; no horizontal
   document overflow or broken words. Check selected links and touch ordering.
4. Exercise zoom, pan, keyboard, reduced motion and blocked vector requests.
5. Missing/invalid retained input fails preparation rather than inventing places.

## Status boundaries

This is a reference reproduction, not an approved bone, generic location family,
production business binding or permission to publish reference brand assets.
Record any provider/media/visual differences in the delivery evidence.
