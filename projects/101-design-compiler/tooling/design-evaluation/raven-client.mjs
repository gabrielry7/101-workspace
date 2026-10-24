import { Client } from './node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from './node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { mkdir } from 'node:fs/promises';
export const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const readTools = ['get_principles','get_pattern','audit_url','audit_layout','audit_typography','audit_contrast','audit_tap_targets','score_page','evaluate_design','list_taste_profiles','audit_taste'];
export function ravenEnvironment() {
  const env = Object.fromEntries(['PATH','SystemRoot','WINDIR','TEMP','TMP','COMSPEC'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
  for (const key of ['TASTE','DECISIONS','CREATIVE','REFERENCE','SYSTEMS']) env[`RAVEN_${key}_HOME`] = resolve(root, `tooling/design-evaluation/state/${key.toLowerCase()}`);
  Object.assign(env,{RAVEN_NO_UPDATE_CHECK:'1',RAVEN_NO_DAILY_DIGEST:'1',RAVEN_NO_USAGE_LOG:'1',RAVEN_NO_CONSULTATION_TRACE:'1'});
  return env;
}
export class RavenSession {
  calls=[];
  async connect() {
    await mkdir(resolve(root,'tooling/design-evaluation/state'),{recursive:true});
    this.transport=new StdioClientTransport({command:process.execPath,args:[resolve(root,'tooling/design-evaluation/node_modules/raven-mcp/dist/index.js')],cwd:root,env:ravenEnvironment(),stderr:'pipe'});
    this.client=new Client({name:'101-design-evaluation',version:'1.0.0'});
    await this.client.connect(this.transport);
    this.tools=(await this.client.listTools()).tools;
    return this;
  }
  async call(name,args) {
    if(!readTools.includes(name)||!this.tools.some(t=>t.name===name)) throw Error(`RAVEN_TOOL_NOT_ALLOWED:${name}`);
    const start=performance.now(),started_at=new Date().toISOString();
    try {
      const raw=await this.client.callTool({name,arguments:args},undefined,{timeout:60000});
      const body=raw.content?.filter(c=>c.type==='text').map(c=>c.text).join('\n')||'';
      let output;try{output=JSON.parse(body);}catch{output={message:body};}
      const receipt={tool:name,version:'2.6.0',started_at,wall_seconds:(performance.now()-start)/1000,status:raw.isError?'ERROR':'OK',input:args,output};
      this.calls.push(receipt); return receipt;
    } catch(error) { const receipt={tool:name,version:'2.6.0',started_at,wall_seconds:(performance.now()-start)/1000,status:'ERROR',input:args,output:{message:String(error)}};this.calls.push(receipt);return receipt; }
  }
  async close(){await this.client?.close();}
}
