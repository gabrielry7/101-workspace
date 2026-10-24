import {verifyPlannerReplay} from './lib/planner-readonly.ts';
console.log(JSON.stringify({status:'H2_BYTE_IDENTICAL_READ_ONLY_REPLAY',files:await verifyPlannerReplay()},null,2));
