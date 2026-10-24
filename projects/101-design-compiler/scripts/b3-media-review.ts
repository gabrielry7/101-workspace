import {readFile,writeFile,access} from 'node:fs/promises';
import {loadDemoPackage} from '../src/media/demo-package.ts';
import {loadContextualScenario} from '../src/design/contextual.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {byteSha256} from '../src/media/package.ts';
import {ContextualMediaReviewV1} from '../src/media/contextual-review.ts';
if(!process.argv.includes('--record-reviewed-b3-uses'))throw Error('EXPLICIT_REVIEW_REQUIRED');
const path='data/media/demo-v1/b3-usage-review.json';if(await access(path).then(()=>true,()=>false))throw Error('REVIEW_EXISTS');
const {pack}=await loadDemoPackage(),s=await loadContextualScenario(),at=new Date().toISOString(),routes=[1,2,3,4].map(n=>`/b3/candidate-0${n}/`);
const document='docs/evidence/corrections/b3/media-review.md',evidence=[document,'fixtures/corrections/b3/la-mesa.json'].map(path=>({path,sha256:''}));
for(const e of evidence)e.sha256=byteSha256(await readFile(e.path));const legal=evidence[0]!;
const assets=structuredClone(pack.assets),grants=structuredClone(pack.grants),usages:any[]=[],modules=s.content.pages.flatMap((p:any)=>p.modules),identity=modules.find((m:any)=>m.capability_id==='identity'),menu=modules.find((m:any)=>m.capability_id==='menu');
const review=(path:string,sha:string)=>({status:'VERIFIED' as const,reference:path,reviewer:'Codex: B3 applicability review of existing licensed bytes, not the rights holder',reviewed_at:at,evidence_sha256:sha});
for(const g of grants){g.id=`b3-${g.id}`;g.document={reference:document,version:'Pixabay Terms 2024-11-18; B2 file review + B3 contextual assessment v1',sha256:legal.sha256};g.review=review(document,legal.sha256);
 g.valid_from=at;g.project_ids=['b3-fictional-compositions'];g.scope_ids=[identity.scope_id,menu.scope_id];g.pages=routes;g.purposes=[];}
const intents=[...['pizza','pasta','salad','dessert'].map((slot,i)=>({slot,asset:pack.sources[i]!.asset_id,module:menu,role:'ILLUSTRATIVE',widths:[640,1280]})),
 {slot:'hero',asset:'pixabay-4991789-received',module:identity,role:'ATMOSPHERIC',widths:[640,1280]},
 {slot:'motion',asset:'pixabay-149678-received',module:identity,role:'ATMOSPHERIC',widths:[0]},
 {slot:'poster',asset:'pixabay-4991789-received',module:identity,role:'ATMOSPHERIC',widths:[640]}];
for(const intent of intents){const purpose=`b3-fictional:${intent.slot}`,g=grants.find(g=>g.original_asset_id===intent.asset)!;g.purposes.push(purpose);
 for(const a of assets.filter(a=>a.original_id===intent.asset))a.relevance.push({purpose,scope_id:intent.module.scope_id,review:review(a.uri,a.file_sha256!)});
 for(const route of routes)for(const width of intent.widths){const a=assets.find(a=>a.original_id===intent.asset&&a.parent_id&&(!width||a.inspection.width===width))!;
  const original=pack.usages.find(u=>u.asset_id===a.id)!;
  usages.push({...original,id:`b3:${route.split('/')[2]}:${intent.slot}:${width}`,need_id:`b3-need:${intent.slot}`,grant_id:g.id,business_id:s.input.business_id,project_id:'b3-fictional-compositions',scope_id:intent.module.scope_id,module_id:intent.module.id,page:route,purpose,role:intent.role,ai_operations:[]});
 }}
const body={schema_version:'1.0.0',kind:'B3_ASSOCIATED_MEDIA_REVIEW',parent_package_sha256:pack.package_sha256,input_sha256:inputSha256(s.input),plan_sha256:s.content.plan_sha256,evaluated_at:at,business_id:s.input.business_id,client_id:pack.scenario.client_id,project_id:'b3-fictional-compositions',routes,assets,grants,usages,evidence,
 policy:{crop:false,source_audio:false,documentary:false,public_stock_redistribution:false,human_approval:'NOT_COLLECTED'}};
const result=ContextualMediaReviewV1.parse({...body,review_sha256:inputSha256(body)});await writeFile(path,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({path,sha256:result.review_sha256,usages:usages.length,valid_until:grants[0]!.valid_until}));
