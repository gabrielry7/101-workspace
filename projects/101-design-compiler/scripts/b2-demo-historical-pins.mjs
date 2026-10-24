import {readFile,writeFile,copyFile} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
import {createHash} from 'node:crypto';
if(!process.argv.includes('--line-endings-only'))throw Error('EXPLICIT_HISTORICAL_BYTE_OVERLAY_REQUIRED');
const root=process.cwd(),target=resolve('.tools/corrections/b0/b2-demo-clean/source'),rel=relative(root,target);
if(isAbsolute(rel)||rel.startsWith('..')||!rel.replaceAll('\\','/').startsWith('.tools/corrections/b0/'))throw Error('OUTSIDE_CONTROLLED_COPY');
const manifest=JSON.parse(await readFile('docs/evidence/corrections/b2-demo/pre/preservation.json','utf8')),sha=b=>createHash('sha256').update(b).digest('hex'),overlays=[];
for(const f of manifest.files.filter(f=>f.normalization==='BINARY')){
 const original=await readFile(f.path),archived=await readFile(resolve(target,f.path));if(sha(original)!==f.sha256)throw Error('ROOT_PROTECTED_PIN_CHANGED');
 if(sha(archived)===f.sha256)continue;
 if(!f.path.startsWith('docs/')||! /\.(txt|html|md|json)$/.test(f.path)||original.toString().replaceAll('\r\n','\n')!==archived.toString().replaceAll('\r\n','\n'))throw Error('NOT_HISTORICAL_DOCUMENT_LINE_ENDINGS_ONLY');
 overlays.push({path:f.path,archive_sha256:sha(archived),pinned_sha256:f.sha256,reason:'PREDECLARED_HISTORICAL_BYTES_LF_EQUIVALENT_NO_PRODUCT_SOURCE_CHANGE'});
}
const expected=['docs/evidence/h3-git-repro.txt','docs/reviews/h7/audit-h7-source.txt','docs/reviews/h7/verify-h7-source.txt','docs/reviews/h8-correction/audit-h8-source.txt','docs/reviews/h8-correction/verify-h8-source.txt','docs/reviews/h8/audit-h8-source.txt','docs/reviews/h9/probe-source.txt'].sort();
if(JSON.stringify(overlays.map(f=>f.path).sort())!==JSON.stringify(expected))throw Error('UNEXPECTED_HISTORICAL_OVERLAY_SET_INVESTIGATE');
for(const f of overlays)await copyFile(f.path,resolve(target,f.path));
await writeFile('docs/evidence/corrections/b2-demo/reproduction/historical-byte-overlays.json',JSON.stringify({kind:'B2_DEMO_HISTORICAL_DOCUMENT_BYTE_OVERLAYS',created_at:new Date().toISOString(),target:rel.replaceAll('\\','/'),overlays,limits:['Root evidence untouched; only isolated copy historical documentation','Pre-manifest treated all txt as byte pins; Git normalized seven documents','No code, media, legal-review, runtime, dependencies, source fixture or permission override']},null,2)+'\n');console.log(JSON.stringify({status:'PASS',overlays:overlays.length}));
