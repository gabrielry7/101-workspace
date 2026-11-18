import * as React from "react";
import { render, toPlainText } from "react-email";
import { inputSchema, type EmailProps } from "./contract";
import Classic from "./templates/classic";
import Barebone from "./templates/barebone";
import Matte from "./templates/matte";
import Protocol from "./templates/protocol";
import Arcane from "./templates/arcane";
import Studio from "./templates/studio";
export const templates = {
  classic: Classic,
  barebone: Barebone,
  matte: Matte,
  protocol: Protocol,
  arcane: Arcane,
  studio: Studio,
};
export async function renderEmail(input: unknown) {
  const p = inputSchema.parse(input);
  const Component = templates[p.template_id];
  const el = <Component {...p} />;
  const html = await render(el);
  return {
    schema_version: "1",
    template_id: p.template_id,
    html,
    text: toPlainText(html, {
      wordwrap: false,
      selectors: [
        { selector: "h1", options: { uppercase: false } },
        { selector: "h2", options: { uppercase: false } },
        { selector: "h3", options: { uppercase: false } },
      ],
    }),
    subject: p.content.subject,
  };
}
export type { EmailProps };
