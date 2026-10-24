import { readFile, readdir } from 'node:fs/promises';
import { z } from 'zod';
import { BusinessInputV1 } from '../src/contracts/v1/schemas.ts';
import { ActivityRelationshipV1 } from '../src/taxonomy/contracts.ts';
import { fixtureNames, loadFixture } from './load-fixtures.ts';

const Fixture = z.strictObject({
  scenario: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/), expected_status: z.enum(['READY', 'CONTENT_BLOCKED']),
  input: BusinessInputV1, activity_relationships: z.array(ActivityRelationshipV1),
});
export type PlannerFixture = z.infer<typeof Fixture>;
export async function loadPlannerFixtures(): Promise<PlannerFixture[]> {
  const original = await Promise.all(fixtureNames.map(async scenario => {
    const fixture = await loadFixture(scenario) as { input: unknown };
    return Fixture.parse({ scenario, expected_status: 'READY', input: fixture.input, activity_relationships: [] });
  }));
  const folder = new URL('../fixtures/planner/v1/', import.meta.url);
  const names = (await readdir(folder)).filter(name => name.endsWith('.json')).sort();
  const added = await Promise.all(names.map(async name => Fixture.parse(JSON.parse(await readFile(new URL(name, folder), 'utf8')))));
  if (added.some(x => x.input.data_mode !== 'SYNTHETIC_FIXTURE')) throw new Error('PLANNER_FIXTURE_MUST_BE_SYNTHETIC');
  if (new Set([...original, ...added].map(x => x.scenario)).size !== original.length + added.length) throw new Error('DUPLICATE_PLANNER_SCENARIO');
  return [...original, ...added];
}
