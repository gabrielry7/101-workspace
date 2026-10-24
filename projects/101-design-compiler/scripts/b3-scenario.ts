import {mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {BusinessInputV1} from '../src/contracts/v1/schemas.ts';
import {planBusiness} from '../src/planner/plan.ts';
import {projectContent} from '../src/composition/content.ts';
import {loadMappingRegistry} from './load-taxonomy.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const directory='fixtures/corrections/b3',path=`${directory}/la-mesa.json`,verify=process.argv.includes('--verify');
const business='b3-la-mesa-fictional',branch=`${business}-sede-imaginaria`,at='2026-10-15T03:00:00Z';
const facts:any[]=[],caps:any[]=[],offerings:any[]=[];
function fact(id:string,kind:string,value:string|boolean,scope_id=business){facts.push({id,kind,value,scope_id,publication:'APPROVED',publication_decision_id:`fiction-authorized-${id}`,source:'USER_AUTHORIZED_SYNTHETIC_DEMO_NOT_REAL_BUSINESS',observed_at:at});return id;}
function cap(id:string,scope_id=business,status='CONFIRMED_PRESENT'){const evidence=fact(`evidence-${id}`,`capability:${id}`,true,scope_id);caps.push({id,scope_id,status,evidence_ids:[evidence]});}
fact('name','business_name','La Mesa');fact('category','observed_category','restaurant');
fact('identity-line','brand_name','Cocina para quedarse un rato.');
cap('identity');cap('about');
fact('story-1','about_text','Todo empieza alrededor de una mesa.');
fact('story-2','about_text','Imaginamos un lugar de barrio donde la conversación dura más que el último bocado. Una carta corta, platos al centro y tiempo para compartir.');
fact('story-3','about_text','Esta es una historia creada para explorar el diseño de un restaurante ficticio. No describe una empresa, una cocina ni un equipo reales.');
cap('menu',branch);
const dishes=[
 {id:'pizza',name:'Pizza de la casa',category:'Al horno',description:'Masa fina, tomate y pepperoni. Una idea de carta para compartir desde el centro de la mesa.',ingredients:'Receta ficticia: harina de trigo, tomate, mozzarella, pepperoni, aceite de oliva.',allergens:'Declaración ficticia: contiene trigo (gluten) y leche. No apta como información alimentaria real.',price:'42.000 COP',calories:'Estimación de ejemplo: 780 kcal por porción. Sin análisis nutricional.'},
 {id:'pasta',name:'Pasta junto al mar',category:'Platos principales',description:'Pasta con camarones, tomate y una salsa suave. Una pausa larga para la hora del almuerzo.',ingredients:'Receta ficticia: pasta de trigo, camarones, tomate, crema, parmesano, perejil.',allergens:'Declaración ficticia: contiene trigo (gluten), crustáceos y leche. No apta como información alimentaria real.',price:'38.000 COP',calories:'Estimación de ejemplo: 620 kcal por porción. Sin análisis nutricional.'},
 {id:'salad',name:'Verde de temporada',category:'Del jardín',description:'Hojas frescas, vegetales y una vinagreta ligera. Textura, color y algo crujiente en cada bocado.',ingredients:'Receta ficticia: lechuga, tomate, pepino, zanahoria, aceite de oliva, limón.',allergens:'Declaración ficticia: alérgenos y trazas por confirmar en una cocina real. No se afirma «libre de».',price:'26.000 COP',calories:'Estimación de ejemplo: 280 kcal por porción. Sin análisis nutricional.'},
 {id:'dessert',name:'El último bocado',category:'Algo dulce',description:'Una porción de pastel y unos minutos más de sobremesa. Porque el final también merece su momento.',ingredients:'Receta ficticia: harina de trigo, huevo, leche, azúcar, cacao, mantequilla.',allergens:'Declaración ficticia: contiene trigo (gluten), huevo y leche. No apta como información alimentaria real.',price:'19.000 COP',calories:'Estimación de ejemplo: 410 kcal por porción. Sin análisis nutricional.'},
];
for(const d of dishes){const name_fact_id=fact(`${d.id}-name`,'offering_name',d.name,branch),fact_ids:string[]=[];
 for(const field of ['category','description','ingredients','allergens','calories'] as const)fact_ids.push(fact(`${d.id}-${field}`,`offering_${field}`,d[field],branch));
 fact_ids.push(fact(`${d.id}-currency`,'currency','COP',branch));const price_fact_id=fact(`${d.id}-price`,'price',d.price,branch);
 offerings.push({id:d.id,kind:'menu_item',scope_id:branch,name_fact_id,fact_ids,price_fact_id});}
cap('locations',branch);const address=fact('address','address','Pasaje de la Imaginación, 12 · sede ficticia, sin ubicación real.',branch);
cap('opening_hours',branch);const hours=fact('hours','opening_hours','Horario de ejemplo: martes a domingo, 12:00–22:00. Lunes cerrado.',branch);
cap('amenities',branch);fact('parking','amenity','Parqueadero: previsto en este escenario ficticio; plazas y acceso por confirmar antes de una web real.',branch);
cap('faqs',branch);fact('faq-1','faq_answer','¿Podemos celebrar algo? En esta propuesta imaginamos mesas para cumpleaños y encuentros de hasta ocho personas. No hay disponibilidad real.',branch);
fact('faq-2','faq_answer','¿Cómo funciona el pedido? Puedes explorar una selección de ejemplo. Esta demo no recibe pedidos, pagos ni datos personales.',branch);
cap('reservation',branch,'UNKNOWN');cap('order',branch,'UNKNOWN');
const input=BusinessInputV1.parse({schema_version:'1.0.0',business_id:business,snapshot_id:'b3-la-mesa-v1',data_mode:'SYNTHETIC_FIXTURE',as_of:at,
 identity:{name_fact_id:'name',alias_fact_ids:['identity-line'],status:'ACTIVE',languages:['es']},category_observations:[{id:'category-observation',source:'osm',field:'amenity',value:'restaurant',confidence:1,evidence_ids:['category']}],
 facts,locations:[{id:branch,address_fact_id:address,coordinate_fact_ids:[],opening_hours_fact_ids:[hours],exception_fact_ids:[],visit_policy_fact_ids:[]}],contact_fact_ids:[],service_area_fact_ids:[],offerings,business_capabilities:caps,action_destinations:[],existing_media:[],
 restrictions:['SYNTHETIC_DEMO_ONLY','NO_REAL_RESERVATIONS_ORDERS_PAYMENTS_OR_REVIEWS','STOCK_IS_NOT_BUSINESS_EVIDENCE'],preference_fact_ids:[]});
const {rules}=await loadMappingRegistry(),planner=planBusiness(input,{rules});if(planner.status!=='READY')throw Error(JSON.stringify(planner.diagnostics));
const content=projectContent({input:planner.input,profile:planner.profile,capabilities:planner.capabilities,plan:planner.plan},planner.requirements);
const result={schema_version:'1.0.0',kind:'B3_COMPLETE_FICTIONAL_SCENARIO',authority:'User authorized complete fictional demos; Codex authored synthetic scenario, not upstream approval',input,planner,content,
 presentation:{mode:'SINGLE_PAGE_ANCHOR_BINDINGS',logical_routes:content.pages.map(p=>({path:p.path,module_ids:p.modules.map(m=>m.id)})),fictional_recipe_source:'WRITTEN_FOR_DEMO_NOT_INFERRED_FROM_STOCK',live_operations:false}};
const bytes=JSON.stringify(result,null,2)+'\n';
if(verify){if(await readFile(path,'utf8')!==bytes)throw Error('B3_SCENARIO_REPLAY_MISMATCH');}
else{if(await access(path).then(()=>true,()=>false))throw Error('B3_SCENARIO_EXISTS');await mkdir(directory,{recursive:true});await writeFile(path,bytes);}
console.log(JSON.stringify({status:verify?'PASS_REPLAY':'SYNTHETIC_SCENARIO_WRITTEN',input_sha256:inputSha256(input),plan_sha256:content.plan_sha256,content_sha256:content.content_sha256,modules:content.pages.flatMap(p=>p.modules).map(m=>m.capability_id),bound:content.bindings.filter(b=>b.status==='BOUND').length}));
