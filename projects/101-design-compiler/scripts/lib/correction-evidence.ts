import { readFile } from 'node:fs/promises';
import { RunJournalV1, hashBytes, workspacePath } from './correction-run.ts';

export async function verifyJournal(path:string,baseline=false) {
 const journal=RunJournalV1.parse(JSON.parse(await readFile(path,'utf8')));
 const ids=new Set<string>();
 for(const step of journal.steps) {
  if(ids.has(step.id))throw Error('B0_DUPLICATE_STEP');ids.add(step.id);
  workspacePath(process.cwd(),step.log);
  const body=await readFile(step.log,'utf8');
  if(hashBytes(body)!==step.log_sha256)throw Error('B0_LOG_CHANGED');
  if(Date.parse(step.finished_at)<Date.parse(step.started_at))throw Error('B0_INVALID_TIMING');
  if(step.status==='PASS'&&step.exit_code!==0)throw Error('B0_STATUS_EXIT_MISMATCH');
  if(step.status==='FAIL'||(step.status==='BLOCKED_HISTORICAL_ENVIRONMENT'&&
   (!['tests','lock-verify'].includes(step.id)||step.exit_code!==1||!body.includes('LOCK_BROWSER_MISMATCH')||
    (step.id==='tests'&&!/\bfail\s+1\b/.test(body)))))throw Error('B0_UNEXPECTED_FAILURE');
 }
 if(baseline) {
  const expected=['tests','check','validate','build','contracts','taxonomy','planner-replay','media-replay','media-verify',
   'composition-replay','composition-verify','design-replay','design-verify','audit-verify','cohort-replay','cohort-verify','lock-verify','h9-inventory'];
  if(ids.size!==expected.length||expected.some(id=>!ids.has(id)))throw Error('B0_BASELINE_COVERAGE');
 }
 return journal;
}

export function verifyViewCoverage(actual:{label:string;lock_id:string;semantic_page:string;viewport:{id:string}}[],
 expected:{label:string;lock_id:string;semantic_page:string;viewport:{id:string}}[]) {
 const key=(v:typeof actual[number])=>`${v.lock_id}|${v.semantic_page}|${v.viewport.id}`;
 const keys=new Set(actual.map(key));
 if(keys.size!==actual.length||actual.length!==expected.length||expected.some(v=>!keys.has(key(v))))throw Error('B0_VIEW_COVERAGE');
}
