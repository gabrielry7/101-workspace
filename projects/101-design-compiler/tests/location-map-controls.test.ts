import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultLocationControls, parseLocationControls } from '../src/bones/location-map-controls.js';
import { locationEditorDefaults, locationEditorFields, locationEditorGroups, mapEditorOptions,
  parseLocationEditor, parseOpenFreeMapOptions } from '../src/bones/location-map-editor.ts';
import { mapSkins } from '../src/bones/location-map.ts';

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

test('every OpenFreeMap editor field appears once and can round-trip independently', () => {
  const fields = locationEditorGroups.flatMap(group => group.fields);
  assert.deepEqual(fields.slice().sort(), Object.keys(locationEditorFields).sort());
  const defaults = locationEditorDefaults(mapSkins.paper);
  assert.deepEqual(parseLocationEditor(defaults), defaults);
  assert.deepEqual(parseOpenFreeMapOptions(mapEditorOptions(defaults)), mapEditorOptions(defaults));
  for (const name of fields) {
    const field = locationEditorFields[name];
    const next = field.kind === 'color' ? '#123abc' : field.kind === 'checkbox' ? !defaults[name]
      : field.kind === 'range' ? field.max : Object.keys(field.options).at(-1);
    const edited = { ...defaults, [name]: next };
    assert.deepEqual(parseLocationEditor(JSON.parse(JSON.stringify(edited))), edited);
  }
});

test('OpenFreeMap editor rejects changes to geography and invalid styling values', () => {
  const defaults = locationEditorDefaults(mapSkins.paper);
  for (const patch of [
    { coordinate: [0, 0] }, { showPois: true }, { source: 'other' }, { pitch: 61 }, { pinScale: 0 },
    { land: 'url(https://example.invalid)' }, { roadCap: 'unknown' }, { dragPan: 'true' }, { logoScale: NaN },
  ]) assert.throws(() => parseLocationEditor({ ...defaults, ...patch }), /INVALID_LOCATION_EDITOR/);
});
