import { TemplateFonts } from "../fonts";
// Adapted from pinned upstream 04-Arcane; original/MIT notice in vendor.
import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
import { skinTailwindConfig as theme } from "../../vendor/react-email/04-Arcane/theme";
export default function Template(p: EmailProps) {
  return (
    <Shell
      p={p}
      config={theme}
      fonts={<TemplateFonts p={p} />}
      background="#FFFFFF"
    >
      <Container className="mx-auto w-full max-w-[640px] bg-bg text-fg">
        <Section className="bg-bg-2 px-10 mobile:px-6 pt-10 pb-6">
          <Brand p={p} />
        </Section>
        <Section className="bg-bg-2 border-stroke border-b border-solid px-10 mobile:px-6 pt-10 pb-16">
          <Text className="font-13 text-fg-2 mt-0 mb-6">{p.content.label}</Text>
          <Heading
            className="font-64 mobile:font-48 text-fg m-0 font-serif"
            style={{ fontWeight: 400, overflowWrap: "anywhere" }}
          >
            {p.content.title}
          </Heading>
        </Section>
        <Photo p={p} width={640} />
        <Section className="px-10 mobile:px-6 pt-16 pb-12">
          <Words p={p} className="text-fg-2" />
          <Section className="mt-10 mb-12">
            <Action p={p} background="#F9F9ED" color="#300610" />
          </Section>
          <Terms p={p} />
        </Section>
        <Section className="bg-bg-3 text-fg-inverted px-10 mobile:px-6 py-12">
          <Footer p={p} color="#300610" />
        </Section>
      </Container>
    </Shell>
  );
}
