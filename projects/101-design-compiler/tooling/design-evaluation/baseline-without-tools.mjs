import {rename,mkdir,writeFile,access} from 'node:fs/promises';
import {resolve,dirname,relative,isAbsolute} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),source=resolve(root,'tooling/design-evaluation/node_modules'),saved=resolve(root,'tooling/design-evaluation/state/dependencies-disabled');
for(const p of [source,saved]){const rel=relative(root,p);if(rel.startsWith('..')||isAbsolute(rel))throw Error('UNSAFE_DEPENDENCY_MOVE');}
if(await access(saved).then(()=>true,()=>false))throw Error('BASELINE_DEPENDENCY_STASH_EXISTS');
await mkdir(dirname(saved),{recursive:true});const start=performance.now();let output='',exit_code;
await rename(source,saved);
try{const child=spawn(process.execPath,[resolve(root,'.tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js'),'run','build'],{cwd:root,env:{...process.env,ASTRO_TELEMETRY_DISABLED:'1',PATH:dirname(process.execPath)+';'+process.env.PATH},windowsHide:true,stdio:['ignore','pipe','pipe']});child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>output+=b);exit_code=await new Promise((done,reject)=>{child.on('error',reject);child.on('close',done);});}
finally{await rename(saved,source);}
const base='docs/evidence/design-evaluation/baseline-without-tools';await writeFile(resolve(root,base+'.txt'),output);await writeFile(resolve(root,base+'.json'),JSON.stringify({status:exit_code===0?'PASS':'FAIL',exit_code,wall_seconds:(performance.now()-start)/1000,evaluator_packages_available:false,dependencies_restored:true,command:'npm run build (original config)',experimental_previews_enabled:false},null,2)+'\n');
console.log(JSON.stringify({exit_code,dependencies_restored:true}));if(exit_code!==0)process.exitCode=1;
