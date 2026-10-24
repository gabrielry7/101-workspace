import {FunctionalDiagnosticV1,FunctionalObjectiveDecisionV1} from './contracts.ts';
import type {FunctionalDiagnostic,ObjectiveDecision,RequirementDefinition} from './contracts.ts';
import {requirementCatalog,validateRequirementCatalog} from './catalog.ts';
import {classifyContextually} from '../taxonomy/context.ts';
import type {ContextOptions} from '../taxonomy/context.ts';
import {planBusiness} from '../planner/plan.ts';
import type {BusinessInput,Capability} from '../contracts/v1/schemas.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {publishable,offeringFactIds,offeringKindsValid,validClass,safeExternalUrl,sorted} from '../planner/content.ts';
type Check=FunctionalDiagnostic['entries'][number]['levels'][number]['requirements'][number];
export type DiagnosticOptions=ContextOptions&{objective_decisions?:ObjectiveDecision[];catalog?:unknown};
function valid(value:BusinessInput['facts'][number]['value'],mode:RequirementDefinition['validation']) {
 if(mode==='PRESENT')return true;
 if(mode==='NONNEGATIVE_NUMBER'||mode==='POSITIVE_NUMBER')return typeof value==='number'&&Number.isFinite(value)&&(mode==='POSITIVE_NUMBER'?value>0:value>=0);
 if(typeof value!=='string')return false;
 if(mode==='CURRENCY')return /^[A-Z]{3}$/.test(value);
 if(mode==='TIMEZONE'){try{new Intl.DateTimeFormat('es',{timeZone:value});return true;}catch{return false;}}
 if(mode==='ISO_DATETIME')return /^\d{4}-\d{2}-\d{2}T/.test(value)&&Number.isFinite(Date.parse(value));
 if(mode==='HTTPS')return safeExternalUrl(value);
 return value.trim().length>0;
}
export function diagnoseBusiness(value:unknown,options:DiagnosticOptions) {
 const catalog=validateRequirementCatalog(options.catalog??requirementCatalog),classification=classifyContextually(value,options),context=classification.context;
 const result=planBusiness(value,{rules:options.rules,classification_mode:'CONTEXTUAL_V1',contextual_activity_links:[...(options.activity_links??[])],
  category_context:[...(options.category_context??[])],activity_relationships:[...(options.activity_relationships??[])],evaluation_time:context.evaluated_at});
 const input=value as BusinessInput,instant=Date.parse(context.evaluated_at),facts=new Map(input.facts.map(f=>[f.id,f]));
 const scopes=[input.business_id,...input.locations.map(s=>s.id)].sort(),definitions=new Map(catalog.definitions.map(d=>[d.id,d]));
 const decisions=(options.objective_decisions??[]).map(v=>FunctionalObjectiveDecisionV1.parse(v));
 if(new Set(decisions.map(d=>d.id)).size!==decisions.length||new Set(decisions.map(d=>`${d.scope_id}:${d.capability_id}`)).size!==decisions.length)throw Error('OBJECTIVE_DUPLICATE_DECISION');
 for(const decision of decisions)if(!scopes.includes(decision.scope_id)||!decision.evidence_ids.every(id=>facts.get(id)?.scope_id===decision.scope_id&&publishable(facts.get(id),instant))||
  !decision.evidence_ids.some(id=>facts.get(id)?.kind===`objective:${decision.disposition.toLowerCase()}:${decision.capability_id}`&&facts.get(id)?.value===true))throw Error('OBJECTIVE_UNVERIFIED_DECISION');
 const modules=result.status==='READY'?result.plan.pages.flatMap(p=>p.modules):[];
 for(const decision of decisions)if(decision.disposition!=='REQUESTED'&&modules.some(m=>m.scope_id===decision.scope_id&&m.capability_id===decision.capability_id))throw Error('OBJECTIVE_DECISION_CONFLICTS_WITH_EMITTED_PLAN');
 const entries:FunctionalDiagnostic['entries']=[];
 for(const scope_id of scopes)for(const card of catalog.cards) {
  if(card.scope_policy==='BUSINESS_ONLY'&&scope_id!==input.business_id)continue;
  const local=context.scopes.find(s=>s.scope_id===scope_id)!,archetypes=local.archetypes.length?local.archetypes:local.alternatives.length?local.alternatives:context.profile.archetypes.map(a=>a.id);
  const claim=input.business_capabilities.find(c=>c.scope_id===scope_id&&c.id===card.id),decision=decisions.find(d=>d.scope_id===scope_id&&d.capability_id===card.id);
  const relevance:FunctionalDiagnostic['entries'][number]['relevance']=decision?.disposition==='NOT_APPLICABLE'?'NOT_APPLICABLE_JUSTIFIED':decision?.disposition==='REJECTED'?'REJECTED':decision?'REQUESTED':claim?'UPSTREAM_DECLARED':
   catalog.common_capabilities.includes(card.id)||archetypes.some(a=>card.candidate_archetypes.includes(a))?'SUGGESTED':'APPLICABILITY_NOT_EVALUATED';
  const eligible=input.offerings.filter(o=>o.scope_id===scope_id&&card.offering_kinds.includes(o.kind));
  const factCandidates=input.facts.filter(f=>f.scope_id===scope_id&&card.fact_kinds.includes(f.kind));
  const actions=input.action_destinations.filter(a=>a.scope_id===scope_id&&a.capability_id===card.id);
  const relevantRefs=sorted([...(claim?.evidence_ids??[]),...eligible.flatMap(offeringFactIds),...factCandidates.map(f=>f.id),...actions.map(a=>a.url_fact_id),
   ...(card.id==='identity'?[input.identity.name_fact_id,...input.identity.alias_fact_ids,...(input.identity.brand_fact_id?[input.identity.brand_fact_id]:[])]:[])]);
  const inMedia=input.existing_media.filter(m=>m.scope_id===scope_id);
  function condition(def:RequirementDefinition) {
   if(def.condition==='PRICES_PRESENT')return eligible.some(o=>offeringFactIds(o).some(id=>facts.get(id)?.kind==='price'));
   if(def.condition==='COORDINATES_PRESENT')return input.locations.find(s=>s.id===scope_id)?.coordinate_fact_ids.length!==0&&!!input.locations.find(s=>s.id===scope_id);
   // Legacy condition name in the associated catalogue. V1 existing_media only
   // carries scope, never a function/use binding; presence cannot prove "if used".
   if(def.condition==='MEDIA_PRESENT')return false;
   if(def.condition==='SCOPE_IS_BRANCH')return scope_id!==input.business_id;
   return true;
  }
  function check(def:RequirementDefinition):Check {
   const base:Check={requirement_id:def.id,label:def.label,owner:def.owner,status:'MISSING',fact_ids:[],offering_ids:[],message:'No hay datos aprobados suficientes para este requisito.',next_step:def.next_step};
   if(!condition(def))return {...base,status:'NOT_REQUIRED_BY_CONDITION',message:def.condition==='MEDIA_PRESENT'
    ?'Requisito condicionado a un uso explícito de H3 vinculado a esta función. V1 no aporta ese vínculo; la mera presencia de un medio no lo activa.'
    :'La condición declarada no se activa en este snapshot; el requisito se conserva.',next_step:null};
   const finish=(ok:boolean,refs:string[]=[],offerings:string[]=[],message=base.message):Check=>{
    const fs=refs.map(id=>facts.get(id)).filter((f):f is BusinessInput['facts'][number]=>!!f),status:Check['status']=ok?'SATISFIED':fs.some(f=>f.publication==='CONFLICTED')?'CONFLICTED':fs.some(f=>f.publication==='WITHHELD')?'WITHHELD':
     fs.some(f=>!publishable(f,instant)&&f.publication==='APPROVED')?'STALE':'MISSING';
    return {...base,status,fact_ids:sorted(refs),offering_ids:sorted(offerings),message:ok?'Requisito respaldado por los datos indicados.':message,next_step:ok?null:def.next_step};
   };
   const approved=(f:BusinessInput['facts'][number])=>publishable(f,instant)&&valid(f.value,def.validation);
   switch(def.check) {
    case 'IDENTITY':{const f=facts.get(input.identity.name_fact_id);return finish(!!f&&f.kind==='business_name'&&approved(f),[input.identity.name_fact_id]);}
    case 'ACTIVE_BUSINESS':return finish(input.identity.status==='ACTIVE',[],[],`Estado del negocio: ${input.identity.status}.`);
    case 'LANGUAGES':return finish(input.identity.languages.length>0,[],[]);
    case 'CAPABILITY_ASSERTION':return finish(claim?.status==='CONFIRMED_PRESENT'&&claim.evidence_ids.every(id=>publishable(facts.get(id),instant)),claim?.evidence_ids??[],[],
     `Estado factual: ${claim?.status??'UNKNOWN'}. La interpretación de actividad no confirma la función.`);
    case 'PUBLICATION':return finish(relevantRefs.length>0&&relevantRefs.every(id=>publishable(facts.get(id),instant)),relevantRefs);
    case 'OFFERINGS':{
     const passing=eligible.filter(o=>offeringKindsValid(o,facts)&&validClass(o,facts)&&offeringFactIds(o).every(id=>publishable(facts.get(id),instant))&&card.offering_fact_requirements.every(req=>
      offeringFactIds(o).some(id=>facts.get(id)?.kind===req.kind&&(!req.value||facts.get(id)?.value===req.value))));
     return finish(passing.length>0,eligible.flatMap(offeringFactIds),passing.map(o=>o.id),'Faltan objetos aprobados del tipo requerido, con referencias completas y papel correcto.');}
    case 'CONTENT_FACTS':{
     let fs=factCandidates;
     if(card.selector==='CONTACT')fs=fs.filter(f=>input.contact_fact_ids.includes(f.id));
     if(card.selector==='SERVICE_AREA')fs=fs.filter(f=>input.service_area_fact_ids.includes(f.id));
     if(card.selector==='LOCATIONS')fs=fs.filter(f=>f.kind==='address'&&(scope_id===input.business_id||input.locations.some(s=>s.id===scope_id&&s.address_fact_id===f.id)));
     if(card.selector==='OPENING_HOURS')fs=fs.filter(f=>f.kind==='opening_hours'&&(scope_id===input.business_id||input.locations.some(s=>s.id===scope_id&&s.opening_hours_fact_ids.includes(f.id))));
     let ok=fs.some(f=>publishable(f,instant));
     if(card.selector==='OPENING_HOURS')ok&&=(input.locations.find(s=>s.id===scope_id)?.exception_fact_ids??[]).every(id=>facts.get(id)?.kind==='opening_hours_exception'&&publishable(facts.get(id),instant));
     return finish(ok,fs.map(f=>f.id));}
    case 'FACT':{
     if(def.validation==='COORDINATE_PAIR') {
      const ids=input.locations.find(s=>s.id===scope_id)?.coordinate_fact_ids??[],fs=ids.map(id=>facts.get(id)).filter((f):f is BusinessInput['facts'][number]=>!!f);
      return finish(['latitude','longitude'].every(kind=>fs.some(f=>f.kind===kind&&f.scope_id===scope_id&&publishable(f,instant)&&typeof f.value==='number'&&Math.abs(f.value)<=(kind==='latitude'?90:180))),ids);
     }
     if(def.binding==='EACH_OFFERING') {
      const objects=def.condition==='PRICES_PRESENT'?eligible.filter(o=>offeringFactIds(o).some(id=>facts.get(id)?.kind==='price')):eligible;
      const matches=objects.map(o=>offeringFactIds(o).map(id=>facts.get(id)).filter((f):f is BusinessInput['facts'][number]=>!!f&&def.fact_kinds.includes(f.kind)));
      return finish(objects.length>0&&matches.every(fs=>fs.some(approved)),matches.flat().map(f=>f.id),objects.map(o=>o.id),'Cada oferta afectada necesita su dato vinculado explícitamente; no se toma el dato de otra oferta o sucursal.');
     }
     const fs=input.facts.filter(f=>f.scope_id===(def.binding==='GLOBAL_IDENTITY'?input.business_id:scope_id)&&def.fact_kinds.includes(f.kind));return finish(fs.some(approved),fs.map(f=>f.id));}
    case 'ACTION_DESTINATION':{
     const fs=actions.map(a=>facts.get(a.url_fact_id)).filter((f):f is BusinessInput['facts'][number]=>!!f);
     return finish(fs.some(f=>f.kind==='action_url'&&f.scope_id===scope_id&&publishable(f,instant)&&safeExternalUrl(f.value)),fs.map(f=>f.id));}
    case 'CONTACT_CHANNEL':{
     const fs=input.contact_fact_ids.map(id=>facts.get(id)).filter((f):f is BusinessInput['facts'][number]=>!!f&&f.scope_id===scope_id&&['phone','email','whatsapp','contact_url'].includes(f.kind));
     return finish(fs.some(f=>publishable(f,instant)&&typeof f.value==='string'&&f.value.trim().length>0&&(f.kind!=='contact_url'||safeExternalUrl(f.value))),fs.map(f=>f.id));}
    case 'MEDIA_FILE':return finish(false,[],[],inMedia.length?'Hay referencias a medios, pero B1 no inspeccionó sus bytes, calidad ni sujeto/rol. Conservar pendiente de revisión H3.':'Falta un archivo pertinente con sujeto/rol comprobados; una URL o metadato no acredita archivo inspeccionado.');
    case 'MEDIA_RIGHTS':return {...base,status:'RIGHTS_REVIEW_PENDING',message:'B1 no verifica permisos. H3 debe comprobar autorización por activo y uso; DOCUMENTED e IDs no equivalen a permiso.'};
    case 'RIGHTS_REVIEW':return {...base,status:'RIGHTS_REVIEW_PENDING',message:'Falta evidencia de autorización vigente del proveedor para la operación concreta.'};
    case 'SEMANTIC_SUPPORT':return card.semantic_status==='AVAILABLE'?finish(true):{...base,status:'SUPPORT_PENDING',message:'Semántica diferida en H2; no se presenta como implementada.'};
    case 'FRONTEND_SUPPORT':return card.component_path?finish(true):{...base,status:'SUPPORT_PENDING',message:'No existe representación frontend compartida de esta función en el runtime local.'};
    case 'BACKEND_SUPPORT':return {...base,status:'SUPPORT_PENDING',message:'Backend comercial ausente. Datos completos o una declaración de fixture no demuestran conexión.'};
   }
  }
  const actual=modules.filter(m=>m.capability_id===card.id&&m.scope_id===scope_id);
  const levels:FunctionalDiagnostic['entries'][number]['levels']=card.levels.map(level=>{
   const requirements=level.requirement_ids.map(id=>check(definitions.get(id)!));
   const dependency=(ids:Capability[],mode:'ALL'|'ANY')=>{
    const conditions=ids.map(id=>modules.some(m=>m.capability_id===id&&m.scope_id===(id==='identity'?input.business_id:scope_id)));
    return {capability_ids:ids,mode,scope_id:ids.every(id=>id==='identity')?input.business_id:scope_id,satisfied:mode==='ALL'?conditions.every(Boolean):conditions.some(Boolean),
     message:'Las dependencias usan módulos del plan emitido y alcance exacto; sólo identidad se comparte globalmente.'};
   };
   const dependency_checks=[...(card.depends_on.length?[dependency(card.depends_on,'ALL')]:[]),...(card.depends_on_any.length?[dependency(card.depends_on_any,'ANY')]:[])];
   const blockers=sorted([...requirements.filter(r=>!['SATISFIED','NOT_REQUIRED_BY_CONDITION'].includes(r.status)).map(r=>r.requirement_id),
    ...dependency_checks.filter(d=>!d.satisfied).map(d=>`dependency:${d.mode}:${d.capability_ids.join('|')}`),...(result.status!=='READY'?['site_plan_not_emitted']:[]),
    ...(relevance==='APPLICABILITY_NOT_EVALUATED'?['applicability_not_evaluated']:[])]);
   let status:FunctionalDiagnostic['entries'][number]['levels'][number]['status']='PENDING';
   if(relevance==='NOT_APPLICABLE_JUSTIFIED')status='NOT_APPLICABLE_JUSTIFIED';else if(relevance==='REJECTED')status='REJECTED';
   else if(!blockers.length&&actual.length&&level.id==='public_information')status='INFORMATION_PLANNED';
   else if(!blockers.length&&actual.length&&level.id==='external_link')status='EXTERNAL_INTENT_PLANNED';
   return {level_id:level.id,label:level.label,implementation:level.implementation,status,requirements,dependency_checks,blockers,next_steps:
    ['REJECTED','NOT_APPLICABLE_JUSTIFIED'].includes(status)?[]:sorted([...requirements.flatMap(r=>r.next_step?[r.next_step]:[]),
     ...dependency_checks.filter(d=>!d.satisfied).map(d=>`Completar dependencias ${d.capability_ids.join(', ')} en el alcance indicado.`),
     ...(result.status!=='READY'?['Resolver los diagnósticos antes de emitir un SitePlan.']:[]),...(relevance==='APPLICABILITY_NOT_EVALUATED'?['Determinar si esta función corresponde al objetivo, con evidencia o decisión explícita.']:[])])};
  });
  entries.push({capability_id:card.id,scope_id,relevance,decision_evidence_ids:decision?.evidence_ids??[],evidence_status:claim?.status??'UNKNOWN',emitted_in_plan:actual.length>0,
   module_ids:actual.map(m=>m.id),factual_evidence_ids:claim?.evidence_ids??[],h2_missing_inputs:result.requirements?.requirements.find(r=>r.capability_id===card.id&&r.scope_id===scope_id)?.missing_inputs??[],levels});
 }
 const body={schema_version:'1.0.0' as const,kind:'FUNCTIONAL_OBJECTIVE_DIAGNOSTIC' as const,business_id:input.business_id,snapshot_id:input.snapshot_id,
  business_input_sha256:inputSha256(input),evaluated_at:context.evaluated_at,catalog_sha256:catalog.catalog_sha256,contextual_interpretation_sha256:context.interpretation_sha256,
  data_mode:input.data_mode,planner_status:result.status,plan_id:result.status==='READY'?result.plan.id:null,plan_sha256:result.status==='READY'?inputSha256(result.plan):null,
  objective_sha256:inputSha256({catalog_sha256:catalog.catalog_sha256,decisions,scopes}),entries,
  warnings:['Catálogo completo del registry V1; no prueba cobertura de toda función futura.',
   'READY significa plan válido de lo emitible; el objetivo puede conservar requisitos pendientes.',
   'Una clasificación contextual no confirma operaciones. Sin datos no se elimina una necesidad.',
   'Un destino externo ficticio no demuestra proveedor real. Medios sin revisión de archivo/rol permanecen pendientes.'],
  operational_integrations:'NOT_CONNECTED' as const,human_design_approval:'NOT_COLLECTED' as const};
 const diagnostic=FunctionalDiagnosticV1.parse({...body,diagnostic_sha256:inputSha256(body)});
 return {context,planner:result,diagnostic};
}
export function verifyFunctionalDiagnostic(value:unknown,input:unknown,options:DiagnosticOptions) {
 const parsed=FunctionalDiagnosticV1.parse(value),expected=diagnoseBusiness(input,options).diagnostic;
 if(inputSha256(parsed)!==inputSha256(expected))throw Error('FUNCTIONAL_DIAGNOSTIC_MISMATCH');return parsed;
}
