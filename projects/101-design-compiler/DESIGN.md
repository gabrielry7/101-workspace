# Visual system · component library workshop

Scope: `/bones/footers/` and Footer 001. Existing approved templates retain their
own visual systems. This document records the built neutral surface; it is not a
new business brand or visual approval.

## Neutral footer

Source: `src/components/bones/footer/footer.css`. Arial/Helvetica/sans-serif,
white paper, #242424 text, #616161 secondary text, #d9d9d9 rules. No source
gradient, brand typeface, frosted finish or copied logo. Generic outlined slots
identify graphics whose identity is intentionally removed.

Desktop structure: 1088 px shell, 32 px gutters; 274 px transition, 448 px
directory and 84 px legal row. Identity occupies 36% before the four link groups.
The large wordmark is intentionally decorative, noninteractive, hidden from
assistive reading and cropped behind the legal row.

Below 992 px identity and directory stack; below 601 px groups become two
columns, actions get 44 px touch geometry and legal links wrap. Those responsive
rules are the proposed bone behavior; the supplied reference is desktop only.
Functional labels use whole words; only the decorative wordmark may crop.

## Operator surface

Mode: Operate. Restrained toolbar, one preview and a measurement sidebar.
View selection switches neutral/reference/comparison. Measurements state their
denominator and method. Magenta part guides and violet insets come from the
existing component-preview owner, never customer markup.

## States and limits

Soon remains readable and does not navigate. Missing cookie integration disables
the action with an accessible explanation. Native focus outlines are visible;
links work without JavaScript. No animation or pointer replacement is added.
The neutral palette is an inspection aid; a business coat must be reviewed with
its real content, fonts and media.
