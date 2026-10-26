import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {loadOptionalRestaurantMedia,optionalRestaurantImage} from '../src/media/optional-restaurant.ts';

test('optional restaurant images admit only their reviewed purposes and routes',async()=>{
 const result=await optionalRestaurantImage(5356682,'/b3/candidate-01/reservas/');
 assert.equal(result.assets.length,2);
 assert.deepEqual(result.assets.map(a=>a.inspection.width),[640,1280]);
 await assert.rejects(optionalRestaurantImage(5356682,'/b3/candidate-01/contacto/'),/OPTIONAL_MEDIA_UNREGISTERED_ROUTE/);
 await assert.rejects(optionalRestaurantImage(1834784,'/b3/candidate-01/reservas/'),/OPTIONAL_MEDIA_UNREGISTERED_ROUTE/);
});

test('optional media expires through the existing rights gate',async()=>{
 await assert.rejects(loadOptionalRestaurantMedia(process.cwd(),'2099-01-01T00:00:00Z'),/OPTIONAL_MEDIA_USE_BLOCKED/);
});

test('changed optional inventory and missing reviewed bytes fail closed',async()=>{
 const folder=await mkdtemp(join(tmpdir(),'101-optional-'));
 try{
  const manifest='data/media/demo-v1/claude-optional-20261024.json',raw=JSON.parse(await readFile(manifest,'utf8'));
  await mkdir(join(folder,'data/media/demo-v1'),{recursive:true});
  await writeFile(join(folder,manifest),JSON.stringify({...raw,choices:[]}));
  await assert.rejects(loadOptionalRestaurantMedia(folder),/OPTIONAL_MEDIA_NOT_PINNED/);
  await writeFile(join(folder,manifest),JSON.stringify(raw));
  await mkdir(join(folder,'docs/evidence/claude-code/redesign-20261024'),{recursive:true});
  await writeFile(join(folder,raw.evidence.path),await readFile(raw.evidence.path));
  await assert.rejects(loadOptionalRestaurantMedia(folder),/ENOENT/);
 }finally{assert.ok(resolve(folder).startsWith(resolve(tmpdir())+requireSeparator()));await rm(folder,{recursive:true,force:true});}
});
function requireSeparator(){return process.platform==='win32'?'\\':'/';}
