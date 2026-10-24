import { spawn } from 'node:child_process';
import { root,ravenEnvironment } from './raven-client.mjs';
import { resolve } from 'node:path';
const child=spawn(process.execPath,[resolve(root,'tooling/design-evaluation/node_modules/raven-mcp/dist/index.js')],{cwd:root,env:ravenEnvironment(),stdio:'inherit',windowsHide:true});
child.on('exit',code=>{process.exitCode=code??1;});
process.on('SIGINT',()=>child.kill());
process.on('SIGTERM',()=>child.kill());
