import {access,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {newJournal,journalCommand,verifyProtectedFiles} from './lib/correction-run.ts';
import {b3Preservation} from './b3-preservation.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('NEW_RUN_ID_REQUIRED');
const directory=`docs/evidence/corrections/b3/${id}`;if(await access(directory).then(()=>true,()=>false))throw Error('RUN_EXISTS');await mkdir(directory,{recursive:true});
const journal=newJournal(`b3-${id}`),npm=resolve('.tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js');
const steps:[string,string[],boolean?][]=[['contracts',[npm,'run','contracts:export']],['tests',[npm,'test'],true],['check',[npm,'run','check']],['validate',[npm,'run','validate']],['build',[npm,'run','build']],
 ['b3-scenario',['--experimental-strip-types','scripts/b3-scenario.ts','--verify']],['b3-design-replay',['--experimental-strip-types','scripts/b3-proposals.ts','--verify']],
 ['b2-media',['--experimental-strip-types','scripts/b2-demo-verify.ts']],['b2-library',['--experimental-strip-types','scripts/b2-verify.ts']],['b1-replay',['--experimental-strip-types','scripts/b1-fixtures.ts','--verify']],
 ['taxonomy',[npm,'run','taxonomy:audit']],['planner-replay',['--permission','--allow-fs-read=*','--experimental-strip-types','scripts/b1-planner-replay.ts']],
 ...['media:replay','media:verify','composition:replay','composition:verify','design:replay','design:verify','audit:verify','cohort:replay','cohort:verify'].map(task=>[task.replace(':','-'),[npm,'run',task]] as [string,string[]]),
 ['lock-verify',[npm,'run','lock:verify','--','--rebuild'],true],['h9-inventory',['--experimental-strip-types','scripts/inventory-h9.ts','--verify']]];
let failed=false;for(const [step,args,known] of steps){const r=await journalCommand(journal,directory,step,args,known);if(r.status==='FAIL'||(step==='tests'&&r.status==='BLOCKED_HISTORICAL_ENVIRONMENT'&&!/\bfail\s+1\b/.test(r.body)))failed=true;}
console.log(JSON.stringify(await verifyProtectedFiles(b3Preservation)));if(failed)process.exitCode=1;
