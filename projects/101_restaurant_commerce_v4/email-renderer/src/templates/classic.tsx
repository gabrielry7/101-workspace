import * as React from "react";
import { Container, Section, Text, Heading } from "react-email";
import { Shell, Brand, Words, Photo, Action, Terms, Footer } from "../parts";
import type { EmailProps } from "../contract";
export default function Template(p: EmailProps) {
  return (
    <Shell p={p} background="#f4efe7" font="Georgia,serif">
      <Container
        style={{
          maxWidth: 600,
          backgroundColor: "#fffdf8",
          color: "#27392d",
          border: "1px solid #ddd6c9",
          margin: "24px auto",
        }}
      >
        <Section
          style={{ padding: "32px 28px", borderBottom: "1px solid #ddd6c9" }}
        >
          <Text style={{ fontSize: 11, letterSpacing: 2 }}>
            {p.content.label}
          </Text>
          <Brand p={p} />
          <Text style={{ fontSize: 13 }}>
            Una invitación a volver a la mesa.
          </Text>
        </Section>
        <Section style={{ padding: "32px 28px" }}>
          <Heading
            style={{
              fontSize: 34,
              lineHeight: "1.15",
              fontWeight: 400,
              overflowWrap: "anywhere",
            }}
          >
            {p.content.title}
          </Heading>
          <Photo p={p} />
          <Words p={p} />
          <Action p={p} background="#27392d" color="#fffdf8" />
          <Terms p={p} />
        </Section>
        <Section
          style={{ padding: "24px 28px", borderTop: "1px solid #ddd6c9" }}
        >
          <Footer p={p} color="#27392d" />
        </Section>
      </Container>
    </Shell>
  );
}
