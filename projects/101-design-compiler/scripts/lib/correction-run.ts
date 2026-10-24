import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import { performance } from 'node:perf_hooks';
import { createHash } from 'node:crypto';
import { z } from 'zod';

export const hashBytes = (bytes: Uint8Array | string) => createHash('sha256').update(bytes).digest('hex');
export function workspacePath(root: string, path: string) {
 const target = resolve(root, path), rel = relative(resolve(root), target);
 if (rel.startsWith('..') || isAbsolute(rel)) throw Error('B0_OUTSIDE_WORKSPACE');
 return target;
}
export function redactLog(text: string) {
 return text.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
  .replace(/([?&](?:key|token|api_key|access_token)=)[^\s&"']+/gi, '$1[REDACTED]')
  .replace(/((?:authorization|api[_-]?key|access[_-]?token)\s*[:=]\s*)(?:Bearer\s+)?[^\s,"']+/gi, '$1[REDACTED]')
  .replace(/\b\d{7,}-[a-f0-9]{20,}\b/gi, '[REDACTED]');
}
const digest = z.string().regex(/^[a-f0-9]{64}$/);
export const RunJournalV1 = z.strictObject({
 schema_version: z.literal('1.0.0'), kind: z.literal('B0_LOCAL_RUN_JOURNAL'),
 run_id: z.string().regex(/^[a-z0-9-]+$/), created_at: z.iso.datetime(),
 steps: z.array(z.strictObject({ id: z.string(), started_at: z.iso.datetime(), finished_at: z.iso.datetime(),
  wall_seconds: z.number().nonnegative(), exit_code: z.number().int(), status: z.enum(['PASS', 'FAIL', 'BLOCKED_HISTORICAL_ENVIRONMENT']),
  log: z.string(), log_sha256: digest })),
 metering: z.strictObject({ machine_time: z.literal('MEASURED_WALL_SECONDS'),
  human_work_seconds: z.null(), session_tokens: z.null(), session_cost: z.null(), total_cost: z.null(), currency: z.null(),
  provider_operations: z.literal('NOT_INVOKED_BY_THIS_RECIPE'), human_approval: z.literal('NOT_COLLECTED') })
});
export type RunJournal = z.infer<typeof RunJournalV1>;
export function newJournal(run_id: string): RunJournal {
 return RunJournalV1.parse({ schema_version: '1.0.0', kind: 'B0_LOCAL_RUN_JOURNAL', run_id, created_at: new Date().toISOString(), steps: [],
  metering: { machine_time: 'MEASURED_WALL_SECONDS', human_work_seconds: null, session_tokens: null, session_cost: null,
   total_cost: null, currency: null, provider_operations: 'NOT_INVOKED_BY_THIS_RECIPE', human_approval: 'NOT_COLLECTED' } });
}
export async function journalCommand(journal: RunJournal, directory: string, id: string, args: string[], expectedBrowserBlock = false) {
 if (!/^[a-z0-9-]+$/.test(id) || journal.steps.some(s => s.id === id)) throw Error('B0_DUPLICATE_OR_INVALID_STEP');
 await mkdir(directory, { recursive: true });
 const started_at = new Date().toISOString(), started = performance.now();
 const env = { ...process.env, ASTRO_TELEMETRY_DISABLED: '1', PATH: `${resolve('.tools/node-v24.21.0-win-x64')};${process.env.PATH ?? ''}` };
 const child = spawn(process.execPath, args, { cwd: process.cwd(), env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
 let output = '';
 child.stdout.on('data', bytes => { output += String(bytes); });
 child.stderr.on('data', bytes => { output += String(bytes); });
 const exit_code = await new Promise<number>((done, reject) => { child.on('error', reject); child.on('close', code => done(code ?? -1)); });
 const log = `${directory}/${id}.txt`, body = redactLog(output);
 await writeFile(log, body, 'utf8');
 const historical = expectedBrowserBlock && exit_code !== 0 && body.includes('LOCK_BROWSER_MISMATCH');
 const status = exit_code === 0 ? 'PASS' as const : historical ? 'BLOCKED_HISTORICAL_ENVIRONMENT' as const : 'FAIL' as const;
 journal.steps.push({ id, started_at, finished_at: new Date().toISOString(), wall_seconds: (performance.now() - started) / 1000,
  exit_code, status, log, log_sha256: hashBytes(body) });
 await writeFile(`${directory}/journal.json`, JSON.stringify(RunJournalV1.parse(journal), null, 2) + '\n');
 console.log(`${id}: ${status} (exit ${exit_code})`);
 return { status, body };
}
export async function treeHashes(root: string, prefix = ''): Promise<{ path: string; bytes: number; sha256: string }[]> {
 const paths: string[] = [];
 const walk = async (part: string) => {
  for (const entry of await readdir(workspacePath(root, part), { withFileTypes: true })) {
   const next = part ? `${part}/${entry.name}` : entry.name;
   if (entry.isSymbolicLink()) throw Error('B0_UNPINNED_SYMLINK');
   if (entry.isDirectory()) await walk(next); else if (entry.isFile()) paths.push(next);
  }
 };
 await walk(prefix);
 return Promise.all(paths.sort().map(async path => { const bytes = await readFile(workspacePath(root, path));
  return { path, bytes: bytes.length, sha256: hashBytes(bytes) }; }));
}
export async function verifyProtectedFiles(manifestPath: string) {
 const manifest = JSON.parse(await readFile(manifestPath, 'utf8')) as { files: { path: string; normalization: string; bytes: number; sha256: string }[] };
 const changed: string[] = [];
 for (const file of manifest.files) {
  try { const raw = await readFile(file.path), bytes = file.normalization === 'BINARY' ? raw : Buffer.from(raw.toString('utf8').replaceAll('\r\n', '\n'));
   if (bytes.length !== file.bytes || hashBytes(bytes) !== file.sha256) changed.push(file.path);
  } catch { changed.push(file.path); }
 }
 if (changed.length) throw Error(`B0_PROTECTED_FILES_CHANGED:${changed.join(',')}`);
 return { status: 'PASS', checked_files: manifest.files.length, normalization: 'AS_DECLARED_PER_FILE', changed: [] };
}
