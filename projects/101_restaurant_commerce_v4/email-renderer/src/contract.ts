import { z } from "zod";
import { chassisSchema } from "./chassis";
const text = (n: number) =>
  z
    .string()
    .min(1)
    .max(n)
    .refine((v) => !/[\x00-\x08\x0b-\x1f]/.test(v));
const url = z.url().refine((v) => {
  const u = new URL(v);
  return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password;
});
export const templateIds = [
  "classic",
  "barebone",
  "matte",
  "protocol",
  "arcane",
  "studio",
] as const;
export const inputSchema = z
  .object({
    schema_version: z.literal("1"),
    font_base_url: url,
    template_id: z.enum(templateIds),
    chassis: chassisSchema.nullable().optional(),
    content: z
      .object({
        subject: text(180),
        title: text(180),
        body: text(4000),
        terms: text(1000),
        cta_label: text(80),
        expiry: text(100),
        label: text(100),
      })
      .strict(),
    brand: z
      .object({
        name: text(180),
        logo_url: url.nullable(),
        accent: z
          .string()
          .regex(/^#[0-9a-fA-F]{6}$/)
          .nullable(),
        font: z.enum(["Inter", "Arial", "Georgia"]).nullable(),
      })
      .strict(),
    media: z
      .object({ url, alt: text(200) })
      .strict()
      .nullable(),
    personalization: z
      .object({ name: text(200), ordering_url: url, unsubscribe_url: url })
      .strict(),
  })
  .strict();
export type EmailProps = z.infer<typeof inputSchema>;
