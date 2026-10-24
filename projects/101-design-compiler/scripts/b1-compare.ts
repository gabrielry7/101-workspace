import {readFile} from 'node:fs/promises';
import {hashBytes} from './lib/correction-run.ts';
import {decodeScreenshot} from '../src/audit/png.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const ids=process.argv.slice(2);if(ids.length!==2||ids.some(id=>!/^[a-z0-9-]+$/.test(id)))throw Error('Usage: b1-compare.ts <qa-id-a> <qa-id-b>');
const [left,right]=await Promise.all(ids.map(async id=>JSON.parse(await readFile(`docs/evidence/corrections/b1/${id}/qa.json`,'utf8'))));
if(left.views.length!==28||right.views.length!==28||left.catalog_sha256!==right.catalog_sha256||left.runtime_sha256!==right.runtime_sha256)throw Error('B1_COMPARISON_CONTEXT');
const pairs=[];
for(const view of left.views) {
 const other=right.views.find((v:{label:string})=>v.label===view.label);if(!other)throw Error('B1_COMPARISON_COVERAGE');
 const a=decodeScreenshot(await readFile(view.screenshot_path)),b=decodeScreenshot(await readFile(other.screenshot_path));
 const html_equal=hashBytes(await readFile(view.html_path))===hashBytes(await readFile(other.html_path));
 const rgba_equal=a.width===b.width&&a.height===b.height&&Buffer.from(a.pixels).equals(Buffer.from(b.pixels));
 const observable=(v:typeof view)=>({root:v.observed.root,goals:v.observed.goals,fields:v.observed.fields,scopes:v.observed.scopes,document:v.observed.document,viewport:v.viewport,keyboard:v.keyboard});
 const functional_equal=inputSha256(observable(view))===inputSha256(observable(other));
 if(!html_equal||!rgba_equal||!functional_equal)throw Error(`B1_COMPARISON_DIFFERENCE:${view.label}`);
 pairs.push({label:view.label,html_equal,rgba_equal,functional_equal});
}
console.log(JSON.stringify({status:'B1_SAME_HOST_REPRODUCTION_EQUIVALENT',pairs,scope:'SAME_OS_FONTS_NODE_DEPENDENCY_BROWSER_SNAPSHOT',production_ready:false},null,2));
