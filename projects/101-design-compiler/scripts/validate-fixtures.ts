import { fixtureNames, loadFixture } from './load-fixtures.ts';
import { validateBundle } from '../src/validation/validate.ts';
import { checkPlannerFixtures } from './check-planner-fixtures.ts';
import { checkMediaFixtures } from './check-media-fixtures.ts';

let failures = 0;
for (const name of fixtureNames) {
  const result = validateBundle(await loadFixture(name));
  console.log(`${name}: ${result.success ? 'PASSED' : 'FAILED'}`);
  if (!result.success) { failures++; console.error(JSON.stringify(result.diagnostics, null, 2)); }
}
for (const fixture of await checkPlannerFixtures()) {
  console.log(`planner/${fixture.scenario}: ${fixture.success ? 'PASSED' : 'FAILED'} (${fixture.result.status})`);
  if (!fixture.success) { failures++; console.error(JSON.stringify([...fixture.result.diagnostics, ...fixture.validation.diagnostics], null, 2)); }
}
for (const fixture of await checkMediaFixtures()) {
  console.log(`media/${fixture.scenario}: ${fixture.success ? 'PASSED' : 'FAILED'} (${fixture.output.brief.closure})`);
  if (!fixture.success) { failures++; console.error(JSON.stringify(fixture.codes)); }
}
if (failures) process.exitCode = 1;
