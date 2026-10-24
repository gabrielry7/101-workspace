import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadB3RichExperience} from '../scripts/load-b3-rich-experience.ts';
import {DemoCommunityV1,HumanDesignFeedbackV1,RichExperienceV1,richExperiencePages} from '../src/design/rich-experience-contracts.ts';
import {evaluateRichExperienceUsage,verifyRichExperienceMedia} from '../src/media/rich-experience-review.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {assertExperienceCoverage} from '../src/design/experience-coverage.ts';
import {auditRichExperience} from '../src/design/rich-experience-audit.ts';
import {capturePresence} from '../scripts/lib/capture-presence.ts';
const lab=await loadB3RichExperience(),at='2026-10-20T18:00:00.000Z';
test('actual blank responsive captures fail pixel presence even though JPEG and DOM were valid',async()=>{
 for(const path of ['docs/evidence/corrections/b3/human-responsive-20261020/candidate-01-home-small.jpg','docs/evidence/corrections/b3/human-responsive-20261020/candidate-04-home-tablet.jpg'])assert.equal((await capturePresence(await readFile(path))).success,false);
 assert.equal((await capturePresence(await readFile('docs/evidence/corrections/b3/human-iab-r2-20261020/candidate-01-home-desktop-00.jpg'))).success,true);
});
test('real human feedback retains liked directions and exact source without invented rating, lock or training',()=>{
 assert.deepEqual(lab.feedback.liked_directions,['candidate-01','candidate-02']);assert.equal(lab.feedback.ratings,null);assert.equal(lab.feedback.final_design_approval,false);
 for(const patch of [{ratings:[10,10]},{final_design_approval:true},{training:'TRAINED'},{liked_directions:['candidate-03','candidate-04']}])assert.equal(HumanDesignFeedbackV1.safeParse({...lab.feedback,...patch}).success,false);
});
test('liked entry typography, palette, hero and collection stay identical; two new artistic operators are distinct',async()=>{
 const prior=JSON.parse(await readFile('data/design/experience-v1/site.json','utf8'));
 for(let i=0;i<2;i++)for(const k of ['hero','palette','type','collection'])assert.equal((lab.site.profiles[i] as any)[k],prior.profiles[i][k]);
 assert.deepEqual(lab.site.profiles.slice(2).map(p=>p.hero),['Collage','Poster']);assert.equal(richExperiencePages.length,11);
 assert.equal(RichExperienceV1.safeParse({...lab.site,human_approval:'APPROVED'}).success,false);
});
test('community fixtures cannot imply real customers, ratings, social accounts or contact delivery',()=>{
 for(const mutate of [(v:any)=>v.reviews[0].verified_customer=true,(v:any)=>v.reviews[0].rating=5,(v:any)=>v.posts[0].source='INSTAGRAM',(v:any)=>v.contact.social_accounts[0].url='https://instagram.com/someone',(v:any)=>v.contact.phone='+123456',(v:any)=>v.contact.email='real@example.com']){const v=structuredClone(lab.community);mutate(v);assert.equal(DemoCommunityV1.safeParse(v).success,false);}
});
test('148 exact usages pass within documented scope; forged handles and altered scope remain blocked',()=>{
 assert.equal(lab.experience_media.review.usages.length,148);
 for(const u of lab.experience_media.review.usages)assert.equal(evaluateRichExperienceUsage(lab.experience_media.handle,u,at).status,'ALLOWED');
 const u=lab.experience_media.review.usages[0]!;
 for(const patch of [{client_id:'another-client'},{project_id:'another-project'},{page:'/not-permitted/'},{scope_id:'other-branch'},{purpose:'documentary'},{role:'DOCUMENTARY'},{attribution_text:null},{ai_operations:['training']}])assert.equal(evaluateRichExperienceUsage(lab.experience_media.handle,{...u,...patch},at).status,'BLOCKED');
 assert.equal(evaluateRichExperienceUsage(lab.experience_media.handle,u,'2030-01-01T00:00:00.000Z').status,'BLOCKED');assert.throws(()=>evaluateRichExperienceUsage({review_sha256:lab.experience_media.review.review_sha256},u,at),/HANDLE_UNVERIFIED/);
});
test('editorial usages bind to their own module, never masquerading as H2 menu on home',()=>{
 const u=lab.experience_media.review.usages.filter(u=>u.id.startsWith('rich-editorial:'));assert.equal(u.length,64);assert(u.every(u=>u.module_id==='editorial:journal'&&u.representation==='GENERIC_CONTEXT'&&u.subject_ids.length===0));
});
test('a changed and resealed new rights review cannot acquire permission',async()=>{
 const {review_sha256,...body}=structuredClone(lab.experience_media.review);body.grants[0]!.pages.push('/another/');assert.equal((await verifyRichExperienceMedia({...body,review_sha256:inputSha256(body)},process.cwd(),at)).success,false);
});
test('88-view coverage rejects duplicate routes and altered dimensions before any receipt can pass',()=>{
 const ids=lab.site.profiles.map(p=>p.id),pages=richExperiencePages.map(p=>p.kind),viewports=[{id:'desktop',width:1440,height:1000},{id:'mobile',width:390,height:844}],views=ids.flatMap(design=>pages.flatMap(kind=>viewports.map(viewport=>({design,kind,viewport}))));
 assertExperienceCoverage(views,ids,pages,viewports);const bad=structuredClone(views);bad[0]=structuredClone(bad[1]!);assert.throws(()=>assertExperienceCoverage(bad,ids,pages,viewports),/COVERAGE_INVALID/);
});
test('88 actual browser views preserve factual and fictional layers with scoped credits and media',async()=>{
 const o=JSON.parse(await readFile('docs/evidence/corrections/b3/human-iab-r3-20261020/observations.json','utf8'));assert.equal(o.views.length,88);for(const v of o.views)assert.deepEqual(auditRichExperience(v.observed,lab),{success:true,codes:[]},`${v.design}/${v.kind}/${v.viewport.id}`);
});
test('editorial audit rejects missing disclosure, invented review author, lost content and nonlocal social claim',async()=>{
 const views=JSON.parse(await readFile('docs/evidence/corrections/b3/human-iab-r3-20261020/observations.json','utf8')).views,home=views.find((v:any)=>v.kind==='home').observed;
 for(const [mutate,code]of [[(o:any)=>o.review_disclosure='Opiniones','RICH_REVIEW_REPRESENTATION_INVALID'],[(o:any)=>o.reviews[0].author='Cliente verificado','RICH_REVIEW_REPRESENTATION_INVALID'],[(o:any)=>o.editorials.pop(),'RICH_EDITORIAL_CONTENT_INVALID'],[(o:any)=>o.links.push({href:'https://instagram.com/real',text:'Instagram'}),'RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID'],[(o:any)=>o.social_controls=1,'RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID'],[(o:any)=>o.links.push({href:'mailto:hola@lamesa.example',text:'Email'}),'RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID'],[(o:any)=>o.links.push({href:'tel:+1234',text:'Teléfono'}),'RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID'],[(o:any)=>o.links.push({href:'https://wa.me/1234',text:'WhatsApp'}),'RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID'],[(o:any)=>o.film_control.label='','RICH_MOTION_CONTROL_INVALID']] as const){const o=structuredClone(home);mutate(o);assert(auditRichExperience(o,lab).codes.includes(code),code);}
});
test('journal binding rejects swapped permitted bytes, slots or usage IDs even with unchanged global inventory',async()=>{
 const views=JSON.parse(await readFile('docs/evidence/corrections/b3/human-iab-r3-20261020/observations.json','utf8')).views,home=views.find((v:any)=>v.kind==='home').observed;
 for(const mutate of [(o:any)=>{[o.editorials[0].src,o.editorials[1].src]=[o.editorials[1].src,o.editorials[0].src];},(o:any)=>{[o.editorials[0].uses,o.editorials[1].uses]=[o.editorials[1].uses,o.editorials[0].uses];},(o:any)=>o.editorials[0].slot='journal-pasta']){const o=structuredClone(home);mutate(o);assert(auditRichExperience(o,lab).codes.includes('RICH_EDITORIAL_MEDIA_MISMATCH'));}
});
