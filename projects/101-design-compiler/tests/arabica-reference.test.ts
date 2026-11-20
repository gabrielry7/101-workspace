import { test } from 'node:test';
import assert from 'node:assert/strict';
import { referenceViewId, referenceHref, offsetCamera, validateReferenceCatalogue } from '../src/references/arabica-locations.js';

test('official hierarchy links are local; unrelated websites and branch details are not intercepted', () => {
  assert.equal(referenceViewId('https://arabica.com/en/locations/'), 'world');
  assert.equal(referenceViewId('https://arabica.com/en/locations/japan/kyoto/'), 'japan/kyoto');
  assert.equal(referenceViewId('https://arabica.com/en/location/branch/'), null);
  assert.equal(referenceViewId('https://other.example/en/locations/japan/'), null);
  assert.equal(referenceViewId('https://arabica.com/en/locations-other/'), null);
  assert.equal(referenceHref('japan/kyoto'), '/arabica/?view=japan%2Fkyoto');
  assert.throws(() => referenceHref('../escape'));
});

test('camera offsets preserve the measured geographic anchor and mobile removes the desktop offset', () => {
  const original = [138.252924, 36.204824];
  assert.deepEqual(offsetCamera(original, 2, 390), original);
  const [longitude, latitude] = offsetCamera(original, 2, 1440);
  assert.ok(Math.abs(longitude - 103.096674) < 0.000001);
  assert.ok(latitude < original[1]);
  assert.deepEqual(original, [138.252924, 36.204824]);
});

test('missing coordinates, public-scope inputs and incomplete hierarchy are rejected', () => {
  const input: any = { schema: '101-arabica-reference-v1', referenceOnly: true, publicationAllowed: false,
    observedAt: '2026-11-17T00:00:00Z', pages: [{ id: 'world', url: 'https://arabica.com/en/locations/',
      center: [0, 0], zoom: 2, level: 'world', mapStyle: [], links: [], markers: [], cards: [] }] };
  assert.equal(validateReferenceCatalogue(input), input);
  const invalid = structuredClone(input); invalid.pages[0].center = null;
  assert.throws(() => validateReferenceCatalogue(invalid), /INVALID_REFERENCE_PAGE/);
  assert.throws(() => validateReferenceCatalogue({ ...input, publicationAllowed: true }), /PRIVATE_REFERENCE/);
  const missing = structuredClone(input); missing.pages[0].links.push({name:'Example',count:1,url:'https://arabica.com/en/locations/missing/'});
  assert.throws(() => validateReferenceCatalogue(missing), /REFERENCE_VIEW_MISSING/);
});
