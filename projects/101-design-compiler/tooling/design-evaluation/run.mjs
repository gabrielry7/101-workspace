import {spawnSync} from 'node:child_process';
import {root} from './raven-client.mjs';
process.chdir(root);
const scripts={prepare:'quality-prepare',observer:'quality-observer',audit:'quality-audit',repair:'quality-repair',judge:'quality-judge',export:'quality-export',verify:'quality-verify'};
const command=process.argv[2];if(!scripts[command])throw Error(`Unknown phase: ${command}. Use ${Object.keys(scripts).join(', ')}.`);
const r=spawnSync(process.execPath,['--experimental-strip-types',`scripts/${scripts[command]}.ts`,...process.argv.slice(3)],{stdio:'inherit',windowsHide:true});process.exitCode=r.status??1;
