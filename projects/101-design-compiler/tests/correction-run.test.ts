import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp,writeFile,readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { RunJournalV1,newJournal,redactLog,hashBytes,workspacePath,verifyProtectedFiles,treeHashes } from '../scripts/lib/correction-run.ts';
import { browserSourceOverlay, B0_BROWSER_FLAGS } from '../scripts/lib/correction-browser.ts';
import { verifyJournal,verifyViewCoverage } from '../scripts/lib/correction-evidence.ts';

test('run metering does not invent human time, session usage, currency or approval',()=>{
 const journal=newJournal('test-run');assert.equal(journal.metering.total_cost,null);
 for(const [key,value] of [['human_work_seconds',0],['session_tokens',0],['currency','USD'],['human_approval','APPROVED']] as const)
  assert.equal(RunJournalV1.safeParse({...journal,metering:{...journal.metering,[key]:value}}).success,false);
});
test('logs remove credential query values and authorization headers while preserving diagnostic codes',()=>{
 const text=redactLog('https://example.invalid/?key=fictional-secret&size=2\nAuthorization: Bearer fictional-token\nLOCK_BROWSER_MISMATCH');
 assert.ok(!text.includes('fictional-secret'));assert.ok(!text.includes('fictional-token'));assert.ok(text.includes('LOCK_BROWSER_MISMATCH'));
});
test('artifact paths cannot escape workspace via relative or absolute paths',()=>{
 assert.throws(()=>workspacePath(process.cwd(),'../elsewhere'),/B0_OUTSIDE_WORKSPACE/);
 assert.throws(()=>workspacePath('C:/workspace','D:/elsewhere'),/B0_OUTSIDE_WORKSPACE/);
});
test('protected evidence permits declared text normalization but rejects changed media bytes',async()=>{
 const folder=await mkdtemp(join(tmpdir(),'b0-preservation-')),text=join(folder,'source.txt'),media=join(folder,'asset.bin'),manifest=join(folder,'manifest.json');
 await writeFile(text,'one\r\ntwo\r\n');await writeFile(media,Buffer.from([1,2,3]));
 await writeFile(manifest,JSON.stringify({files:[{path:text,normalization:'LF_TEXT',bytes:8,sha256:hashBytes('one\ntwo\n')},{path:media,normalization:'BINARY',bytes:3,sha256:hashBytes(Buffer.from([1,2,3]))}]}));
 assert.equal((await verifyProtectedFiles(manifest)).checked_files,2);
 await writeFile(media,Buffer.from([1,2,4]));await assert.rejects(verifyProtectedFiles(manifest),/B0_PROTECTED_FILES_CHANGED/);
 assert.equal((await readFile(text,'utf8')),'one\r\ntwo\r\n');
});
test('runtime/output tree fingerprint detects changed bytes and inserted files',async()=>{
 const folder=await mkdtemp(join(tmpdir(),'b0-tree-'));await writeFile(join(folder,'a.bin'),Buffer.from([1]));
 const original=await treeHashes(folder);await writeFile(join(folder,'a.bin'),Buffer.from([2]));
 assert.notEqual((await treeHashes(folder))[0]!.sha256,original[0]!.sha256);
 await writeFile(join(folder,'b.bin'),Buffer.from([1]));assert.equal((await treeHashes(folder)).length,2);
});
test('journal verification rejects tampered logs and hidden additional failures',async()=>{
 const folder=await mkdtemp(join(process.cwd(),'.tools/b0-journal-test-')),log=join(folder,'tests.txt'),path=join(folder,'journal.json');
 const body='LOCK_BROWSER_MISMATCH\nfail 2\n';await writeFile(log,body);
 const journal=newJournal('negative');journal.steps.push({id:'tests',started_at:journal.created_at,finished_at:journal.created_at,wall_seconds:0,
  exit_code:1,status:'BLOCKED_HISTORICAL_ENVIRONMENT',log,log_sha256:hashBytes(body)});
 await writeFile(path,JSON.stringify(journal));await assert.rejects(verifyJournal(path),/B0_UNEXPECTED_FAILURE/);
 await writeFile(log,'changed');await assert.rejects(verifyJournal(path),/B0_LOG_CHANGED/);
});
test('capture coverage rejects duplicate views and wrong page or viewport',()=>{
 const a={label:'a',lock_id:'pilot',semantic_page:'/',viewport:{id:'mobile'}},b={...a,label:'b',viewport:{id:'desktop'}};
 verifyViewCoverage([a,b],[a,b]);
 assert.throws(()=>verifyViewCoverage([a,a],[a,b]),/B0_VIEW_COVERAGE/);
 assert.throws(()=>verifyViewCoverage([{...a,semantic_page:'/wrong'},b],[a,b]),/B0_VIEW_COVERAGE/);
});
test('documented launch overlay refuses changed or ambiguous source; sandbox scope is explicit',()=>{
 const source="spawn('browser',['--headless=new','--disable-gpu','--no-first-run']);";
 const changed=browserSourceOverlay(source);assert.ok(changed.includes('--no-sandbox'));assert.equal(B0_BROWSER_FLAGS.length,4);
 assert.throws(()=>browserSourceOverlay('unrelated code'),/B0_BROWSER_OVERLAY_SOURCE_CHANGED/);
 assert.throws(()=>browserSourceOverlay(source+source),/B0_BROWSER_OVERLAY_SOURCE_CHANGED/);
});
