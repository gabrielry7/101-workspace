import {readFile,writeFile} from 'node:fs/promises';
import {proposeRefinement} from '../src/design/evaluators/policy.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {loadQualityLab} from './load-quality-lab.ts';
const iteration=Number(process.argv[2]??0);if(![0,1].includes(iteration))throw Error('ITERATION_BUDGET');
await loadQualityLab();
const path='data/derived/design-evaluation-v1/experiment.json',before=JSON.parse(await readFile(path,'utf8')),next=structuredClone(before),audit=JSON.parse(await readFile(`docs/evidence/design-evaluation/iteration-${iteration}/audit.json`,'utf8'));
if(audit.experiment_id!==before.experiment_id||audit.iteration!==iteration)throw Error('REPAIR_AUDIT_MISMATCH');
const decisions=[];
for(const c of next.cases)for(const v of c.variants){
 const findings=audit.views.filter((r:any)=>r.case_id===c.id&&r.condition===v.condition).flatMap((r:any)=>r.findings);
 if(!v.flags.impeccable&&!v.flags.raven){decisions.push({case_id:c.id,condition:v.condition,status:'BASELINE_FROZEN'});continue;}
 const count=audit.raven_calls.length+audit.impeccable_calls.length+before.metering.preflight_tool_calls;
 if(findings.some((f:any)=>f.severity==='BLOCKING')||count>=before.budget.max_tool_calls||audit.wall_seconds>=before.budget.max_wall_seconds){decisions.push({case_id:c.id,condition:v.condition,status:'STOP_HARD_GATE_OR_BUDGET'});continue;}
 if(v.iteration>iteration||v.iteration>=before.budget.max_iterations)throw Error('REPAIR_ITERATION_REUSE');
 const proposed=proposeRefinement(v.refinement,findings);
 decisions.push({case_id:c.id,condition:v.condition,status:proposed.changed?'PROPOSED_BOUNDED_REPAIR':'STOP_NO_SAFE_PATCH',before:v.refinement,after:proposed.refinement,reason_ids:proposed.reason_ids});
 if(proposed.changed){v.refinement=proposed.refinement;v.iteration=iteration+1;v.trace.push({source:'BOUNDED_REPAIR',audit_sha256:inputSha256(audit),reason_ids:proposed.reason_ids});}
}
await writeFile(`docs/evidence/design-evaluation/repair-${iteration+1}.json`,JSON.stringify({schema_version:'1.0.0',before,after_sha256:inputSha256(next),decisions},null,2)+'\n');
await writeFile(path,JSON.stringify(next,null,2)+'\n');console.log(JSON.stringify(decisions.map(d=>({case_id:d.case_id,condition:d.condition,status:d.status}))));
