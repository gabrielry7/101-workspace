import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {root} from './raven-client.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const install=spawnSync(process.execPath,[resolve(root,'tooling/design-evaluation/node_modules/impeccable/cli/bin/cli.js'),'install','--providers=codex','--scope=project','--no-hooks','--yes'],{cwd:root,encoding:'utf8',windowsHide:true});
process.stdout.write(install.stdout||'');process.stderr.write(install.stderr||'');if(install.status!==0)throw Error('IMPECCABLE_INSTALL_FAILED');
const paths=[];async function walk(p){for(const e of await readdir(p,{withFileTypes:true})){const f=`${p}/${e.name}`;if(e.isDirectory())await walk(f);else if(!f.includes('/bin/'))paths.push(f);}}
await walk('.agents/skills/impeccable');const files=await Promise.all(paths.sort().map(async path=>({path,sha256:sha((await readFile(path,'utf8')).replaceAll('\r\n','\n'))})));
const pin='tooling/design-evaluation/skill-integrity.json';
if(process.argv.includes('--record'))await writeFile(pin,JSON.stringify({package:'impeccable@4.7.0',engine:'0.1.16',files},null,2)+'\n');
else if(JSON.stringify(JSON.parse(await readFile(pin,'utf8')).files)!==JSON.stringify(files))throw Error('INSTALLED_SKILL_DRIFT');
await mkdir('.codex',{recursive:true});
const config=`# Generated project-local configuration. No global settings changed.\n[mcp_servers.raven]\ncommand = ${JSON.stringify(process.execPath.replaceAll('\\','/'))}\nargs = [${JSON.stringify(resolve(root,'tooling/design-evaluation/launch-raven.mjs').replaceAll('\\','/'))}]\ncwd = ${JSON.stringify(root.replaceAll('\\','/'))}\nstartup_timeout_sec = 20\ntool_timeout_sec = 60\nenabled_tools = ["get_principles", "get_pattern", "audit_url", "audit_layout", "audit_typography", "audit_contrast", "audit_tap_targets", "score_page", "evaluate_design", "list_taste_profiles", "audit_taste"]\n`;
let old='';try{old=await readFile('.codex/config.toml','utf8');}catch{}
if(old&&!old.startsWith('# Generated project-local configuration.'))throw Error('EXISTING_CODEX_CONFIG_REQUIRES_MERGE');
await writeFile('.codex/config.toml',config);console.log('Local skill integrity and project MCP configuration verified. Codex host may require a new session/restart to discover tools; SDK client exercises the actual stdio MCP now.');
