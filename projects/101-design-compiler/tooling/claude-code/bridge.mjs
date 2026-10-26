import {spawn} from 'node:child_process';
import {readFile, writeFile, mkdir, open, realpath, copyFile, access} from 'node:fs/promises';
import {resolve, dirname, relative, isAbsolute, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

export const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const home = process.env.USERPROFILE || process.env.HOME;
const storage = resolve(root, '.tools/claude-code');
const config = JSON.parse(await readFile(new URL('./config.json', import.meta.url), 'utf8'));
const role = await readFile(new URL('./frontend-role.txt', import.meta.url), 'utf8');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const json = async path => JSON.parse(await readFile(path, 'utf8'));
const save = (path, value) => writeFile(path, JSON.stringify(value, null, 2)+'\n');
export function responseSucceeded(transport,response,previousSession=null) {
  return transport.code===0&&!transport.timedOut&&!transport.overflow&&!response?.is_error
    &&response?.type==='result'&&response?.subtype==='success'
    &&typeof response?.result==='string'&&typeof response?.session_id==='string'&&!!response.session_id
    &&(!previousSession||response.session_id===previousSession);
}
function idCheck(id) { if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id)) throw Error('Invalid task ID'); return id; }
export function limits(c) {
  for (const key of ['maxCalls','maxTurns','timeoutMs','maxBudgetUsdPerCall','maxBudgetUsdTotal']) {
    if (!Number.isFinite(c[key]) || c[key] <= 0) throw Error(`Invalid limit: ${key}`);
  }
  if (![c.maxCalls,c.maxTurns,c.timeoutMs].every(Number.isInteger)) throw Error('Integer limits required');
  return c;
}
export async function run(executable, args, {cwd=root, input='', timeoutMs=30000, env=process.env}={}) {
  return new Promise((done, reject) => {
    const child = spawn(executable, args, {cwd, env, shell:false, windowsHide:true, stdio:['pipe','pipe','pipe']});
    let stdout='', stderr='', timedOut=false, overflow=false;
    const stop = () => {
      if (process.platform === 'win32' && child.pid) {
        const killer=spawn('taskkill.exe',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
        killer.on('error',()=>child.kill());
        killer.on('close',code=>{if(code!==0)child.kill('SIGKILL');});
      } else child.kill('SIGKILL');
    };
    const timer = setTimeout(()=>{timedOut=true;stop();},timeoutMs);
    const collect = key => data => { if (stdout.length+stderr.length > 8_000_000) {overflow=true;stop();return;} if(key==='out') stdout+=data; else stderr+=data; };
    child.stdout.on('data',collect('out')); child.stderr.on('data',collect('err'));
    child.on('error',error=>{clearTimeout(timer);reject(error);});
    child.on('close',(code,signal)=>{clearTimeout(timer);done({code,signal,stdout,stderr,timedOut,overflow});});
    child.stdin.on('error',()=>{});child.stdin.end(input);
  });
}
async function git(args,cwd=root) {
  // Trust only these explicit checkout paths for this invocation; no global exception.
  const r=await run('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'-c',`safe.directory=${resolve(cwd).replaceAll('\\','/')}`,...args],{cwd,timeoutMs:180000}); if(r.code!==0) throw Error(`git ${args[0]}: ${r.stderr}`); return r.stdout;
}
async function executable() {
  if(process.env.CLAUDE_CODE_BIN) return process.env.CLAUDE_CODE_BIN;
  const native=resolve(home,'.local/bin',process.platform==='win32'?'claude.exe':'claude');
  try {await realpath(native);return native;} catch {return 'claude';}
}
export async function doctor() {
  const bin=await executable();
  const version=await run(bin,['--version']);
  const help=await run(bin,['--help']);
  const required=['--output-format','--resume','--max-turns','--max-budget-usd','--tools','--allowedTools','--permission-mode','--strict-mcp-config','--settings'];
  // Some supported flags (notably max-turns in 2.1.308) are hidden from help.
  const turnsProbe=await run(bin,['--max-turns','1','--version']);
  const missing=required.filter(flag=>!help.stdout.includes(flag)&&!(flag==='--max-turns'&&turnsProbe.code===0));
  const auth=await run(bin,['auth','status']);
  let parsed;try{parsed=JSON.parse(auth.stdout);}catch{}
  // Deliberately omit account identity and all credential material.
  const result={platform:process.platform,arch:process.arch,node:process.version,bin,version:version.stdout.trim(),
    supported:version.code===0 && help.code===0 && missing.length===0 && help.stdout.includes('--restricted'),missingFlags:missing,
    authenticated:auth.code===0 && parsed?.loggedIn===true,authMethod:parsed?.authMethod ?? null,
    restrictedAvailable:help.stdout.includes('--restricted'),checkedAt:new Date().toISOString()};
  await mkdir(storage,{recursive:true});await save(resolve(storage,'doctor.json'),result);return result;
}
async function contextFiles(paths,base) {
  const result=[];
  for(const path of paths || []) {
    const actual=await realpath(resolve(base,path));const rel=relative(await realpath(base),actual);
    if(isAbsolute(rel)||rel==='..'||rel.startsWith('..'+sep)||/(^|[\\/])(?:\.env[^\\/]*|\.git|\.aws|\.claude)(?:[\\/]|$)/i.test(rel)) throw Error(`Context path rejected: ${path}`);
    const bytes=await readFile(actual);if(bytes.length>1_000_000)throw Error(`Context too large: ${path}`);
    result.push({path:rel.replaceAll('\\','/'),sha256:sha(bytes),text:bytes.toString('utf8')});
  }
  return result;
}
async function capture(state,dir,index) {
  await writeFile(resolve(dir,`${index}-changes.patch`),await git(['diff','--binary','HEAD'],state.worktree));
  const status=await git(['status','--porcelain=v1','--untracked-files=all'],state.worktree);
  await writeFile(resolve(dir,`${index}-status.txt`),status);
  // Untracked source files remain in the retained worktree for review.
  return status;
}
export async function start(taskPath) {
  const task=await json(resolve(root,taskPath));idCheck(task.id);
  if(!['analysis','implement'].includes(task.mode)||!task.prompt?.trim())throw Error('Task requires mode and prompt');
  const c=limits({...config,...task.limits});
  const preflight=await doctor();if(!preflight.supported||!preflight.authenticated)throw Error(`Claude unavailable or unauthenticated; inspect .tools/claude-code/doctor.json and run claude auth login`);
  const context=await contextFiles(task.context,root);
  const dir=resolve(storage,task.id);
  let exists=false;try{await access(dir);exists=true;}catch{}
  if(exists)throw Error('Task ID already exists; use feedback/status or select a new ID');
  const worktree=resolve(root,'.tools/claude-worktrees',task.id);
  const base=(await git(['rev-parse','HEAD'])).trim();
  try {await git(['worktree','add','--detach',worktree,base]);}
  catch(error){await save(resolve(storage,`${task.id}-setup-error.json`),{id:task.id,phase:'worktree',error:String(error),at:new Date().toISOString()});throw error;}
  await mkdir(dir); // exclusive task creation; failed host permission leaves ID reusable
  const state={id:task.id,mode:task.mode,base,worktree,limits:c,sessionId:null,calls:[],reservedUsd:0,status:'preparing',createdAt:new Date().toISOString()};
  await save(resolve(dir,'task.json'),task);await save(resolve(dir,'context.json'),context);await save(resolve(dir,'state.json'),state);
  const attachments=[];
  try {
  for(const path of task.attachments || []) {
    if(!task.attachmentAuthorization)throw Error('Screenshots/references require attachmentAuthorization describing permitted vision use');
    const actual=await realpath(resolve(root,path)),rel=relative(await realpath(root),actual);
    if(isAbsolute(rel)||rel==='..'||rel.startsWith('..'+sep)||! /\.(png|jpe?g|webp)$/i.test(rel))throw Error('Attachment path rejected');
    const bytes=await readFile(actual);if(bytes.length>8_000_000)throw Error('Attachment too large');
    const target=`.tools/claude-inputs/${attachments.length+1}${actual.slice(actual.lastIndexOf('.'))}`;
    await mkdir(dirname(resolve(worktree,target)),{recursive:true});await copyFile(actual,resolve(worktree,target));
    attachments.push({source:path,path:target,sha256:sha(bytes),authorization:task.attachmentAuthorization});
  }
  await save(resolve(dir,'attachments.json'),attachments);
  }catch(error){state.status='setup_error';state.error=String(error);await save(resolve(dir,'state.json'),state);throw error;}
  state.status='ready';await save(resolve(dir,'state.json'),state);
  return exchange(task.id,task.prompt+`\nApproved local vision attachments (use Read): ${JSON.stringify(attachments)}`,context,task.criteria);
}
export async function exchange(id,prompt,context=[],criteria=[]) {
  idCheck(id);if(!prompt?.trim())throw Error('Empty feedback');
  const dir=resolve(storage,id),lock=await open(resolve(dir,'exchange.lock'),'wx');
  try {
    const state=await json(resolve(dir,'state.json')),c=limits(state.limits);
    if(['running','preparing','setup_error'].includes(state.status))throw Error('Task setup/running state requires inspection before recovery');
    if(state.calls.length>=c.maxCalls||state.reservedUsd+c.maxBudgetUsdPerCall>c.maxBudgetUsdTotal+1e-9)throw Error('Task call/spend reservation limit reached');
    const check=await doctor();if(!check.supported||!check.authenticated)throw Error('Claude authentication/capability preflight failed');
    if(state.calls.length&&!state.sessionId)throw Error('No resumable session; create a new task');
    const index=state.calls.length+1;
    const tools=state.mode==='analysis'?'Read,Glob,Grep':'Read,Glob,Grep,Edit,Write';
    const args=['-p','--output-format','json','--model',c.model,'--max-turns',String(c.maxTurns),'--max-budget-usd',String(c.maxBudgetUsdPerCall),
      '--permission-mode','default','--tools',tools,'--allowedTools',tools,'--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
      '--settings',JSON.stringify({permissions:{deny:['Read(**/.env*)','Read(**/.aws/**)','Read(**/.claude/**)','Edit(**/.git/**)','Write(**/.git/**)']}}),
      '--append-system-prompt',role];
    if(check.restrictedAvailable)args.push('--restricted');
    // Avoid project/user hooks, plugins and implicit MCP context when supported.
    const help=await run(check.bin,['--help']);if(help.stdout.includes('--setting-sources'))args.push('--setting-sources','');
    if(state.sessionId)args.push('--resume',state.sessionId);
    const input=`Task ${id}. Worktree: ${state.worktree}. Mode: ${state.mode}.\n${prompt}\nEvaluation criteria:\n${JSON.stringify(criteria)}\nExplicit context (current orchestrator snapshot; worktree starts from ${state.base}):\n${context.map(f=>`PATH ${f.path} SHA256 ${f.sha256}\n${f.text}`).join('\n')}\nReturn a concise report with changed files, decisions, checks and risks. Do not claim checks Codex has not run.`;
    await writeFile(resolve(dir,`${index}-prompt.txt`),input);
    state.status='running';state.reservedUsd+=c.maxBudgetUsdPerCall;
    const record={index,startedAt:new Date().toISOString(),resume:state.sessionId,budgetReservationUsd:c.maxBudgetUsdPerCall,status:'running',cliVersion:check.version};
    state.calls.push(record);await save(resolve(dir,'state.json'),state);
    let r;
    try{r=await run(check.bin,args,{cwd:state.worktree,input,timeoutMs:c.timeoutMs,env:{...process.env,CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC:'1'}});}
    catch(error){r={code:null,stdout:'',stderr:String(error),spawnError:true};}
    await writeFile(resolve(dir,`${index}-stdout.json`),r.stdout);await writeFile(resolve(dir,`${index}-stderr.txt`),r.stderr);
    let response;try{response=JSON.parse(r.stdout);}catch{}
    const session=response?.session_id;
    const sameSession=!record.resume||session===record.resume;
    if(session&&!state.sessionId)state.sessionId=session;
    const ok=responseSucceeded(r,response,record.resume);
    const previousCost=Math.max(0,...state.calls.slice(0,-1).map(c=>c.estimatedCostUsd??0));
    Object.assign(record,{finishedAt:new Date().toISOString(),status:ok?'responded':'error',exitCode:r.code,timedOut:!!r.timedOut,
      sessionId:session??null,sameSession,usage:response?.usage??null,estimatedCostUsd:response?.total_cost_usd??null,
      incrementalEstimatedCostUsd:Number.isFinite(response?.total_cost_usd)?Math.max(0,response.total_cost_usd-previousCost):null,
      numTurns:response?.num_turns??null,durationMs:response?.duration_ms??null,permissionDenials:response?.permission_denials??[],
      error:ok?null:(response?.errors??response?.subtype??r.stderr??'Invalid Claude response')});
    state.status=record.status;await save(resolve(dir,'state.json'),state);
    try {record.changedFiles=await capture(state,dir,index);}
    catch(error){record.diffError=String(error);state.status='error';record.status='error';}
    await save(resolve(dir,'state.json'),state);
    return {id,sessionId:state.sessionId,status:state.status,record,result:response?.result??null,artifacts:dir,worktree:state.worktree};
  } finally {await lock.close();const {unlink}=await import('node:fs/promises');await unlink(resolve(dir,'exchange.lock'));}
}
export async function main(args) {
  const [command,...rest]=args;let result;
  if(command==='doctor')result=await doctor();
  else if(command==='start')result=await start(rest[0]);
  else if(command==='feedback')result=await exchange(rest[0],await readFile(resolve(root,rest[1]),'utf8'));
  else if(command==='status'){idCheck(rest[0]);result=await json(resolve(storage,rest[0],'state.json'));}
  else throw Error('Usage: node tooling/claude-code/bridge.mjs doctor | start task.json | feedback task-id feedback.txt | status task-id');
  console.log(JSON.stringify(result,null,2));
  if(result.status==='error'||command==='doctor'&&(!result.supported||!result.authenticated))process.exitCode=1;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main(process.argv.slice(2)).catch(error=>{console.error(error.message);process.exitCode=1;});
