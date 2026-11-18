import * as React from "react";
import { Font } from "react-email";
import type { EmailProps } from "./contract";
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
