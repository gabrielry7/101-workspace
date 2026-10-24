import {readFile,writeFile} from 'node:fs/promises';
import {judgeRefinement} from '../src/design/evaluators/policy.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const iteration=Number(process.argv[2]??1);if(![1,2].includes(iteration))throw Error('ITERATION_BUDGET');
const artifactPath='data/derived/design-evaluation-v1/experiment.json',run=JSON.parse(await readFile(artifactPath,'utf8')),prior=JSON.parse(await readFile(`docs/evidence/design-evaluation/iteration-${iteration-1}/audit.json`,'utf8')),after=JSON.parse(await readFile(`docs/evidence/design-evaluation/iteration-${iteration}/audit.json`,'utf8')),repair=JSON.parse(await readFile(`docs/evidence/design-evaluation/repair-${iteration}.json`,'utf8'));
if(repair.after_sha256!==inputSha256(run)||prior.experiment_id!==run.experiment_id||after.experiment_id!==run.experiment_id)throw Error('JUDGE_EVIDENCE_MISMATCH');
const decisions=[];
for(const c of run.cases)for(const v of c.variants){if(v.iteration!==iteration)continue;
 const views=(a:any)=>a.views.filter((r:any)=>r.case_id===c.id&&r.condition===v.condition),previous=views(prior),current=views(after);
 const keys=(xs:any[])=>xs.map(x=>`${x.route}:${x.viewport}`).sort();if(JSON.stringify(keys(previous))!==JSON.stringify(keys(current)))throw Error('REPAIR_COVERAGE_MISMATCH');
 const d=judgeRefinement(previous.flatMap((r:any)=>r.findings),current.flatMap((r:any)=>r.findings),iteration,after.raven_calls.length+after.impeccable_calls.length,after.wall_seconds,run.budget);
 decisions.push({case_id:c.id,condition:v.condition,...d});if(!d.keep){const old=repair.before.cases.find((x:any)=>x.id===c.id).variants.find((x:any)=>x.condition===v.condition);Object.assign(v,old);}
}
await writeFile(`docs/evidence/design-evaluation/judgment-${iteration}.json`,JSON.stringify({schema_version:'1.0.0',decisions},null,2)+'\n');await writeFile(artifactPath,JSON.stringify(run,null,2)+'\n');
console.log(JSON.stringify(decisions));if(decisions.some(d=>!d.keep)){console.error('ROLLBACK_APPLIED_REBUILD_AND_RECAPTURE_REQUIRED');process.exitCode=2;}
