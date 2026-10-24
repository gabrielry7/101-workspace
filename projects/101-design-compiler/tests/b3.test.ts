import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadB3Lab} from '../scripts/load-b3-lab.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {ContextualDesignPlanV2,ArtDirectionV2} from '../src/design/contextual-contracts.ts';
import {structuralDistance,validateContextualPlan,validateContextualPresentation} from '../src/design/contextual.ts';
import {contextualMediaData,evaluateContextualUsage,verifyContextualMediaReview,REVIEWED_B3_MEDIA_SHA256} from '../src/media/contextual-review.ts';
import {REVIEWED_DEMO_PACKAGE_SHA256} from '../src/media/demo-package.ts';
import {auditContextual} from '../src/design/contextual-audit.ts';
import {rightsGate} from '../src/media/gate.ts';
const lab=await loadB3Lab(),at=lab.media.evaluated_at,review=lab.media.review;
test('B3 new synthetic scenario preserves H2 projection, seven modules, 42 bound facts and no operational action',()=>{
 assert.equal(lab.scenario.input.data_mode,'SYNTHETIC_FIXTURE');assert.equal(lab.scenario.content.pages.flatMap((p:any)=>p.modules).length,7);
 assert.equal(lab.scenario.content.bindings.filter((b:any)=>b.status==='BOUND').length,42);
 assert(lab.scenario.planner.capabilities.capabilities.every((c:any)=>c.backend_status==='BACKEND_NOT_CONNECTED'));
 assert(lab.scenario.planner.plan.excluded_capabilities.some((c:any)=>c.id==='reservation'&&c.reason==='UNKNOWN'));
 assert(lab.scenario.planner.plan.excluded_capabilities.some((c:any)=>c.id==='order'&&c.reason==='UNKNOWN'));
});
test('V2 grammar rejects arbitrary code, unknown operator, duplicate/lost module, route and changed context',()=>{
 const d=lab.designs[0]!;assert(ContextualDesignPlanV2.safeParse(d).success);
 for(const changed of [{...d,css:'body{}'},{...d,recipe:{...d.recipe,hero:'ClientTemplate'}},{...d,module_refs:d.module_refs.slice(1)},{...d,module_refs:[...d.module_refs,d.module_refs[0]]},{...d,route:'/b3/other/'},{...d,content_sha256:'f'.repeat(64)}])assert.equal(validateContextualPlan(changed,lab.scenario,lab.context_sha256,review.review_sha256).success,false);
 assert.equal(ArtDirectionV2.safeParse({...lab.proposals[0],html:'<script>'}).success,false);
});
test('four coherent session directions share exact content and media; diversity counts relations on both devices, not colors',()=>{
 for(const d of lab.designs){assert.equal(d.plan_sha256,lab.scenario.content.plan_sha256);assert.equal(d.content_sha256,lab.scenario.content.content_sha256);assert.equal(d.media_sha256,review.review_sha256);assert.equal(d.human_approval,'NOT_COLLECTED');}
 for(let i=0;i<4;i++)for(let j=i+1;j<4;j++){const distance=structuralDistance(lab.designs[i]!,lab.designs[j]!);assert(distance.desktop>=2&&distance.mobile>=2);}
 const d=lab.designs[0]!,cosmetic={...d,tokens:{...d.tokens,palette:'night' as const}};assert.deepEqual(structuralDistance(d,cosmetic),{desktop:0,mobile:0});
});
test('21 original reference scopes retained, three partials and current visual inspection honestly pending',async()=>{
 const c=JSON.parse(await readFile('data/design/contextual-v2/context.json','utf8'));assert.equal(c.references.length,21);
 const by=(id:string)=>c.references.find((r:any)=>r.id===id);
 assert.equal(by('reference-12').scope,'SPECIFIC_PAGE_ONLY');assert.equal(by('reference-13').scope,'STORYTELLING_ONLY');assert.equal(by('reference-21').scope,'DROPDOWN_ONLY');
 assert(c.references.every((r:any)=>r.current_reading.visual_desktop==='PENDING_BROWSER_UNAVAILABLE'&&r.current_reading.visual_mobile==='PENDING_BROWSER_UNAVAILABLE'&&!r.current_reading.new_aesthetic_approval));
});
test('48 exact B3 uses pass current gate with independently reviewed contextual scope, preserving B2 pin',()=>{
 assert.equal(review.review_sha256,REVIEWED_B3_MEDIA_SHA256);assert.equal(review.parent_package_sha256,REVIEWED_DEMO_PACKAGE_SHA256);assert.equal(review.usages.length,48);
 for(const u of review.usages)assert.deepEqual(evaluateContextualUsage(lab.media.handle,u,at),{status:'ALLOWED',codes:[]});
 assert.equal(new Set(review.usages.map(u=>u.page)).size,4);
});
test('VERIFIED fixture flags, resealed checksum and forged trusted handle do not authenticate a media review',async()=>{
 const clone=structuredClone(review);clone.grants[0]!.review.status='VERIFIED';clone.grants[0]!.client_ids=['other'];const {review_sha256:_,...body}=clone;clone.review_sha256=inputSha256(body);
 assert.equal((await verifyContextualMediaReview(clone)).success,false);
 assert.throws(()=>contextualMediaData({review_sha256:review.review_sha256}),/HANDLE_NOT_VERIFIED/);
});
test('wrong client/project/page/branch/purpose, disclosure loss and documentary representation block B3',()=>{
 const u=review.usages[0]!;
 for(const patch of [{client_id:'other'},{project_id:'other'},{page:'/b2/demo/'},{scope_id:review.business_id},{purpose:'document-product'},{generic_label:null},{attribution_text:null},{context_notices:[]},{role:'DOCUMENTARY',representation:'BUSINESS_EVIDENCE',subject_ids:['pizza']},{transformations:['CROP']}])assert.equal(evaluateContextualUsage(lab.media.handle,{...u,...patch},at).status,'BLOCKED');
});
test('expiry and AI/derivative restrictions still block; silent video exception is exact and does not authorize source audio',()=>{
 const u=review.usages[0]!;assert.equal(evaluateContextualUsage(lab.media.handle,u,'2027-01-01T00:00:00Z').status,'BLOCKED');
 assert.equal(evaluateContextualUsage(lab.media.handle,{...u,ai_operations:['training']},at).status,'BLOCKED');
 const source=review.assets.find(a=>a.id==='pixabay-149678-received')!,g=review.grants.find(g=>g.original_asset_id===source.id)!,v=review.usages.find(u=>u.asset_id==='pixabay-149678-silent')!;
 assert(rightsGate(source,g,{...v,asset_id:source.id},review.assets,at).codes.includes('VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED'));
 assert.equal(evaluateContextualUsage(lab.media.handle,{...v,asset_id:source.id},at).status,'BLOCKED');
 assert.equal(evaluateContextualUsage(lab.media.handle,{...v,asset_id:'forged-silent'},at).status,'BLOCKED');
});
test('B3 binding/media/browser negatives reject altered facts, missing required modules, scope, notice, diagnostics and crop',async()=>{
 const qa=JSON.parse(await readFile('docs/evidence/corrections/b3/qa-08/qa.json','utf8'));
 assert.equal(qa.status,'TECHNICAL_PASS_HUMAN_PENDING');assert.equal(qa.views.length,8);assert.equal(qa.responsive.length,16);
 const v=qa.views[0],o=v.observed,d=lab.designs.find(d=>d.id===v.design)!;assert(auditContextual(o,lab.scenario,d,review).success);
 for(const mutate of [(x:any)=>{x.modules[0].facts[0].text='Inventado';},(x:any)=>x.modules.pop(),(x:any)=>{x.modules[0].scope='other';},(x:any)=>{x.notice='';},(x:any)=>{x.diagnostics=[];},(x:any)=>{x.images[0].object_fit='cover';},(x:any)=>{x.images[0].height/=2;},(x:any)=>{x.video.autoplay=true;},(x:any)=>{x.usage_ids.pop();},(x:any)=>{x.links[0].exists=false;}]){const altered=structuredClone(o);mutate(altered);assert.equal(auditContextual(altered,lab.scenario,d,review).success,false);}
});
test('editorial fixture maps modules, subjects and B1 preview references without a client template or invented feature IDs',()=>{
 const p=lab.presentation;assert.equal(validateContextualPresentation(p,lab.scenario).operation,'DEMO_ONLY');
 for(const patch of [{...p,offering_order:p.offering_order.slice(1)},{...p,preview_catalog_references:{...p.preview_catalog_references,selection:'invented-function'}},{...p,anchors:{}},{...p,operation:'LIVE'}])assert.throws(()=>validateContextualPresentation(patch,lab.scenario));
});
