import {access,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {newJournal,journalCommand,verifyProtectedFiles} from './lib/correction-run.ts';
const id=process.argv[2];if(!id||!/^[a-z0-9-]+$/.test(id))throw Error('Usage: b2-run.ts <new-run-id>');
const directory=`docs/evidence/corrections/b2/${id}`;
if(await access(directory).then(()=>true,()=>false))throw Error('B2_RUN_ALREADY_EXISTS');await mkdir(directory,{recursive:true});
const journal=newJournal(`b2-${id}`),npm=resolve('.tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js');
const steps:[string,string[],boolean?][]=[
 ['contracts',[npm,'run','contracts:export']],['tests',[npm,'test'],true],['check',[npm,'run','check']],['validate',[npm,'run','validate']],['build',[npm,'run','build']],
 ['b2-readonly-replay',['--experimental-strip-types','scripts/b2-verify.ts']],
 ['corpus-replay',['--experimental-strip-types','scripts/b2-corpus.ts','--verify']],
 ['b1-replay',['--experimental-strip-types','scripts/b1-fixtures.ts','--verify']],['taxonomy',[npm,'run','taxonomy:audit']],
 ['planner-replay',['--permission','--allow-fs-read=*','--experimental-strip-types','scripts/b1-planner-replay.ts']],
 ...['media:replay','media:verify','composition:replay','composition:verify','design:replay','design:verify','audit:verify','cohort:replay','cohort:verify'].map(task=>[task.replace(':','-'),[npm,'run',task]] as [string,string[]]),
 ['lock-verify',[npm,'run','lock:verify','--','--rebuild'],true],['h9-inventory',['--experimental-strip-types','scripts/inventory-h9.ts','--verify']]
];
let failed=false;for(const [step,args,expected] of steps){const result=await journalCommand(journal,directory,step,args,expected);
 if(result.status==='FAIL'||(step==='tests'&&result.status==='BLOCKED_HISTORICAL_ENVIRONMENT'&&!/\bfail\s+1\b/.test(result.body)))failed=true;}
console.log(JSON.stringify(await verifyProtectedFiles('docs/evidence/corrections/b2/pre/preservation.json')));
if(failed)process.exitCode=1;
