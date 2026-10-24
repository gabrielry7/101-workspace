import {readFile,writeFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import sharp from 'sharp';
import {hashBytes} from './lib/correction-run.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const [first,second,output]=process.argv.slice(2);if(!first||!second||!output)throw Error('Usage: b2-compare.ts <qa-dir> <qa-dir> <new-receipt>');
if(await access(output).then(()=>true,()=>false))throw Error('COMPARISON_ALREADY_EXISTS');
const a=JSON.parse(await readFile(resolve(first,'qa.json'),'utf8')),b=JSON.parse(await readFile(resolve(second,'qa.json'),'utf8'));
if(a.views.length!==8||b.views.length!==8||a.runtime_sha256!==b.runtime_sha256||a.library_sha256!==b.library_sha256)throw Error('COMPARISON_CONTEXT_MISMATCH');
const pairs=[];
for(const view of a.views){const other=b.views.find((v:any)=>v.label===view.label);if(!other)throw Error('MISSING_VIEW');
 const stable=(v:any)=>{const {resources:_resources,...rest}=v.observed;return rest;};
 for(const [folder,v] of [[first,view],[second,other]] as const){
  const png=await readFile(resolve(folder,`${v.label}.png`));if(hashBytes(png)!==v.screenshot.sha256||hashBytes(await sharp(png).raw().toBuffer())!==v.screenshot.rgba_sha256)throw Error('SCREENSHOT_BYTES_CHANGED');
  if(v.viewport.id==='desktop'&&hashBytes(await readFile(resolve(folder,`${v.label}.html`)))!==v.html_sha256)throw Error('HTML_EVIDENCE_CHANGED');
 }
 if(view.html_sha256!==other.html_sha256||view.screenshot.rgba_sha256!==other.screenshot.rgba_sha256||inputSha256(stable(view))!==inputSha256(stable(other)))throw Error(`REPRODUCTION_MISMATCH:${view.label}`);
 pairs.push({label:view.label,html_sha256:view.html_sha256,rgba_sha256:view.screenshot.rgba_sha256,stable_observations_sha256:inputSha256(stable(view)),status:'IDENTICAL'});
}
await writeFile(output,JSON.stringify({kind:'B2_SAME_HOST_REPRODUCTION_COMPARISON',created_at:new Date().toISOString(),first,second,status:'PASS',pairs,
 limits:['Same B2 font observation, OS, dependencies and browser; no historical pixel identity claim','Network timing and resource bookkeeping excluded; served media hashes, geometry, content, bindings and screenshot pixels compared','Not a new media acquisition or current aesthetic approval']},null,2)+'\n');console.log(`PASS ${pairs.length} HTML/RGBA/DOM pairs`);
