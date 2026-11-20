import { test } from 'node:test';
import assert from 'node:assert/strict';
import { locationDirectorySchema, neutralLocationDirectory, locationDirectoryAnatomy } from '../src/bones/location-directory.ts';

test('neutral hierarchy has identifiable unique parts, unbound images/actions and unknown counts', () => {
  const c = locationDirectorySchema.parse(neutralLocationDirectory);
  const parts = locationDirectoryAnatomy(c);
  assert.equal(new Set(parts.map(p => p.id)).size, parts.length);
  assert.ok(parts.some(p => p.kind === 'integration-slot'));
  assert.ok(c.views.flatMap(v => v.groups.flatMap(g => g.items)).some(item => item.count === null));
  assert.ok(c.views.flatMap(v => v.cards).every(card => card.action.state === 'unbound'));
});

test('invalid hierarchy and scope-breaking placeholders are rejected', () => {
  const change = (fn: (value: any) => void) => { const c = structuredClone(neutralLocationDirectory); fn(c); return c; };
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views.push(c.views[0]))), /VIEW_ID_DUPLICATE/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[1].parentId = 'missing')), /PARENT_VIEW_REQUIRED/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[1].parentId = 'region-1/city-1')), /PARENT_CYCLE/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[0].groups[0].items[0].viewId = 'missing')), /TARGET_VIEW_REQUIRED/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[1].level = 'locality')), /PARENT_LEVEL_INVALID/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[1].entries[0].viewId = 'region-2/city-3')), /TARGET_LEVEL_INVALID/);
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[0].groups[0].items[0].count = -1)));
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[0].cards[0].imageURL = 'https://unrelated.invalid/photo.jpg')));
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[0].cards[0].action = {state:'available',href:'javascript:alert(1)'})));
  assert.throws(() => locationDirectorySchema.parse(change(c => c.views[0].cards[0].action = {state:'unbound',href:'/unexpected/'})));
});

test('optional empty local group and long labels remain distinct from a fabricated zero', () => {
  const c = structuredClone(neutralLocationDirectory);
  c.title = 'Título de ubicaciones con varias palabras para comprobar su ajuste';
  c.views[0].groups[1].items[0].label = 'Región con un nombre largo y varias palabras';
  const parsed = locationDirectorySchema.parse(c);
  assert.equal(parsed.views[0].groups[1].items[0].count, null);
  assert.equal(parsed.views.find(v => v.id === 'region-3')!.entries.length, 0);
});
