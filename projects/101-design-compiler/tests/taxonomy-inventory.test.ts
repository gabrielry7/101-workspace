import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { loadInventoryBytes } from '../src/taxonomy/inventory.ts';
import { classifyBusiness } from '../src/taxonomy/resolve.ts';
import { loadMappingRegistry } from '../scripts/load-taxonomy.ts';
import { loadFixture } from '../scripts/load-fixtures.ts';
import { BusinessInputV1 } from '../src/contracts/v1/schemas.ts';

test('the complete real taxonomy inventory cannot activate operational capabilities', async () => {
  const bytes = await readFile(new URL('../data/reference/message (4).txt', import.meta.url));
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  assert.equal(sha256, 'ef6e8856e431e6414b5826887cabafb12667f8c0bba4a9d3998d91b747de5f80');
  const records = loadInventoryBytes(bytes, 'data/reference/message (4).txt');
  assert.equal(records.length, 4582);
  const { rules } = await loadMappingRegistry();
  assert.equal(rules.length, 67);
  const fixture = await loadFixture('gimnasio') as { input: unknown };
  // Reuse one explicitly synthetic probe. Inventory rows are never real businesses.
  const probe = BusinessInputV1.parse(fixture.input);
  probe.business_capabilities = [];
  probe.offerings = [];
  for (const record of records) {
    assert.equal(record.category_value, record.raw['category_value']);
    assert.equal(record.provider_label, record.raw['source']);
    assert.equal(record.provenance.sha256, sha256);
    probe.category_observations = [{
      id: record.id, source: record.provider_label, field: record.category_field,
      value: record.category_value, confidence: 0, evidence_ids: [],
      ...(record.provider_category_id ? { provider_category_id: record.provider_category_id } : {}),
    }];
    const before = JSON.stringify(probe);
    const result = classifyBusiness(probe, { rules });
    assert.equal(JSON.stringify(probe), before, record.id);
    assert.deepEqual(probe.business_capabilities, [], record.id);
    assert.ok(result.candidate_capabilities.every(x => x.authority === 'RELEVANCE_ONLY_NOT_VERIFIED'), record.id);
    assert.ok(!('capabilities' in result) && !('site_plan' in result), record.id);
  }
});
