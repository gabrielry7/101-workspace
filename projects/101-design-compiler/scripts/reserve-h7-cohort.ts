// One-time creation of new synthetic held-out data; never called by build/replay.
import { mkdir, writeFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { BusinessInputV1 } from '../src/contracts/v1/schemas.ts';
const folder = 'fixtures/cohort/h7';
if(await access(`${folder}/reservation.json`).then(()=>true,()=>false))throw Error('COHORT_ALREADY_RESERVED_DO_NOT_OVERWRITE');
await mkdir(folder, { recursive: true });
const specs = [
  {id:'hotel',category:['osm','tourism','hotel'],offers:['room','room'],extra:['amenities','amenity','Patio de prueba sintético, sin fotografía documental.']},
  {id:'dentista',category:['osm','amenity','dentist'],offers:['service','professional'],extra:['about','about_text','Caso clínico ficticio; no acredita licencia ni resultados.']},
  {id:'servicio',category:['osm','craft','plumber'],offers:['service','service'],extra:['service_area','service_area','Zona de prueba sintética, sin domicilio operativo.']},
  {id:'hibrido',category:['foursquare','foursquare.category','Sports and Recreation > Gym and Studio > Gym'],offers:['membership_plan','class_session','product_category'],extra:[]},
  {id:'unknown',category:[],offers:[],extra:[]},
  {id:'media-unknown',category:['osm','craft','plumber'],offers:['service'],extra:[]},
] as const;
const capabilityFor:Record<string,string>={room:'rooms',service:'service_catalog',professional:'professional_profiles',membership_plan:'membership',class_session:'class_schedule',product_category:'product_catalog'};
const files=[];
for(const spec of specs){
 const business=`h7-synthetic-${spec.id}`; const facts:any[]=[]; const caps:any[]=[];
 const fact=(id:string,kind:string,value:string|boolean)=>{facts.push({id,kind,value,scope_id:business,publication:'APPROVED',publication_decision_id:`synthetic-decision-${id}`,source:'h7-new-synthetic-fixture',observed_at:'2026-10-08T00:00:00Z'});return id;};
 const cap=(id:string)=>{if(caps.some(c=>c.id===id))return;caps.push({id,scope_id:business,status:'CONFIRMED_PRESENT',evidence_ids:[fact(`assert-${id}`,`capability:${id}`,true)]});};
 fact('name','business_name',`${spec.id} · NUEVO fixture sintético H7; no es negocio real`);cap('identity');
 const observations:any[]=[];
 if(spec.category.length)observations.push({id:'category',source:spec.category[0],field:spec.category[1],value:spec.category[2],confidence:1,evidence_ids:[fact('category-evidence','observed_category',spec.category[2])]});
 const offerings=spec.offers.map((kind,i)=>{cap(capabilityFor[kind]!);const o:any={id:`object-${i+1}`,kind,scope_id:business,name_fact_id:fact(`object-${i+1}-name`,'offering_name',`Objeto ${i+1} de prueba (${kind}); descripción sintética`),fact_ids:[fact(`object-${i+1}-description`,'offering_description',`Información declarada de prueba ${i+1}, sin precio o promesa operativa.`)]};if(kind==='class_session'){o.starts_at_fact_id=fact('starts','class_starts_at','2026-11-01T09:00:00-05:00');o.timezone_fact_id=fact('zone','timezone','America/Bogota');}return o;});
 if(spec.extra.length){cap(spec.extra[0]);fact('extra',spec.extra[1],spec.extra[2]);}
 const relationships:any[]=[];
 if(spec.id==='hibrido'){observations.push({id:'shop-category',source:'osm',field:'shop',value:'hardware',confidence:1,evidence_ids:[fact('shop-evidence','observed_category','hardware')]});relationships.push({id:'coexisting',kind:'COEXISTING',category_observation_ids:['category','shop-category'],evidence_ids:[fact('coexisting-evidence','activity:coexisting',true)]});}
 const input=BusinessInputV1.parse({schema_version:'1.0.0',business_id:business,snapshot_id:`${business}-reserved-v1`,data_mode:'SYNTHETIC_FIXTURE',as_of:'2026-10-08T00:00:00Z',identity:{name_fact_id:'name',alias_fact_ids:[],status:'ACTIVE',languages:['es']},category_observations:observations,facts,locations:[],contact_fact_ids:[],service_area_fact_ids:spec.id==='servicio'?['extra']:[],offerings,business_capabilities:caps,action_destinations:[],existing_media:spec.id==='media-unknown'?[{id:'unknown-image',source:'synthetic-fixture',uri:'https://example.invalid/h7-unlicensed.jpg',kind:'image',scope_id:business,rights_status:'UNKNOWN',rights_document_ids:[],restrictions:['No permission established; do not fetch or render.']}]:[],restrictions:['SYNTHETIC_FIXTURE: NO PUBLICAR COMO NEGOCIO REAL','H7 held-out reservation; no real credentials or media permission'],preference_fact_ids:[]});
 const value={scenario:spec.id,input,activity_relationships:relationships};const bytes=JSON.stringify(value,null,2)+'\n';const path=`${folder}/${spec.id}.json`;await writeFile(path,bytes);files.push({path,sha256:createHash('sha256').update(bytes).digest('hex')});
}
await writeFile(`${folder}/reservation.json`,JSON.stringify({schema_version:'1.0.0',data_mode:'SYNTHETIC_FIXTURE',reserved_before_first_execution:true,baseline_commit:'99dfa596ce922721e03330e23f04888fe7216659',cohort_version:'h7-synthetic-held-out-1',external_evidence:false,human_preferences:'NOT_COLLECTED',files},null,2)+'\n');
