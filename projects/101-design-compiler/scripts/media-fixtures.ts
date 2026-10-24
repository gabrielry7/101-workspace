import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { checkMediaFixtures } from './check-media-fixtures.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';

const directory = resolve('data/derived/media-v1');
const replay = process.argv.includes('--replay');
if (!replay) await mkdir(directory, { recursive: true });
for (const fixture of await checkMediaFixtures()) {
  const body = JSON.stringify(fixture.output, null, 2) + '\n';
  const file = resolve(directory, `${fixture.scenario}.json`);
  const identical = !replay || await readFile(file, 'utf8') === body;
  if (!replay) await writeFile(file, body);
  console.log(JSON.stringify({ scenario: fixture.scenario, success: fixture.success && identical,
    manifest_sha256: inputSha256(fixture.output.manifest), needs: fixture.output.manifest.needs.length,
    gaps: fixture.output.brief.gaps.length, allowed: fixture.output.manifest.decisions.filter(x => x.status === 'ALLOWED').length,
    closure: fixture.output.brief.closure,
    synthetic_test_only: fixture.scenario.startsWith('synthetic-permission'), codes: fixture.codes, replay_identical: replay ? identical : null }));
  if (!fixture.success || !identical) process.exitCode = 1;
}
