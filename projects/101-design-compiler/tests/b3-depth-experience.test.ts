import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadB3DepthExperience} from '../scripts/load-b3-depth-experience.ts';
import {loadB3RichExperience} from '../scripts/load-b3-rich-experience.ts';
import {DesignIterationFeedbackV1,DepthExperienceV1} from '../src/design/depth-experience-contracts.ts';
import {validateReferenceDepth} from '../src/design/reference-depth-validation.ts';
import {auditDepthExperience,auditFilteredJournal} from '../src/design/depth-experience-audit.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const lab=await loadB3DepthExperience(),read=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
test('human rejection replaces proposals without manufacturing acceptance, rating or training',()=>{
 assert.deepEqual(lab.revision_feedback.rejected,['candidate-03','candidate-04']);assert.equal(lab.site.human_approval,'NOT_COLLECTED');
 for(const patch of [{ratings:[1,1]},{final_design_approval:true},{training:'TRAINED'},{rejected:['candidate-01','candidate-02']}])assert.equal(DesignIterationFeedbackV1.safeParse({...lab.revision_feedback,...patch}).success,false);
 assert.equal(DepthExperienceV1.safeParse({...lab.site,human_approval:'APPROVED'}).success,false);
});
test('revision keeps exact content, plan, 148 rights usages and liked directions; no new reference confers media rights',async()=>{
 const prior=await loadB3RichExperience();for(const k of ['content_sha256','plan_sha256','media_review_sha256','editorial_sha256','feedback_sha256'] as const)assert.equal(lab.site[k],prior.site[k]);
 assert.equal(inputSha256(lab.experience_media.review),inputSha256(prior.experience_media.review));assert.equal(lab.experience_media.review.usages.length,148);
 for(let i=0;i<2;i++)for(const k of ['hero','palette','type','collection','home_composition'] as const)assert.equal(lab.site.profiles[i]![k],prior.site.profiles[i]![k]);
 assert.equal(lab.research.asset_reuse,'NOT_AUTHORIZED');
});
test('iteration contract binds exact profile identities and order to liked or replacement status',()=>{
 for(const mutate of [(v:any)=>v.profiles[0].design_status='REPLACEMENT_AWAITING_HUMAN_REVIEW',(v:any)=>v.profiles[2].design_status='LIKED_DIRECTION_REFINEMENT',(v:any)=>v.profiles[3].design_status='LIKED_DIRECTION_REFINEMENT',(v:any)=>{[v.profiles[0],v.profiles[1]]=[v.profiles[1],v.profiles[0]];},(v:any)=>{[v.profiles[2],v.profiles[3]]=[v.profiles[3],v.profiles[2]];}]){const v=structuredClone(lab.site);mutate(v);assert.equal(DepthExperienceV1.safeParse(v).success,false);}
});
test('reference binding rejects upgraded partial approvals, invented sources and unimplemented claims without operator',async()=>{
 const prior=await read('data/reference/design/visual-review-2026-10-15.json');validateReferenceDepth(lab.research,prior);
 for(const mutate of [(v:any)=>v.coverage[20].scope='GLOBAL_REPORTED',(v:any)=>v.coverage[22].scope='GLOBAL_REPORTED',(v:any)=>v.features[0].references.push('reference-99'),(v:any)=>v.features[0].operator=null,(v:any)=>v.features.push(v.features[0])]){const v=structuredClone(lab.research);mutate(v);assert.throws(()=>validateReferenceDepth(v,prior));}
});
test('104 current browser observations preserve all factual, media and editorial layers',async()=>{
 const main=await read('docs/evidence/corrections/b3/depth-iab-r3-20261021/observations.json'),responsive=await read('docs/evidence/corrections/b3/depth-iab-r3-20261021/responsive.json');assert.equal(main.views.length,88);assert.equal(responsive.views.length,16);
 for(const v of [...main.views,...responsive.views])assert.deepEqual(auditDepthExperience(v.observed,lab),{success:true,codes:[]},`${v.design}/${v.kind}/${v.viewport.id}`);
});
test('render audit blocks swapped route targets, lost preparation, invented editorial copy and missing navigation',async()=>{
 const views=(await read('docs/evidence/corrections/b3/depth-iab-r3-20261021/observations.json')).views,home=views.find((v:any)=>v.kind==='home').observed;
 for(const [mutate,code]of [[(o:any)=>o.directory[0].href=o.directory[1].href,'DEPTH_DIRECTORY_LOST'],[(o:any)=>o.readings[0].body[0]='Clientes reales confirman nuestro premio.','DEPTH_READING_BINDING_LOST'],[(o:any)=>o.navigation.pop(),'DEPTH_NAVIGATION_LOST'],[(o:any)=>o.features=[],'DEPTH_FEATURE_CONTENT_LOST'],[(o:any)=>o.features_sha256='0'.repeat(64),'DEPTH_CONTEXT_CHANGED']] as const){const o=structuredClone(home);mutate(o);assert(auditDepthExperience(o,lab).codes.includes(code),code);}
 for(const kind of ['visit','request']){const o=structuredClone(views.find((v:any)=>v.kind===kind).observed);o.features=[];assert(auditDepthExperience(o,lab).codes.includes('DEPTH_FEATURE_CONTENT_LOST'));}
});
test('historical render evidence cannot verify the current rejected-and-replaced iteration',async()=>{
 const old=(await read('docs/evidence/corrections/b3/human-iab-r3-20261020/observations.json')).views[0].observed;
 assert(auditDepthExperience({...old,directory:[],readings:[],features:[]},lab).codes.includes('DEPTH_CONTEXT_CHANGED'));
});
test('filtered reading audit rejects retained quarter-column width, right-side offset and narrow copy',async()=>{
 const records=(await read('docs/evidence/corrections/b3/depth-iab-r3-20261021/interactions.json')).records;
 for(const r of records.filter((r:any)=>r.step==='journal-filter'||r.step==='journal-read'))assert.deepEqual(auditFilteredJournal(r.observed.layout),{success:true,codes:[]});
 const current=records.find((r:any)=>r.step==='journal-filter'&&r.viewport==='desktop').observed.layout;
 for(const mutate of [(v:any)=>v.visible[0].card.width=v.grid.width*.25,(v:any)=>v.visible[0].card.x=v.grid.x+v.grid.width*.75,(v:any)=>v.visible[0].copy.width=v.grid.width*.2]){const v=structuredClone(current);mutate(v);assert(auditFilteredJournal(v).codes.includes('JOURNAL_FILTER_READING_TOO_NARROW'));}
});
