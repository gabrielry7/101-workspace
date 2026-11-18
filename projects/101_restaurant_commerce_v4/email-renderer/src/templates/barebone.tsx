import { bone, type, classes } from "../chassis";
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
      <Container
        className={classes(p, "panel", "mx-auto w-full max-w-[640px]")}
        {...bone(p, "panel")}
      >
        <Section
          className={classes(p, "stage", "bg-bg px-6 mobile:px-3 py-6")}
          {...bone(p, "stage")}
        >
          <Section className="px-6 py-6">
            <Brand p={p} />
          </Section>
          <Section
            className={classes(
              p,
              "content",
              "bg-bg-2 rounded-[10px] px-8 mobile:px-5 py-14 text-left",
            )}
            {...bone(p, "content")}
          >
            <Text className="font-13 text-fg-3 mt-0 mb-4" {...type(p, "label")}>
              {p.content.label}
            </Text>
            <Heading
              as="h1"
              className={classes(
                p,
                "heading",
                "mt-0 mb-6 font-40 font-sans text-fg",
              )}
              style={{ overflowWrap: "anywhere", ...type(p, "heading").style }}
              data-101-bone="text"
              data-101-bone-role="heading"
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
          <Section
            className={classes(p, "footer", "px-6 py-10")}
            {...bone(p, "footer")}
          >
            <Footer p={p} color="#43454B" />
          </Section>
        </Section>
      </Container>
    </Shell>
  );
}
