import { loadDesignLab } from './load-design-lab.ts';
import { AuditCandidateV1,type AuditCandidate } from '../src/audit/contracts.ts';
import { mutate } from '../src/audit/mutate.ts';
export const H6_LAB_POLICY={schema_version:'1.0.0',profile:'LAB',max_page_bytes:2500000,max_requests:3,max_client_js_bytes:0,original_media_exception:true} as const;
export const H6_COMMERCIAL_POLICY={...H6_LAB_POLICY,profile:'COMMERCIAL',max_page_bytes:300000,original_media_exception:false} as const;
export async function loadAuditLab(){
 const {lab,result}=await loadDesignLab();
 const base=(plan:typeof result.finalists[number],mode:AuditCandidate['fixture_mode']='FROZEN_LAB',measure:AuditCandidate['layout']['measure']='fluid')=>AuditCandidateV1.parse({schema_version:'1.0.0',plan,fixture_mode:mode,layout:{measure}});
 const before=base(result.finalists[0]!,'SEEDED_DEFECT_TEST','fixed-wide');
 const repair=mutate(before,{schema_version:'1.0.0',id:'repair-fluid',reason_issue_id:'seeded-overflow',patch:{measure:'fluid'}});
 const worse=mutate(repair,{schema_version:'1.0.0',id:'seed-worse',reason_issue_id:'regression-control',patch:{measure:'fixed-wide'}});
 const mounts=[
  ...result.finalists.map(plan=>({id:`final-${plan.id}`,kind:'FINALIST',candidate:base(plan)})),
  {id:'repair-before',kind:'SEEDED_DEFECT_TEST',candidate:before},
  {id:'repair-after',kind:'SEEDED_DEFECT_TEST',candidate:repair},
  {id:'worse-after',kind:'SEEDED_DEFECT_TEST',candidate:worse},
  {id:'rollback-restored',kind:'SEEDED_DEFECT_TEST',candidate:repair},
 ];
 return {lab,result,mounts,policy:H6_LAB_POLICY,commercial_policy:H6_COMMERCIAL_POLICY,
  budget:{plans:8,baseline_views:16,mutation_views:8,seeded_browser_faults:4,raster_stride:4,max_mutations:2,max_new_spend:0},
  historical_critic:'MISSING',historical_mutator:'MISSING',implementation:'LOCAL_LAB_V1_NOT_HISTORICAL_INTEGRATION'};
}
