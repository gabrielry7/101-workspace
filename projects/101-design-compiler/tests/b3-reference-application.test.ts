import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadB3Lab} from '../scripts/load-b3-lab.ts';
import {validateContextualPresentation} from '../src/design/contextual.ts';
import {validateReferenceApplication} from '../src/design/reference-application.ts';
import {auditContextual} from '../src/design/contextual-audit.ts';
import {sameReferenceContext} from '../src/design/reference-comparison.ts';
const read=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
const lab=await loadB3Lab(),context=await read('data/design/contextual-v2/context.json'),research=await read('data/reference/design/visual-review-2026-10-15.json');
test('context comparison ignores key insertion order but rejects actual changes to any bound hash or missing fields',()=>{
 const a={plan:'1'.repeat(64),content:'2'.repeat(64),media:'3'.repeat(64),context:'4'.repeat(64)};
 const reordered={context:a.context,media:a.media,content:a.content,plan:a.plan};
 assert(sameReferenceContext(a,reordered));
 for(const key of Object.keys(a))assert.equal(sameReferenceContext(a,{...reordered,[key]:'f'.repeat(64)}),false);
 assert.equal(sameReferenceContext(a,{plan:a.plan}),false);assert.equal(sameReferenceContext({},{}),false);
});
test('reference application is replayable, associated, diverse and cannot invent user approval or consume different evidence',()=>{
 assert.equal(validateReferenceApplication(lab.application,context,research,lab.designs,lab.media.review).variants.length,4);
 for(const patch of [{...lab.application,research_sha256:'0'.repeat(64)},{...lab.application,human_approval:'APPROVED'},{...lab.application,authority:'USER_VOTES'},{...lab.application,variants:lab.application.variants.map(v=>({...v,relationship:'EditorialCard'}))},{...lab.application,variants:lab.application.variants.map(v=>({...v,palette:'night'}))}])assert.throws(()=>validateReferenceApplication(patch,context,research,lab.designs,lab.media.review));
});
test('offering to need convention rejects valid-but-wrong slots, missing slots and unknown subjects before render',()=>{
 for(const mapping of [{...lab.presentation.offering_media,pizza:'pasta',pasta:'pizza'},{...lab.presentation.offering_media,pizza:'hero'},{...lab.presentation.offering_media,pizza:'unreviewed'}])assert.throws(()=>validateContextualPresentation({...lab.presentation,offering_media:mapping},lab.scenario),/B3_OFFERING_MEDIA_MISMATCH/);
});
test('DOM audit rejects swapping permitted bytes or need/usage between offerings, even when global media set is unchanged',async()=>{
 const archive=await read('docs/evidence/corrections/b3/qa-08/qa.json'),o=structuredClone(archive.views[0].observed),d=lab.designs[0]!;
 o.reference_application=lab.application_sha256;
 o.offering_media=lab.presentation.offering_order.map(offering=>{const usages=lab.media.review.usages.filter(u=>u.page===d.route&&u.need_id===`b3-need:${offering}`);return {offering,slot:offering,src:lab.media.review.assets.find(a=>a.id===usages[0]!.asset_id)!.uri,usages:usages.map(u=>u.id)};});
 assert(auditContextual(o,lab.scenario,d,lab.media.review).success);
 for(const mutate of [(v:any)=>{[v.offering_media[0].src,v.offering_media[1].src]=[v.offering_media[1].src,v.offering_media[0].src];},(v:any)=>{[v.offering_media[0].usages,v.offering_media[1].usages]=[v.offering_media[1].usages,v.offering_media[0].usages];},(v:any)=>{v.offering_media[0].slot='pasta';},(v:any)=>{v.offering_media=[];}]){const changed=structuredClone(o);mutate(changed);assert(auditContextual(changed,lab.scenario,d,lab.media.review).codes.includes('B3_OFFERING_MEDIA_MISMATCH'));}
});
