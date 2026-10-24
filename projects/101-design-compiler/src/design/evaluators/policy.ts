import { DesignFindingV1,DesignRefinementV1,EvaluationBudgetV1,type DesignFinding,type DesignRefinement } from './contracts.ts';
import { inputSha256 } from '../../upstream/v1/protocol.ts';
export function consolidateFindings(raw:unknown[]) {
 const map=new Map<string,DesignFinding>();
 for(const value of raw){const f=DesignFindingV1.parse(value),key=JSON.stringify([f.rule,f.route,f.viewport,f.selector,f.kind]);const old=map.get(key);
  if(!old)map.set(key,f);else{old.evidence=[...new Set([...old.evidence,...f.evidence])];old.sources=[...new Map([...old.sources,...f.sources].map(s=>[inputSha256(s),s])).values()];old.confidence=Math.max(old.confidence,f.confidence);if(f.severity==='BLOCKING'||old.severity==='NOTE')old.severity=f.severity;}}
 return [...map.values()];
}
const patchKeys={READING_MEASURE:['reading_measure','bounded'],TOUCH_TARGETS:['touch_targets','comfortable'],TYPE_RHYTHM:['type_rhythm','reading'],TRACKING:['tracking','natural'],LABEL_PLACEMENT:['label_placement','after-title']} as const;
export function proposeRefinement(before:DesignRefinement,findings:DesignFinding[]) {
 const next={...DesignRefinementV1.parse(before)},reasons:string[]=[];
 for(const f of findings){if(f.repair==='NONE'||f.confidence<0.8||f.kind==='AESTHETIC')continue;const [key,value]=patchKeys[f.repair];Object.assign(next,{[key]:value});reasons.push(f.id);}
 return {refinement:DesignRefinementV1.parse(next),reason_ids:reasons,changed:inputSha256(next)!==inputSha256(before)};
}
export function judgeRefinement(before:DesignFinding[],after:DesignFinding[],iteration:number,calls:number,seconds:number,rawBudget:unknown){
 if(!Number.isInteger(iteration)||iteration<1||iteration>2)throw Error('ITERATION_BUDGET');
 const budget=EvaluationBudgetV1.parse(rawBudget),hard=(fs:DesignFinding[])=>new Set(fs.filter(f=>f.kind==='MEASURED'&&f.severity==='BLOCKING').map(f=>`${f.route}:${f.viewport}:${f.rule}:${f.selector}`));
 const prior=hard(before),next=hard(after),regression=[...next].some(k=>!prior.has(k));
 const count=(fs:DesignFinding[])=>new Set(fs.filter(f=>f.kind!=='AESTHETIC'&&f.repair!=='NONE').map(f=>`${f.route}:${f.viewport}:${f.rule}:${f.selector}`)).size;
 const improved=count(after)<count(before)&&!regression;
 return {keep:improved,stop:regression||!improved||iteration>=budget.max_iterations||calls>=budget.max_tool_calls||seconds>=budget.max_wall_seconds,
 reason:regression?'REGRESSION':!improved?'NO_VERIFIED_IMPROVEMENT':iteration>=budget.max_iterations?'ITERATION_BUDGET':calls>=budget.max_tool_calls||seconds>=budget.max_wall_seconds?'RESOURCE_BUDGET':'IMPROVED',before:count(before),after:count(after)};
}
