import {z} from 'zod';

const text = z.string().trim().min(1).max(400);
const href = z.string().refine(value => {
  try { return ['https:', 'http:', 'mailto:'].includes(new URL(value).protocol); }
  catch { return false; }
}, 'A footer destination must be an absolute web or mail URL');
const common = {id: z.string().regex(/^[a-z][a-z0-9-]*$/), label: text};
const available = z.object({...common, state: z.literal('available'), href, newTab: z.boolean()}).strict();
const soon = z.object({...common, state: z.literal('soon')}).strict();
export const footerItemSchema = z.discriminatedUnion('state', [available, soon]);
const schema = z.object({
  schemaVersion: z.literal('101-footer-content-v1'),
  source: z.object({key: text, url: href, image: href, capturedAt: text, destinationsObservedOn: text}).strict(),
  brand: z.object({name: text, description: text, backersHeading: text, copyright: text, wordmark: text}).strict(),
  assistantsLabel: text,
  assistants: z.array(available).max(6),
  backers: z.array(available).max(6),
  groups: z.array(z.object({id: text, label: text, items: z.array(footerItemSchema).min(1).max(16)}).strict()).length(4),
  legal: z.array(available).max(10),
}).strict().superRefine((data, context) => {
  const ids = new Set<string>();
  for (const item of [...data.assistants, ...data.backers, ...data.groups.flatMap(g => [g, ...g.items]), ...data.legal]) {
    if (ids.has(item.id)) context.addIssue({code: 'custom', message: 'Duplicate footer ID: ' + item.id});
    ids.add(item.id);
  }
});
export type FooterContent = z.infer<typeof schema>;
export type FooterItemData = z.infer<typeof footerItemSchema>;
export {FOOTER_BONE} from './anatomy.ts';
export const parseFooterContent = (value: unknown): FooterContent => schema.parse(value);
