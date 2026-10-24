import { readFile } from 'node:fs/promises';
import { loadAuditLab } from './load-audit-lab.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { auditPreviewPath } from '../src/audit/evaluate.ts';
export async function loadComparisons(){
 const state=await loadAuditLab();
 let report:any;try{report=JSON.parse(await readFile('docs/evidence/h6/run.json','utf8'));}catch{return {ready:false,pairs:[] as any[]};}
 if(report.status!=='PASSED'||report.context_sha256!==state.result.context_sha256)return {ready:false,pairs:[] as any[]};
 const mounts=state.mounts.filter(m=>m.kind==='FINALIST'),pairs:any[]=[];
 let pairIndex=0;
 for(let i=0;i<mounts.length;i++)for(let j=i+1;j<mounts.length;j++){
  pairIndex++;
  for(const viewport of [{id:'mobile',width:390,height:844},{id:'desktop',width:1280,height:900}])for(const page of state.lab.content.pages){
   const seed=inputSha256({context:state.result.context_sha256,pair:pairIndex,viewport:viewport.id,page:page.path});
   const flip=parseInt(seed.slice(0,8),16)%2===1;
   const left=mounts[flip?j:i]!,right=mounts[flip?i:j]!;
   const receipt=(id:string)=>report.receipts.find((r:any)=>r.mount_id===id&&r.viewport.id===viewport.id&&r.semantic_page===page.path&&!r.seeded_fault);
   const a=receipt(left.id),b=receipt(right.id);if(!a||!b)throw new Error('COMPARISON_EVIDENCE_MISSING');
   if([a,b].some(r=>r.audit.status!=='LAB_TECHNICAL_PASS_NEEDS_HUMAN_REVIEW')||a.candidate_sha256!==inputSha256(left.candidate)||b.candidate_sha256!==inputSha256(right.candidate))throw new Error('COMPARISON_CANDIDATE_INVALID');
   const id=`pair-${String(pairIndex).padStart(2,'0')}-${viewport.id}-${page.path==='/'?'identity':'offering'}`;
   pairs.push({id,pair:`pair-${String(pairIndex).padStart(2,'0')}`,view:viewport.id,page:page.path==='/'?'identity':'offering',semantic_page:page.path,
    context_sha256:state.result.context_sha256,left_id:left.id,right_id:right.id,
    left_sha256:inputSha256(left.candidate),right_sha256:inputSha256(right.candidate),left_screenshot_sha256:a.screenshot_sha256,right_screenshot_sha256:b.screenshot_sha256,
    viewport:{width:viewport.width,height:viewport.height},left_route:auditPreviewPath(left.id,page.path),right_route:auditPreviewPath(right.id,page.path),
    order_seed:seed,order_status:'DETERMINISTIC_PSEUDORANDOM_ORDER_RECORDED',human_preference:'NOT_COLLECTED',
    route:`/h6/compare/pair-${String(pairIndex).padStart(2,'0')}/${viewport.id}/${page.path==='/'?'identity':'offering'}/`});
  }
 }
 return {ready:true,pairs};
}
