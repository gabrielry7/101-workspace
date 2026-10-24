import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { relative, resolve } from 'node:path';
import { loadInventoryBytes } from '../src/taxonomy/inventory.ts';
import { resolveObservation } from '../src/taxonomy/resolve.ts';
import { loadMappingRegistry } from './load-taxonomy.ts';

const registry = await loadMappingRegistry();
const sourceDirectory = resolve('data/reference');
let paths: string[];
if (process.argv[2]) paths = [resolve(process.argv[2])];
else {
  try {
    paths = (await readdir(sourceDirectory, { withFileTypes: true }))
      .filter(entry => entry.isFile() && /\.(csv|tsv|txt)$/i.test(entry.name))
      .map(entry => resolve(sourceDirectory, entry.name)).sort();
  } catch { paths = []; }
}
if (!paths.length) {
  console.error('MISSING_REFERENCE_INVENTORY: add the original category file to data/reference/. No coverage figures generated.');
  process.exitCode = 2;
} else {
  const files = await Promise.all(paths.map(async path => {
    const bytes = await readFile(path).catch(error => {
      if (error.code === 'ENOENT') {
        console.error(`MISSING_REFERENCE_INVENTORY: ${path}. No coverage figures generated.`);
        process.exit(2);
      }
      throw error;
    });
    const file = relative(process.cwd(), path).replaceAll('\\', '/');
    return { file, sha256: createHash('sha256').update(bytes).digest('hex'), records: loadInventoryBytes(bytes, file) };
  }));
  const records = files.flatMap(file => file.records);
  if (!records.length) throw new Error('EMPTY_REFERENCE_INVENTORY: inventory has headers but no data rows');
  const resolutions = records.map(record => ({
    record,
    resolution: resolveObservation({
      id: record.id, source: record.provider_label, field: record.category_field, value: record.category_value,
      ...(record.provider_category_id ? { provider_category_id: record.provider_category_id } : {}),
      ...(record.normalized_category ? { normalized_category: record.normalized_category } : {}),
      hierarchy: record.hierarchy, evidence_ids: [], provenance: [],
    }, registry.rules),
  }));
  const provider_summaries = [...new Set(records.map(x => x.provider))].sort().map(provider => {
    const subset = resolutions.filter(x => x.record.provider === provider);
    const count = (outcome: string) => subset.filter(x => x.resolution.outcome === outcome).length;
    return { provider, inventory_rows: subset.length, mapped_rows: count('MAPPED'), ambiguous_rows: count('AMBIGUOUS'), non_business_rows: count('NON_BUSINESS'), unknown_rows: count('UNKNOWN'), unmapped_rows: count('UNMAPPED'), mapped_row_fraction: count('MAPPED') / subset.length };
  });
  // Keep aggregation layers apart: a normalized row and a source-category row
  // may count the same observations. These are inventory weights, never entities.
  const weighted_summaries = provider_summaries.flatMap(({ provider }) =>
    [...new Set(records.filter(x => x.provider === provider).map(x => x.category_field))].sort().map(category_field => {
      const subset = resolutions.filter(x => x.record.provider === provider && x.record.category_field === category_field);
      const weights = (['source_observations', 'business_candidates', 'other_observations'] as const).map(metric => {
        const sum = (outcome?: string) => {
          const result = subset.filter(x => !outcome || x.resolution.outcome === outcome)
            .reduce((total, x) => total + BigInt(x.record.counts[metric]), 0n);
          if (result > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error(`UNSAFE_WEIGHT_TOTAL: ${provider}/${category_field}/${metric}`);
          return Number(result);
        };
        const total = sum();
        return { metric, total, mapped: sum('MAPPED'), ambiguous: sum('AMBIGUOUS'),
          non_business: sum('NON_BUSINESS'), unknown: sum('UNKNOWN'), unmapped: sum('UNMAPPED'),
          mapped_fraction: total === 0 ? null : sum('MAPPED') / total };
      });
      return { provider, category_field, inventory_rows: subset.length, weights };
    }));
  const rule_coverage = registry.rules.map(rule => ({
    rule_id: rule.id, provider: rule.provider,
    resolved_inventory_rows: resolutions.filter(x => x.resolution.rule_ids.includes(rule.id)).length,
  }));
  const report = {
    schema_version: '1.0.0', registry_version: registry.version,
    registry_sha256: createHash('sha256').update(registry.bytes).digest('hex'),
    sources: files.map(({ records, ...source }) => ({ ...source, inventory_rows: records.length })),
    unit: 'TAXONOMY_INVENTORY_ROWS_NOT_UNIQUE_BUSINESSES',
    counts_policy: 'Weights are inventory mentions, not unique businesses. Aggregate only within provider and category_field; never across providers or taxonomy layers. Zero denominator yields null.',
    provider_summaries, weighted_summaries, rule_coverage,
    records: resolutions.map(({ record, resolution }) => ({
      ...record, mapping: {
        outcome: resolution.outcome, archetypes: resolution.archetypes, alternatives: resolution.alternatives,
        rule_ids: resolution.rule_ids, diagnostics: resolution.diagnostics,
      },
    })),
  };
  const directory = resolve('data/derived/taxonomy-v1');
  await mkdir(directory, { recursive: true });
  await writeFile(resolve(directory, 'coverage.json'), JSON.stringify(report, null, 2) + '\n');
  await writeFile(resolve(directory, 'unresolved.json'), JSON.stringify({
    schema_version: '1.0.0', sources: report.sources, registry_sha256: report.registry_sha256,
    records: report.records.filter(x => ['UNMAPPED', 'UNKNOWN', 'AMBIGUOUS'].includes(x.mapping.outcome)),
  }, null, 2) + '\n');
  console.log(JSON.stringify({ sources: report.sources, provider_summaries, unit: report.unit }, null, 2));
}
