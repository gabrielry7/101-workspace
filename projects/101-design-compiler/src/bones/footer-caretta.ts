import { z } from 'zod';

const text = z.string().trim().min(1).max(240);
const id = z.string().regex(/^[a-z][a-z0-9-]*$/);
const destination = z.string().refine(value => {
  if (value !== value.trim() || /[\s\\\u0000-\u001f]/.test(value)) return false;
  if (/^\/(?!\/)/.test(value)) return true;
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' && Boolean(url.hostname) && !url.username && !url.password)
      || (url.protocol === 'mailto:' && /^[^?@]+@[^?@]+\.[^?@]+$/.test(url.pathname));
  } catch { return false; }
}, 'Destino no permitido: usar HTTPS, ruta local o correo');

export const footerEntrySchema = z.object({
  id, label: text, icon: text.optional(),
  state: z.enum(['unbound', 'available', 'upcoming']),
  href: destination.optional(),
  statusLabel: text.optional(),
}).strict().superRefine((entry, ctx) => {
  if ((entry.state === 'available') !== Boolean(entry.href)) {
    ctx.addIssue({ code: 'custom', message: 'Sólo un elemento disponible debe tener destino' });
  }
  if (entry.state === 'upcoming' && !entry.statusLabel) {
    ctx.addIssue({ code: 'custom', message: 'Un elemento próximo debe identificar su estado' });
  }
});
export type FooterEntry = z.infer<typeof footerEntrySchema>;

const groupSchema = z.object({ id, title: text, items: z.array(footerEntrySchema) }).strict();
export const footerContentSchema = z.object({
  brandLogo: text, description: text, backersLabel: text,
  backers: z.array(footerEntrySchema).length(3),
  assistantsLabel: text, assistants: z.array(footerEntrySchema).length(5),
  groups: z.tuple([
    groupSchema.extend({ items: z.array(footerEntrySchema).length(5) }),
    groupSchema.extend({ items: z.array(footerEntrySchema).length(4) }),
    groupSchema.extend({ items: z.array(footerEntrySchema).length(5) }),
    groupSchema.extend({ items: z.array(footerEntrySchema).length(10) }),
  ]),
  watermark: text, copyright: text,
  legal: z.array(footerEntrySchema).length(2),
  cookies: z.object({ label: text, statusLabel: text }).strict(),
  trust: footerEntrySchema, social: footerEntrySchema, email: footerEntrySchema,
}).strict().superRefine((content, ctx) => {
  const ids = new Set<string>(['transition', 'assistants', 'assistants-label', 'identity',
    'brand-logo', 'description', 'backers', 'backers-label', 'directory', 'watermark',
    'legal', 'copyright', 'cookies', 'cookies-status']);
  const register = (value: string) => {
    if (ids.has(value)) ctx.addIssue({ code: 'custom', message: `ID de parte duplicado: ${value}` });
    ids.add(value);
  };
  const entry = (item: FooterEntry) => {
    register(item.id); register(`${item.id}-text`);
    if (item.icon) register(`${item.id}-icon`);
    if (item.statusLabel) register(`${item.id}-status`);
  };
  [...content.assistants, ...content.backers, ...content.legal,
    content.trust, content.social, content.email].forEach(entry);
  for (const group of content.groups) {
    register(group.id); register(`${group.id}-title`); group.items.forEach(entry);
  }
});
export type FooterContent = z.infer<typeof footerContentSchema>;

// Reference content belongs to the anatomy map only, never to the neutral fixture.
export const sourceGroups = [
  { title: 'Product', items: ['Before the call', 'During the call', 'After the call', 'Caretta Metrics', 'Brain'], upcoming: [] },
  { title: 'Teams', items: ['SDRs', 'AEs', 'GTM Leaders', 'Founders'], upcoming: [0, 1] },
  { title: 'Industries', items: ['Compute & Inference', 'Voice AI', 'Insurance', 'Startups', 'Cybersecurity'], upcoming: [1] },
  { title: 'Resources', items: ['Pricing', 'Blog', 'Docs', 'Resources', 'Customers', 'About', 'Contact', 'Brand guidelines', 'Careers', 'Security'], upcoming: [4, 9] },
] as const;

const slot = (key: string, label: string): FooterEntry => ({ id: key, label, state: 'unbound' });
export const neutralFooter: FooterContent = footerContentSchema.parse({
  brandLogo: 'Logo de marca', description: 'Texto descriptivo de marca 1',
  backersLabel: 'Texto de encabezado de respaldos 1',
  backers: Array.from({ length: 3 }, (_, i) => slot(`backer-${i + 1}`, `Logo de respaldo ${i + 1}`)),
  assistantsLabel: 'Texto de invitación a resumir con IA 1',
  assistants: Array.from({ length: 5 }, (_, i) => ({
    ...slot(`assistant-${i + 1}`, `Texto de acceso a IA ${i + 1}`), icon: `Icono de IA ${i + 1}`,
  })),
  groups: sourceGroups.map((group, g) => ({
    id: `group-${g + 1}`, title: `Texto de título del grupo ${g + 1}`,
    items: group.items.map((_, i) => ({
      ...slot(`group-${g + 1}-item-${i + 1}`, `Texto del enlace ${i + 1}, grupo ${g + 1}`),
      icon: `Icono ${i + 1}, grupo ${g + 1}`,
      ...((group.upcoming as readonly number[]).includes(i)
        ? { state: 'upcoming', statusLabel: `Texto de estado próximo ${i + 1}, grupo ${g + 1}` } : {}),
    })),
  })),
  watermark: 'Espacio de marca gráfica de gran formato', copyright: 'Texto de copyright 1',
  legal: [slot('privacy', 'Texto de enlace legal 1'), slot('terms', 'Texto de enlace legal 2')],
  cookies: { label: 'Texto de ajustes de cookies 1', statusLabel: 'Sin gestor de consentimiento conectado' },
  trust: slot('trust', 'Texto de enlace de confianza 1'),
  social: slot('social-1', 'Texto de red social 1'), email: slot('email', 'Texto de correo 1'),
});

export const carettaFooterBone = {
  id: 'footer.directory-watermark', version: '0.1.0', family: 'footer',
  review: 'pending-human-review', implementation: 'reconstructed-from-reference',
  source: { key: 'caretta/08', url: 'https://www.regards.design/sections/caretta/08',
    live: 'https://caretta.so/', capturedAt: '2026-10-19T03:18:17.681+00:00',
    viewport: { width: 1440, height: 900 }, section: { top: 10421, height: 806 } },
  regions: ['transition', 'assistants', 'identity', 'backers', 'directory', 'watermark', 'legal'],
  behavior: { scroll: 'normal-document-flow', motion: 'none-observed-none-added',
    responsive: 'proposed-reflow-600-992', missingDestination: 'non-interactive-labelled-slot',
    cookies: 'disabled-until-a-separately-specified-integration', pointer: 'native' },
} as const;

export type FooterPart = { id: string; label: string; reference: string; kind: string };
export function footerAnatomy(content: FooterContent = neutralFooter): FooterPart[] {
  const parts: FooterPart[] = [];
  const add = (key: string, label: string, reference: string, kind: string) => parts.push({ id: key, label, reference, kind });
  const entry = (item: FooterEntry, reference: string, kind = 'action') => {
    add(item.id, item.label, reference, kind);
    add(`${item.id}-text`, item.label, reference, 'text');
    if (item.icon) add(`${item.id}-icon`, item.icon, `Icono de ${reference}`, 'icon');
    if (item.statusLabel) add(`${item.id}-status`, item.statusLabel, 'Soon', 'state');
  };
  add('transition', 'Banda superior sin tratamiento gráfico', 'Banda de degradado', 'region');
  add('assistants', 'Fila de accesos a IA', 'Fila de cinco asistentes', 'region');
  add('assistants-label', content.assistantsLabel, 'Ask an AI to summarise this page', 'text');
  content.assistants.forEach((item, i) => entry(item, ['ChatGPT', 'Claude', 'Perplexity', 'Google AI Mode', 'Grok'][i]!));
  add('identity', 'Identidad y descripción', 'Columna izquierda', 'region');
  add('brand-logo', content.brandLogo, 'Logo Caretta', 'media-slot');
  add('description', content.description, 'Real-time intelligence for the moments that decide whether the deal moves forward.', 'text');
  add('backers', 'Bloque de respaldos', 'Respaldos debajo de descripción', 'region');
  add('backers-label', content.backersLabel, 'Backed by', 'text');
  content.backers.forEach((item, i) => entry(item, ['Y Combinator', 'Robinhood', 'Long Journey'][i]!, 'media-slot'));
  add('directory', 'Directorio de cuatro grupos', 'Product / Teams / Industries / Resources', 'region');
  content.groups.forEach((group, g) => {
    add(group.id, `Grupo ${g + 1}`, sourceGroups[g]!.title, 'group');
    add(`${group.id}-title`, group.title, sourceGroups[g]!.title, 'text');
    group.items.forEach((item, i) => entry(item, sourceGroups[g]!.items[i]!));
  });
  add('watermark', content.watermark, 'Wordmark Caretta grande, tenue y recortado', 'region');
  add('legal', 'Barra legal y social', 'Barra de cierre', 'region');
  add('copyright', content.copyright, 'Caretta Inc. © 2026', 'text');
  content.legal.forEach((item, i) => entry(item, ['Privacy', 'Terms'][i]!));
  add('cookies', content.cookies.label, 'Cookie settings', 'action');
  add('cookies-status', content.cookies.statusLabel, 'Requiere gestor de consentimiento', 'state');
  entry(content.trust, 'Trust Center'); entry(content.social, 'LinkedIn'); entry(content.email, 'Email');
  return parts;
}
