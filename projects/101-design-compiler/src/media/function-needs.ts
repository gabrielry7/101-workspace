import type {FixtureBundle} from '../contracts/v1/schemas.ts';
import type {MediaManifest} from './contracts.ts';
import {requirementCatalog} from '../requirements/catalog.ts';
import {humanReviewCatalog} from '../requirements/review-catalog.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {MediaRequirementRequestV1,MediaFunctionBindingV1} from './library-contracts.ts';
import type {MediaFunctionBinding} from './library-contracts.ts';

export function functionMediaRequests(bundle:FixtureBundle,manifest:MediaManifest) {
 const modules=bundle.plan.pages.flatMap(p=>p.modules);
 const fromPlan=manifest.needs.map(need=>{
  const module=modules.find(m=>m.id===need.module_id);
  const capability_id=module?.capability_id??requirementCatalog.cards.find(c=>need.purpose===`document:${c.id}`)?.id;
  if(!capability_id)throw Error('MEDIA_REQUEST_CAPABILITY_MISSING');
  const authorized=manifest.usages.some(u=>u.need_id===need.id&&manifest.decisions.find(d=>d.usage_id===u.id)?.status==='ALLOWED');
  return MediaRequirementRequestV1.parse({id:`plan:${need.id}`,capability_id,feature_id:capability_id==='identity'?'identity':null,
   scope_id:need.scope_id,subject_ids:need.subject_ids,subject_status:'EXACT',role:need.role,purpose:need.purpose,source:'SEMANTIC_PLAN',need,
   status:authorized?'AUTHORIZED':need.role==='DOCUMENTARY'?'PENDING_AUTHENTIC_MATERIAL':'PENDING_EXPLICIT_USE',
   reason:authorized?'Uso revisado específico; no cubre otras funciones.':'La necesidad conserva su rol y alcance. No se rellena con stock documental falso.'});
 });
 const fromCatalog=requirementCatalog.cards.filter(c=>c.media_roles.length).flatMap(card=>{
  const scopes=card.scope_policy==='BUSINESS_ONLY'?[bundle.input.business_id]:[bundle.input.business_id,...bundle.input.locations.map(l=>l.id)];
  return scopes.flatMap(scope_id=>{
   const offerings=bundle.input.offerings.filter(o=>o.scope_id===scope_id&&card.offering_kinds.includes(o.kind));
   const targets=card.offering_kinds.length?offerings.map(o=>[o.id]):[[scope_id]];
   if(!targets.length)targets.push([]);
   return targets.map(subject_ids=>MediaRequirementRequestV1.parse({id:`catalog:${inputSha256([card.id,scope_id,subject_ids]).slice(0,24)}`,
    capability_id:card.id,feature_id:card.id==='gallery'?'media':humanReviewCatalog.features.find(f=>f.id==='offer_detail'&&f.registry_references.includes(card.id))?.id??null,scope_id,subject_ids,
    subject_status:subject_ids.length?'EXACT':'SUBJECT_PENDING',role:card.media_roles[0],purpose:`objective:${card.id}`,source:'MASTER_CATALOG',need:null,
    status:card.media_roles[0]==='DOCUMENTARY'?'PENDING_AUTHENTIC_MATERIAL':'PENDING_LICENSED_RESOURCE',reason:'Objetivo del catálogo, no módulo emitido. Requiere confirmar aplicabilidad, sujeto/rol, archivo y permiso; la ausencia no elimina el hueco. Material genérico permitido sólo en rol ilustrativo/atmosférico.'}));
  });
 });
 return [...fromPlan,...fromCatalog].sort((a,b)=>a.id.localeCompare(b.id));
}
export function bindMediaFunction(value:unknown,bundle:FixtureBundle,manifest:MediaManifest):MediaFunctionBinding {
 const b=MediaFunctionBindingV1.parse(value),usage=manifest.usages.find(u=>u.id===b.usage_id),need=manifest.needs.find(n=>n.id===usage?.need_id);
 const module=bundle.plan.pages.find(p=>p.path===b.page)?.modules.find(m=>m.id===b.module_id);
 const feature=humanReviewCatalog.features.find(f=>f.id===b.feature_id);
 if(!usage||!need||!module||!feature||!feature.registry_references.includes(b.capability_id)||module.capability_id!==b.capability_id||
  module.scope_id!==b.scope_id||usage.scope_id!==b.scope_id||usage.page!==b.page||usage.module_id!==b.module_id||need.module_id!==b.module_id||
  inputSha256(b.subject_ids)!==inputSha256(usage.subject_ids)||inputSha256(usage.subject_ids)!==inputSha256(need.subject_ids))throw Error('FUNCTION_MEDIA_BINDING_MISMATCH');
 return b;
}
