import {readFile} from 'node:fs/promises';
import sharp from 'sharp';
import {loadB3Lab} from './load-b3-lab.ts';
import {auditContextual} from '../src/design/contextual-audit.ts';
import {structuralDistance} from '../src/design/contextual.ts';
import {hashBytes,verifyProtectedFiles} from './lib/correction-run.ts';
import {b3Preservation} from './b3-preservation.ts';
import {verifyRuntime} from './lib/correction-runtime.ts';
import {b2RuntimePath} from './b2-runtime.ts';
const historical=process.argv.includes('--historical-replay'),snapshot=JSON.parse(await readFile('data/media/demo-v1/b3-usage-review.json','utf8'));
const lab=await loadB3Lab(historical?{evaluation_time:snapshot.evaluated_at}:{}),qa=JSON.parse(await readFile('docs/evidence/corrections/b3/qa-08/qa.json','utf8')),runtime=await verifyRuntime(b2RuntimePath);
if(qa.status!=='TECHNICAL_PASS_HUMAN_PENDING'||qa.context_sha256!==lab.context_sha256||qa.runtime_sha256!==runtime.snapshot_sha256||qa.views.length!==8||qa.responsive.length!==16||qa.failures.length||qa.historical_html_unchanged!==16)throw Error('B3_QA_RECEIPT_INVALID');
for(const v of qa.views){const d=lab.designs.find(d=>d.id===v.design)!;if(!auditContextual(v.observed,lab.scenario,d,lab.media.review).success||v.initial.video_requests||!v.video.advanced||v.video.bytes!==4446094||v.network_external||v.exceptions||v.video.verification_method!=='EXPLICIT_LOCAL_BROWSER_INTEGRITY_FETCH_AFTER_PLAYBACK'||!Number.isFinite(v.video.display_height)||Math.abs(v.video.display_height-v.observed.video.height)>.6)throw Error('B3_QA_OBSERVATION_INVALID');
 const screenshot=await readFile(v.screenshot.path);if(hashBytes(screenshot)!==v.screenshot.sha256||hashBytes(await sharp(screenshot).raw().toBuffer())!==v.screenshot.rgba_sha256)throw Error('B3_SCREENSHOT_CHANGED');
 if(hashBytes(await readFile(`docs/evidence/corrections/b3/qa-08/${v.design}.html`))!==v.html_sha256)throw Error('B3_HTML_CHANGED');
 for(const f of v.served){const a=lab.media.review.assets.find(a=>a.uri===f.path);if(!a||f.sha256!==a.file_sha256||hashBytes(await readFile(`public${f.path}`))!==f.sha256)throw Error('B3_SERVED_FILE_CHANGED');}
}
if(qa.responsive.some((v:any)=>!v.audit.success||v.geometry.document_width>v.width||v.geometry.overflow.length||v.min_font<14||v.min_contrast<4.5))throw Error('B3_RESPONSIVE_QA_INVALID');
const distances=[];for(let i=0;i<lab.designs.length;i++)for(let j=i+1;j<lab.designs.length;j++){const distance=structuralDistance(lab.designs[i]!,lab.designs[j]!);if(distance.desktop<2||distance.mobile<2)throw Error('B3_STRUCTURAL_DIVERSITY_INSUFFICIENT');distances.push({pair:[lab.designs[i]!.id,lab.designs[j]!.id],...distance});}
console.log(JSON.stringify({status:'PASS_ARCHIVED_QA_VERIFIED',mode:historical?'HISTORICAL_REPLAY_NOT_CURRENT_AUTHORIZATION':'CURRENT_PACKAGE_AND_ARCHIVED_QA',context_sha256:lab.context_sha256,views:8,responsive:16,distances,protection:await verifyProtectedFiles(b3Preservation),human_approval:'NOT_COLLECTED',external_reference_visual_review:'PENDING'}));
