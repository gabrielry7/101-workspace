import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultLocationControls, parseLocationControls } from '../src/bones/location-map-controls.js';

test('saved visual settings accept supported skins and compositions without business data', () => {
  for (const skin of ['neutral', 'paper', 'ink']) for (const variant of ['direct', 'map-led', 'editorial']) {
    const value = { ...defaultLocationControls, skin, variant, markerLabel: true, zoom: 18, mapHeight: 560 };
    assert.deepEqual(parseLocationControls(value), value);
  }
});

test('restoring settings rejects unknown controls, facts, secrets, stale versions and invalid bounds', () => {
  for (const edit of [
    { coordinate: [0, 0] }, { apiKey: 'TEST_NOT_A_KEY' }, { pois: { mode: 'all' } },
    { bone: 'location.single-business@0.2.0' }, { skin: 'invalid' }, { variant: 'invalid' },
    { markerLabel: 'false' }, { zoom: 19 }, { zoom: 2 }, { zoom: NaN },
    { mapHeight: 279 }, { mapHeight: 561 }, { pinPaper: 'url(https://example.invalid)' },
  ]) assert.throws(() => parseLocationControls({ ...defaultLocationControls, ...edit }));
  assert.throws(() => parseLocationControls(null));
  assert.throws(() => parseLocationControls({ skin: 'ink' }));
});
