import * as React from "react";
import Template from "../src/templates/arcane";
import { fixture } from "../src/fixture";
import type { EmailProps } from "../src/contract";
export default function Email(p: EmailProps) {
  return <Template {...p} />;
}
Email.PreviewProps = { ...fixture, template_id: "arcane" } satisfies EmailProps;
