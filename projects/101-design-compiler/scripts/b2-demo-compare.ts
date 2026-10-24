import {readFile,writeFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
import sharp from 'sharp';
import {hashBytes} from './lib/correction-run.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const [first,second,output]=process.argv.slice(2);if(!first||!second||!output)throw Error('Usage: b2-demo-compare.ts <qa-dir> <qa-dir> <new-receipt>');if(await access(output).then(()=>true,()=>false))throw Error('COMPARISON_EXISTS');
const a=JSON.parse(await readFile(resolve(first,'qa.json'),'utf8')),b=JSON.parse(await readFile(resolve(second,'qa.json'),'utf8'));if(a.views.length!==2||b.views.length!==2||a.package_sha256!==b.package_sha256||a.runtime_sha256!==b.runtime_sha256)throw Error('COMPARISON_CONTEXT');
const pairs=[];
for(const v of a.views){const other=b.views.find((e:any)=>e.viewport.id===v.viewport.id);if(!other)throw Error('MISSING_VIEW');
 for(const [folder,view] of [[first,v],[second,other]] as const){const bytes=await readFile(resolve(folder,`${view.viewport.id}.png`));if(hashBytes(bytes)!==view.screenshot.sha256||hashBytes(await sharp(bytes).raw().toBuffer())!==view.screenshot.rgba_sha256)throw Error('SCREENSHOT_CHANGED');}
 if(v.html_sha256!==other.html_sha256||inputSha256(v.observed)!==inputSha256(other.observed)||inputSha256(v.served)!==inputSha256(other.served))throw Error('HTML_DOM_OR_MEDIA_REPRODUCTION_CHANGED');
 pairs.push({viewport:v.viewport.id,html_sha256:v.html_sha256,dom_sha256:inputSha256(v.observed),served_media_sha256:inputSha256(v.served),rgba_identical:v.screenshot.rgba_sha256===other.screenshot.rgba_sha256});
}
await writeFile(output,JSON.stringify({kind:'B2_FICTIONAL_SAME_HOST_REPRODUCTION',created_at:new Date().toISOString(),status:'PASS_HTML_DOM_MEDIA',pairs,all_rgba_identical:pairs.every(p=>p.rgba_identical),first,second,limits:['Same host/B2 fonts/browser and private media package, not public standalone reproduction','Native video controls/playback are observed separately from source-byte identity']},null,2)+'\n');console.log(JSON.stringify({pairs:pairs.length,all_rgba_identical:pairs.every(p=>p.rgba_identical)}));
