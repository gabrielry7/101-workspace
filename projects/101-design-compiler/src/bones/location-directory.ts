import { z } from 'zod';

const text = z.string().trim().min(1).max(180);
const id = z.string().regex(/^[a-z0-9][a-z0-9/-]{0,95}$/);
const href = z.string().refine(value => {
  if (value !== value.trim() || /[\s\\\u0000-\u001f]/.test(value)) return false;
  if (/^\/(?!\/)/.test(value)) return true;
  try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password; } catch { return false; }
}, 'Usar una ruta local o HTTPS sin credenciales');
export const directoryActionSchema = z.object({ state: z.enum(['unbound', 'available']), href: href.optional() }).strict()
  .superRefine((action, ctx) => { if ((action.state === 'available') !== Boolean(action.href)) ctx.addIssue({ code: 'custom', message: 'La acción disponible necesita destino; un hueco no lo admite' }); });
const entry = z.object({ label: text, count: z.number().int().nonnegative().nullable(), viewId: id }).strict();
const card = z.object({ id, title: text, imageLabel: text, action: directoryActionSchema }).strict();
const view = z.object({ id, title: text, level: z.enum(['overview', 'area', 'locality']), parentId: id.nullable(),
  panelTitle: text, groups: z.array(z.object({ label: text, items: z.array(entry).max(300) }).strict()).max(50),
  entries: z.array(entry).max(300), openings: z.array(z.object({ label: text, items: z.array(text).max(100) }).strict()).max(10),
  cardsTitle: text, cards: z.array(card).max(100),
}).strict();

export const locationDirectorySchema = z.object({ rootId: id, title: text, mapLabel: text,
  labels: z.object({ back: text, cardPage: text, navigation: text }).strict(), views: z.array(view).min(1).max(300),
}).strict().superRefine((content, ctx) => {
  const views = new Map(content.views.map(v => [v.id, v]));
  const issue = (message: string) => ctx.addIssue({ code: 'custom', message });
  if (views.size !== content.views.length) issue('VIEW_ID_DUPLICATE');
  const root = views.get(content.rootId);
  if (!root || root.level !== 'overview' || root.parentId !== null) issue('ROOT_VIEW_REQUIRED');
  for (const v of content.views) {
    if (v.id !== content.rootId && (v.parentId === null || !views.has(v.parentId))) issue(`PARENT_VIEW_REQUIRED:${v.id}`);
    const parent = v.parentId ? views.get(v.parentId) : undefined;
    if (v.id !== content.rootId && (v.level === 'overview' ||
      (v.level === 'area' && parent?.level !== 'overview') ||
      (v.level === 'locality' && parent?.level !== 'area'))) issue(`PARENT_LEVEL_INVALID:${v.id}`);
    if ((v.level === 'overview' && v.entries.length) || (v.level !== 'overview' && v.groups.length)) issue(`ENTRY_STRUCTURE_INVALID:${v.id}`);
    const chain = new Set<string>(); let current: typeof v | undefined = v;
    while (current) {
      if (chain.has(current.id)) { issue(`PARENT_CYCLE:${v.id}`); break; }
      chain.add(current.id); current = current.parentId ? views.get(current.parentId) : undefined;
    }
    if (new Set(v.cards.map(c => c.id)).size !== v.cards.length) issue(`CARD_ID_DUPLICATE:${v.id}`);
    const items = [...v.entries, ...v.groups.flatMap(g => g.items)];
    if (new Set(items.map(item => item.viewId)).size !== items.length) issue(`ENTRY_TARGET_DUPLICATE:${v.id}`);
    for (const item of items) {
      const target = views.get(item.viewId);
      if (!target) issue(`TARGET_VIEW_REQUIRED:${item.viewId}`);
      else if ((v.level === 'overview' && target.parentId !== v.id) ||
        (v.level === 'area' && target.parentId !== v.id) ||
        (v.level === 'locality' && (target.level !== 'locality' || target.parentId !== v.parentId))) issue(`TARGET_LEVEL_INVALID:${item.viewId}`);
    }
  }
});
export type LocationDirectoryContent = z.infer<typeof locationDirectorySchema>;
export type DirectoryView = LocationDirectoryContent['views'][number];

export const locationDirectoryBone = {
  id: 'location.directory-map-hierarchy', version: '0.1.0', family: 'location', review: 'pending-human-review',
  source: { official: 'https://arabica.com/en/locations/', referenceVersion: '0.1.1', inspectedAt: '2026-11-20' },
  composition: { mobileMax: 780, cameraMobileMax: 559, mobileMapHeight: 300, panelWidth: 230,
    cardWidth: 270, cardMediaRatio: 270 / 118.125 },
  behavior: { directory: 'overview-area-locality-with-history-and-back', panel: 'independently-scrollable',
    cards: 'manual-horizontal-scroll-and-mobile-pagination', map: 'unbound-provider-slot-with-view-change-events',
    navigation: 'explicit-anchor-only', pointer: 'native', noJavaScript: 'native-expanded-view-list' },
  media: 'label-only-slots; caller markup remains subject to existing media permissions',
  eligibility: { required: ['overview', 'valid-view-hierarchy', 'directory-labels', 'map-slot'],
    optional: ['opening-states', 'location-cards', 'available-actions'],
    excluded: ['reference-page-header', 'provider-implementation', 'automatic-business-authority'] },
} as const;

export function locationDirectoryAnatomy(content: LocationDirectoryContent) {
  const rows: { id: string; kind: string; purpose: string; owner: string }[] = [
    { id: 'section', kind: 'region', purpose: 'Contener el directorio de ubicaciones', owner: 'hueso' },
    { id: 'title', kind: 'text', purpose: 'Título de la sección', owner: 'contenido / tipografía de piel' },
    { id: 'map-slot', kind: 'integration-slot', purpose: 'Reservar mapa; proveedor por vincular', owner: 'integración separada' },
    { id: 'status', kind: 'live-region', purpose: 'Anunciar el cambio de ubicación', owner: 'comportamiento' },
  ];
  const add = (viewId: string, part: string, kind: string, purpose: string, owner = 'hueso + contenido') => rows.push({ id: `${viewId}:${part}`, kind, purpose, owner });
  for (const v of content.views) {
    add(v.id, 'panel', 'region', 'Directorio superpuesto en escritorio; debajo del mapa en móvil', 'hueso');
    add(v.id, 'panel-title', 'text', 'Tipo de agrupación');
    [...v.groups.flatMap(g => g.items), ...v.entries].forEach((item, index) => {
      add(v.id, `entry-${index + 1}`, 'navigation-link', `Seleccionar ${item.label}`, 'comportamiento + contenido');
      add(v.id, `count-${index + 1}`, 'text', 'Recuento confirmado; ausente cuando es desconocido');
    });
    if (v.level !== 'overview' && v.entries.length === 0) add(v.id, 'empty', 'status', 'No hay entradas vinculadas');
    v.groups.forEach((_, index) => add(v.id, `group-${index + 1}`, 'group', 'Agrupar ubicaciones'));
    v.openings.forEach((_, index) => add(v.id, `opening-${index + 1}`, 'status-group', 'Ubicaciones futuras, sin destino supuesto'));
    if (v.parentId) add(v.id, 'back', 'navigation-link', 'Volver al nivel superior', 'comportamiento');
    if (v.cards.length) {
      add(v.id, 'cards', 'region', 'Carril de locales', 'hueso');
      add(v.id, 'cards-title', 'text', 'Título de locales');
      add(v.id, 'card-track', 'scroll-region', 'Recorrido horizontal y táctil', 'comportamiento');
      add(v.id, 'card-pages', 'control', 'Elegir una tarjeta en móvil', 'comportamiento');
    }
    for (const c of v.cards) {
      add(v.id, `media-${c.id}`, 'image-slot', c.imageLabel, 'contenido; permisos e inspección existentes');
      add(v.id, `title-${c.id}`, 'text', 'Nombre del local');
      add(v.id, `action-${c.id}`, 'action-slot', 'Destino del local; sin enlace cuando está sin vincular');
    }
  }
  return rows;
}

const mediaCard = (n: number) => ({ id: `local-${n}`, title: `Título del local ${n}`,
  imageLabel: `Foto del local ${n}`, action: { state: 'unbound' as const } });
const empty = { groups: [], entries: [], openings: [], cards: [], cardsTitle: 'Título del carril de locales' };
export const neutralLocationDirectory = locationDirectorySchema.parse({
  rootId: 'overview', title: 'Título de ubicaciones', mapLabel: 'Mapa',
  labels: { back: 'Volver', cardPage: 'Ver local', navigation: 'Directorio de ubicaciones' },
  views: [
    { ...empty, id: 'overview', title: 'Todas las ubicaciones', level: 'overview', parentId: null, panelTitle: 'Agrupaciones',
      groups: [
        { label: 'Grupo de ubicaciones 1', items: [{ label: 'Región 1', count: 3, viewId: 'region-1' }, { label: 'Región 2', count: 1, viewId: 'region-2' }] },
        { label: 'Grupo de ubicaciones 2', items: [{ label: 'Región 3', count: null, viewId: 'region-3' }] },
      ], openings: [{ label: 'Próximas aperturas', items: ['Ubicación por confirmar 1', 'Ubicación por confirmar 2'] },
        { label: 'Aperturas posteriores', items: ['Ubicación por confirmar 3'] }], cards: [1, 2, 3].map(mediaCard) },
    { ...empty, id: 'region-1', title: 'Región 1', level: 'area', parentId: 'overview', panelTitle: 'Ciudades',
      entries: [{ label: 'Ciudad 1', count: 2, viewId: 'region-1/city-1' }, { label: 'Ciudad 2', count: 1, viewId: 'region-1/city-2' }] },
    { ...empty, id: 'region-2', title: 'Región 2', level: 'area', parentId: 'overview', panelTitle: 'Ciudades',
      entries: [{ label: 'Ciudad 3', count: 1, viewId: 'region-2/city-3' }] },
    { ...empty, id: 'region-3', title: 'Región 3', level: 'area', parentId: 'overview', panelTitle: 'Ciudades' },
    { ...empty, id: 'region-1/city-1', title: 'Ciudad 1', level: 'locality', parentId: 'region-1', panelTitle: 'Ciudades',
      entries: [{ label: 'Ciudad 1', count: 2, viewId: 'region-1/city-1' }, { label: 'Ciudad 2', count: 1, viewId: 'region-1/city-2' }], cards: [1, 2].map(mediaCard) },
    { ...empty, id: 'region-1/city-2', title: 'Ciudad 2', level: 'locality', parentId: 'region-1', panelTitle: 'Ciudades',
      entries: [{ label: 'Ciudad 1', count: 2, viewId: 'region-1/city-1' }, { label: 'Ciudad 2', count: 1, viewId: 'region-1/city-2' }], cards: [3].map(mediaCard) },
    { ...empty, id: 'region-2/city-3', title: 'Ciudad 3', level: 'locality', parentId: 'region-2', panelTitle: 'Ciudades',
      entries: [{ label: 'Ciudad 3', count: 1, viewId: 'region-2/city-3' }], cards: [4].map(mediaCard) },
  ],
});
