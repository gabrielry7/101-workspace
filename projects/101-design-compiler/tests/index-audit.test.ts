import test from 'node:test';
import assert from 'node:assert/strict';
import { auditIndex,type IndexObservation } from '../src/audit/index.ts';
const valid:IndexObservation={main_count:1,nested_main:false,h1_count:1,ax_main_count:1,skip_visible:true,skip_activated:true,skip_target_id:'contenido',skip_target_is_main:true,link_reachable_by_tab:true,link_activated:true,link_href:'/h7/hotel-candidate-01/'};
test('index gate rejects nested/duplicate DOM or AX main even when candidate audits pass',()=>{
 assert.equal(auditIndex(valid).status,'LAB_INDEX_PASS');for(const patch of [{main_count:2,nested_main:true},{ax_main_count:2},{h1_count:2}])assert.equal(auditIndex({...valid,...patch}).status,'FAIL');
});
test('index gate requires real skip target main and keyboard-reachable activated candidate link',()=>{
 for(const patch of [{skip_target_id:'main'},{skip_target_is_main:false},{skip_visible:false},{skip_activated:false},{link_reachable_by_tab:false},{link_activated:false}])assert.equal(auditIndex({...valid,...patch}).status,'FAIL');
});
