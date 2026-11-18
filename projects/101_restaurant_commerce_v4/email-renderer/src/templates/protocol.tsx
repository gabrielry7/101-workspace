import { bone, type, classes } from "../chassis";
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
      <Container
        className={classes(
          p,
          "panel",
          "mx-auto w-full max-w-[640px] bg-bg text-fg",
        )}
        {...bone(p, "panel")}
      >
        <Section
          className={classes(
            p,
            "intro",
            "border-stroke border-b border-solid px-6 py-10",
          )}
          {...bone(p, "intro")}
        >
          <Brand p={p} />
          <Text
            className="font-11 font-mono text-fg-3 uppercase mt-8 mb-0"
            {...type(p, "label")}
          >
            {p.content.label}
          </Text>
        </Section>
        <Section
          className={classes(p, "content", "px-6 pt-14 pb-12")}
          {...bone(p, "content")}
        >
          <Heading
            className={classes(
              p,
              "heading",
              "font-56 mobile:font-40 font-condensed uppercase text-fg m-0 mb-8",
            )}
            style={{
              fontWeight: 400,
              overflowWrap: "anywhere",
              ...type(p, "heading").style,
            }}
            data-101-bone="text"
            data-101-bone-role="heading"
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
        <Section
          className={classes(
            p,
            "footer",
            "border-stroke border-t border-solid px-6 py-10",
          )}
          {...bone(p, "footer")}
        >
          <Footer p={p} color="#C4C4C4" />
        </Section>
      </Container>
    </Shell>
  );
}
