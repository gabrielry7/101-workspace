import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile,writeFile,mkdir } from 'node:fs/promises';
import { DesignLockV1 } from '../src/lock/contracts.ts';
import { lockHash } from '../src/lock/validate.ts';
import { verifyLockFiles,REBUILD_ENTRIES } from '../scripts/lib/rebuild-lock.ts';
import { sourceGraph } from '../scripts/lib/lock-files.ts';
const lock=DesignLockV1.parse(JSON.parse(await readFile('fixtures/locks/h8/pilot-flow.json','utf8')));
test('source graph closes runtime imports without creative loaders or sampler; all archived bytes are recoverable',async()=>{
 const graph=await sourceGraph(process.cwd(),REBUILD_ENTRIES);assert.deepEqual(graph.paths,lock.sources.map(s=>s.path));assert.ok(graph.paths.every(p=>!p.includes('design/search.ts')&&!p.includes('scripts/load-')));assert.ok(graph.paths.includes('src/components/composition/DesignComposition.astro'));assert.ok(graph.paths.includes('src/media/package.ts'));
 for(const source of lock.sources)assert.ok((await readFile(`${lock.source_snapshot_root}/${source.path}.txt`)).length>0);
});
test('source and Node fingerprint mismatches fail before rendering without editing shared files',async()=>{
 const source=structuredClone(lock);source.sources.find(s=>s.path==='scripts/rebuild-h8.ts')!.sha256='0'.repeat(64);source.lock_sha256=lockHash(source);await assert.rejects(verifyLockFiles(source),/LOCK_SOURCE_MISMATCH/);
 const node=structuredClone(lock);node.toolchain.node_version='v0.0.0-seeded';node.lock_sha256=lockHash(node);await assert.rejects(verifyLockFiles(node),/LOCK_NODE_MISMATCH/);
});
test('missing or corrupt audit source bytes and source-report inconsistency reject before render',async()=>{
 const folder=`.tools/h8-r1-audit-negative-${Date.now()}`;await mkdir(folder,{recursive:true});
 const corrupt=structuredClone(lock),path=`${folder}/source-corrupt.json`;await writeFile(path,'corrupted audit source');corrupt.audit_state.source.stored_path=path;corrupt.lock_sha256=lockHash(corrupt);await assert.rejects(verifyLockFiles(corrupt),/LOCK_AUDIT_FILE_MISMATCH/);
 const missing=structuredClone(lock);missing.audit_state.source.stored_path=`${folder}/missing.json`;missing.lock_sha256=lockHash(missing);await assert.rejects(verifyLockFiles(missing),/ENOENT/);
 const mismatch=structuredClone(lock);mismatch.audit_state.source.group_label='nonexistent-group';mismatch.lock_sha256=lockHash(mismatch);await assert.rejects(verifyLockFiles(mismatch),/LOCK_AUDIT_SOURCE_REPORT_MISMATCH/);
});
