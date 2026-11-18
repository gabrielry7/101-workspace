import { TemplateFonts } from "../fonts";
// Adapted from pinned upstream 02-Matte; original/MIT notice in vendor.
import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
import { collageTailwindConfig as theme } from "../../vendor/react-email/02-Matte/theme";
export default function Template(p: EmailProps) {
  return (
    <Shell
      p={p}
      config={theme}
      fonts={<TemplateFonts p={p} />}
      background="#FBFCFB"
    >
      <Container className="mx-auto w-full max-w-[640px] px-4 pt-16 mobile:pt-6 pb-6">
        <Section className="shadow-collage-card rounded-[8px]">
          <Section className="bg-bg border-stroke rounded-[8px] border border-solid">
            <Photo p={p} width={608} />
            <Section className="mobile:px-6 px-10 pt-12 pb-14 text-left">
              <Brand p={p} />
              <Text className="font-13 text-fg-3 mt-8 mb-4">
                {p.content.label}
              </Text>
              <Heading
                className="font-48 mobile:font-32 text-fg m-0 mb-8 font-sans"
                style={{ fontWeight: 400, overflowWrap: "anywhere" }}
              >
                {p.content.title}
              </Heading>
              <Words p={p} className="text-fg-2" />
              <Section className="pt-4">
                <Action p={p} background="#103B05" color="#FBFFF9" />
              </Section>
            </Section>
            <Section className="bg-bg-2 border-stroke border-t border-solid px-10 mobile:px-6 py-8">
              <Terms p={p} />
            </Section>
          </Section>
        </Section>
        <Section className="px-6 py-10">
          <Footer p={p} color="#194A07" />
        </Section>
      </Container>
    </Shell>
  );
}
