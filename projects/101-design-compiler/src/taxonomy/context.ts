import {BusinessProfileV1,ArchetypeId} from '../contracts/v1/schemas.ts';
import type {BusinessInput} from '../contracts/v1/schemas.ts';
import {validateBusinessInput} from '../validation/input.ts';
import {classifyBusiness,candidateCapabilitiesByArchetype} from './resolve.ts';
import type {MappingRule,TaxonomyObservation,ActivityRelationship,Archetype} from './contracts.ts';
import {ContextualActivityLinkV1,ContextualInterpretationV1} from './context-contracts.ts';
import type {ContextualActivityLink,ContextualInterpretation,ActivitySignal} from './context-contracts.ts';
import {contextPolicy} from './context-policy.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
import {publishable,offeringFactIds,offeringKindsValid,validClass,sorted} from '../planner/content.ts';
export type ContextOptions={rules:readonly MappingRule[];category_context?:readonly TaxonomyObservation[];
 activity_relationships?:readonly ActivityRelationship[];activity_links?:readonly ContextualActivityLink[];evaluation_time?:string};
const uniq=(a:Archetype[])=>sorted(a) as Archetype[];
export function classifyContextually(value:unknown,options:ContextOptions) {
 const boundary=validateBusinessInput(value);if(!boundary.success||!boundary.data)throw Error('CONTEXT_INPUT_INVALID:'+JSON.stringify(boundary.diagnostics));
 const input:BusinessInput=boundary.data,time=options.evaluation_time??input.as_of,instant=Date.parse(time);
 if(!Number.isFinite(instant)||instant<Date.parse(input.as_of)||!ContextualInterpretationV1.shape.evaluated_at.safeParse(time).success)throw Error('CONTEXT_INVALID_TIME');
 const legacy=classifyBusiness(input,options),facts=new Map(input.facts.map(f=>[f.id,f])),scopeIds=[input.business_id,...input.locations.map(x=>x.id)].sort();
 const signals:ActivitySignal[]=[],ignored:ContextualInterpretation['ignored']=[],conflicts=new Set<string>();
 const describedCoexistence:{scope_id:string;archetypes:Archetype[];fact_id:string}[]=[],describedAlternatives=new Set<string>();
 const add=(signal:Omit<ActivitySignal,'id'>)=>signals.push({...signal,id:`signal-${inputSha256(signal).slice(0,24)}`});
 for(const observation of legacy.observations) {
  const refs=observation.observation.evidence_ids,scope=refs.length?facts.get(refs[0]!)?.scope_id:input.business_id;
  if(!scope||!refs.length||refs.some(ref=>!publishable(facts.get(ref),instant)||facts.get(ref)?.scope_id!==scope)) {
   ignored.push({id:observation.observation.id,scope_id:scope??input.business_id,reason:'CATEGORY_WITHOUT_CURRENT_APPROVED_EXACT_SCOPE_EVIDENCE'});continue;
  }
  if(refs.some(ref=>facts.get(ref)?.kind==='observed_category'&&facts.get(ref)?.value!==observation.observation.value)||
   observation.diagnostics.some(d=>['HIERARCHY_SOURCE_CONFLICT','ORIGINAL_NORMALIZED_CONFLICT','CONFLICTING_MAPPING_RULES'].includes(d))) {
   conflicts.add(scope);ignored.push({id:observation.observation.id,scope_id:scope,reason:'CATEGORY_PROVENANCE_OR_VALUE_CONFLICT'});continue;
  }
  if(observation.outcome==='MAPPED') for(const arch of observation.archetypes) add({scope_id:scope,rule_id:observation.rule_ids.join('|'),kind:'CATEGORY',polarity:'POSITIVE',
   candidates:[arch],category_observation_ids:[observation.observation.id],offering_ids:[],fact_ids:refs});
  else if(observation.outcome==='AMBIGUOUS') {
   const candidates=uniq(observation.alternatives.flat());if(candidates.length)add({scope_id:scope,rule_id:'ambiguous-category',kind:'CATEGORY',polarity:'POSITIVE',candidates,category_observation_ids:[observation.observation.id],offering_ids:[],fact_ids:refs});
  } else ignored.push({id:observation.observation.id,scope_id:scope,reason:observation.outcome});
 }
 for(const fact of input.facts) {
  const activity=ArchetypeId.safeParse(fact.kind.replace(/^activity:/,''));
  const isAssertion=fact.kind.startsWith('activity:')&&activity.success&&typeof fact.value==='boolean';
  const descriptive=contextPolicy.description_kinds.includes(fact.kind)&&typeof fact.value==='string';
  if(!isAssertion&&!descriptive)continue;
  if(!publishable(fact,instant)) {
   ignored.push({id:fact.id,scope_id:fact.scope_id,reason:`FACT_${fact.publication}_${fact.expires_at&&Date.parse(fact.expires_at)<=instant?'EXPIRED':'NOT_CURRENT_OR_APPROVED'}`});
   if(fact.publication==='CONFLICTED')conflicts.add(fact.scope_id);continue;
  }
  if(isAssertion&&activity.success) add({scope_id:fact.scope_id,rule_id:'exact-approved-activity-assertion',kind:'ACTIVITY_ASSERTION',
   polarity:fact.value===true?'POSITIVE':'NEGATIVE',candidates:[activity.data],category_observation_ids:[],offering_ids:[],fact_ids:[fact.id]});
  if(descriptive) {
   let matched=false;
   for(const clause of String(fact.value).normalize('NFKC').toLowerCase().split(/[.;\n]+|,\s*(?=(?:no somos|somos|we are))|\s+(?:pero|but)\s+/)) {
    let text=clause.trim(),negative=false;
    if(/^(?:ya no somos|no somos|no es|we are not|this is not)\s+/.test(text)){negative=true;text=text.replace(/^(?:ya no somos|no somos|no es|we are not|this is not)\s+/,'');}
    else text=text.replace(/^(?:somos|somos una?|es una?|we are|we are an?|this is an?)\s+/,'');
    text=text.replace(/^(?:un|una|an|a)\s+/,'');
    const alternative=contextPolicy.alternative_subject_connectors.some(connector=>text.includes(connector));
    const parts=text.split(/\s+(?:y|con|and|with|o|or)\s+/).map(part=>part.replace(/^(?:un|una|an|a)\s+/,'')),described:Archetype[]=[];
    if(!Object.values(contextPolicy.descriptions).some(phrases=>phrases.some(phrase=>parts[0]===phrase||parts[0]?.startsWith(phrase+' ')||parts[0]?.startsWith(phrase+','))))continue;
    for(const part of parts.filter((part,index)=>index===0||!/(?:al lado|cerca de|nearby|next door|not ours|no es nuestra)/.test(part)))for(const [archetype,phrases] of Object.entries(contextPolicy.descriptions)) if(phrases.some(phrase=>part===phrase||part.startsWith(phrase+' ')||part.startsWith(phrase+','))) {
     matched=true;described.push(archetype as Archetype);add({scope_id:fact.scope_id,rule_id:`subject-prefix:${archetype}`,kind:'DESCRIPTION',polarity:negative?'NEGATIVE':'POSITIVE',
      candidates:[archetype as Archetype],category_observation_ids:[],offering_ids:[],fact_ids:[fact.id]});
    }
    if(!negative&&uniq(described).length>1){if(alternative)describedAlternatives.add(fact.scope_id);else describedCoexistence.push({scope_id:fact.scope_id,archetypes:uniq(described),fact_id:fact.id});}
   }
   if(!matched)ignored.push({id:fact.id,scope_id:fact.scope_id,reason:'UNSUPPORTED_OR_NON_SUBJECT_PROSE_NO_KEYWORD_GUESS'});
  }
 }
 for(const item of input.offerings) {
  const candidates=contextPolicy.offering_candidates[item.kind],refs=offeringFactIds(item);
  if(!candidates){ignored.push({id:item.id,scope_id:item.scope_id,reason:'OFFERING_KIND_NOT_SPECIFIC_ENOUGH_FOR_ACTIVITY'});continue;}
  if(refs.some(id=>!publishable(facts.get(id),instant))||!offeringKindsValid(item,facts)||!validClass(item,facts)) {
   ignored.push({id:item.id,scope_id:item.scope_id,reason:'OFFERING_NOT_FULLY_PUBLISHABLE_OR_TYPED'});continue;
  }
  add({scope_id:item.scope_id,rule_id:`typed-offering:${item.kind}`,kind:'OFFERING',polarity:'POSITIVE',candidates,category_observation_ids:[],offering_ids:[item.id],fact_ids:refs});
 }
 for(const media of input.existing_media)ignored.push({id:media.id,scope_id:media.scope_id,reason:'RAW_MEDIA_NOT_INSPECTED_NO_ACTIVITY_OR_PERMISSION_INFERRED'});
 const links=(options.activity_links??[]).map(v=>ContextualActivityLinkV1.parse(v));
 for(const old of options.activity_relationships??[]) {
  const archetypes=uniq(legacy.observations.filter(o=>old.category_observation_ids.includes(o.observation.id)).flatMap(o=>o.archetypes));
  if(archetypes.length>1)links.push({id:old.id,scope_id:input.business_id,kind:old.kind,archetype_ids:archetypes,evidence_ids:old.evidence_ids});
 }
 if(new Set(links.map(x=>x.id)).size!==links.length)throw Error('CONTEXT_DUPLICATE_ACTIVITY_LINK');
 for(const link of links) {
  if(!scopeIds.includes(link.scope_id)||new Set(link.archetype_ids).size!==link.archetype_ids.length||
   !link.evidence_ids.every(id=>facts.get(id)?.scope_id===link.scope_id&&publishable(facts.get(id),instant))||
   !link.evidence_ids.some(id=>facts.get(id)?.kind===`activity:${link.kind.toLowerCase()}`&&facts.get(id)?.value===true))throw Error('CONTEXT_UNVERIFIED_ACTIVITY_LINK');
 }
 const scopes:ContextualInterpretation['scopes']=scopeIds.map(scope_id=>{
  const local=signals.filter(s=>s.scope_id===scope_id),positive=local.filter(s=>s.polarity==='POSITIVE'),negative=uniq(local.filter(s=>s.polarity==='NEGATIVE').flatMap(s=>s.candidates));
  const definite=uniq(positive.filter(s=>s.candidates.length===1).flatMap(s=>s.candidates)),core=definite.filter(x=>x!=='regulated_services');
  let alternatives=uniq(positive.flatMap(s=>s.candidates)),selected:Archetype[]=[],status:ContextualInterpretation['scopes'][number]['status']='UNKNOWN';
  const diagnostics:string[]=[];
  if(conflicts.has(scope_id)||definite.some(x=>negative.includes(x))){status='CONFLICTED';diagnostics.push('CONTRADICTORY_ACTIVITY_EVIDENCE');}
  else if(describedAlternatives.has(scope_id)||links.some(l=>l.scope_id===scope_id&&l.kind==='ALTERNATIVE'))status='AMBIGUOUS';
  else if(core.length>1) {
   if(links.some(l=>l.scope_id===scope_id&&l.kind==='COEXISTING'&&core.every(a=>l.archetype_ids.includes(a)))||
    describedCoexistence.some(l=>l.scope_id===scope_id&&core.every(a=>l.archetypes.includes(a)))){status='HYBRID';selected=definite;diagnostics.push('COEXISTENCE_BACKED_BY_SAME_SCOPE_APPROVED_EVIDENCE');}
   else {status='AMBIGUOUS';diagnostics.push('SAME_SCOPE_MULTIPLE_ACTIVITIES_REQUIRE_EXPLICIT_COEXISTENCE');}
  } else if(core.length===1) {
   if(positive.some(s=>s.candidates.every(a=>a!=='regulated_services'&&!core.includes(a)))){status='AMBIGUOUS';diagnostics.push('DESCRIPTION_CATEGORY_OFFERING_DISAGREEMENT');}
   else {status='RESOLVED';selected=definite;}
  } else if(positive.length) {
   const intersection=alternatives.filter(a=>a!=='regulated_services'&&!negative.includes(a)&&positive.every(s=>s.candidates.includes(a)));
   const globalModels=uniq(signals.filter(s=>s.scope_id===input.business_id&&s.polarity==='POSITIVE'&&s.candidates.length===1).flatMap(s=>s.candidates));
   const refined=scope_id!==input.business_id?intersection.filter(a=>globalModels.includes(a)):[];
   if(intersection.length===1){status='RESOLVED';selected=intersection;}
   else if(refined.length===1){status='RESOLVED';selected=refined;diagnostics.push('GLOBAL_MODEL_REFINES_BRANCH_OFFERING_NOT_CAPABILITY');}
   else {status='AMBIGUOUS';diagnostics.push('OFFERING_SUPPORTS_MULTIPLE_MODELS');}
  }
  if(status==='UNKNOWN'&&scope_id===input.business_id&&legacy.status==='NON_BUSINESS')status='NON_BUSINESS';
  if(status==='RESOLVED'||status==='HYBRID')alternatives=[];
  return {scope_id,status,archetypes:selected,alternatives,signal_ids:local.map(s=>s.id).sort(),diagnostics,
   clarification:['RESOLVED','HYBRID'].includes(status)?[]:[{need:status==='AMBIGUOUS'?'activity_relationship_or_specific_business_description':'approved_activity_description_or_assertion',
    requested_from:'upstream' as const,message:status==='AMBIGUOUS'?'Aclarar qué actividades conviven en esta sucursal y cuáles son alternativas.':'Aportar o corregir una descripción explícita de la actividad, aprobada y vigente, para este alcance.'}]};
 });
 const resolved=scopes.filter(s=>['RESOLVED','HYBRID'].includes(s.status)),global=scopes.find(s=>s.scope_id===input.business_id)!;
 let archetypes=uniq(resolved.flatMap(s=>s.archetypes)),status:ContextualInterpretation['status']='UNKNOWN';
 const bad=scopes.filter(s=>s.status==='CONFLICTED'||s.status==='AMBIGUOUS');
 if(bad.length)status=bad.some(s=>s.status==='CONFLICTED')?'CONFLICTED':'AMBIGUOUS';
 else if(global.status==='NON_BUSINESS'&&resolved.length)status='CONFLICTED';
 else if(global.status==='NON_BUSINESS')status='NON_BUSINESS';
 else if(archetypes.length) {
  const globalCore=global.archetypes.filter(a=>a!=='regulated_services'),branchCore=uniq(resolved.filter(s=>s.scope_id!==input.business_id).flatMap(s=>s.archetypes)).filter(a=>a!=='regulated_services');
  if(globalCore.length&&branchCore.some(a=>!globalCore.includes(a))&&!links.some(l=>l.scope_id===input.business_id&&l.kind==='COEXISTING'&&archetypes.filter(a=>a!=='regulated_services').every(a=>l.archetype_ids.includes(a))))status='AMBIGUOUS';
  else status=resolved.some(s=>s.status==='HYBRID')?'HYBRID':archetypes.filter(a=>a!=='regulated_services').length>1?'MULTISCOPE':'RESOLVED';
 }
 if(!['RESOLVED','HYBRID','MULTISCOPE'].includes(status))archetypes=[];
 signals.sort((a,b)=>a.id.localeCompare(b.id));ignored.sort((a,b)=>a.id.localeCompare(b.id));
 const options_sha256=inputSha256({rules:options.rules,category_context:options.category_context??[],activity_relationships:options.activity_relationships??[],activity_links:options.activity_links??[]});
 const body={schema_version:'1.0.0' as const,kind:'CONTEXTUAL_ACTIVITY_INTERPRETATION' as const,business_id:input.business_id,snapshot_id:input.snapshot_id,
  business_input_sha256:inputSha256(input),evaluated_at:time,policy_sha256:inputSha256(contextPolicy),options_sha256,
  original_categories:legacy.observations.map(o=>o.observation),signals,ignored,scopes,status,
  authority:'ACTIVITY_RELEVANCE_ONLY_NOT_OPERATIONAL_CONFIRMATION' as const,calibrated_confidence:null,limitations:contextPolicy.limitations};
 const fingerprint=inputSha256(body),profile=BusinessProfileV1.parse({schema_version:'1.0.0',business_id:input.business_id,snapshot_id:input.snapshot_id,
  id:`${input.snapshot_id}:context-profile:${fingerprint.slice(0,24)}`,classification:archetypes.length?'RESOLVED':status==='NON_BUSINESS'?'NON_BUSINESS':'UNRESOLVED',scope_ids:scopeIds,
  archetypes:archetypes.map(a=>{const support=signals.filter(s=>s.polarity==='POSITIVE'&&s.candidates.includes(a));return {id:a,relevance:a==='regulated_services'?'modifier':a===archetypes[0]?'primary':'secondary',confidence:0,
   category_observation_ids:sorted(support.flatMap(s=>s.category_observation_ids)),offering_ids:sorted(support.flatMap(s=>s.offering_ids)),evidence_ids:sorted(support.flatMap(s=>s.fact_ids))};}),
  offering_ids:input.offerings.map(o=>o.id).sort(),candidate_capabilities:sorted(archetypes.flatMap(a=>candidateCapabilitiesByArchetype[a]??[])),
  missing_inputs:archetypes.length?[]:[{need:'contextual_activity_review',scope_id:input.business_id,reason:status,requested_from:'upstream'}],restrictions:input.restrictions});
 const context=ContextualInterpretationV1.parse({...body,profile,interpretation_sha256:inputSha256({...body,profile})});
 return {...legacy,status,profile,context};
}
