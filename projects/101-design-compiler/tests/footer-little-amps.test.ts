import assert from 'node:assert/strict';
import { test } from 'node:test';
import { littleAmpsActionSchema, littleAmpsContentSchema, littleAmpsAnatomy, littleAmpsBone, neutralLittleAmps, socialMediaBriefs } from '../src/bones/footer-little-amps.ts';

test('Little Amps anatomy separates graphics, embed and eleven individually classified media slots', () => {
  const parts = littleAmpsAnatomy();
  assert.equal(new Set(parts.map(part => part.id)).size, parts.length);
  assert.equal(parts.filter(part => part.kind === 'media-slot').length, 11);
  assert.equal(parts.filter(part => part.kind === 'embed-slot').length, 1);
  assert.equal(parts.filter(part => part.kind === 'graphic-slot').length, 2);
  assert.equal(socialMediaBriefs.filter(item => item.type === 'event-poster').length, 1);
  assert.deepEqual(neutralLittleAmps.menus.map(menu => menu.items.length), [3, 5]);
  assert.equal(littleAmpsBone.composition.playerDesktopMin, 1201);
  assert.equal(littleAmpsBone.review, 'pending-human-review');
});

test('neutral content contains no customer content, media URLs, skin or live destinations', () => {
  const json = JSON.stringify(littleAmpsContentSchema.parse(neutralLittleAmps));
  for (const token of ['Little Amps', 'State Street', 'Green Street', 'https:', 'mailto:', 'href', 'font', 'color', 'src']) {
    assert.ok(!json.includes(token), token);
  }
});

test('binding native actions leaves fixed composition and anatomy intact', () => {
  const content = structuredClone(neutralLittleAmps);
  content.logo = { ...content.logo, state: 'available', href: '/' };
  content.followGraphic = { ...content.followGraphic, state: 'available', href: 'https://example.com/social' };
  content.email = { ...content.email, state: 'available', href: 'mailto:hello@example.com' };
  const parsed = littleAmpsContentSchema.parse(content);
  assert.equal(parsed.email.href, 'mailto:hello@example.com');
  assert.deepEqual(parsed.gallery, neutralLittleAmps.gallery);
});

test('unsafe destinations and unavailable actions cannot become links', () => {
  for (const href of ['javascript:alert(1)', 'data:text/html,test', '//evil.example', '/\\evil.example',
    'https://user:password@example.com', 'https://example.com\n', ' https://example.com', 'ftp://example.com']) {
    assert.equal(littleAmpsActionSchema.safeParse({ label: 'Acción', state: 'available', href }).success, false, href);
  }
  assert.equal(littleAmpsActionSchema.safeParse({ label: 'Acción', state: 'available' }).success, false);
  assert.equal(littleAmpsActionSchema.safeParse({ label: 'Acción', state: 'unbound', href: '/' }).success, false);
});

test('incomplete structure and media/skin injection are rejected rather than silently changing layout', () => {
  for (const change of [
    (value: any) => { value.gallery.pop(); },
    (value: any) => { value.addresses = []; },
    (value: any) => { value.menus[1].items.pop(); },
    (value: any) => { value.logo.label = ''; },
    (value: any) => { value.gallery[0] = { src: 'https://example.com/photo.jpg' }; },
    (value: any) => { value.player = { src: 'https://open.spotify.com/embed' }; },
    (value: any) => { value.skin = { font: 'Other', columns: 3 }; },
  ]) {
    const value = structuredClone(neutralLittleAmps);
    change(value);
    assert.equal(littleAmpsContentSchema.safeParse(value).success, false);
  }
});
