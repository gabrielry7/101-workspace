import { createHash } from 'node:crypto';
import { permissionFixture, syntheticReview } from '../../fixtures/media/v1/permissions.ts';
import { proposeUsage } from '../media/plan.ts';
import { resolveLocationLogo } from './location-map.ts';
import type { LogoEvidence, LocationBoneInput } from './location-map.ts';

export const fixtureLogo = '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="90" viewBox="0 0 180 90"><text x="90" y="57" text-anchor="middle" fill="#222" font-family="Arial,sans-serif" font-size="42">Logo</text></svg>';
export const fixtureLocation = {
  schema_version: 1, business_id: 'synthetic-business', location_id: 'synthetic-location',
  name: 'Nombre del negocio', address: 'Dirección de la sucursal · dato de prueba',
  google: { place_id: 'synthetic-no-google-listing' }, publication_allowed: false,
  binding: { business_id: 'synthetic-business', location_id: 'synthetic-location', evidence_ref: 'synthetic:location-bone-v1' },
  coordinate: { latitude: 6.125, longitude: -75.425, purpose: 'synthetic', source: {
    kind: 'synthetic', reference: 'synthetic:location-bone-v1', observed_at: '2026-11-05T00:00:00Z', map_use: 'permitted' } },
};
export function fixtureLogoEvidence(): LogoEvidence {
  const need = { id: 'synthetic-logo-need', requirement_id: 'LM-03', module_id: 'location.single-business',
    page: '/', scope_id: fixtureLocation.location_id, purpose: 'brand_identity', role: 'ILLUSTRATIVE' as const,
    subject_ids: [], kinds: ['image' as const], required: false, count: 1, min_width: null, min_height: null };
  const { asset, grant } = permissionFixture(need, fixtureLocation.business_id);
  const sha = createHash('sha256').update(fixtureLogo).digest('hex');
  asset.uri = '/fixture-logo.svg'; asset.original_sha256 = sha; asset.file_sha256 = sha;
  asset.hash_review = syntheticReview(sha); asset.relevance[0]!.review = syntheticReview(sha);
  asset.inspection.review = syntheticReview(sha); asset.inspection.width = 180; asset.inspection.height = 90;
  asset.inspection.subject = 'Texto Logo sobre fondo transparente: espacio gráfico de prueba, ninguna empresa real.';
  asset.inspection.findings = ['SYNTHETIC_TEST_ASSET; NOT A REAL BRAND OR LEGAL GRANT'];
  grant.original_sha256 = sha;
  const usage = proposeUsage(need, asset, { client_id: 'synthetic-client', project_id: 'synthetic-project',
    business_id: fixtureLocation.business_id, evaluated_at: '2026-11-05T00:00:00Z' }, grant.id);
  usage.generic_label = 'Logo de prueba; no representa una empresa real.';
  return { asset, grant, usage, inventory: [asset], evaluatedAt: '2026-11-05T00:00:00Z' };
}
export function fixtureLocationInput(): LocationBoneInput {
  return { location: structuredClone(fixtureLocation), synthetic: true, directions: [],
    marker: resolveLocationLogo(fixtureLocation, fixtureLogoEvidence(), true) };
}
