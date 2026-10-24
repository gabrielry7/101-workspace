import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { checkPlannerFixtures } from './check-planner-fixtures.ts';

const directory = resolve('data/derived/planner-v1');
await mkdir(directory, { recursive: true });
const fixtures = await checkPlannerFixtures();
for (const fixture of fixtures) {
  await writeFile(resolve(directory, `${fixture.scenario}.json`), JSON.stringify(fixture.result, null, 2) + '\n');
  console.log(JSON.stringify({ scenario: fixture.scenario, status: fixture.result.status, expected: fixture.expected_status,
    modules: fixture.result.status === 'READY' ? fixture.result.plan.pages.flatMap(x => x.modules.map(m => `${m.scope_id}:${m.capability_id}`)) : [],
    diagnostics: fixture.result.diagnostics, success: fixture.success }));
}
if (fixtures.some(x => !x.success)) process.exitCode = 1;
