import test from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { bindLocationBone, resolveLocationLogo, locationVariant, displayLocation } from '../src/bones/location-map.ts';
import { fixtureLocation, fixtureLogoEvidence } from '../src/bones/location-map-fixture.ts';
import { fixedPresentation } from '../src/bones/location-map-runtime.js';
import { googleConfiguration } from '../src/bones/location-map-google.js';

test('single-business policy rejects all ways to reactivate nearby businesses or alter facts', () => {
  assert.deepEqual(fixedPresentation({ zoom: 16 }).pois, { mode: 'none', ids: [], limit: 0 });
  for (const value of [{ pois: { mode: 'all' } }, { pois: { mode: 'selected', ids: ['other'] } },
    { pois: { mode: 'none', limit: 1 } }, { coordinate: [1, 2] }, { provider: 'google_embed' },
    { decorateMap: true }, { contextPreview: true }, { colors: {}, mapId: 'other' }]) {
    assert.throws(() => fixedPresentation(value));
  }
  assert.throws(() => locationVariant('new-layout'));
});

test('logo consumes existing media gates and synthetic opt-in, never an approval boolean', () => {
  const evidence = fixtureLogoEvidence();
  const content = displayLocation.parse(fixtureLocation);
  assert.equal(resolveLocationLogo(content).reason, 'LOGO_MISSING');
  assert.equal(resolveLocationLogo(content, evidence).kind, 'pin');
  assert.equal(resolveLocationLogo(content, evidence, true).kind, 'logo');
  assert.equal(resolveLocationLogo(content, { ...evidence, asset: { approved: true, uri: '/x.svg' } }, true).kind, 'pin');
});

test('logo failures: other branch, revoked, expired, unknown inspection and unsafe URL', () => {
  const content = displayLocation.parse(fixtureLocation);
  const mutations: ((e: ReturnType<typeof fixtureLogoEvidence>) => void)[] = [
    e => { (e.usage as any).scope_id = 'other-branch'; },
    e => { (e.usage as any).business_id = 'other-business'; },
    e => { (e.grant as any).revoked = true; },
    e => { (e.grant as any).valid_until = '2026-10-10T00:00:00Z'; },
    e => { (e.asset as any).inspection.quality = 'UNKNOWN'; },
    e => { (e.asset as any).uri = '//external.example/logo.svg'; },
    e => { (e.asset as any).uri = '/../../logo.svg'; },
  ];
  for (const mutate of mutations) {
    const evidence = fixtureLogoEvidence(); mutate(evidence);
    assert.equal(resolveLocationLogo(content, evidence, true).kind, 'pin');
  }
});

test('Google configuration needs a real map ID and matching reviewed cloud style', () => {
  const value = { enabled: true, apiKey: 'TEST_CONFIG_NOT_A_KEY', mapId: 'test-map',
    styleReview: { mapId: 'test-map', pois: 'none', reference: 'synthetic-review', reviewedAt: '2026-11-05T00:00:00Z' } };
  assert.equal(googleConfiguration(undefined), null);
  assert.equal(googleConfiguration(value), value);
  for (const edit of [{ ...value, enabled: false }, { ...value, mapId: 'DEMO_MAP_ID' },
    { ...value, enabled: 'yes' },
    { ...value, apiKey: '' }, { ...value, styleReview: { ...value.styleReview, pois: 'all' } },
    { ...value, styleReview: { ...value.styleReview, mapId: 'another' } }]) assert.equal(googleConfiguration(edit), null);
});

test('actual pinned owner preserves coordinates, rejects restricted reuse and cannot navigate synthetic input', async context => {
  let owner;
  try { owner = await import(pathToFileURL(resolve('.tools/bones-handoff-20261105/source/packages/location-map/src/contract.js')).href); }
  catch { context.skip('Private pinned owner not restored; run the documented private preview checks separately.'); return; }
  const input = bindLocationBone(owner, fixtureLocation, fixtureLogoEvidence(), true);
  assert.equal(input.marker.kind, 'logo'); assert.deepEqual(input.directions, []);
  assert.deepEqual(input.location['coordinate'], fixtureLocation.coordinate);
  const real = structuredClone(fixtureLocation) as any;
  real.coordinate.purpose = 'listing'; real.coordinate.source.kind = 'google_places';
  real.coordinate.source.map_use = 'requires_google_map';
  const bound = owner.locationInput(real);
  assert.equal(owner.rendererEligibility(bound, 'maplibre').render, false);
  assert.equal(owner.rendererEligibility(bound, 'google_embed').render, true);
  real.coordinate = null;
  assert.equal(owner.rendererEligibility(owner.locationInput(real), 'maplibre').render, false);
  assert.equal(owner.rendererEligibility(owner.locationInput(real), 'google_embed').render, false);
});
