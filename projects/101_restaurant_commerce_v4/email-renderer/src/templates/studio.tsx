import { bone, type, classes } from "../chassis";
import { TemplateFonts } from "../fonts";
// Adapted from pinned upstream 05-Studio; original/MIT notice in vendor.
import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
import { techTailwindConfig as theme } from "../../vendor/react-email/05-Studio/theme";
export default function Template(p: EmailProps) {
  return (
    <Shell
      p={p}
      config={theme}
      fonts={<TemplateFonts p={p} />}
      background="#F6F6F6"
    >
      <Container
        className={classes(p, "panel", "mx-auto w-full max-w-[640px]")}
        {...bone(p, "panel")}
      >
        <Section
          className={classes(p, "intro", "bg-fg px-4 py-4 text-center")}
          {...bone(p, "intro")}
        >
          <Text className="m-0 font-14 text-white" {...type(p, "label")}>
            {" "}
            {p.content.label}
          </Text>
        </Section>
        <Section {...bone(p, "stage", { backgroundColor: "#E8E8E8" })}>
          <Section
            className={classes(
              p,
              "intro",
              "px-8 mobile:px-5 pt-10 pb-12 text-center",
            )}
            {...bone(p, "intro")}
          >
            <Brand p={p} center />
            <Heading
              className={classes(
                p,
                "heading",
                "mx-auto mt-10 mb-0 max-w-[480px] font-48 mobile:font-32 font-geist text-fg",
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
            className={classes(
              p,
              "content",
              "bg-white px-10 mobile:px-6 pt-12 pb-14 text-center",
            )}
            {...bone(p, "content")}
          >
            <Action
              p={p}
              background="#FFFFFF"
              color="#332C2C"
              rounded={8}
              border="1px solid #E8E9E9"
            />
            <Section className="mt-10 text-left">
              <Words p={p} className="text-fg-2" />
            </Section>
          </Section>
        </Section>
        <Section className="px-8 mobile:px-4 pt-8 pb-12">
          <Section
            className={classes(
              p,
              "footer",
              "bg-bg-4 rounded-[10px] px-10 mobile:px-6 py-10",
            )}
            {...bone(p, "footer")}
          >
            <Terms p={p} />
          </Section>
          <Section
            className={classes(p, "footer", "px-6 pt-10")}
            {...bone(p, "footer")}
          >
            <Footer p={p} color="#726A6A" />
          </Section>
        </Section>
      </Container>
    </Shell>
  );
}
