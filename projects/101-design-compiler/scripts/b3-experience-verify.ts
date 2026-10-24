import {readFile,writeFile,access,readdir} from 'node:fs/promises';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import ts from 'typescript';
import sharp from 'sharp';
import {loadB3Experience} from './load-b3-experience.ts';
import {auditExperience} from '../src/design/experience-audit.ts';
import {experiencePages,experienceRoute} from '../src/design/experience-contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {byteSha256} from '../src/media/package.ts';
import {assertExperienceCoverage} from '../src/design/experience-coverage.ts';
const dir='docs/evidence/corrections/b3/experience-iab-01',receipt=dir+'/verification.json',lab=await loadB3Experience();
const read=async(p:string)=>readFile(p),json=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
const observations=await json(dir+'/observations.json');assert.equal(observations.views.length,64);
const responsivePath='docs/evidence/corrections/b3/experience-responsive-01/observations.json',responsive=await json(responsivePath);
assert.equal(responsive.views.length,16);
assertExperienceCoverage(responsive.views,lab.site.profiles.map(p=>p.id),['home'],[{id:'small',width:360,height:800},{id:'tablet',width:768,height:1024},{id:'laptop',width:1024,height:768},{id:'wide',width:1920,height:1080}]);
for(const v of responsive.views){assert.deepEqual(auditExperience(v.observed,lab),{success:true,codes:[]});assert.equal(byteSha256(await read(v.screenshot.path)),v.screenshot.sha256);assert.equal(v.observed.video.paused,false);}
const interactions=await json(dir+'/interactions.json'),step=(id:string)=>interactions.records.find((r:any)=>r.step===id).state;
assert.equal(step('manual-pause').paused,true);assert.equal(step('manual-resume').paused,false);assert.equal(step('mobile-menu-escape').open,false);assert.deepEqual(step('search-pasta').visible,['pasta']);assert.deepEqual(step('filter-salad').visible,['salad']);assert(step('add-second-item').includes('2 platos elegidos'));assert(step('simulated-table-and-summary').preview.includes('No se ha reservado ni enviado nada.'));
const expected=lab.site.profiles.flatMap(p=>experiencePages.flatMap(page=>['desktop','mobile'].map(view=>`${p.id}/${page.kind}/${view}`))).sort();
assert.deepEqual(observations.views.map((v:any)=>`${v.design}/${v.kind}/${v.viewport.id}`).sort(),expected);
assertExperienceCoverage(observations.views,lab.site.profiles.map(p=>p.id),experiencePages.map(p=>p.kind),[{id:'desktop',width:1440,height:1000},{id:'mobile',width:390,height:844}]);
const pages=[];
for(const v of observations.views){assert.deepEqual(auditExperience(v.observed,lab),{success:true,codes:[]},`${v.design}/${v.kind}/${v.viewport.id}`);const bytes=await read(v.screenshot.path);assert.equal(byteSha256(bytes),v.screenshot.sha256);const m=await sharp(bytes).metadata();assert.equal(m.format,'jpeg');assert(m.height!>=v.viewport.height);assert(Math.abs(m.height!-v.observed.geometry.height)/v.observed.geometry.height<.05,'IAB_FULLPAGE_GEOMETRY_DELTA_EXCEEDS_5_PERCENT');assert(m.width!<=v.viewport.width&&m.width!>=v.viewport.width-20);
 for(const link of v.observed.links){if(!link.href?.startsWith('/')||link.href.startsWith('//'))continue;const pathname=new URL(link.href,'http://local').pathname;assert(await access(join('dist',pathname,'index.html')).then(()=>true,()=>false),`BROKEN_LINK:${link.href}`);}
 if(v.kind==='home'){assert.equal(v.observed.video.paused,false);assert(v.observed.video.time>0);}
}
for(const p of lab.site.profiles){for(const view of ['desktop','mobile']){const views=observations.views.filter((v:any)=>v.design===p.id&&v.viewport.id===view),modules=new Set(views.flatMap((v:any)=>v.observed.modules.map((m:any)=>m.id))),facts=new Set(views.flatMap((v:any)=>v.observed.modules.flatMap((m:any)=>m.facts.map((f:any)=>f.id))));assert.equal(modules.size,7);assert.equal(facts.size,42);}
 for(const page of experiencePages){const route=experienceRoute(p.root,page),file=join('dist',route,'index.html'),bytes=await read(file);pages.push({route,bytes:bytes.length,sha256:byteSha256(bytes)});}}
const files:string[]=[];async function walk(dir:string){for(const e of await readdir(dir,{withFileTypes:true})){const p=join(dir,e.name);if(e.isDirectory())await walk(p);else if(/\.(ts|astro|css)$/.test(p))files.push(p.replaceAll('\\','/'));}}
await walk('src');await walk('scripts');await walk('tests');
const sources=await Promise.all(files.sort().map(async path=>({path,sha256:byteSha256(Buffer.from((await readFile(path,'utf8')).replaceAll('\r\n','\n')))})));
const source=(await readFile('src/design/experience-audit.ts','utf8')).replaceAll('\r\n','\n');const observer=ts.transpileModule(source.slice(source.indexOf('export function observeExperience'),source.indexOf('const sorted=')),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,newLine:ts.NewLineKind.LineFeed}}).outputText.replace('export function','function');assert.equal(await readFile(dir+'/observer.js','utf8'),observer);
const assets=[];for(const uri of [...new Set(lab.experience_media.review.usages.map(u=>lab.experience_media.review.assets.find(a=>a.id===u.asset_id)!.uri))]){const path='public'+uri,b=await read(path),built=await read('dist'+uri);assert.equal(byteSha256(built),byteSha256(b));assets.push({uri,bytes:b.length,sha256:byteSha256(b)});}
const result={kind:'B3_MULTIPAGE_VERIFICATION',site_sha256:lab.site_sha256,media_sha256:lab.experience_media.review.review_sha256,views:64,responsive_views:16,routes:32,facts_per_profile:42,modules_per_profile:7,observations_sha256:byteSha256(await read(dir+'/observations.json')),responsive_sha256:byteSha256(await read(responsivePath)),interactions_sha256:byteSha256(await read(dir+'/interactions.json')),sources,pages,assets,limits:['Human aesthetic approval pending','IAB viewport observations; no cold transfer or Web Vitals measurement','Fullpage JPEG excludes scrollbar and can reflow text; screenshot and DOM heights differ by up to 69px, under 5 percent; not a pixel-identical geometry proof','Video original 1280x720, no invented resolution','Representative interaction path; not all combinations']};
if(process.argv.includes('--record')){assert.equal(await access(receipt).then(()=>true,()=>false),false,'RECEIPT_EXISTS');await writeFile(receipt,JSON.stringify(result,null,2)+'\n');}
else if(process.argv.includes('--verify'))assert.equal(inputSha256(await json(receipt)),inputSha256(result),'EXPERIENCE_REPLAY_MISMATCH');
else throw Error('EXPLICIT_RECORD_OR_VERIFY_REQUIRED');console.log(JSON.stringify({success:true,views:64,routes:32,assets:assets.length,html_bytes:pages.map(p=>p.bytes),media_bytes:assets.reduce((n,a)=>n+a.bytes,0)}));
