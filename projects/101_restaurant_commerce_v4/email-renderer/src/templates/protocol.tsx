import { TemplateFonts } from "../fonts";
// Adapted from pinned upstream 03-Protocol; original/MIT notice in vendor.
import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
import { ditherTailwindConfig as theme } from "../../vendor/react-email/03-Protocol/theme";
export default function Template(p: EmailProps) {
  return (
    <Shell
      p={p}
      config={theme}
      fonts={<TemplateFonts p={p} />}
      background="#131313"
    >
      <Container className="mx-auto w-full max-w-[640px] bg-bg text-fg">
        <Section className="border-stroke border-b border-solid px-6 py-10">
          <Brand p={p} />
          <Text className="font-11 font-mono text-fg-3 uppercase mt-8 mb-0">
            {p.content.label}
          </Text>
        </Section>
        <Section className="px-6 pt-14 pb-12">
          <Heading
            className="font-56 mobile:font-40 font-condensed uppercase text-fg m-0 mb-8"
            style={{ fontWeight: 400, overflowWrap: "anywhere" }}
          >
            {p.content.title}
          </Heading>
          <Section className="mb-10">
            <Photo p={p} />
          </Section>
          <Words p={p} className="text-fg-2" />
          <Section className="pt-8 pb-10">
            <Action p={p} background="#FFFFFF" color="#131313" />
          </Section>
          <Terms p={p} />
        </Section>
        <Section className="border-stroke border-t border-solid px-6 py-10">
          <Footer p={p} color="#C4C4C4" />
        </Section>
      </Container>
    </Shell>
  );
}
