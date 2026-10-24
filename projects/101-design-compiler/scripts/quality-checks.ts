import {mkdir,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {newJournal,journalCommand} from './lib/correction-run.ts';
const name=process.argv[2]??'checks';if(!/^[a-z0-9-]+$/.test(name))throw Error('INVALID_CHECK_ID');const dir=`docs/evidence/design-evaluation/${name}`;if(await access(dir).then(()=>true,()=>false))throw Error('CHECK_RUN_ALREADY_EXISTS');await mkdir(dir,{recursive:true});
const journal=newJournal('impeccable-raven-pilot-20261021'),npm=resolve('.tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js');
const steps:[string,string[]][]=[['contracts',[npm,'run','contracts:export']],['evaluation-contracts',['--experimental-strip-types','scripts/quality-export.ts']],['tests',[npm,'test']],['check',[npm,'run','check']],['validate',[npm,'run','validate']],['build',[npm,'run','build','--','--config','tooling/design-evaluation/astro.config.mjs']],
 ...['taxonomy:audit','media:replay','media:verify','composition:replay','composition:verify','design:replay','design:verify','audit:verify','cohort:replay','cohort:verify','lock:verify'].map(s=>[s.replace(':','-'),[npm,'run',s]] as [string,string[]]),
 ['tool-dependency-audit',[npm,'--prefix','tooling/design-evaluation','audit','--json','--registry=https://registry.npmjs.org']]];
let failed=false;for(const [id,args] of steps){const result=await journalCommand(journal,dir,id,args);if(result.status!=='PASS')failed=true;}
console.log('See journal.json: H8 frozen-source/browser gates are reported as failures, never converted to a green run.');if(failed)process.exitCode=1;
