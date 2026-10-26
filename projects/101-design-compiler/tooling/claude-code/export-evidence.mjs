// Explicitly export reviewed local task evidence; does not export credentials,
// account identity, private runtime/media files or full Claude profile transcripts.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
import {createHash} from 'node:crypto';
import {root,responseSucceeded} from './bridge.mjs';
const [id,destination]=process.argv.slice(2);
if(!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id??'')||!destination)throw Error('Task ID and destination required');
const out=resolve(root,destination),rel=relative(root,out);if(isAbsolute(rel)||rel.startsWith('..'))throw Error('Destination outside project');
const source=resolve(root,`.tools/claude-code/${id}`),state=JSON.parse(await readFile(resolve(source,'state.json'),'utf8'));
if(state.status==='running')throw Error('Cannot export a running task');
await mkdir(out,{recursive:true});const files=[];
const names=['task.json','state.json','attachments.json',...state.calls.flatMap(c=>[`${c.index}-prompt.txt`,`${c.index}-stdout.json`,`${c.index}-stderr.txt`,`${c.index}-changes.patch`,`${c.index}-status.txt`])];
for(const name of names){const bytes=await readFile(resolve(source,name));await writeFile(resolve(out,name),bytes);files.push({path:name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});}
const exchanges=[];let previousCost=0;
for(const c of state.calls){const response=JSON.parse(await readFile(resolve(source,`${c.index}-stdout.json`),'utf8'));exchanges.push({index:c.index,sessionId:response.session_id,resumedFrom:c.resume,success:responseSucceeded({code:c.exitCode,timedOut:c.timedOut},response,c.resume),reportedSessionCostUsd:c.estimatedCostUsd,incrementalEstimatedCostUsd:Number.isFinite(c.estimatedCostUsd)?Math.max(0,c.estimatedCostUsd-previousCost):null,numTurns:c.numTurns});if(Number.isFinite(c.estimatedCostUsd))previousCost=c.estimatedCostUsd;}
const summary={id,status:state.status,sessionId:state.sessionId,exchanges,files,source:'Actual installed Claude Code CLI process stdout, not transport test fixtures',exportedAt:new Date().toISOString()};
await writeFile(resolve(out,'index.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary,null,2));
