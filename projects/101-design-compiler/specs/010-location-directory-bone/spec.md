# Location directory bone

Date: 2026-11-20. Bone `location.directory-map-hierarchy@0.1.0`.
User requests extracting the reviewed Arabica section into bones. The user's
earlier instruction explicitly makes the map an unbound space at this stage.

## Requirements

- B1: Refactor the current Astro reference composition and navigation into one
  reusable component. Retain the reference consumer and its private assets;
  do not create a second competing renderer or change Honorato's location bone.
- B2: Neutral output separates title, map slot, overlaid grouped directory,
  entries/counts/current state, future openings, back action, card rail, individual
  image/title/action slots, pagination and live status. Define parts and owners.
  Remove reference fonts, logo, colours, photos, locations and external services.
- B3: Keep overview → area → locality navigation, history, keyboard focus, active
  selection, independent panel scrolling and touch/manual card scrolling. Preserve
  the drag bug fix: only explicit navigation links change the selected view.
- B4: Desktop overlays the directory on the map; mobile <=780 px orders map then
  directory then rail. Preserve 300 px mobile map, 230 px desktop panel and the
  original rail proportions, while allowing safe text reflow and long words.
- B5: The neutral map is a labelled, provider-independent slot. No map library,
  credentials, real geography, paid initialization or fake geographic interaction
  is needed to inspect this bone. Expose view/marker selection events so the
  existing private Google adapter remains a separate consumer.
- B6: Validate view identity, parent hierarchy, target references, counts and
  action availability. Image/graphic slots accept labels only; real binding still
  belongs to existing media permissions. Astro named render slots are trusted
  caller markup, not a new asset-approval or HTML-input API.
- B7: Native no-JS data fallback, reduced motion, font fallback, forced colours,
  multiple instances and empty/invalid cases remain useful and honest. Synthetic
  workshop inputs must be identified outside the customer-facing section.
- B8: Deliver a local workshop with neutral output, slot anatomy and separated
  identity notes; preserve the private reference beside it through links or
  comparison frames. Commit/push own files only; do not deploy retained media.

## Acceptance

1. Navigate the neutral overview, area and locality, then back/forward; verify
   counts, selection, card media slots and focused keyboard action.
2. Change content and visual skin without changing the section recipe. Verify
   retained reference data can use the same renderer with its original identity.
3. Inspect 360/390/768/1440 widths and both sides of 560 and 780 px; retain whole
   words and no document overflow, including long labels and font fallback.
4. Confirm neutral pages make zero external/provider requests, including after
   all navigation and controls. Map click/drag-like events do not reset selection.
5. Reject duplicate IDs, missing targets, parent cycles, invalid counts, unsafe
   actions and media URLs inserted into placeholder data.

Technical verification is not human visual approval of this new bone.
