import {readFile,writeFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {hashBytes} from './lib/correction-run.ts';
import sharp from 'sharp';
const [first,second,out]=process.argv.slice(2);if(!first||!second||!out||await access(out).then(()=>true,()=>false))throw Error('NEW_COMPARISON_OUTPUT_REQUIRED');
const a=JSON.parse(await readFile(resolve(first,'qa.json'),'utf8')),b=JSON.parse(await readFile(resolve(second,'qa.json'),'utf8'));if(a.views.length!==8||b.views.length!==8||a.context_sha256!==b.context_sha256||a.runtime_sha256!==b.runtime_sha256)throw Error('REPRODUCTION_CONTEXT_CHANGED');
const pairs=[];
const stable=(v:any)=>{const {resources:_,navigation_ms:__,...rest}=v.observed;return rest;};
for(const v of a.views){const other=b.views.find((x:any)=>x.design===v.design&&x.viewport.id===v.viewport.id);if(!other)throw Error('REPRODUCTION_VIEW_MISSING');
 for(const [dir,view] of [[first,v],[second,other]] as const){const png=await readFile(resolve(dir,`${view.design}-${view.viewport.id}.png`));if(hashBytes(png)!==view.screenshot.sha256||hashBytes(await sharp(png).raw().toBuffer())!==view.screenshot.rgba_sha256)throw Error('REPRODUCTION_SCREENSHOT_TAMPERED');}
 if(v.html_sha256!==other.html_sha256||inputSha256(stable(v))!==inputSha256(stable(other))||inputSha256(v.served)!==inputSha256(other.served))throw Error(`REPRODUCTION_HTML_DOM_OR_BYTES_CHANGED:${v.design}/${v.viewport.id}`);
 pairs.push({design:v.design,viewport:v.viewport.id,html_sha256:v.html_sha256,dom_sha256:inputSha256(stable(v)),served_sha256:inputSha256(v.served),rgba_identical:v.screenshot.rgba_sha256===other.screenshot.rgba_sha256});
}
await writeFile(out,JSON.stringify({kind:'B3_SAME_HOST_REPRODUCTION_COMPARISON',created_at:new Date().toISOString(),status:'PASS_HTML_DOM_SERVED_BYTES',first,second,pairs,all_rgba_identical:pairs.every(p=>p.rgba_identical),limits:['Observed native video controls may paint differently; original PNG retained without masking','Timing/resource-duration observations excluded from stable DOM comparison; geometry/bindings/permissions included','Same OS/fonts/browser/private package, not portable production or aesthetic approval']},null,2)+'\n');console.log(JSON.stringify({pairs:8,all_rgba_identical:pairs.every(p=>p.rgba_identical)}));
