import {readFile,writeFile,copyFile,access} from 'node:fs/promises';
import {sameReferenceContext} from '../src/design/reference-comparison.ts';
const root='docs/evidence/corrections/b3/reference-application-iab-02',path=`${root}/before-after.json`;
const old=JSON.parse(await readFile('docs/evidence/corrections/b3/qa-08/qa.json','utf8')),current=JSON.parse(await readFile(`${root}/observations.json`,'utf8'));
const pairs=current.views.filter((v:any)=>v.screenshot).map((v:any)=>{const p=old.views.find((o:any)=>o.design===v.design&&o.viewport.id===v.viewport.id);if(!p)throw Error('B3_COMPARISON_PAIR_MISSING');return {design:v.design,viewport:v.viewport.id,shared_context:sameReferenceContext(p.observed.context,v.observed.context),before:{hero:p.observed.geometry.hero,title:p.observed.geometry.title,collection:p.observed.geometry.collection,height:p.observed.geometry.height},after:{hero:v.observed.geometry.hero,title:v.observed.geometry.title,collection:v.observed.geometry.collection,height:v.observed.geometry.height}};});
if(pairs.length!==8||pairs.some((v:any)=>!v.shared_context))throw Error('B3_COMPARISON_CONTEXT_CHANGED');
const result={kind:'B3_REFERENCE_APPLICATION_GEOMETRY_COMPARISON',scope:'Archived controlled Edge vs current IAB; structural observations, not same-browser pixel regression or beauty scores',context_comparison:'CANONICAL_INPUT_SHA256_ORDER_INDEPENDENT_STRICT_FOUR_HASHES',pairs};
if(process.argv.includes('--record-canonical-correction')){const original=`${root}/before-after-order-sensitive-original.json`;if(await access(original).then(()=>true,()=>false))throw Error('B3_COMPARISON_CORRECTION_ALREADY_RECORDED');await copyFile(path,original);await writeFile(path,JSON.stringify(result,null,2)+'\n');}
else if(process.argv.includes('--verify')){if(JSON.stringify(JSON.parse(await readFile(path,'utf8')))!==JSON.stringify(result))throw Error('B3_COMPARISON_REPLAY_MISMATCH');}
else throw Error('EXPLICIT_CORRECTION_OR_VERIFY_REQUIRED');
console.log(JSON.stringify({status:'PASS_SHARED_CONTEXT_GEOMETRY_COMPARISON',pairs:8,shared_context:true,method:result.context_comparison}));
