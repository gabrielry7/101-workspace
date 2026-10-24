import {FunctionalDiagnosticV1} from './contracts.ts';
import {requirementCatalog} from './catalog.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {BoundMediaDiagnosticV1} from '../media/library-contracts.ts';
import {libraryData,attachmentState} from '../media/library.ts';
import type {VerifiedLibrary} from '../media/library.ts';

// Associated overlay only: never rewrites V1 diagnosis, facts or closure.
export function diagnoseBoundMedia(baseValue:unknown,handle:VerifiedLibrary,evaluated_at:string){
 const base=FunctionalDiagnosticV1.parse(baseValue),library=libraryData(handle),{diagnostic_sha256,...body}=base;
 if(inputSha256(body)!==diagnostic_sha256||base.business_input_sha256!==library.manifest.input_sha256||base.plan_sha256!==library.manifest.plan_sha256||
  base.catalog_sha256!==library.catalog_sha256||base.business_id!==library.manifest.business_id||base.snapshot_id!==library.manifest.snapshot_id)throw Error('MEDIA_DIAGNOSTIC_CONTEXT_MISMATCH');
 const definitions=new Map(requirementCatalog.definitions.map(d=>[d.id,d]));
 const entries=base.entries.flatMap(entry=>entry.levels.flatMap(level=>level.requirements.filter(r=>['MEDIA_FILE','MEDIA_RIGHTS'].includes(definitions.get(r.requirement_id)?.check??'')).map(req=>{
  const card=requirementCatalog.cards.find(c=>c.id===entry.capability_id)!,canonical=card.levels.find(l=>l.id===level.level_id);
  if(!canonical?.requirement_ids.includes(req.requirement_id))throw Error('MEDIA_DIAGNOSTIC_REQUIREMENT_MISMATCH');
  const def=definitions.get(req.requirement_id)!,attachment=attachmentState(handle,entry.capability_id,entry.scope_id,evaluated_at);
  const complete=attachment.condition_active,codes=attachment.codes;
  const condition_active=def.condition!=='MEDIA_PRESENT'||complete;
  const status=!condition_active?(attachment.explicit_use?(def.check==='MEDIA_RIGHTS'?'RIGHTS_REVIEW_PENDING':'MISSING'):'NOT_REQUIRED_BY_CONDITION'):
   complete?'SATISFIED':def.check==='MEDIA_RIGHTS'?'RIGHTS_REVIEW_PENDING':'MISSING';
  return {capability_id:entry.capability_id,scope_id:entry.scope_id,level_id:level.level_id,requirement_id:req.requirement_id,condition_active,status,
   usage_ids:attachment.evaluations.map(e=>e.usage.id),codes:codes.length?codes:complete?[]:[attachment.explicit_use?'INCOMPLETE_SUBJECT_OR_USE_COVERAGE':'NO_MATCHING_EXPLICIT_AUTHORIZED_USE']};
 })));
 return BoundMediaDiagnosticV1.parse({schema_version:'1.0.0',kind:'B1_BOUND_MEDIA_DIAGNOSTIC',base_diagnostic_sha256:base.diagnostic_sha256,library_sha256:library.library_sha256,evaluated_at,entries,operational_integrations:'NOT_CONNECTED'});
}
