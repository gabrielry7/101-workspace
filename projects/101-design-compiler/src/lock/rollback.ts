import type { DesignLock } from './contracts.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
export function selectRollback(history:{lock_id:string;lock_sha256:string;output_sha256:string;status:'LAB_EQUIVALENCE_PASS'|'FAIL'}[],target:DesignLock){
 const entry=[...history].reverse().find(h=>h.lock_id===target.id&&h.lock_sha256===target.lock_sha256&&h.status==='LAB_EQUIVALENCE_PASS');
 if(!entry)throw Error('ROLLBACK_SNAPSHOT_NOT_VERIFIED');return {action:'SELECT_PREVIOUS_LOCK_AND_REBUILD',lock_id:target.id,lock_sha256:target.lock_sha256,resolved_plan_sha256:inputSha256(target.resolved_plan),expected_output_sha256:entry.output_sha256,production_ready:false,human_preference:'NOT_COLLECTED'};
}
