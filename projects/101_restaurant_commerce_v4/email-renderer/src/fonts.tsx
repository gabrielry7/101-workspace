import * as React from "react";
import { Font } from "react-email";
import type { EmailProps } from "./contract";
import { effectiveChassis } from "./chassis";
export function TemplateFonts({ p }: { p: EmailProps }) {
  const families: [
    string,
    string,
    number[],
    React.ComponentProps<typeof Font>["fallbackFontFamily"],
  ][] = [];
  if (p.template_id === "arcane")
    families.push([
      "Instrument Serif",
      "instrument-serif",
      [400],
      ["Georgia", "serif"],
    ]);
  if (p.template_id === "protocol")
    families.push(
      ["IBM Plex Mono", "ibm-plex-mono", [400], ["monospace"]],
      [
        "IBM Plex Sans Condensed",
        "ibm-plex-sans-condensed",
        [400],
        ["Arial", "sans-serif"],
      ],
    );
  if (p.template_id === "studio")
    families.push(["Geist", "geist", [400, 500, 600], ["Arial", "sans-serif"]]);
  const extra = Object.values(effectiveChassis(p).typography).map(
    (t) => t?.fontFamily,
  );
  for (const [family, file, weights, fallback] of [
    ["Instrument Serif", "instrument-serif", [400], ["Georgia", "serif"]],
    ["IBM Plex Mono", "ibm-plex-mono", [400], ["monospace"]],
    [
      "IBM Plex Sans Condensed",
      "ibm-plex-sans-condensed",
      [400],
      ["Arial", "sans-serif"],
    ],
    ["Geist", "geist", [400, 500, 600], ["Arial", "sans-serif"]],
  ] as typeof families) {
    if (
      extra.includes(family as never) &&
      !families.some((f) => f[0] === family)
    )
      families.push([family, file, weights, fallback]);
  }
  // React Email Font also emits a global fallback: keep Inter last for body copy.
  families.push(["Inter", "inter", [400, 500, 600], ["Arial", "sans-serif"]]);
  return (
    <>
      {families.flatMap(([family, file, weights, fallback]) =>
        weights.map((weight) => (
          <Font
            key={family + weight}
            fontFamily={family}
            fallbackFontFamily={fallback}
            fontWeight={weight}
            fontStyle="normal"
            webFont={{
              url:
                p.font_base_url + file + "-latin-" + weight + "-normal.woff2",
              format: "woff2",
            }}
          />
        )),
      )}
    </>
  );
}
