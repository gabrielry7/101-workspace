import type { CSSProperties } from "react";
import { z } from "zod";
// The actual shared validators are pinned build inputs, not a second bones implementation.
import { boneProfile } from "../vendor/101-bones/contract.js";
import { validateBoneAnatomy } from "../vendor/101-bones/types.js";

const color = z.string().regex(/^#[a-fA-F0-9]{6}$/);
const length = (max: number) => z.number().finite().min(0).max(max);
const surface = z
  .object({
    radius: length(96).optional(),
    fill: color.optional(),
    borderWidth: length(4).optional(),
    borderColor: color.optional(),
    padding: length(64).optional(),
    marginTop: length(96).optional(),
    marginBottom: length(96).optional(),
    shadow: z.enum(["none", "soft"]).optional(),
  })
  .strict();
const surfaces = [
  "panel",
  "card",
  "stage",
  "brand",
  "intro",
  "content",
  "photo",
  "controls",
  "footer",
] as const;
const typeRoles = ["heading", "body", "label", "action", "meta"] as const;
const fonts = [
  "Inter",
  "Arial",
  "Georgia",
  "Instrument Serif",
  "IBM Plex Sans Condensed",
  "IBM Plex Mono",
  "Geist",
] as const;
const typeStyle = z
  .object({
    fontFamily: z.enum(fonts).optional(),
    fontSize: z.number().min(12).max(72).optional(),
    fontWeight: z
      .union([z.literal(400), z.literal(500), z.literal(600)])
      .optional(),
    lineHeight: z.number().min(1).max(2).optional(),
    letterSpacing: z.number().min(-1).max(4).optional(),
    textTransform: z.enum(["none", "uppercase"]).optional(),
    color: color.optional(),
  })
  .strict();
export const chassisSchema = z
  .object({
    schema_version: z.literal("1"),
    coat: z.enum(["source", "neutral"]).default("source"),
    geometry: z
      .object({
        maxWidth: z.number().int().min(320).max(800).optional(),
        logoWidth: z.number().int().min(48).max(240).optional(),
      })
      .strict()
      .default({}),
    bones: z
      .object({
        shape: z.enum(["recipe", "square", "soft", "round"]).default("recipe"),
        surfaces: z
          .object(
            Object.fromEntries(
              surfaces.map((role) => [role, surface.optional()]),
            ) as Record<
              (typeof surfaces)[number],
              z.ZodOptional<typeof surface>
            >,
          )
          .strict()
          .default({}),
        colors: z
          .object({
            heading: color.optional(),
            intro: color.optional(),
            action: color.optional(),
            date: color.optional(),
            brand: color.optional(),
          })
          .strict()
          .default({}),
      })
      .strict()
      .default({ shape: "recipe", surfaces: {}, colors: {} }),
    typography: z
      .object(
        Object.fromEntries(
          typeRoles.map((role) => [role, typeStyle.optional()]),
        ) as Record<
          (typeof typeRoles)[number],
          z.ZodOptional<typeof typeStyle>
        >,
      )
      .strict()
      .default({}),
  })
  .strict()
  .superRefine((value, ctx) => {
    try {
      boneProfile(value.bones);
    } catch {
      ctx.addIssue({ code: "custom", message: "Shared bones profile invalid" });
    }
  });
export type EmailChassis = z.infer<typeof chassisSchema>;
type Props = { template_id: string; chassis?: EmailChassis | null };

export function effectiveChassis(p: Props): EmailChassis {
  const c = chassisSchema.parse(p.chassis || { schema_version: "1" });
  if (c.coat !== "neutral") return c;
  const defaults: Record<string, z.infer<typeof surface>> = Object.fromEntries(
    surfaces.map((role) => [
      role,
      { fill: "#ffffff", radius: 0, shadow: "none" },
    ]),
  );
  defaults.controls = { fill: "#202020", radius: 0, borderWidth: 0 };
  return {
    ...c,
    bones: {
      shape: c.bones.shape === "recipe" ? "square" : c.bones.shape,
      surfaces: Object.fromEntries(
        surfaces.map((role) => [
          role,
          { ...defaults[role], ...c.bones.surfaces[role] },
        ]),
      ),
      colors: {
        heading: "#202020",
        intro: "#404040",
        date: "#555555",
        brand: "#202020",
        action: "#ffffff",
        ...c.bones.colors,
      },
    },
    typography: Object.fromEntries(
      typeRoles.map((role) => [
        role,
        { fontFamily: "Inter", textTransform: "none", ...c.typography[role] },
      ]),
    ),
  } as EmailChassis;
}

export function bone(
  p: Props,
  role: (typeof surfaces)[number],
  base: CSSProperties = {},
) {
  const c = effectiveChassis(p),
    s = c.bones.surfaces[role] || {};
  const style: CSSProperties = { ...base };
  if (
    ["panel", "card", "stage", "content", "photo", "controls"].includes(role) &&
    c.bones.shape !== "recipe"
  )
    style.borderRadius = { square: 0, soft: 12, round: 24 }[c.bones.shape];
  for (const [key, value] of Object.entries(s)) {
    const css =
      (
        {
          radius: "borderRadius",
          fill: "backgroundColor",
          shadow: "boxShadow",
        } as Record<string, string>
      )[key] || key;
    (style as Record<string, unknown>)[css] =
      key === "shadow"
        ? value === "soft"
          ? "0 12px 30px #0002"
          : "none"
        : value;
  }
  if (s.borderWidth !== undefined) style.borderStyle = "solid";
  if (role === "panel" && c.geometry.maxWidth !== undefined)
    style.maxWidth = c.geometry.maxWidth;
  return {
    style,
    "data-101-bone": role === "photo" ? "media" : "surface",
    "data-101-bone-role": role,
  };
}
export function type(
  p: Props,
  role: (typeof typeRoles)[number],
  base: CSSProperties = {},
) {
  const c = effectiveChassis(p),
    t = c.typography[role] || {};
  const colorRole = {
    heading: "heading",
    body: "intro",
    label: "date",
    action: "action",
    meta: "date",
  } as const;
  return {
    style: {
      ...base,
      ...(c.bones.colors[colorRole[role]]
        ? { color: c.bones.colors[colorRole[role]] }
        : {}),
      ...t,
    },
    "data-101-bone": "text",
    "data-101-bone-role": role,
  };
}
// Responsive source classes must not override an explicit edit at a narrow viewport.
export function classes(p: Props, role: string, source: string) {
  const c = effectiveChassis(p),
    s = c.bones.surfaces[role as (typeof surfaces)[number]],
    t = c.typography[role as (typeof typeRoles)[number]];
  return source
    .split(/\s+/)
    .filter((token) => {
      const v = token.split(":").at(-1)!;
      if (s?.padding !== undefined && /^p[xytrbl]?-/.test(v)) return false;
      if (s?.radius !== undefined && /^rounded/.test(v)) return false;
      if (t?.fontSize !== undefined && /^font-\d/.test(v)) return false;
      if (t?.fontFamily && /^font-(sans|serif|mono|condensed|geist)$/.test(v))
        return false;
      if (t?.textTransform && /^(uppercase|lowercase|capitalize)$/.test(v))
        return false;
      return true;
    })
    .join(" ");
}

const part = (
  role: string,
  category: string,
  kind: string,
  parent: string | null,
  owner: string,
  hierarchy?: { group: string; level: number },
) => ({
  role,
  category,
  type: kind,
  parent,
  status: "reused",
  source: owner,
  selector: `[data-101-bone-role="${role}"]`,
  ...(hierarchy ? { hierarchy } : {}),
});
export const anatomy = validateBoneAnatomy([
  part(
    "panel",
    "surface",
    "container",
    null,
    "templates/*.tsx → React Email Container",
  ),
  ...["card", "stage", "intro", "content", "footer"].map((role) =>
    part(
      role,
      "surface",
      "container",
      "panel",
      "templates/*.tsx → React Email Section",
    ),
  ),
  part(
    "brand",
    "media",
    "logo",
    "panel",
    "parts.tsx Brand → frozen business name/logo",
  ),
  part(
    "controls",
    "button",
    "primary",
    "content",
    "parts.tsx Action → existing tracked ordering URL",
  ),
  part(
    "photo",
    "media",
    "image",
    "panel",
    "parts.tsx Photo → approved image URL",
  ),
  part(
    "heading",
    "text",
    "heading",
    "intro",
    "templates/*.tsx → React Email Heading",
    { group: "message", level: 1 },
  ),
  part("body", "text", "body", "content", "parts.tsx Words", {
    group: "message",
    level: 2,
  }),
  {
    ...part(
      "content-inset",
      "layout",
      "spacing",
      "content",
      "React Email Section internal cell owns padding",
    ),
    selector: '[data-101-bone-role="content"] > tbody > tr > td',
  },
  part("label", "text", "feedback", "intro", "campaign scope → parts.tsx", {
    group: "message",
    level: 3,
  }),
  part(
    "action",
    "text",
    "button-label",
    "controls",
    "parts.tsx Action → existing tracked ordering URL",
    { group: "action", level: 1 },
  ),
  part(
    "meta",
    "text",
    "body",
    "footer",
    "parts.tsx Terms/Footer → existing terms/expiry/unsubscribe",
    { group: "legal", level: 3 },
  ),
]);
export const chassisCatalogue = {
  schema_version: "1",
  contract: "101-email-chassis-v1",
  shared_bones: "101-bones-v1",
  anatomy,
  recipes: Object.fromEntries(
    ["classic", "barebone", "matte", "protocol", "arcane", "studio"].map(
      (family) => [
        family,
        {
          parts: validateBoneAnatomy(
            anatomy
              .filter(
                (d: { role: string }) =>
                  (d.role !== "intro" ||
                    !["barebone", "matte"].includes(family)) &&
                  (d.role !== "card" || family === "matte") &&
                  (d.role !== "stage" ||
                    ["barebone", "arcane", "studio"].includes(family)),
              )
              .map((d: { role: string; parent: string | null }) => ({
                ...d,
                parent:
                  d.role === "heading"
                    ? ["arcane", "studio"].includes(family)
                      ? "intro"
                      : "content"
                    : d.role === "label"
                      ? ["barebone", "matte"].includes(family)
                        ? "content"
                        : "intro"
                      : d.role === "brand"
                        ? family === "matte"
                          ? "content"
                          : ["classic", "protocol", "studio"].includes(family)
                            ? "intro"
                            : "panel"
                        : d.role === "controls"
                          ? "content"
                          : d.role === "meta"
                            ? null
                            : d.parent,
              })),
          ),
          metadata_parent_scope:
            "Legal text repeats in content and footer; actual DOM ancestry is recorded per instance by the shared measurement tool.",
        },
      ],
    ),
  ),
  coats: ["source", "neutral"],
  supported_surfaces: surfaces,
  typography_roles: typeRoles,
  limits:
    "Email-safe adapter. No opacity, hidden parts, arbitrary CSS/HTML, animation, webpage grid/flex or action destination edits.",
};
