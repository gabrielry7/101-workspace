import { bone, type, classes } from "../chassis";
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
            "stage",
            "bg-bg-2 px-10 mobile:px-6 pt-10 pb-6",
          )}
          {...bone(p, "stage")}
        >
          <Brand p={p} />
        </Section>
        <Section
          className={classes(
            p,
            "intro",
            "bg-bg-2 border-stroke border-b border-solid px-10 mobile:px-6 pt-10 pb-16",
          )}
          {...bone(p, "intro")}
        >
          <Text className="font-13 text-fg-2 mt-0 mb-6" {...type(p, "label")}>
            {" "}
            {p.content.label}
          </Text>
          <Heading
            className={classes(
              p,
              "heading",
              "font-64 mobile:font-48 text-fg m-0 font-serif",
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
        </Section>
        <Photo p={p} width={640} />
        <Section
          className={classes(p, "content", "px-10 mobile:px-6 pt-16 pb-12")}
          {...bone(p, "content")}
        >
          <Words p={p} className="text-fg-2" />
          <Section className="mt-10 mb-12">
            <Action p={p} background="#F9F9ED" color="#300610" />
          </Section>
          <Terms p={p} />
        </Section>
        <Section
          className={classes(
            p,
            "footer",
            "bg-bg-3 text-fg-inverted px-10 mobile:px-6 py-12",
          )}
          {...bone(p, "footer")}
        >
          <Footer p={p} color="#300610" />
        </Section>
      </Container>
    </Shell>
  );
}
