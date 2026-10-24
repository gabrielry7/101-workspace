import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const cli = fileURLToPath(new URL('../scripts/audit-taxonomy.ts', import.meta.url));
async function removeOwnedTemp(directory: string) {
  const target = resolve(directory);
  assert.ok(target.startsWith(resolve(tmpdir()) + sep));
  assert.ok(target.split(sep).at(-1)?.startsWith('101-taxonomy-test-'));
  await rm(target, { recursive: true, force: true });
}
test('audit exits 2 without a real input file and does not invent coverage', async () => {
  const directory = await mkdtemp(join(tmpdir(), '101-taxonomy-test-'));
  try {
    await assert.rejects(execute(process.execPath, [cli], { cwd: directory }), (error: unknown) => {
      const failure = error as { code: number; stderr: string };
      assert.equal(failure.code, 2); assert.match(failure.stderr, /MISSING_REFERENCE_INVENTORY/); return true;
    });
    await assert.rejects(readFile(join(directory, 'data/derived/taxonomy-v1/coverage.json')));
    await assert.rejects(execute(process.execPath, [cli, 'data/reference/message (4).txt'], { cwd: directory }), (error: unknown) => {
      const failure = error as { code: number; stderr: string };
      assert.equal(failure.code, 2); assert.match(failure.stderr, /MISSING_REFERENCE_INVENTORY/); return true;
    });
  } finally { await removeOwnedTemp(directory); }
});
test('audit preserves every inventory row, separates providers, records unresolved cases and replays identically', async () => {
  const directory = await mkdtemp(join(tmpdir(), '101-taxonomy-test-'));
  try {
    await mkdir(join(directory, 'data/reference'), { recursive: true });
    const source = 'source\tcategory_field\tcategory_value\tprovider_category_id\tsource_observations\tbusiness_candidates\tother_observations\n'
      + 'osm\tshop\thardware\t\t100\t90\t10\n'
      + 'osm\tshop\tunknown_shop\t\t300\t10\t0\n'
      + 'osm\t101.normalized_category\tUnknown\t\t400\t100\t0\n'
      + 'osm\tamenity\tbench\t\t0\t0\t0\n'
      + 'overture\ttaxonomy.primary\thardware_store\t001\t100\t90\t10\n'
      + 'foursquare\t101.normalized_category\tProfessional Services/Other Professional\t\t100\t90\t10\n'
      + 'future-provider\tnew-field\tunknown\t\t100\t90\t10\n';
    await writeFile(join(directory, 'data/reference/synthetic.tsv'), source);
    await execute(process.execPath, [cli], { cwd: directory });
    const output = join(directory, 'data/derived/taxonomy-v1/coverage.json');
    const first = await readFile(output, 'utf8');
    const report = JSON.parse(first) as {
      unit: string; provider_summaries: { provider: string; inventory_rows: number }[];
      records: { counts: { business_candidates: number }; provenance: { file: string; sha256: string } }[];
      weighted_summaries: { provider: string; category_field: string; weights: { metric: string; total: number; mapped_fraction: number | null }[] }[];
      rule_coverage: { rule_id: string; resolved_inventory_rows: number }[];
    };
    assert.equal(report.unit, 'TAXONOMY_INVENTORY_ROWS_NOT_UNIQUE_BUSINESSES');
    assert.equal(report.records.length, 7); assert.equal(report.provider_summaries.length, 4);
    assert.ok(report.provider_summaries.every(x => !('business_candidates' in x)));
    assert.ok(report.records.every(x => x.provenance.file === 'data/reference/synthetic.tsv'));
    const shop = report.weighted_summaries.find(x => x.provider === 'osm' && x.category_field === 'shop')!;
    assert.equal(shop.weights.find(x => x.metric === 'source_observations')?.mapped_fraction, 0.25);
    assert.equal(shop.weights.find(x => x.metric === 'business_candidates')?.mapped_fraction, 0.9);
    assert.equal(shop.weights.find(x => x.metric === 'source_observations')?.total, 400);
    assert.ok(report.weighted_summaries.find(x => x.category_field === 'amenity')!.weights.every(x => x.mapped_fraction === null));
    assert.equal(report.rule_coverage.length, 67);
    assert.ok(report.rule_coverage.some(x => x.resolved_inventory_rows > 0));
    const unresolved = JSON.parse(await readFile(join(directory, 'data/derived/taxonomy-v1/unresolved.json'), 'utf8')) as { records: unknown[] };
    assert.equal(unresolved.records.length, 4);
    await execute(process.execPath, [cli], { cwd: directory });
    assert.equal(await readFile(output, 'utf8'), first);
  } finally { await removeOwnedTemp(directory); }
});
