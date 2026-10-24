import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdtemp,copyFile,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {verifyPlannerReplay} from '../scripts/lib/planner-readonly.ts';
import {loadPlannerFixtures} from '../scripts/load-planner-fixtures.ts';
import {loadB1Fixtures} from '../scripts/lib/b1-fixtures.ts';
import {loadMappingRegistry} from '../scripts/load-taxonomy.ts';
import {diagnoseBusiness} from '../src/requirements/diagnose.ts';
test('H2 replay succeeds with filesystem writes denied by Node permissions and keeps exact original bytes/mtime',async()=>{
 const names=(await loadPlannerFixtures()).map(f=>`data/derived/planner-v1/${f.scenario}.json`);
 const before=await Promise.all(names.map(async path=>({path,bytes:await readFile(path),mtime:(await stat(path,{bigint:true})).mtimeNs})));
 const result=await promisify(execFile)(process.execPath,['--permission','--allow-fs-read=*','--experimental-strip-types','scripts/b1-planner-replay.ts'],{cwd:process.cwd(),maxBuffer:1000000});
 assert.equal(JSON.parse(result.stdout).status,'H2_BYTE_IDENTICAL_READ_ONLY_REPLAY');
 for(const file of before){assert.deepEqual(await readFile(file.path),file.bytes);assert.equal((await stat(file.path,{bigint:true})).mtimeNs,file.mtime);}
});
test('byte-only replay rejects corrupted or whitespace-altered H2 output without repairing it',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'b1-h2-replay-')),fixtures=await loadPlannerFixtures();
 for(const f of fixtures)await copyFile(`data/derived/planner-v1/${f.scenario}.json`,join(directory,`${f.scenario}.json`));
 await verifyPlannerReplay(directory);const path=resolve(directory,`${fixtures[0]!.scenario}.json`),original=await readFile(path);
 const changed=Buffer.concat([original,Buffer.from(' ')]);await writeFile(path,changed);const mtime=(await stat(path,{bigint:true})).mtimeNs;
 await assert.rejects(verifyPlannerReplay(directory),/PLANNER_REPLAY_BYTES_MISMATCH/);
 assert.deepEqual(await readFile(path),changed);assert.equal((await stat(path,{bigint:true})).mtimeNs,mtime);
});
test('an unrelated same-branch price does not activate currency requirements for a menu without prices',async()=>{
 const f=structuredClone((await loadB1Fixtures()).find(f=>f.scenario==='restaurante')!),{rules}=await loadMappingRegistry(),branch=f.input.locations[0]!.id;
 const opts={rules,activity_links:f.activity_links,activity_relationships:f.activity_relationships,category_context:f.category_context,objective_decisions:f.objective_decisions};
 const currency=(value:ReturnType<typeof diagnoseBusiness>)=>value.diagnostic.entries.find(e=>e.scope_id===branch&&e.capability_id==='menu')!.levels[0]!.requirements.find(r=>r.requirement_id.includes(':currency:'))!;
 const before=currency(diagnoseBusiness(f.input,opts));assert.equal(before.status,'NOT_REQUIRED_BY_CONDITION');
 f.input.facts.push({id:'unrelated-price',kind:'price',value:123,scope_id:branch,publication:'APPROVED',publication_decision_id:'synthetic-unrelated-price',source:'synthetic-regression-fixture',observed_at:'2026-10-01T00:00:00Z'});
 assert.deepEqual(currency(diagnoseBusiness(f.input,opts)),before);
});
test('a media reference in the same scope never proves use by opening hours or triggers optional rights checks',async()=>{
 const f=structuredClone((await loadB1Fixtures()).find(f=>f.scenario==='restaurante')!),{rules}=await loadMappingRegistry(),scope=f.input.locations[0]!.id;
 const opts={rules,activity_links:f.activity_links,activity_relationships:f.activity_relationships,category_context:f.category_context,objective_decisions:f.objective_decisions};
 const conditional=(result:ReturnType<typeof diagnoseBusiness>)=>result.diagnostic.entries.find(e=>e.scope_id===scope&&e.capability_id==='opening_hours')!.levels.find(l=>l.level_id==='detailed_information')!.requirements.filter(r=>r.requirement_id.endsWith('_if_used'));
 const before=conditional(diagnoseBusiness(f.input,opts));assert.ok(before.length===2&&before.every(r=>r.status==='NOT_REQUIRED_BY_CONDITION'));
 f.input.existing_media.push({id:'unrelated-photo',source:'synthetic-regression',uri:'https://example.invalid/photo.jpg',kind:'image',scope_id:scope,rights_status:'DOCUMENTED',rights_document_ids:['fixture-document-not-permission'],restrictions:[]});
 assert.deepEqual(conditional(diagnoseBusiness(f.input,opts)),before);
 const gallery=diagnoseBusiness(f.input,opts).diagnostic.entries.find(e=>e.scope_id===scope&&e.capability_id==='gallery')!;
 assert.ok(gallery.levels[0]!.requirements.some(r=>r.requirement_id==='media_rights'&&r.status==='RIGHTS_REVIEW_PENDING'));
});
