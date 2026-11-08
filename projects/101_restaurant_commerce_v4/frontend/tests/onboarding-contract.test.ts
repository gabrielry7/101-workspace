import assert from 'node:assert/strict';
import test from 'node:test';
import { parseBusinesses } from '../src/onboarding-contract.ts';

test('bulk CSV preserves quoted names and normalizes optional domains', () => {
  assert.deepEqual(parseBusinesses('nombre,enlace,dominio\r\n"Tienda, Norte",tienda-norte,SHOP.EXAMPLE.TEST.\r\n"La ""Aurora""",aurora,\n'), [
    { name: 'Tienda, Norte', slug: 'tienda-norte', custom_hostname: 'shop.example.test' },
    { name: 'La "Aurora"', slug: 'aurora' },
  ]);
});
test('reject ambiguous or conflicting batches before any server mutation', () => {
  for (const input of ['', '"Sin cerrar,slug', 'Nombre,slug,https://example.test', 'Nombre,a', 'Nombre,SLUG', 'Nombre,slug,one.test,extra', 'Uno,same\nDos,same', 'Uno,one,shop.test\nDos,two,SHOP.TEST', '"Name"junk,slug']) assert.throws(() => parseBusinesses(input), input);
  assert.equal(parseBusinesses(Array.from({length:100},(_,i)=>`Demo ${i},demo-${i}`).join('\n')).length,100);
  assert.throws(() => parseBusinesses(Array.from({length:101},(_,i)=>`Demo ${i},demo-${i}`).join('\n')));
});
