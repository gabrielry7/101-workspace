import {z} from 'zod';
import {ArchetypeId,CapabilityId} from '../contracts/v1/schemas.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
const text=z.string().min(1).regex(/\S/);
const need=z.strictObject({id:text,label:text,owner:z.enum(['BUSINESS','PROJECT','PLATFORM','RIGHTS_HOLDER']),
 scope:z.enum(['BUSINESS','EXACT_BRANCH','EXACT_OFFERING','EXACT_PERSON','EXACT_REVIEW','EXACT_REVIEW_SUBJECT','EXACT_RESOURCE','EXACT_MEDIA_USAGE','PROJECT']),evidence_needed:text,validation_hint:text});
export const ReviewFeatureV1=z.strictObject({id:text,label:text,purpose:text,group:text,
 registry_references:z.array(CapabilityId),registry_relation:z.enum(['PARTIAL_V1_REFERENCE','EXTENSION_REQUIRED']),
 business_data:z.array(need).min(1),future_visitor_inputs:z.array(text),frontend_expectation:text,
 operation_dependencies:z.array(text).min(1),depends_on:z.array(text),acceptance_checks:z.array(text).min(1),
 expected_states:z.array(text).min(1),risks:z.array(text).min(1),
 frontend_status:z.literal('NOT_BUILT'),operation_status:z.literal('NOT_CONNECTED'),data_status:z.literal('NOT_EVALUATED')});
export const HumanReviewCatalogV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('HUMAN_REVIEW_REQUIREMENTS_SUPPLEMENT'),
 catalog_id:text,catalog_sha256:z.string().regex(/^[a-f0-9]{64}$/),technical_catalog_sha256:z.string().regex(/^[a-f0-9]{64}$/),
 source:z.strictObject({date:text,user_request_summary:text,reviewer_thread:text}),
 status:z.literal('PROPOSED_FOR_HUMAN_REVIEW'),business_input_evaluation:z.literal('NOT_PERFORMED'),
 common_feature_ids:z.array(text).min(1),restaurant_requested_feature_ids:z.array(text).min(1),features:z.array(ReviewFeatureV1).min(1),
 profiles:z.array(z.strictObject({archetype_id:ArchetypeId,label:text,offering_label:text,
  caveat:text,features:z.array(z.strictObject({feature_id:text,priority:z.enum(['BASE','CONDITIONAL','OPTIONAL']),condition:text})).min(1)})),
 performance_source:z.strictObject({url:z.url(),consulted_on:text,targets:text,measurement_status:z.literal('NOT_MEASURED_FOR_FINAL_SITE')})});
export type ReviewFeature=z.infer<typeof ReviewFeatureV1>;
export type ReviewCatalog=z.infer<typeof HumanReviewCatalogV1>;
export function validateHumanReviewCatalog(value:unknown):ReviewCatalog {
 const c=HumanReviewCatalogV1.parse(value),{catalog_sha256:checksum,...body}=c;
 if(inputSha256(body)!==checksum)throw Error('REVIEW_CATALOG_HASH_MISMATCH');
 const ids=new Set(c.features.map(f=>f.id));
 if(ids.size!==c.features.length)throw Error('REVIEW_DUPLICATE_FEATURE');
 if(new Set(c.profiles.map(p=>p.archetype_id)).size!==ArchetypeId.options.length||c.profiles.length!==ArchetypeId.options.length)throw Error('REVIEW_PROFILE_COVERAGE');
 for(const f of c.features){
  if((f.registry_references.length===0)!==(f.registry_relation==='EXTENSION_REQUIRED'))throw Error('REVIEW_REGISTRY_RELATION');
  if(new Set(f.business_data.map(d=>d.id)).size!==f.business_data.length)throw Error('REVIEW_DUPLICATE_DATA');
  if(f.depends_on.some(id=>id===f.id||!ids.has(id)))throw Error('REVIEW_BAD_DEPENDENCY');
 }
 const visiting=new Set<string>(),visited=new Set<string>(),byId=new Map(c.features.map(f=>[f.id,f]));
 const visit=(id:string)=>{if(visiting.has(id))throw Error('REVIEW_DEPENDENCY_CYCLE');if(visited.has(id))return;visiting.add(id);for(const dep of byId.get(id)!.depends_on)visit(dep);visiting.delete(id);visited.add(id);};
 for(const id of ids)visit(id);
 for(const list of [c.common_feature_ids,c.restaurant_requested_feature_ids,...c.profiles.map(p=>p.features.map(f=>f.feature_id))]){
  if(new Set(list).size!==list.length||list.some(id=>!ids.has(id)))throw Error('REVIEW_BAD_FEATURE_REFERENCE');
 }
 return c;
}
