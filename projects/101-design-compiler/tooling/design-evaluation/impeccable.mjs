import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { root } from './raven-client.mjs';
export async function detect(target) {
 const start=performance.now();
 const child=spawn(process.execPath,[resolve(root,'tooling/design-evaluation/node_modules/impeccable/cli/bin/cli.js'),'detect','--json',target],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
 let out='',err='';child.stdout.on('data',b=>out+=b);child.stderr.on('data',b=>err+=b);
 const exit_code=await new Promise((done,reject)=>{child.on('error',reject);child.on('close',done);});
 if(![0,2].includes(exit_code))throw Error(`IMPECCABLE_SCAN_FAILED:${exit_code}:${err}`);
 return {tool:'impeccable.detect',version:'4.7.0/engine-0.1.16',target,wall_seconds:(performance.now()-start)/1000,exit_code,findings:JSON.parse(out)};
}
