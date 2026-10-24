import type { CompositionLab } from '../../scripts/load-composition-lab.ts';
// General lab context: absence of an authorized medium is explicit, never a fallback grant.
export type GeneralCompositionLab = Omit<CompositionLab, 'media'> & { media: CompositionLab['media'] | null };
