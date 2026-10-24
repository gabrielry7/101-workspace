import { DesignLockV1,type DesignLock } from './contracts.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
import { projectContent } from '../composition/content.ts';
import type { GeneralCompositionLab } from '../composition/lab.ts';
import { validateMediaManifest } from '../media/plan.ts';
import { contextHash,validateDirection,validateDesign,designContext } from '../design/validate.ts';
import { auditCandidate,type BrowserView } from '../audit/evaluate.ts';
export function lockHash(lock:Omit<DesignLock,'lock_sha256'>|DesignLock){const {lock_sha256:_,...payload}=lock as DesignLock;return inputSha256(payload);}
export function validateLock(value:unknown){const parsed=DesignLockV1.safeParse(value);if(!parsed.success)return {success:false,codes:['DESIGN_LOCK_SCHEMA'],lock:undefined,lab:undefined};
 const lock=parsed.data,lab=lock.lab as GeneralCompositionLab,codes:string[]=[];
 if(lockHash(lock)!==lock.lock_sha256)codes.push('LOCK_HASH_MISMATCH');
 try{const s=lock.semantic;const bundle={input:s.input,profile:s.profile,capabilities:s.capabilities,plan:s.plan};const expected=projectContent(bundle,s.requirements);
  if(inputSha256(expected)!==inputSha256(lab.content))codes.push('LOCK_CONTENT_MISMATCH');
  const context={client_id:lock.media.manifest.client_id,project_id:lock.media.manifest.project_id,evaluated_at:lock.media.manifest.evaluated_at, ...(lock.media.manifest.package_proof?{package_proof:lock.media.manifest.package_proof}:{})};
  if(!validateMediaManifest(lock.media.manifest,lock.media.brief,bundle,s.requirements,context).success)codes.push('LOCK_MEDIA_MANIFEST_INVALID');
  if(lab.manifest_sha256!==inputSha256(lock.media.manifest)||inputSha256(lab.gaps)!==inputSha256(lock.media.brief.gaps)||inputSha256(lab.constraints)!==inputSha256(lock.media.brief.constraints)||lab.client_id!==context.client_id||lab.project_id!==context.project_id||lab.evaluated_at!==context.evaluated_at)codes.push('LOCK_MEDIA_CONTEXT_MISMATCH');
  if(lab.media){const {asset,grant,usage}=lab.media;if(!lock.media.manifest.assets.some(a=>inputSha256(a)===inputSha256(asset))||!lock.media.manifest.grants.some(g=>inputSha256(g)===inputSha256(grant))||!lock.media.manifest.usages.some(u=>inputSha256(u)===inputSha256(usage)))codes.push('LOCK_MEDIA_BINDING_MISMATCH');
   if(!lock.files.some(f=>f.role==='AUTHORIZED_MEDIA'&&f.path===`public${asset.uri}`&&f.sha256===asset.file_sha256)||!lock.files.some(f=>f.role==='RIGHTS_DOCUMENT'&&f.path===grant.document.reference&&f.sha256===grant.document.sha256))codes.push('LOCK_RIGHTS_FILE_MISMATCH');
  }
  else if(lock.resolved_plan.pages.some(p=>p.composition.child.media_usage_refs.length))codes.push('LOCK_MEDIA_ABSENCE_MISMATCH');
  const proof=lock.media.manifest.package_proof;if(proof){for(const f of [...proof.files,...proof.documents])if(!lock.files.some(x=>x.path===f.path&&x.sha256===f.sha256))codes.push('LOCK_PACKAGE_EVIDENCE_MISSING');for(const [path,sha256] of [[proof.render.html_path,proof.render.html_sha256],[proof.render.screenshot_path,proof.render.screenshot_sha256],[proof.render.receipt_path,proof.render.receipt_sha256]])if(!lock.files.some(f=>f.path===path&&f.sha256===sha256))codes.push('LOCK_PACKAGE_EVIDENCE_MISSING');}
  const direction=lock.creative.proposals.find(d=>d.id===lock.resolved_plan.art_direction_id);if(!direction||!validateDirection(direction,lab).success)codes.push('LOCK_ART_DIRECTION_INVALID');
  if(!validateDesign(lock.resolved_plan,lab,direction).success)codes.push('LOCK_RESOLVED_PLAN_INVALID');
  if(inputSha256(lock.creative.context)!==contextHash(lab)||inputSha256(designContext(lab))!==contextHash(lab))codes.push('LOCK_CREATIVE_CONTEXT_MISMATCH');
  const provenance=lock.creative.provenance as {output_sha256?:string;prompt_sha256?:string;context_sha256?:string};if(provenance.output_sha256!==inputSha256(lock.creative.proposals)||provenance.prompt_sha256!==inputSha256(lock.creative.prompt)||provenance.context_sha256!==contextHash(lab))codes.push('LOCK_CREATIVE_PROVENANCE_MISMATCH');
  const a=lock.audit_state,candidate={schema_version:'1.0.0',plan:lock.resolved_plan,fixture_mode:'FROZEN_LAB',layout:{measure:'fluid'}} as const;
  if(a.candidate_sha256!==inputSha256(candidate)||a.context_sha256!==contextHash(lab)||a.policy.profile!=='LAB')codes.push('LOCK_AUDIT_CONTEXT_MISMATCH');
  if(a.status!==(lock.purpose==='NORMAL_LAB_SNAPSHOT'?'REAL_BROWSER_LAB_TECHNICAL_PASS':'BASELINE_ONLY_SEEDED_NOT_ACCEPTED'))codes.push('LOCK_AUDIT_PURPOSE_MISMATCH');
  const expectedCoverage=lock.resolved_plan.pages.flatMap(p=>lock.environment.viewports.map(v=>`${p.path}:${v.id}:${v.width}:${v.height}`)).sort();
  const actual=a.entries.map(e=>`${e.semantic_page}:${e.viewport.id}:${e.viewport.width}:${e.viewport.height}`).sort();
  if(inputSha256(expectedCoverage)!==inputSha256(actual))codes.push('LOCK_AUDIT_COVERAGE_INCOMPLETE');
  const file=(path:string,hash:string)=>a.evidence.some(f=>f.path===path&&f.sha256===hash);
  if(new Set(a.evidence.map(f=>f.path)).size!==a.evidence.length||new Set(a.renderer_sources.map(f=>f.path)).size!==a.renderer_sources.length)codes.push('LOCK_AUDIT_DUPLICATE_EVIDENCE');
  for(const f of a.renderer_sources){const current=lock.sources.find(s=>s.path===f.path);if(!current||current.sha256!==f.sha256){if(!(lock.purpose==='SEEDED_COMPONENT_REGRESSION'&&f.path==='src/design/styles.css'))codes.push('LOCK_AUDIT_SOURCE_MISMATCH');}}
  for(const e of a.entries){const route=`/${lock.mount.kind}/${lock.mount.id}${e.semantic_page==='/'?'/':`${e.semantic_page}/`}`,v=e.view as BrowserView;
   if(v.route!==route||v.mount_id!==lock.mount.id||v.observation.semantic_page!==e.semantic_page||inputSha256(v.requested_viewport)!==inputSha256({width:e.viewport.width,height:e.viewport.height})||v.screenshot_path!==e.screenshot_path||e.audit.route!==route)codes.push('LOCK_AUDIT_LOCATION_MISMATCH');
   const recomputed=auditCandidate(candidate,lab,v,a.policy,p=>`/${lock.mount.kind}/${lock.mount.id}${p==='/'?'/':`${p}/`}`);
   if(inputSha256(recomputed)!==inputSha256(e.audit))codes.push('LOCK_AUDIT_REPORT_INCONSISTENT');
   if(e.audit.status==='FAIL'||recomputed.status==='FAIL'||e.audit.families.some(f=>f.status==='FAIL')||e.audit.issues.some(i=>i.severity==='BLOCKING'))codes.push('LOCK_AUDIT_FAILED');
   if(!file(e.html_path,e.html_sha256)||!file(e.screenshot_path,e.screenshot_sha256)||e.styles.some(s=>!file(s.stored_path,s.sha256))||e.served_media_sha256!==(lab.media?.asset.file_sha256??null))codes.push('LOCK_AUDIT_EVIDENCE_MISSING');
  }
 }catch(error){codes.push('LOCK_SNAPSHOT_VALIDATION_FAILED');}
 if(new Set(lock.sources.map(s=>s.path)).size!==lock.sources.length||new Set(lock.files.map(f=>f.path)).size!==lock.files.length)codes.push('LOCK_DUPLICATE_FILE');
 if(lock.files.some(f=>f.stored_path!==`${lock.media_snapshot_root}/${f.path}`))codes.push('LOCK_FILE_STORAGE_MISMATCH');
 const routes=lock.resolved_plan.pages.map(p=>`/${lock.mount.kind}/${lock.mount.id}${p.path==='/'?'/':`${p.path}/`}`);if(inputSha256(routes)!==inputSha256(lock.mount.original_routes)||(lock.mount.kind==='h5'&&lock.mount.id!==lock.resolved_plan.id))codes.push('LOCK_MOUNT_ROUTE_MISMATCH');
 return {success:!codes.length,codes,lock,lab};
}
