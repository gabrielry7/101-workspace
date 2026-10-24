import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadB3Experience} from '../scripts/load-b3-experience.ts';
import {ExperienceV1,experiencePages,experienceRoute} from '../src/design/experience-contracts.ts';
import {auditExperience} from '../src/design/experience-audit.ts';
import {allowBackgroundMotion} from '../src/design/background-policy.ts';
import {evaluateExperienceUsage,verifyExperienceMedia} from '../src/media/experience-review.ts';
import {videoOnlyMp4} from '../src/media/remux-video.ts';
import {mp4Handlers} from '../src/media/video-tracks.ts';
import {byteSha256} from '../src/media/package.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {assertExperienceCoverage} from '../src/design/experience-coverage.ts';
const lab=await loadB3Experience(),at='2026-10-16T18:00:00.000Z';
const observations=JSON.parse(await readFile('docs/evidence/corrections/b3/experience-iab-01/observations.json','utf8')).views;
test('responsive coverage rejects duplicate, substituted and mislabeled viewport dimensions',async()=>{
 const views=JSON.parse(await readFile('docs/evidence/corrections/b3/experience-responsive-01/observations.json','utf8')).views;
 const widths=[{id:'small',width:360,height:800},{id:'tablet',width:768,height:1024},{id:'laptop',width:1024,height:768},{id:'wide',width:1920,height:1080}],profiles=lab.site.profiles.map(p=>p.id);
 assert.doesNotThrow(()=>assertExperienceCoverage(views,profiles,['home'],widths));
 for(const mutate of [(v:any[])=>v[0]=structuredClone(v[1]),(v:any[])=>v[0].design='candidate-99',(v:any[])=>v[0].viewport.width=361,(v:any[])=>v[0].viewport.height=801,(v:any[])=>v.pop()]){const bad=structuredClone(views);mutate(bad);assert.throws(()=>assertExperienceCoverage(bad,profiles,['home'],widths),/VIEWPORT_COVERAGE_INVALID/);}
});
test('multipage experience preserves context and cannot claim a human score or arbitrary style code',()=>{
 assert.equal(new Set(lab.site.profiles.flatMap(p=>experiencePages.map(page=>experienceRoute(p.root,page)))).size,32);
 for(const patch of [{human_approval:'APPROVED'},{feedback_status:'RATED_10'},{profiles:lab.site.profiles.map(p=>({...p,css:'body{}'}))}])assert.equal(ExperienceV1.safeParse({...lab.site,...patch}).success,false);
});
test('background motion respects five independent suppression conditions',()=>{
 const allowed={reducedMotion:false,saveData:false,documentVisible:true,inView:true,manualPause:false};assert(allowBackgroundMotion(allowed));
 for(const key of Object.keys(allowed) as (keyof typeof allowed)[])assert.equal(allowBackgroundMotion({...allowed,[key]:!allowed[key]}),false,key);
});
test('all exact multipage usages are allowed, while a different scope, purpose, transformation or date is blocked',()=>{
 const media=lab.experience_media;for(const u of media.review.usages)assert.equal(evaluateExperienceUsage(media.handle,u,at).status,'ALLOWED');
 const u=media.review.usages[0]!;
 for(const patch of [{client_id:'another-client'},{project_id:'another-project'},{page:'/elsewhere/'},{business_id:'another-business'},{role:'DOCUMENTARY'},{transformations:['AI_PROCESSING']},{scope_id:'another-branch'}])assert.equal(evaluateExperienceUsage(media.handle,{...u,...patch},at).status,'BLOCKED');
 assert.equal(evaluateExperienceUsage(media.handle,u,'2030-01-01T00:00:00.000Z').status,'BLOCKED');
 assert.throws(()=>evaluateExperienceUsage({review_sha256:media.review.review_sha256},u,at),/HANDLE_UNVERIFIED/);
});
test('editing and resealing a media review cannot manufacture verified rights',async()=>{
 const changed=structuredClone(lab.experience_media.review);changed.policy.human_approval='APPROVED' as any;assert.equal((await verifyExperienceMedia(changed,process.cwd(),at)).success,false);
 const {review_sha256,...body}=lab.experience_media.review;body.project_id='other-project' as any;
 assert.equal((await verifyExperienceMedia({...body,review_sha256:inputSha256(body)},process.cwd(),at)).success,false);
});
test('lossless remux reproduces actual reviewed bytes with a sole video track and identical decoded pixels',async()=>{
 const source=await readFile('.tools/b2-demo/originals/149678.mp4'),output=await readFile('public/media/b3-experience/149678-silent-1280.mp4');
 assert.deepEqual(mp4Handlers(source).sort(),['soun','vide']);assert.deepEqual(mp4Handlers(output),['vide']);
 assert.equal(byteSha256(videoOnlyMp4(source).output),byteSha256(output));assert.throws(()=>videoOnlyMp4(Buffer.from('not mp4')));
 const decode=JSON.parse(await readFile('docs/evidence/corrections/b3/experience-media-01/decode.json','utf8'));assert.equal(decode.decoded_frames,234);assert.equal(decode.all_decoded_pixels_identical,true);
});
test('64 actual browser views retain scoped facts, media bindings, labels and navigation',()=>{
 assert.equal(observations.length,64);for(const v of observations)assert.deepEqual(auditExperience(v.observed,lab),{success:true,codes:[]},`${v.design}/${v.kind}/${v.viewport.id}`);
});
test('browser audit rejects lost facts, wrong offering bytes, credit loss and fake operational forms',()=>{
 const cases:[string,(o:any)=>void,string][]=[
  ['collection',o=>o.modules[0].facts.pop(),'EXPERIENCE_FACT_OR_MODULE_LOSS'],
  ['collection',o=>o.modules[0].scope='other-branch','EXPERIENCE_FACT_OR_MODULE_LOSS'],
  ['collection',o=>o.modules[0].offerings[0].src=o.modules[0].offerings[1].src,'EXPERIENCE_OFFERING_MEDIA_MISMATCH'],
  ['collection',o=>o.inline_credits=1,'EXPERIENCE_CREDIT_OR_CONTEXT_MISSING'],
  ['credits',o=>o.credits=[],'EXPERIENCE_CREDITS_OR_DIAGNOSTICS_LOST'],
  ['home',o=>o.video.muted=false,'EXPERIENCE_BACKGROUND_POLICY_INVALID'],
  ['home',o=>o.film.width=400,'EXPERIENCE_BACKGROUND_POLICY_INVALID'],
  ['home',o=>o.operation=['DEMO_ONLY'],'EXPERIENCE_HOME_FUNCTION_PILEUP'],
  ['request',o=>o.forms=1,'EXPERIENCE_NAVIGATION_OR_OPERATION_INVALID'],
  ['request',o=>o.operation=[],'EXPERIENCE_PREVIEW_LABEL_MISSING'],
 ];for(const [kind,mutate,code]of cases){const o=structuredClone(observations.find((v:any)=>v.kind===kind).observed);mutate(o);assert(auditExperience(o,lab).codes.includes(code),code);}
});
