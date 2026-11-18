# 101 campaign email rendering

React Email6.11.16 renders HTML and plain text. Python remains the authority for
business permissions, recipients, immutable revisions, approval, scheduling,
tracking, unsubscribe, costs and the existing Amazon SES adapter.

## Develop and build

Requires Node22+ and the existing npm package manager:

```sh
cd projects/101_restaurant_commerce_v4/email-renderer
npm ci
npm run typecheck
npm run build
npm run email
```

The official React Email development preview runs at `http://localhost:3000` and
uses `emails/*.tsx` with conspicuously fictional preview properties. It is separate
from the normal authenticated101campaign editor and is not the delivery service.
`@react-email/ui` is that developer preview, not the uninstalled visual editor.
No Resend sending SDK, account or provider replaces SES.

The package lock pins rendering, development preview and font dependencies.
`npm run build` produces a bundled `renderer.cjs`, an asset/version manifest and
full license notices under `src/world_model/restaurant_commerce/email_runtime`.
The Python wheel includes those files and the licensed fonts. Production needs the
built wheel plus a Node22+ executable; it does not need npm, a Node service,
`node_modules`, a TypeScript loader or the developer preview. Build artifacts before
packaging; never run npm/downloads during a campaign request. `CAMPAIGN_EMAIL_NODE`
can name an explicit server-controlled Node executable; otherwise PATH is used.

## Where code lives

- `src/contract.ts`: strict typed JSON inputs. Copy, brand, media, layout identity,
  font base URL and personalization are separate.
- `src/templates/`: six separate TSX components. Future templates are added here,
  then registered explicitly in `src/index.tsx` and the Python allowlist.
- `src/parts.tsx`: small shared brand/copy/photo/CTA/footer pieces. Layout ordering,
  typography, colors and surfaces remain separate in the family components.
- `src/fonts.tsx`: locally served, licensed source-family fonts. No system fonts
  are redistributed; no external font request is needed in the campaign preview.
- `emails/`: official developer-preview wrappers and synthetic properties.
- `vendor/react-email/`: byte-identical original selected templates, themes, fonts,
  source manifest, commit and MIT notice, separate from101adaptations.
- Python `campaign_react_email.py`: validation, source/version binding, bounded
  JSON stdin/stdout subprocess, manifest checks and read-only comparisons.

## Included designs and source scope

|101design|Pinned official reference|Retained visual structure|
|---|---|---|
|Clásico|Existing101campaign renderer|Original editorial header, copy, ordering action and permission footer|
|Barebone|01-Barebone/feature-announcement|Inset rounded pale card and rounded action|
|Matte|02-Matte/feature-announcement|Raised green editorial card, outline and split information panel|
|Protocol|03-Protocol/feature-announcement|Dark rules, condensed uppercase heading, monospaced label|
|Arcane|04-Arcane/promo|Burgundy blocks, Instrument Serif heading and pale footer|
|Studio|05-Studio/promo|Centered heading/image/action and a separate pale information panel|

These are shortened single-message adaptations of one selected design per family,
not every upstream template or every section of the demonstrations. Missing product
cards, testimonials, addresses, offers and social accounts are omitted rather than
invented. No upstream demonstration product photographs are merchant assets.
Optional campaign images use owner-supplied absolute PNG/JPEG/GIF URLs and descriptions.
Brand/name/logo and optional accent/base font come from the existing frozen brand
snapshot. The actual black logo is displayed on a light plate in the dark families.
A configured accent gets an appropriate black/white CTA foreground for readability.
Merchant creative fonts remain distinct from the101UI's Inter typography.

Upstream source: https://github.com/resend/react-email/tree/beda35bb12cad36c202534601591cc98c651c8c9/apps/demo/emails
Official collection: https://react.email/templates
Manual setup/render: https://react.email/docs/getting-started/manual-setup and https://react.email/docs/utilities/render
The official agent skill was installed from the same pinned repository.

## Runtime and approval contract

Python sends validated structured input to a fixed Node bundle with a12s timeout,
192MB Node heap ceiling and bounded input/output. Submitted strings are React text,
never template source, code, HTML or commands. Node returns `{html,text,subject}`;
plain text is made by React Email's `toPlainText`, preserving heading case.
Python never passes credentials or the provider environment to the renderer.

The saved revision contains the selected template/version, image URL/description,
CTA text, frozen business branding, public origin and a renderer identity combining
bundle and font hashes. A design change creates a new digest and requires fresh
approval. Approval preflights rendering before committing. Dispatch checks the
approved identity and renders actual recipient/tracking/unsubscribe values before
crossing the existing provider boundary. Local failures leave eligible jobs queued
with zero sending attempts; there is no ambiguous provider submission to retry.

The template selector can compare the same saved campaign read-only. Unsaved
comparisons clear the review checkbox and disable approval/scheduling. Returning
to the saved design restores the actual saved rendering path. Saving a comparison
uses a digest-checked design-only endpoint that preserves copy, promotion binding,
audience, schedule and budget. Existing clients omitting the new field retain the
saved design instead of resetting it.

Legacy revisions keep `honorato-editorial-v1` and their Python renderer. WhatsApp
and SMS do not invoke Node. The explicit “Clásico anterior” choice remains a recovery
path; the system never silently substitutes it for an approved React Email design.
A failed renderer leaves a saved draft readable/editable with an explicit unavailable
preview, while approval is blocked. No schema migration is required.

Remote image URLs are frozen, not their externally hosted bytes. A content-addressed
owned asset/CDN connection remains a later media-library integration. Production
activation still needs the existing verified HTTPS origin/sender/provider controls;
this integration does not enable real sending. Ordinary browser rendering does not
prove every Gmail/Outlook client is visually identical. Original fonts and CSS have
fallbacks; the actual desktop/mobile checks and limitations are retained in the
World Model React Email implementation report.
