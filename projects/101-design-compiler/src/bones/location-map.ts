import { z } from 'zod';
import { rightsGate, evaluateSuitability } from '../media/gate.ts';
import { MediaAssetV1, MediaUsageV1 } from '../media/contracts.ts';

export const locationBone = {
  id: 'location.single-business', version: '0.2.0', family: 'location',
  variants: ['direct', 'map-led', 'editorial'],
  owner: { package: '@101/location-map', version: '0.3.0', commit: '6c0ed29940985bfb1789280c1972e47386775193' },
  review: 'pending-human-review',
  parts: [
    ['heading', 'Título', 'hueso + contenido'],
    ['business-name', 'Nombre del negocio', 'contenido con fuente'],
    ['address', 'Dirección de la sucursal', 'contenido con fuente'],
    ['directions', 'Abrir indicaciones', 'acción elegible del dueño'],
    ['map-viewport', 'Mapa y controles', 'primitiva de Tomás'],
    ['business-marker', 'Un único marcador geográfico', 'hueso; logo de piel validado'],
    ['marker-pin', 'Forma de pin y punta anclada', 'hueso; mismo destino con o sin logo'],
    ['brand-logo-slot', 'Espacio de logo dentro del pin', 'medio de marca con permisos'],
    ['provider-attribution', 'Créditos del proveedor', 'proveedor; no ocultables'],
    ['status-fallback', 'Estado y alternativa', 'hueso'],
  ],
} as const;
export type LocationVariant = typeof locationBone.variants[number];
export type LocationSkin = 'neutral' | 'paper' | 'ink';
// The original owner's locationInput remains the authority for geographic validation.
export const displayLocation = z.looseObject({
  business_id: z.string().min(1), location_id: z.string().min(1), name: z.string().min(1),
  address: z.string().optional(), publication_allowed: z.boolean(),
});
export type LocationDisplay = z.infer<typeof displayLocation>;
export type LogoEvidence = {
  asset: unknown; grant: unknown; usage: unknown; inventory: unknown[]; evaluatedAt: string;
};
export type LogoBinding = {
  kind: 'logo' | 'pin'; url?: string; asset_id?: string; sha256?: string;
  reason: string; credit?: string; synthetic?: boolean;
};
export type LocationBoneInput = {
  location: Record<string, unknown>;
  directions: { provider: string; label: string; url: string }[];
  marker: LogoBinding;
  synthetic: boolean;
};
export function bindLocationBone(owner: {
  locationInput: (value: unknown) => Record<string, unknown>;
  navigationLinks: (value: unknown) => { provider: string; label: string; url: string }[];
}, locationValue: unknown, evidence?: LogoEvidence, allowSynthetic = false): LocationBoneInput {
  const location = owner.locationInput(locationValue);
  const content = displayLocation.parse(location);
  const synthetic = (location['coordinate'] as { purpose?: string } | null)?.purpose === 'synthetic';
  return { location, directions: owner.navigationLinks(location),
    marker: resolveLocationLogo(content, evidence, allowSynthetic && synthetic), synthetic };
}

export function resolveLocationLogo(location: LocationDisplay, evidence?: LogoEvidence,
  allowSynthetic = false): LogoBinding {
  if (!evidence) return { kind: 'pin', reason: 'LOGO_MISSING' };
  const { asset, grant, usage, inventory, evaluatedAt } = evidence;
  const a = MediaAssetV1.safeParse(asset), u = MediaUsageV1.safeParse(usage);
  if (!a.success || !u.success) return { kind: 'pin', reason: 'LOGO_SCHEMA_INVALID' };
  if (a.data.kind !== 'image' || u.data.business_id !== location.business_id
    || u.data.scope_id !== location.location_id || u.data.purpose !== 'brand_identity'
    || u.data.module_id !== locationBone.id) return { kind: 'pin', reason: 'LOGO_SCOPE_MISMATCH' };
  // This consumes the existing attestations. It does not invent a second approval flag.
  const rights = rightsGate(asset, grant, usage, inventory, evaluatedAt, { allow_synthetic: allowSynthetic });
  const suitability = evaluateSuitability(a.data, u.data, evaluatedAt);
  const reasons = [...rights.codes, ...suitability];
  if (reasons.length) return { kind: 'pin', reason: reasons.join(',') };
  if (!/^\/(?!\/)[a-zA-Z0-9_./-]+\.(?:svg|png|webp|avif|jpe?g)$/.test(a.data.uri)
    || a.data.uri.split('/').includes('..')) return { kind: 'pin', reason: 'LOGO_LOCAL_ASSET_REQUIRED' };
  if (a.data.data_mode === 'REAL' && u.data.representation !== 'BUSINESS_EVIDENCE') {
    return { kind: 'pin', reason: 'LOGO_BUSINESS_IDENTITY_REQUIRED' };
  }
  return { kind: 'logo', url: a.data.uri, asset_id: a.data.id, sha256: a.data.file_sha256!,
    reason: 'LOGO_MEDIA_GATES_PASSED', synthetic: a.data.data_mode === 'SYNTHETIC_FIXTURE',
    ...(u.data.attribution_text ? { credit: u.data.attribution_text } : {}) };
}

export function locationVariant(value: string): LocationVariant {
  if (!(locationBone.variants as readonly string[]).includes(value)) throw Error('UNKNOWN_LOCATION_BONE');
  return value as LocationVariant;
}
export function locationSkin(value: string): LocationSkin {
  if (!['neutral', 'paper', 'ink'].includes(value)) throw Error('UNKNOWN_LOCATION_SKIN');
  return value as LocationSkin;
}

export const mapSkins = {
  neutral: { paper: '#f4f4f4', land: '#eeeeee', water: '#d9d9d9', road: '#ffffff',
    roadOutline: '#c8c8c8', building: '#dedede', ink: '#222222', pin: '#333333' },
  paper: { paper: '#f6f0e5', land: '#eee6d7', water: '#bcd3ce', road: '#fffdf7',
    roadOutline: '#d6c9b6', building: '#e2d5c2', ink: '#302d25', pin: '#7b4233' },
  ink: { paper: '#202b2c', land: '#273536', water: '#162527', road: '#59696a',
    roadOutline: '#3f4d4e', building: '#354445', ink: '#faf5e9', pin: '#faf5e9' },
} as const;
