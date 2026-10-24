import { writeFile,mkdir } from 'node:fs/promises';
import { RavenSession,readTools } from './raven-client.mjs';
const r=await new RavenSession().connect();
try {
 await mkdir('.tools/design-tools',{recursive:true});
 await writeFile('.tools/design-tools/raven-tools.json',JSON.stringify(r.tools,null,2));
 for(const [name,args] of [['get_principles',{context:'editorial website mobile typography spacing',format:'checklist'}],['get_pattern',{type:'navigation',platform:'responsive'}],['list_taste_profiles',{}]])await r.call(name,args);
 await writeFile('.tools/design-tools/raven-probe.json',JSON.stringify(r.calls,null,2));
 console.log(JSON.stringify({discovered:r.tools.length,requested:readTools.map(name=>({name,available:r.tools.some(t=>t.name===name)})),calls:r.calls.map(c=>({tool:c.tool,status:c.status}))}));
} finally {await r.close();}
