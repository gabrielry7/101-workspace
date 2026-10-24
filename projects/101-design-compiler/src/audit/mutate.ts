import { inputSha256 } from '../upstream/v1/protocol.ts';
import { AuditCandidateV1,MutationV1,type AuditCandidate,type AuditReport } from './contracts.ts';
export function proposeRepair(report:AuditReport){
 const issue=report.issues.find(i=>i.severity==='BLOCKING'&&i.repair==='FLUID_MEASURE');
 return issue?MutationV1.parse({schema_version:'1.0.0',id:'repair-fluid-measure',reason_issue_id:issue.id,patch:{measure:'fluid'}}):null;
}
export function mutate(candidate:AuditCandidate,raw:unknown){
 const mutation=MutationV1.parse(raw);
 return AuditCandidateV1.parse({...structuredClone(candidate),layout:{measure:mutation.patch.measure}});
}
export function judgeMutation(before:AuditCandidate,after:AuditCandidate,beforeReports:AuditReport[],afterReports:AuditReport[],evidence:{before:string[];after:string[]}){
 if(!beforeReports.length||beforeReports.length!==afterReports.length)throw new Error('MUTATION_REPORT_COVERAGE');
 const location=(r:AuditReport)=>`${r.semantic_page}:${r.viewport.width}:${r.viewport.height}`;
 const beforeLocations=beforeReports.map(location),afterLocations=afterReports.map(location);
 if(new Set(beforeLocations).size!==beforeLocations.length||new Set(afterLocations).size!==afterLocations.length
  ||JSON.stringify([...beforeLocations].sort())!==JSON.stringify([...afterLocations].sort()))throw new Error('MUTATION_REPORT_COVERAGE');
 if(beforeReports.some(r=>r.policy_sha256!==afterReports.find(a=>location(a)===location(r))!.policy_sha256))throw new Error('MUTATION_POLICY_MISMATCH');
 if(beforeReports.some(r=>r.candidate_sha256!==inputSha256(before))||afterReports.some(r=>r.candidate_sha256!==inputSha256(after)))throw new Error('MUTATION_RECEIPT_MISMATCH');
 const count=(reports:AuditReport[])=>reports.reduce((n,r)=>n+r.issues.filter(i=>i.severity==='BLOCKING').length,0);
 const prior=count(beforeReports),next=count(afterReports);
 const priorCodes=new Set(beforeReports.flatMap(r=>r.issues.filter(i=>i.severity==='BLOCKING').map(i=>`${location(r)}:${i.family}:${i.code}`)));
 const newFault=afterReports.some(r=>r.issues.some(i=>i.severity==='BLOCKING'&&!priorCodes.has(`${location(r)}:${i.family}:${i.code}`)));
 const improved=next<prior&&!newFault;
 const kept=improved?after:before;
 return {schema_version:'1.0.0',decision:improved?'KEEP_REPAIR':'ROLLBACK',reason:improved?'Fewer blocking faults with no new hard failure.':'Worse or non-improving mutation restores the exact previous candidate.',
  before_sha256:inputSha256(before),after_sha256:inputSha256(after),kept_sha256:inputSha256(kept),
  before,after,kept,before_reports:beforeReports,after_reports:afterReports,evidence,blocking_before:prior,blocking_after:next};
}
