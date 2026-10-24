import {readFile,stat} from 'node:fs/promises';
import {resolve} from 'node:path';
import {checkPlannerFixtures} from '../check-planner-fixtures.ts';
import {hashBytes} from './correction-run.ts';

// Recompute expected H2 values in memory; never create, repair or rewrite goldens.
export async function verifyPlannerReplay(directory='data/derived/planner-v1') {
 const expected=await checkPlannerFixtures(),receipts=[];
 for(const fixture of expected) {
  if(!fixture.success)throw Error(`PLANNER_REPLAY_SCENARIO_FAILED:${fixture.scenario}`);
  const path=resolve(directory,`${fixture.scenario}.json`),before=await stat(path,{bigint:true}),bytes=await readFile(path);
  const body=Buffer.from(JSON.stringify(fixture.result,null,2)+'\n');
  if(!bytes.equals(body))throw Error(`PLANNER_REPLAY_BYTES_MISMATCH:${fixture.scenario}`);
  const after=await stat(path,{bigint:true});
  if(before.mtimeNs!==after.mtimeNs||before.size!==after.size||before.ino!==after.ino)throw Error('PLANNER_REPLAY_FILE_CHANGED_DURING_READ');
  receipts.push({scenario:fixture.scenario,status:'BYTE_IDENTICAL_READ_ONLY',bytes:bytes.length,sha256:hashBytes(bytes),mtime_ns:after.mtimeNs.toString()});
 }
 return receipts;
}
