import * as React from "react";
import {
  Html,
  Head,
  Body,
  Tailwind,
  Preview,
  Text,
  Img,
  Link,
  Button,
  type TailwindConfig,
} from "react-email";
import type { EmailProps } from "./contract";
export function Shell({
  p,
  config,
  children,
  background,
  font,
  fonts,
}: {
  p: EmailProps;
  config?: TailwindConfig;
  children: React.ReactNode;
  background: string;
  font?: string;
  fonts?: React.ReactNode;
}) {
  const html = (
    <Html lang="es">
      <Head>{fonts}</Head>
      <Body
        style={{
          margin: 0,
          padding: 0,
          backgroundColor: background,
          fontFamily: p.brand.font || font || "Inter,Arial,sans-serif",
        }}
      >
        <Preview>{p.content.subject}</Preview>
        {children}
      </Body>
    </Html>
  );
  return config ? <Tailwind config={config}>{html}</Tailwind> : html;
}
export function Brand({
  p,
  center = false,
}: {
  p: EmailProps;
  center?: boolean;
}) {
  return p.brand.logo_url ? (
    <Img
      src={p.brand.logo_url}
      alt={p.brand.name}
      width="180"
      style={{
        display: "block",
        width: "100%",
        maxWidth: 180,
        boxSizing: "border-box",
        padding: ["protocol", "arcane"].includes(p.template_id)
          ? "8px"
          : undefined,
        backgroundColor: ["protocol", "arcane"].includes(p.template_id)
          ? "#ffffff"
          : undefined,
        height: "auto",
        margin: center ? "0 auto" : "0",
      }}
    />
  ) : (
    <Text
      style={{ margin: 0, fontSize: 20, lineHeight: "28px", fontWeight: 600 }}
    >
      {p.brand.name}
    </Text>
  );
}
export function Photo({ p, width = 592 }: { p: EmailProps; width?: number }) {
  return p.media ? (
    <Img
      src={p.media.url}
      alt={p.media.alt}
      width={width}
      style={{
        display: "block",
        width: "100%",
        maxWidth: width,
        height: "auto",
        border: 0,
      }}
    />
  ) : null;
}
export function Words({
  p,
  className = "",
}: {
  p: EmailProps;
  className?: string;
}) {
  return (
    <>
      <Text
        className={className}
        style={{ margin: "0 0 20px", fontSize: 16, lineHeight: "26px" }}
      >
        Hola, {p.personalization.name}.
      </Text>
      {p.content.body.split(/\n\s*\n/).map((s, i) => (
        <Text
          key={i}
          className={className}
          style={{
            margin: "0 0 20px",
            fontSize: 16,
            lineHeight: "26px",
            whiteSpace: "pre-line",
            overflowWrap: "anywhere",
          }}
        >
          {s}
        </Text>
      ))}
    </>
  );
}
export function Terms({ p }: { p: EmailProps }) {
  return (
    <>
      <Text
        style={{
          fontSize: 13,
          lineHeight: "21px",
          whiteSpace: "pre-line",
          overflowWrap: "anywhere",
        }}
      >
        {p.content.terms}
      </Text>
      <Text style={{ fontSize: 12, lineHeight: "20px" }}>
        Vigencia: {p.content.expiry}
      </Text>
    </>
  );
}
export function Footer({ p, color }: { p: EmailProps; color: string }) {
  return (
    <>
      <Text style={{ fontSize: 12, lineHeight: "20px", color }}>
        Recibes esta invitación por tu permiso de comunicaciones de{" "}
        {p.brand.name}.
      </Text>
      <Link
        href={p.personalization.unsubscribe_url}
        style={{ fontSize: 12, color, textDecoration: "underline" }}
      >
        Dejar de recibir promociones
      </Link>
    </>
  );
}
export function Action({
  p,
  background,
  color,
  rounded = 0,
  border,
}: {
  p: EmailProps;
  background: string;
  color: string;
  rounded?: number;
  border?: string;
}) {
  const fill = p.brand.accent || background;
  if (p.brand.accent) {
    const values = [1, 3, 5]
      .map((i) => parseInt(fill.slice(i, i + 2), 16) / 255)
      .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    const light = values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    color =
      (light + 0.05) / 0.05 >= 1.05 / (light + 0.05) ? "#000000" : "#ffffff";
  }
  return (
    <Button
      href={p.personalization.ordering_url}
      style={{
        boxSizing: "border-box",
        display: "inline-block",
        backgroundColor: fill,
        border,
        color,
        padding: "16px 24px",
        borderRadius: rounded,
        textDecoration: "none",
        fontSize: 16,
        fontWeight: 600,
        lineHeight: "24px",
        maxWidth: "100%",
      }}
    >
      {p.content.cta_label}
    </Button>
  );
}
