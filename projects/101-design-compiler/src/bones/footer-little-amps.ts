import { z } from 'zod';

const text = z.string().trim().min(1).max(180);
const destination = z.string().refine(value => {
  if (value !== value.trim() || /[\s\\\u0000-\u001f]/.test(value)) return false;
  if (/^\/(?!\/)/.test(value)) return true;
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' && Boolean(url.hostname) && !url.username && !url.password)
      || (url.protocol === 'mailto:' && /^[^?@]+@[^?@]+\.[^?@]+$/.test(url.pathname));
  } catch { return false; }
}, 'Usar HTTPS, ruta local o correo sin credenciales');

export const littleAmpsActionSchema = z.object({
  label: text, state: z.enum(['unbound', 'available']), href: destination.optional(),
}).strict().superRefine((value, ctx) => {
  if ((value.state === 'available') !== Boolean(value.href)) {
    ctx.addIssue({ code: 'custom', message: 'Una acción disponible requiere destino; un hueco no lo admite' });
  }
});
export type LittleAmpsAction = z.infer<typeof littleAmpsActionSchema>;
const menu = z.object({ title: text, items: z.array(littleAmpsActionSchema) }).strict();

// Media slots deliberately accept labels only. Binding an asset requires the existing
// rights/scope/inspection pipeline, not a new URL/approved boolean on this component.
export const littleAmpsContentSchema = z.object({
  logo: littleAmpsActionSchema, visitTitle: text, addresses: z.array(text).length(2),
  social: z.array(littleAmpsActionSchema).length(2), email: littleAmpsActionSchema,
  menus: z.tuple([
    menu.extend({ items: z.array(littleAmpsActionSchema).length(3) }),
    menu.extend({ items: z.array(littleAmpsActionSchema).length(5) }),
  ]),
  player: text, followGraphic: littleAmpsActionSchema,
  gallery: z.array(text).length(11), copyright: text, copyrightBrand: littleAmpsActionSchema, credits: littleAmpsActionSchema,
}).strict();
export type LittleAmpsContent = z.infer<typeof littleAmpsContentSchema>;

export const socialMediaBriefs = [
  { file: 'Rectangle_27', type: 'product-photo', label: 'Foto de producto', subject: 'Mano sosteniendo una lata o envase con gráfica', crop: 'vertical convertido a cuadro; conservar envase y mano' },
  { file: 'Rectangle_29', type: 'documentary-photo', label: 'Foto de fachada', subject: 'Entrada del local con personas y jardineras', crop: 'fachada y personas completas dentro del cuadro' },
  { file: 'Rectangle_30', type: 'event-poster', label: 'Cartel de evento', subject: 'Cartel tipográfico de concierto con retratos', crop: 'no cortar información; preferir versión cuadrada legible o contain' },
  { file: 'Rectangle_31', type: 'documentary-photo', label: 'Foto de proceso', subject: 'Persona junto a tostadora de café y recipientes', crop: 'conservar persona, máquina y contexto de trabajo' },
  { file: 'Rectangle_32', type: 'documentary-photo', label: 'Foto de edificio', subject: 'Esquina urbana y edificio del local', crop: 'mantener reconocible el local en su entorno' },
  { file: 'Rectangle_33', type: 'documentary-photo', label: 'Foto de actividad', subject: 'Trabajo manual sobre un letrero en exterior', crop: 'mantener persona, gesto de trabajo y letrero' },
  { file: 'Rectangle_34', type: 'documentary-photo', label: 'Foto de comunidad', subject: 'Dos personas frente al local y una calle urbana', crop: 'conservar personas y ubicación; no afirmar su relación laboral' },
  { file: 'Rectangle_35', type: 'documentary-photo', label: 'Retrato en local', subject: 'Dos personas dentro de una cafetería', crop: 'rostros y contexto completos; no inferir identidades' },
  { file: 'Rectangle_36', type: 'product-photo', label: 'Foto de exhibición', subject: 'Bolsas de café en un exhibidor comercial', crop: 'conservar producto y contexto de venta' },
  { file: 'Rectangle_37', type: 'documentary-photo', label: 'Foto de grupo', subject: 'Grupo de personas posando ante una puerta', crop: 'grupo completo; confirmar identidades y permisos por separado' },
  { file: 'Rectangle_38', type: 'product-photo', label: 'Foto de mercancía', subject: 'Dos personas con camisetas gráficas frente a un mural', crop: 'conservar prendas y personas sin atribuirles roles' },
] as const;

const action = (label: string): LittleAmpsAction => ({ label, state: 'unbound' });
export const neutralLittleAmps: LittleAmpsContent = littleAmpsContentSchema.parse({
  logo: action('Logo gráfico de marca'), visitTitle: 'Título de ubicaciones',
  addresses: ['Texto de dirección 1', 'Texto de dirección 2'],
  social: [action('Icono social 1'), action('Icono social 2')],
  email: action('Texto de correo'),
  menus: [
    { title: 'Título de empresa', items: [1, 2, 3].map(i => action(`Enlace de empresa ${i}`)) },
    { title: 'Título de tienda', items: [1, 2, 3, 4, 5].map(i => action(`Enlace de tienda ${i}`)) },
  ],
  player: 'Reproductor externo de música', followGraphic: action('Gráfica de invitación social'),
  gallery: socialMediaBriefs.map((item, i) => `${item.type === 'event-poster' ? 'Cartel' : 'Foto'} ${i + 1}`),
  copyright: 'Copyright y año', copyrightBrand: action('Marca'), credits: action('Créditos del sitio'),
});

export const littleAmpsBone = {
  id: 'footer.identity-menus-social-rail', version: '0.1.0', family: 'footer',
  review: 'pending-human-review', implementation: 'reconstructed-from-public-reference',
  source: {
    gallery: 'https://www.footer.design/sites/little-amps-coffee',
    official: 'https://littleampscoffee.com/', inspectedAt: '2026-11-05',
    desktop: { width: 2048, height: 846 }, mobile: { width: 786, height: 1618 },
    note: 'Image pixels are capture dimensions, not confirmed CSS viewport widths.',
  },
  composition: { menuDesktopMin: 1100, playerDesktopMin: 1201,
    invitationWideMin: 769, gallerySmallMax: 749, galleryCount: 11,
    logoRatio: 385 / 156.67493796526054, playerHeight: 380 },
  behavior: { scroll: 'normal-document-flow', menus: 'initially-open-mobile-exclusive-on-activation',
    gallery: 'linear-loop-with-pause-and-manual-scroll-fallback', pointer: 'native',
    player: 'unbound-provider-slot-no-network', noJavaScript: 'native-details-and-manual-gallery' },
  changesFromReference: ['visible-pause-control', 'manual-scroll-without-motion',
    'safe-text-reflow', 'no-provider-embed-loaded', 'native-details-without-duplicate-menu-content'],
  eligibility: { required: ['brand-logo-slot', 'two-addresses', 'two-social-actions', 'email',
    'two-menus-with-3-and-5-items', 'provider-player-slot', 'social-invitation-graphic', '11-social-media-slots', 'copyright', 'credits'],
    missing: 'reject-incomplete-content; placeholders permitted for workshop review only',
    media: 'no-asset-binding-in-this-version; use existing media gates before client adaptation' },
} as const;

export type LittleAmpsPart = {
  id: string; kind: 'region' | 'text' | 'graphic-slot' | 'icon-action' | 'link' | 'disclosure' | 'embed-slot' | 'media-slot' | 'control';
  position: string; purpose: string; reference: string; owner: string;
};
export function littleAmpsAnatomy(): LittleAmpsPart[] {
  const rows: LittleAmpsPart[] = [];
  const add = (id: string, kind: LittleAmpsPart['kind'], position: string, purpose: string, reference: string, owner = 'hueso + contenido') => rows.push({ id, kind, position, purpose, reference, owner });
  add('main-panel', 'region', 'Banda superior', 'Agrupar identidad, contacto, menús y reproductor', 'Panel beige con margen exterior', 'hueso');
  add('identity', 'region', 'Izquierda; primero en móvil', 'Identidad arriba y contacto al pie', 'Columna del logo y contacto', 'hueso');
  add('brand-logo', 'graphic-slot', 'Arriba izquierda', 'Logo completo enlazado al inicio; no texto recreado ni fotografía', 'SVG compuesto: wordmark y amplificador; proporción 385:156.675', 'contenido de identidad; tratamiento de piel');
  add('contact', 'region', 'Debajo del logo', 'Ubicaciones a izquierda; canales a derecha cuando caben', 'Bloque inferior de la columna izquierda', 'hueso');
  add('locations', 'region', 'Abajo izquierda', 'Dos ubicaciones como texto, no mapas ni botones', 'Bloque Visit us', 'hueso');
  add('visit-title', 'text', 'Sobre direcciones', 'Título de ubicaciones; no es botón', 'Etiqueta de ubicaciones con fondo', 'contenido; fondo y fuente de piel');
  add('address-1', 'text', 'Primera línea', 'Dirección de sucursal 1', 'State Street');
  add('address-2', 'text', 'Segunda línea', 'Dirección de sucursal 2', 'Green Street');
  add('channels', 'region', 'Junto a ubicaciones; debajo si no caben', 'Redes sobre correo', 'Bloque de canales', 'hueso');
  add('social-1', 'icon-action', 'Primero de dos iconos', 'Enlace con nombre accesible, no botón de envío', 'Facebook');
  add('social-2', 'icon-action', 'Segundo de dos iconos', 'Enlace con nombre accesible', 'Instagram');
  add('email', 'link', 'Debajo de iconos', 'Enlace mailto cuando tenga destino', 'Correo de contacto');
  add('menus', 'region', 'Centro; después de contacto en móvil', 'Dos grupos, no cuatro menús duplicados', 'Company / Shop', 'hueso');
  const names = [['About', 'Blog', 'Contact'], ['Coffee', 'Subscriptions', 'Amps Gear', 'Brewing Equipment', 'Shop All']];
  names.forEach((items, g) => {
    const id = `menu-${g + 1}`;
    add(id, 'region', `Columna central ${g + 1}; fila móvil ${g + 1}`, 'Grupo de navegación', g === 0 ? 'Company' : 'Shop', 'hueso');
    add(`${id}-toggle`, 'disclosure', 'Encabezado móvil', 'Abrir/cerrar; empieza abierto; activa exclusividad', 'Summary y caret móvil', 'hueso/comportamiento');
    add(`${id}-title`, 'text', 'Encabezado de grupo', 'Nombre del grupo, fuente reemplazable', g === 0 ? 'Company' : 'Shop');
    add(`${id}-caret`, 'control', 'Extremo derecho móvil', 'Indicador del estado abierto/cerrado', 'Chevron ascendente/descendente', 'hueso; trazo de piel');
    items.forEach((name, i) => add(`${id}-link-${i + 1}`, 'link', `Grupo ${g + 1}, fila ${i + 1}`, 'Navegación nativa cuando se vincule', name));
  });
  add('player', 'embed-slot', 'Extremo derecho; sólo desde 1201 px', 'Reservar reproductor externo; controles pertenecen al proveedor', 'Spotify playlist embed, alto 380; carátula, título, autor, guardar, reproducción y tracks', 'proveedor + permisos/integración');
  add('social-band', 'region', 'Banda intermedia', 'Invitación fija izquierda y carril a derecha', 'Franja naranja de Instagram', 'hueso');
  add('follow-graphic', 'graphic-slot', 'Izquierda de carril; fija también en móvil', 'Enlace gráfico a Instagram: ilustración + bocadillo; no foto ni botón de acción', 'PNG compuesto de cactus/taza y bocadillo de invitación', 'contenido de identidad; tratamiento de piel');
  add('gallery-window', 'region', 'Derecha de invitación', 'Ventana horizontal, sin overflow de página', 'Viewport de Swiper', 'hueso');
  add('gallery-track', 'region', 'Dentro de ventana', 'Once medios en orden; copias decorativas no son inventario nuevo', 'Bucle lineal de imágenes; sin enlaces configurados', 'hueso/comportamiento');
  socialMediaBriefs.forEach((item, i) => add(`gallery-${i + 1}`, 'media-slot', `Carril, posición canónica ${i + 1}`, `${item.label}: ${item.subject}. Recorte: ${item.crop}.`, item.file, 'contenido documental; permisos e inspección existentes'));
  add('gallery-pause', 'control', 'Junto a invitación', 'Pausar/reanudar; alternativa accesible añadida', 'No presente en original; mejora declarada', 'hueso/comportamiento');
  add('legal', 'region', 'Última banda', 'Separar copyright y créditos', 'Barra marrón inferior', 'hueso');
  add('copyright', 'text', 'Izquierda de cierre', 'Copyright con año y marca configurables', 'Copyright y nombre de marca');
  add('copyright-brand', 'link', 'Junto a copyright y año', 'Nombre de marca enlazado al inicio', 'Enlace de marca al inicio');
  add('credits', 'link', 'Derecha de cierre', 'Navegación a créditos si existe destino', 'Site Credits');
  return rows;
}
