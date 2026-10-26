// Real CLI invocation; a rejected invocation is not a successful exchange.
import {run,doctor} from './bridge.mjs';
import {writeFile} from 'node:fs/promises';
const d=await doctor();
if(d.authenticated)throw Error('Already authenticated: use the scoped smoke task instead');
const result=await run(d.bin,['-p','--output-format','json','--max-turns','1','--max-budget-usd','0.01','--tools','','--restricted','--strict-mcp-config','--mcp-config','{"mcpServers":{}}'],{input:'Return only the word authenticated.',timeoutMs:30000});
await writeFile('.tools/claude-code/unauthenticated-probe.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
process.exitCode=result.code===0?0:1;
