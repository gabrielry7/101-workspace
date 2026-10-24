import {readFile} from 'node:fs/promises';
import {loadDesignLab} from './load-design-lab.ts';
import {loadCohortLab} from './load-cohort-lab.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {validateDesign} from '../src/design/validate.ts';
import {QualityExperimentV1} from '../src/design/evaluators/contracts.ts';
export const qualityPath=(caseId:string,condition:string,page:string)=>`/quality/${caseId}-${condition.toLowerCase()}${page==='/'?'/':`${page}/`}`;
export async function qualityInputs(){
 const restaurant=await loadDesignLab(),cohort=await loadCohortLab(true),hotel=cohort.cases.find(c=>c.scenario==='hotel')!;
 return [{id:'restaurante',lab:restaurant.lab,design:restaurant.result.finalists[0]!,mode:'SYNTHETIC_FIXTURE'},
 {id:'hotel',lab:hotel.lab!,design:hotel.search!.finalists[0]!,mode:'SYNTHETIC_FIXTURE'}];
}
export async function loadQualityLab(){
 const inputs=await qualityInputs();const artifact=QualityExperimentV1.parse(JSON.parse(await readFile('data/derived/design-evaluation-v1/experiment.json','utf8')));
 const cases=artifact.cases.map(c=>{const input=inputs.find(i=>i.id===c.id);if(!input||c.input_sha256!==inputSha256(input))throw Error('EVALUATOR_INPUT_DRIFT');
  for(const v of c.variants){
   if(v.flags.impeccable!==['B','D'].includes(v.condition)||v.flags.raven!==['C','D'].includes(v.condition))throw Error('EXPERIMENT_FLAG_MISMATCH');
   if(inputSha256(v.design)!==inputSha256(input.design)||!validateDesign(v.design,input.lab).success)throw Error('EVALUATOR_TRUTH_OR_DESIGN_CHANGED');
   if(v.condition==='A'&&(v.flags.impeccable||v.flags.raven||Object.values(v.refinement).some(x=>x!=='incumbent'&&x!=='1.0.0')))throw Error('BASELINE_TOOL_INFLUENCE');}
  return {...c,lab:input.lab};
 });
 if(new Set(cases.map(c=>c.id)).size!==2||cases.some(c=>JSON.stringify(c.variants.map(v=>v.condition))!==JSON.stringify(['A','B','C','D'])))throw Error('EXPERIMENT_COVERAGE');
 return {...artifact,cases};
}
