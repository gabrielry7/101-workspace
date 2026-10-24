// Local lab primitives. No claim of compatibility with the absent @101/site-runtime.
export const COMPOSITION_VERSION = '1.0.0' as const;
export const compositions = [
  { id: 'editorial', label: 'Editorial', operator: 'Sequence', description: 'Título dominante, imagen centrada y secuencia amplia.' },
  { id: 'split', label: 'Split', operator: 'Split', description: 'Dos campos de proporción desigual; texto e imagen en diálogo.' },
  { id: 'rail', label: 'Rail', operator: 'Rail', description: 'Navegación lateral, título compacto y campo visual desplazado.' },
] as const;
export type CompositionId = typeof compositions[number]['id'];
export const componentRegistry = {
  identity: { component: 'Identity', path: 'src/components/composition/Identity.astro' },
  offering_collection: { component: 'OfferingCollection', path: 'src/components/composition/OfferingCollection.astro' },
  fact_collection: { component: 'FactCollection', path: 'src/components/composition/FactCollection.astro' },
  schedule: { component: 'Schedule', path: 'src/components/composition/Schedule.astro' },
  location_information: { component: 'FactCollection', path: 'src/components/composition/FactCollection.astro' },
} as const;
export function previewPath(variant: CompositionId, semanticPath: string) {
  if (!compositions.some(c => c.id === variant) || !/^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/.test(semanticPath)) throw new Error('INVALID_PREVIEW_ROUTE');
  return `/h4/${variant}${semanticPath === '/' ? '/' : `${semanticPath}/`}`;
}
