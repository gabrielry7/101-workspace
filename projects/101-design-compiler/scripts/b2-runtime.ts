import {readFile,writeFile,access} from 'node:fs/promises';
import {RuntimeSnapshotV1,runtimeDigest,verifyRuntime} from './lib/correction-runtime.ts';
import {fontFingerprint} from './lib/lock-files.ts';
// New B2 observation. Never modifies B0/H8 or claims their font identity.
export const b2RuntimePath='docs/evidence/corrections/b2/runtime.json';
if(process.argv.includes('--capture-current-fonts')){
 if(await access(b2RuntimePath).then(()=>true,()=>false))throw Error('B2_RUNTIME_ALREADY_EXISTS');
 const old=RuntimeSnapshotV1.parse(JSON.parse(await readFile('docs/evidence/corrections/b0/runtime.json','utf8')));
 const snapshot={...old,fonts:await fontFingerprint()};snapshot.snapshot_sha256=runtimeDigest(snapshot);
 await writeFile(b2RuntimePath,JSON.stringify(snapshot,null,2)+'\n');
 // All other OS/tool/dependency/browser pins must still pass unmodified checks.
 console.log(JSON.stringify({status:'PASS_NEW_B2_FONT_OBSERVATION',snapshot_sha256:(await verifyRuntime(b2RuntimePath)).snapshot_sha256,
  historical_fonts_preserved:false,historical_evidence_modified:false,drift:'docs/evidence/corrections/b2/qa-01/runtime-drift.json'}));
}
