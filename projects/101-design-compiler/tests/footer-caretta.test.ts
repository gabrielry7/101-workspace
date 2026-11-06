import assert from 'node:assert/strict';
import { test } from 'node:test';
import { carettaFooterBone, footerContentSchema, footerAnatomy, neutralFooter } from '../src/bones/footer-caretta.ts';

test('neutral footer covers source anatomy once, with no brand content or destinations', () => {
  const content = footerContentSchema.parse(neutralFooter);
  assert.deepEqual(content.groups.map(group => group.items.length), [5, 4, 5, 10]);
  assert.equal(content.groups.flatMap(group => group.items).filter(item => item.state === 'upcoming').length, 5);
  const parts = footerAnatomy(content);
  assert.equal(new Set(parts.map(part => part.id)).size, parts.length);
  assert.deepEqual(parts.filter(part => part.kind === 'region').map(part => part.id), [...carettaFooterBone.regions]);
  assert.ok(parts.some(part => part.id === 'social-1-text' && part.label === 'Texto de red social 1'));
  assert.ok(!JSON.stringify(content).includes('Caretta'));
  assert.ok(!JSON.stringify(content).includes('href'));
});

test('binding available actions retains labels, anatomy, destinations and version', () => {
  const content = structuredClone(neutralFooter);
  content.social = { ...content.social, state: 'available', href: 'https://example.com/social' };
  content.email = { ...content.email, state: 'available', href: 'mailto:hello@example.com' };
  content.legal[0] = { ...content.legal[0]!, state: 'available', href: '/privacy/' };
  const bound = footerContentSchema.parse(content);
  assert.equal(bound.social.href, 'https://example.com/social');
  assert.deepEqual(footerAnatomy(bound).map(part => part.id), footerAnatomy().map(part => part.id));
  assert.equal(carettaFooterBone.version, '0.1.0');
});

test('rejects unsafe destinations, upcoming links and missing required content', () => {
  for (const href of ['javascript:alert(1)', 'data:text/html,x', '//evil.example', '/\\evil.example',
    'https://user:password@example.com', ' https://example.com', 'https://example.com\n']) {
    const content = structuredClone(neutralFooter);
    content.social = { ...content.social, state: 'available', href };
    assert.equal(footerContentSchema.safeParse(content).success, false, href);
  }
  const upcoming = structuredClone(neutralFooter);
  upcoming.groups[1].items[0]!.href = '/future/';
  assert.equal(footerContentSchema.safeParse(upcoming).success, false);
  const empty = structuredClone(neutralFooter);
  empty.brandLogo = '   ';
  assert.equal(footerContentSchema.safeParse(empty).success, false);
  const wrongCount = structuredClone(neutralFooter);
  wrongCount.groups[0].items.pop();
  assert.equal(footerContentSchema.safeParse(wrongCount).success, false);
});

test('rejects colliding part IDs including generated children and structural regions', () => {
  for (const duplicate of ['transition', 'social-1-text', 'group-1-title']) {
    const content = structuredClone(neutralFooter);
    content.email.id = duplicate;
    assert.equal(footerContentSchema.safeParse(content).success, false, duplicate);
  }
  const content = structuredClone(neutralFooter);
  content.social.state = 'available';
  assert.equal(footerContentSchema.safeParse(content).success, false, 'available requires destination');
});
