import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {resolve,relative,isAbsolute,sep} from 'node:path';
import {tmpdir} from 'node:os';
import {loadDemoPackage,verifyDemoPackage,demoPackageData,evaluateDemoUsage} from '../src/media/demo-package.ts';
import {rightsGate} from '../src/media/gate.ts';
import {webmTracks,mp4Handlers} from '../src/media/video-tracks.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const snapshot=JSON.parse(await readFile('data/media/demo-v1/pixabay-fictional.json','utf8'));
const loaded=await loadDemoPackage({evaluation_time:snapshot.evaluated_at}),{handle,pack}=loaded,at=pack.evaluated_at,u=pack.usages[0]!;
test('fictional media has real files/licenses without declaring business evidence or closing documentary gaps',()=>{
 assert.equal(pack.sources.length,5);assert.equal(pack.sources.filter(s=>s.license==='CC0_1_0_BY_TERMS_SECTION_4').length,3);
 assert(pack.assets.every(a=>a.data_mode==='REAL'&&a.documentary===null));assert(pack.needs.every(n=>!n.satisfies_documentary_need));
 assert(pack.usages.every(v=>v.role!=='DOCUMENTARY'&&v.representation==='GENERIC_CONTEXT'&&v.subject_ids.length===0));
 assert(pack.sources.every(s=>s.camera_original==='NOT_OBTAINED'&&s.ai_generated==='NOT_REPORTED'));
 assert(pack.usages.every(v=>evaluateDemoUsage(handle,v,at).status==='ALLOWED'));
});
test('the original audio track stays blocked; only exact byte-verified silent derivative receives associated disposition',async()=>{
 const proof=pack.silent_video,a=pack.assets.find(a=>a.id===proof.render_asset_id)!,v=pack.usages.find(u=>u.asset_id===a.id)!,g=pack.grants.find(g=>g.id===v.grant_id)!;
 assert(rightsGate(a,g,v,pack.assets,at).codes.includes('VIDEO_AUDIO_RIGHTS_REVIEW_REQUIRED'),'Historical H3 behavior preserved');
 assert.equal(evaluateDemoUsage(handle,v,at).status,'ALLOWED');
 const root=pack.files.find(f=>f.asset_id===proof.source_asset_id)!,render=pack.files.find(f=>f.asset_id===proof.render_asset_id)!;
 assert(mp4Handlers(await readFile(root.path)).includes('soun'));assert.deepEqual(webmTracks(await readFile(render.path)),[{type:1,codec:'V_VP8'}]);
 assert.equal(evaluateDemoUsage(handle,{...v,asset_id:proof.source_asset_id},at).status,'BLOCKED');
 assert.equal(evaluateDemoUsage(handle,{...v,attribution_text:null},at).status,'BLOCKED');
});
test('self-created VERIFIED or rewritten checksum cannot authorize another package, audio assertion or serialized handle',async()=>{
 assert.throws(()=>demoPackageData(JSON.parse(JSON.stringify(handle))),/NOT_VERIFIED/);
 const fake=structuredClone(pack);fake.assets.find(a=>a.id===fake.silent_video.source_asset_id)!.audio_track='NONE';
 const {package_sha256:_,...body}=fake;fake.package_sha256=inputSha256(body);
 const denied=await verifyDemoPackage(fake);assert.equal(denied.success,false);assert(denied.codes.includes('DEMO_SOURCE_REVIEW_NOT_PINNED'));
 const copy=demoPackageData(handle);copy.grants[0]!.commercial_web='DENIED';assert.equal(evaluateDemoUsage(handle,u,at).status,'ALLOWED');
});
test('fictional approval cannot migrate to actual evidence, another client, project, branch, purpose or page',()=>{
 for(const mutation of [{client_id:'other'},{project_id:'other'},{scope_id:pack.scenario.scope_id},{page:'/production/'},{purpose:'document:menu'},
  {role:'DOCUMENTARY',representation:'BUSINESS_EVIDENCE',subject_ids:['real-dish']},{generic_label:'Plato real de este restaurante'},{context_notices:[]},{attribution_text:null},{transformations:['CROP']},{ai_operations:['training']},{grant_id:null}]){
  assert.equal(evaluateDemoUsage(handle,{...u,...mutation},at).status,'BLOCKED',JSON.stringify(mutation));
 }
 assert.equal(evaluateDemoUsage(handle,u,pack.grants[0]!.valid_until!).status,'BLOCKED');
});
test('current loader refuses expired package while explicit historical replay remains separately possible',async()=>{
 await assert.rejects(loadDemoPackage({evaluation_time:pack.grants[0]!.valid_until!}),/CURRENT_USE_BLOCKED/);
});
test('changed private source bytes cannot be masked by claims of inspection or permission',async()=>{
 const root=await mkdtemp(resolve(tmpdir(),'101-b2-demo-'));
 try{for(const f of [...pack.files,...pack.evidence]){const p=resolve(root,f.path);await mkdir(resolve(p,'..'),{recursive:true});await writeFile(p,await readFile(f.path));}
  const base='data/derived/requirements-v1/restaurante.json';await mkdir(resolve(root,base,'..'),{recursive:true});await writeFile(resolve(root,base),await readFile(base));
  await writeFile(resolve(root,pack.files[0]!.path),'tampered-source');const denied=await verifyDemoPackage(pack,root);assert.equal(denied.success,false);assert(denied.codes.includes('DEMO_FILE_OR_EVIDENCE_CHANGED'));
 }finally{const rel=relative(resolve(tmpdir()),root);if(isAbsolute(rel)||rel.startsWith('..')||!rel.startsWith('101-b2-demo-')||rel.includes(sep))throw Error('UNSAFE_TEMP_CLEANUP');await rm(root,{recursive:true,force:true});}
});
test('truncated or non-media containers cannot masquerade as a silent rendition',()=>{
 assert.throws(()=>webmTracks(Buffer.from('not-webm')));assert.throws(()=>mp4Handlers(Buffer.alloc(8)));
});
