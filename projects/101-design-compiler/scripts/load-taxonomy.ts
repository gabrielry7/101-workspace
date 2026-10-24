import { readFile } from 'node:fs/promises';
import { MappingRegistryV1 } from '../src/taxonomy/contracts.ts';
import { validateRegistry } from '../src/taxonomy/resolve.ts';

export async function loadMappingRegistry() {
  const bytes = await readFile(new URL('../taxonomy/v1/mappings.json', import.meta.url));
  const registry = MappingRegistryV1.parse(JSON.parse(bytes.toString('utf8')) as unknown);
  return { version: registry.schema_version, rules: validateRegistry(registry.rules), bytes };
}
