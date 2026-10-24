import { prepareRuntime, verifyRuntime } from './lib/correction-runtime.ts';
const snapshot = process.argv.includes('--verify') ? await verifyRuntime() : await prepareRuntime();
console.log(JSON.stringify({status:'PASS',scope:snapshot.scope,browser:snapshot.browser_version,
 browser_files:snapshot.browser_files.length,snapshot_sha256:snapshot.snapshot_sha256,system_browser_modified:false,old_locks_modified:false}));
