import {writeFile,readFile} from 'node:fs/promises';
import {RavenSession,root} from './raven-client.mjs';
import {resolve} from 'node:path';
process.chdir(root);const r=await new RavenSession().connect();
try{for(const id of ['restaurante','hotel']){const receipt=await r.call('audit_url',{url:`http://127.0.0.1:4331/quality/${id}-d/`,viewports:[{w:1280,h:900,label:'desktop'},{w:390,h:844,label:'mobile'}],themes:['light'],compact:true,timeoutMs:10000});console.log(JSON.stringify({tool:receipt.tool,status:receipt.status,coverage:receipt.output.coverage}));}
 await writeFile(resolve(root,'docs/evidence/design-evaluation/raven-url.json'),JSON.stringify(r.calls,null,2)+'\n');
}finally{await r.close();}
