import { mkdir, access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { newJournal, journalCommand, verifyProtectedFiles } from './lib/correction-run.ts';
const id = process.argv[2];
if (!id || !/^[a-z0-9-]+$/.test(id)) throw Error('Usage: b0-baseline.ts <new-run-id>');
const directory = `docs/evidence/corrections/b0/${id}`;
if (await access(directory).then(() => true, () => false)) throw Error('B0_RUN_ALREADY_EXISTS');
await mkdir(directory, { recursive: true });
const journal = newJournal(id), npm = resolve('.tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js');
const steps: [string, string[], boolean?][] = [
 ['tests', [npm, 'test'], true], ['check', [npm, 'run', 'check']], ['validate', [npm, 'run', 'validate']],
 ['build', [npm, 'run', 'build']], ['contracts', [npm, 'run', 'contracts:export']], ['taxonomy', [npm, 'run', 'taxonomy:audit']],
 ['planner-replay', ['--experimental-strip-types', 'scripts/plan-fixtures.ts', '--replay']],
 ...['media:replay','media:verify','composition:replay','composition:verify','design:replay','design:verify','audit:verify','cohort:replay','cohort:verify'].map(task => [task.replace(':','-'), [npm,'run',task]] as [string,string[]]),
 ['lock-verify', [npm,'run','lock:verify','--','--rebuild'], true],
 ['h9-inventory', ['--experimental-strip-types','scripts/inventory-h9.ts','--verify']]
];
let failed = false;
for (const [name,args,historical] of steps) {
 const result = await journalCommand(journal,directory,name,args,historical);
 if (name === 'tests' && result.status === 'BLOCKED_HISTORICAL_ENVIRONMENT' && !/\b(?:fail|failed)\s+1\b/.test(result.body)) failed = true;
 if (result.status === 'FAIL') failed = true;
}
console.log(JSON.stringify(await verifyProtectedFiles('docs/evidence/corrections/b0/pre/protected-files.json')));
if (failed) process.exitCode = 1;
