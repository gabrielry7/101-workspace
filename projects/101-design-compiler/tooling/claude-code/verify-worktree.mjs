// Runs the repository's existing checks; does not change their thresholds.
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {root,run} from './bridge.mjs';
const id=process.argv[2];if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id??''))throw Error('Task ID required');
const label=process.argv[3]??'verify';if(!/^[a-z0-9-]+$/.test(label))throw Error('Invalid check label');
const dir=resolve(root,`.tools/claude-code/${id}`),state=JSON.parse(await readFile(resolve(dir,'state.json'),'utf8'));
if(state.status==='running')throw Error('Do not verify while Claude is editing');
if(resolve(state.worktree)!==resolve(root,`.tools/claude-worktrees/${id}`))throw Error('Unexpected worktree');
process.env.PATH=dirname(process.execPath)+';'+process.env.PATH;
process.env.ASTRO_TELEMETRY_DISABLED='1';
const npm=resolve(dirname(process.execPath),'node_modules/npm/bin/npm-cli.js'),checks=[];
for(const script of ['test','check','build']){
  const startedAt=new Date().toISOString();console.log(`Running existing npm ${script}`);
  const result=await run(process.execPath,[npm,'run',script],{cwd:state.worktree,timeoutMs:240000});
  await writeFile(resolve(dir,`${label}-${script}.log`),result.stdout+'\n'+result.stderr);
  checks.push({script,startedAt,finishedAt:new Date().toISOString(),exitCode:result.code,timedOut:result.timedOut,passed:result.code===0&&!result.timedOut});
  console.log(JSON.stringify(checks.at(-1)));
}
await writeFile(resolve(dir,`${label}.json`),JSON.stringify({checks},null,2)+'\n');
if(checks.some(c=>!c.passed))process.exitCode=1;
