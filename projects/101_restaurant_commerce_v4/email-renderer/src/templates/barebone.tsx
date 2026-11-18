import { TemplateFonts } from "../fonts";
// Adapted from pinned upstream 01-Barebone; original/MIT notice in vendor.
import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
import { barebonesBoxedTailwindConfig as theme } from "../../vendor/react-email/01-Barebone/theme";
export default function Template(p: EmailProps) {
  return (
    <Shell
      p={p}
      config={theme}
      fonts={<TemplateFonts p={p} />}
      background="#F3F4F6"
    >
      <Container className="mx-auto w-full max-w-[640px]">
        <Section className="bg-bg px-6 mobile:px-3 py-6">
          <Section className="px-6 py-6">
            <Brand p={p} />
          </Section>
          <Section className="bg-bg-2 rounded-[10px] px-8 mobile:px-5 py-14 text-left">
            <Text className="font-13 text-fg-3 mt-0 mb-4">
              {p.content.label}
            </Text>
            <Heading
              as="h1"
              className="mt-0 mb-6 font-40 font-sans text-fg"
              style={{ overflowWrap: "anywhere" }}
            >
              {p.content.title}
            </Heading>
            <Section className="mb-6">
              <Photo p={p} />
            </Section>
            <Words p={p} className="text-fg-2" />
            <Section className="pt-4 pb-6">
              <Action p={p} background="#14171E" color="#FFFFFF" rounded={8} />
            </Section>
            <Terms p={p} />
          </Section>
          <Section className="px-6 py-10">
            <Footer p={p} color="#43454B" />
          </Section>
        </Section>
      </Container>
    </Shell>
  );
}
