import {capabilityRegistry,validateCapabilityRegistry} from '../planner/registry.ts';
import {CapabilityId,ArchetypeId} from '../contracts/v1/schemas.ts';
import type {Capability} from '../contracts/v1/schemas.ts';
import {componentRegistry} from '../composition/registry.ts';
import {RequirementCatalogV1} from './contracts.ts';
import type {RequirementDefinition,RequirementCatalog,RequirementCard} from './contracts.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
const labels:Record<Capability,string>={identity:'Identidad',about:'Acerca del negocio',locations:'Ubicación',opening_hours:'Horarios',contact_channels:'Canales de contacto',
 social_profiles:'Perfiles oficiales',reputation:'Reputación documentada',gallery:'Galería',service_catalog:'Servicios',product_catalog:'Catálogo de productos',menu:'Carta o menú',
 product_variants:'Variantes de producto',price_list:'Tarifas',packages:'Paquetes',rooms:'Habitaciones',programs:'Programas',professional_profiles:'Profesionales',trainer_profiles:'Entrenadores',
 portfolio:'Portafolio',case_studies:'Casos documentados',reservation:'Reservas',appointment:'Citas',quote_request:'Cotizaciones',contact_request:'Solicitud de contacto',purchase:'Compra',order:'Pedidos',
 delivery:'Entrega',pickup:'Retiro',membership:'Membresías',membership_signup:'Inscripción a membresía',class_enrollment:'Inscripción a clases',ticketing:'Entradas',room_booking:'Reserva de estancia',
 visit_booking:'Visitas',service_request:'Solicitud de servicio',class_schedule:'Calendario de clases',events:'Eventos',availability_display:'Disponibilidad informada',service_area:'Cobertura del servicio',
 delivery_policy:'Condiciones de entrega',visit_policy:'Condiciones de visita',payment_methods:'Métodos de pago',amenities:'Comodidades',accessibility_info:'Accesibilidad',branches:'Directorio de sucursales',faqs:'Preguntas frecuentes',documents:'Documentos'};
// Facts shared by capabilities; these are data requirements, not sector templates.
const details:Record<Capability,string[]>={
 identity:['brand_identity','publication_languages'],about:['business_description','history_evidence'],locations:['arrival_instructions','timezone'],opening_hours:['timezone','hours_validity','holiday_exception_policy'],
 contact_channels:['channel_purpose','contact_hours'],social_profiles:['official_profile_ownership'],reputation:['reputation_source','reputation_date','testimonial_publication_permission'],gallery:['media_caption','media_entity_binding'],
 service_catalog:['offering_description','service_conditions','service_duration'],product_catalog:['offering_description','sku','product_specifications'],menu:['offering_description','price','currency','menu_validity','ingredients','allergen_disclosure_policy'],
 product_variants:['variant_attributes','variant_offering_binding'],price_list:['currency','price_validity','price_conditions'],packages:['package_inclusions','package_exclusions','package_terms'],rooms:['room_capacity','room_features','stay_rules'],
 programs:['program_duration','program_requirements','program_calendar'],professional_profiles:['professional_role','professional_credentials','credential_verification_reference'],trainer_profiles:['professional_role','trainer_qualifications'],
 portfolio:['work_entity_binding','work_publication_permission'],case_studies:['case_context','case_result_evidence','case_publication_permission'],
 reservation:['booking_rules'],appointment:['appointment_rules'],quote_request:['quote_scope','quote_nonbinding_notice'],contact_request:['request_purpose'],purchase:['purchase_terms'],order:['order_modes'],
 delivery:['delivery_coverage','delivery_conditions','delivery_fees'],pickup:['pickup_location','pickup_hours','pickup_conditions'],membership:['membership_terms','membership_eligibility','membership_validity'],
 membership_signup:['membership_signup_rules'],class_enrollment:['class_enrollment_rules'],ticketing:['event_access_rules'],room_booking:['stay_rules'],visit_booking:['visit_rules'],service_request:['service_request_scope'],
 class_schedule:['class_duration','class_capacity','instructor_binding'],events:['event_starts_at','timezone','event_location','event_access_rules'],availability_display:['availability_updated_at','availability_source','availability_not_guaranteed_notice'],
 service_area:['coverage_boundaries','coverage_exclusions'],delivery_policy:['delivery_times','delivery_fees','delivery_exclusions'],visit_policy:['visit_access_rules','visit_requirements'],payment_methods:['payment_scope','payment_conditions'],
 amenities:['amenity_conditions'],accessibility_info:['accessibility_scope','accessibility_verified_details'],branches:['branch_relationships','branch_contacts'],faqs:['faq_question','faq_answer_validity'],documents:['document_version','document_validity','document_publication_permission']};
const actionFields:Partial<Record<Capability,string[]>>={
 reservation:['booking_hours','timezone','booking_capacity','booking_availability','party_limits','booking_rules','confirmation_policy','cancellation_policy','customer_fields','personal_data_policy'],
 appointment:['appointment_resources','appointment_duration','appointment_calendar','timezone','appointment_rules','confirmation_policy','cancellation_policy','customer_fields','personal_data_policy'],
 quote_request:['quote_scope','quote_questions','quote_validity','quote_nonbinding_notice','personal_data_policy'],contact_request:['request_purpose','request_fields','personal_data_policy'],
 purchase:['orderable_offering_ids','stock_availability','price','currency','tax_rules','fulfillment_rules','return_policy','payment_authorization','personal_data_policy'],
 order:['orderable_offering_ids','order_options','order_modes','stock_availability','price','currency','fulfillment_rules','cancellation_policy','personal_data_policy'],
 membership_signup:['membership_plan_binding','membership_terms','membership_start_rules','renewal_rules','cancellation_policy','customer_fields','personal_data_policy'],
 class_enrollment:['class_binding','class_calendar','timezone','class_capacity','class_eligibility','confirmation_policy','cancellation_policy','personal_data_policy'],
 ticketing:['event_binding','event_starts_at','timezone','event_capacity','price','currency','event_access_rules','ticket_confirmation','refund_policy','personal_data_policy'],
 room_booking:['room_inventory','checkin_checkout_rules','timezone','room_capacity','room_rates','currency','booking_availability','confirmation_policy','cancellation_policy','personal_data_policy'],
 visit_booking:['visit_target_binding','visit_calendar','timezone','visit_capacity','visit_rules','confirmation_policy','cancellation_policy','personal_data_policy'],
 service_request:['service_request_scope','service_request_questions','service_area','service_terms','confirmation_policy','personal_data_policy']};
const visitorFields:Partial<Record<Capability,[string,string][]>>={
 reservation:[['branch_id','Sucursal elegida'],['requested_date','Fecha deseada'],['requested_time','Hora deseada'],['party_size','Número de comensales'],['reply_contact','Contacto para responder']],
 appointment:[['branch_id','Sucursal elegida'],['offering_id','Servicio solicitado'],['professional_preference','Profesional preferido, cuando corresponda'],['requested_date','Fecha deseada'],['requested_time','Hora deseada'],['reply_contact','Contacto para responder']],
 quote_request:[['offering_id','Producto o servicio de la consulta'],['request_scope','Alcance, cantidades o necesidades'],['service_location','Lugar de prestación, si afecta la cotización'],['reply_contact','Contacto para responder']],
 contact_request:[['request_purpose','Motivo de contacto'],['message','Mensaje'],['reply_contact','Contacto para responder']],
 purchase:[['offering_id','Producto y variante'],['quantity','Cantidad'],['fulfillment_choice','Entrega o retiro'],['reply_contact','Contacto del pedido']],
 order:[['offering_id','Oferta y opciones del pedido'],['quantity','Cantidad'],['fulfillment_choice','Modalidad de cumplimiento'],['reply_contact','Contacto del pedido']],
 membership_signup:[['offering_id','Plan elegido'],['requested_date','Inicio deseado'],['participant_data','Datos mínimos del participante'],['terms_ack','Aceptación de condiciones cuando corresponda']],
 class_enrollment:[['offering_id','Clase o programa elegido'],['participant_data','Datos mínimos del participante'],['terms_ack','Condiciones y elegibilidad cuando correspondan']],
 ticketing:[['offering_id','Evento y categoría de entrada'],['quantity','Número de entradas'],['reply_contact','Destino de las entradas']],
 room_booking:[['branch_id','Alojamiento elegido'],['offering_id','Habitación o categoría'],['checkin_date','Fecha de entrada'],['checkout_date','Fecha de salida'],['party_size','Ocupación'],['reply_contact','Contacto de la estancia']],
 visit_booking:[['offering_id','Espacio o propiedad'],['requested_date','Fecha deseada'],['requested_time','Hora deseada'],['reply_contact','Contacto para responder']],
 service_request:[['offering_id','Servicio solicitado'],['request_scope','Necesidad y alcance'],['service_location','Lugar de prestación cuando corresponda'],['reply_contact','Contacto para responder']]};
const fieldLabels:Record<string,string>={business_description:'Descripción aprobada del negocio',offering_description:'Descripción de cada oferta',price:'Importes vigentes',currency:'Moneda de los importes',timezone:'Zona horaria',
 booking_hours:'Turnos y horario de reservas',booking_capacity:'Capacidad por turno y sucursal',booking_availability:'Disponibilidad de reserva actualizable',party_limits:'Límites de comensales',booking_rules:'Reglas de reserva',
 confirmation_policy:'Confirmación verificable y estados de error',cancellation_policy:'Cancelación y cambios',customer_fields:'Datos mínimos del solicitante',personal_data_policy:'Tratamiento de datos personales y retención',
 request_receiver:'Canal receptor y responsable',request_fields:'Campos de solicitud',provider_authorization:'Contrato, versión y permiso de integración del proveedor',
 media_entity_binding:'Vínculo auténtico del medio con negocio/oferta/sucursal',allergen_disclosure_policy:'Qué información de alérgenos puede publicarse con respaldo',ingredients:'Ingredientes documentados cuando se ofrecen',
 official_profile_ownership:'Control del perfil oficial',history_evidence:'Fuente de la historia del negocio',sku:'Referencia o SKU',menu_validity:'Vigencia del menú',
 brand_identity:'Identidad de marca aprobada',publication_languages:'Idiomas de publicación',arrival_instructions:'Instrucciones de llegada',hours_validity:'Vigencia de los horarios',holiday_exception_policy:'Excepciones y festivos conocidos',
 channel_purpose:'Finalidad del canal de contacto',contact_hours:'Horario de atención por canal',reputation_source:'Fuente de la reputación',reputation_date:'Fecha de la valoración',testimonial_publication_permission:'Autorización para publicar testimonios',
 media_caption:'Descripción contextual del medio',service_conditions:'Condiciones del servicio',service_duration:'Duración del servicio',product_specifications:'Especificaciones del producto',variant_attributes:'Atributos de cada variante',variant_offering_binding:'Vínculo de la variante con el producto',
 price_validity:'Vigencia de las tarifas',price_conditions:'Condiciones de los importes',package_inclusions:'Qué incluye el paquete',package_exclusions:'Qué excluye el paquete',package_terms:'Condiciones del paquete',room_capacity:'Capacidad de la habitación',room_features:'Características de la habitación',stay_rules:'Reglas de estancia',
 program_duration:'Duración del programa',program_requirements:'Requisitos de ingreso al programa',program_calendar:'Calendario del programa',professional_role:'Papel del profesional',professional_credentials:'Credenciales del profesional',credential_verification_reference:'Fuente de verificación de las credenciales',trainer_qualifications:'Cualificaciones del entrenador',
 work_entity_binding:'Vínculo de cada trabajo con el negocio',work_publication_permission:'Permiso para publicar el trabajo',case_context:'Contexto del caso',case_result_evidence:'Evidencia de los resultados del caso',case_publication_permission:'Permiso para publicar el caso',
 appointment_rules:'Reglas de las citas',quote_scope:'Alcance de la cotización',quote_nonbinding_notice:'Aviso de cotización sin compromiso',request_purpose:'Finalidad de la solicitud',purchase_terms:'Condiciones de compra',order_modes:'Modalidades de pedido',
 delivery_coverage:'Zona de entrega',delivery_conditions:'Condiciones de entrega',delivery_fees:'Costos de entrega',pickup_location:'Lugar de retiro',pickup_hours:'Horario de retiro',pickup_conditions:'Condiciones de retiro',membership_terms:'Condiciones de la membresía',membership_eligibility:'Requisitos de membresía',membership_validity:'Vigencia de la membresía',
 membership_signup_rules:'Reglas de inscripción a la membresía',class_enrollment_rules:'Reglas de inscripción a clases',event_access_rules:'Reglas de acceso al evento',visit_rules:'Reglas de visita',service_request_scope:'Alcance de la solicitud de servicio',class_duration:'Duración de la clase',class_capacity:'Cupo de la clase',instructor_binding:'Instructor vinculado a la clase',
 event_starts_at:'Fecha y hora de inicio del evento',event_location:'Lugar del evento',availability_updated_at:'Última actualización de disponibilidad',availability_source:'Fuente de la disponibilidad',availability_not_guaranteed_notice:'Aviso del alcance de la disponibilidad informada',
 coverage_boundaries:'Límites de la cobertura',coverage_exclusions:'Exclusiones de cobertura',delivery_times:'Plazos de entrega respaldados',delivery_exclusions:'Exclusiones de entrega',visit_access_rules:'Reglas de acceso para visitas',visit_requirements:'Requisitos para visitar',payment_scope:'Alcance de cada método de pago',payment_conditions:'Condiciones de pago',
 amenity_conditions:'Condiciones de las comodidades',accessibility_scope:'Alcance de la información de accesibilidad',accessibility_verified_details:'Detalles de accesibilidad respaldados',branch_relationships:'Relación entre sucursales',branch_contacts:'Contacto de cada sucursal',faq_question:'Pregunta asociada a cada respuesta',faq_answer_validity:'Vigencia de las respuestas',document_version:'Versión del documento',document_validity:'Vigencia del documento',document_publication_permission:'Autorización de publicación del documento',
 appointment_resources:'Profesionales o recursos que pueden atender',appointment_duration:'Duración de la cita',appointment_calendar:'Agenda actualizable de citas',quote_questions:'Datos necesarios para cotizar',quote_validity:'Vigencia de la cotización',orderable_offering_ids:'Ofertas habilitadas para comprar o pedir',stock_availability:'Existencias disponibles',tax_rules:'Reglas e importes tributarios aplicables',fulfillment_rules:'Preparación y cumplimiento del pedido',return_policy:'Devoluciones',payment_authorization:'Autorización del servicio de pagos',order_options:'Opciones del pedido',
 membership_plan_binding:'Plan de membresía elegido',membership_start_rules:'Inicio de la membresía',renewal_rules:'Renovación de la membresía',class_binding:'Clase elegida',class_calendar:'Calendario actualizable de clases',class_eligibility:'Requisitos para participar en la clase',event_binding:'Evento elegido',event_capacity:'Cupo del evento',ticket_confirmation:'Emisión y verificación de la entrada',refund_policy:'Reembolsos',
 room_inventory:'Inventario de habitaciones',checkin_checkout_rules:'Entrada y salida del alojamiento',room_rates:'Tarifas por habitación y fecha',visit_target_binding:'Espacio o propiedad que se visitará',visit_calendar:'Agenda actualizable de visitas',visit_capacity:'Cupo de visitas',service_request_questions:'Información necesaria para prestar el servicio',service_area:'Zona de prestación del servicio',service_terms:'Condiciones de prestación del servicio',reception_error_policy:'Recepción, respuesta y errores de la solicitud'};
const defs=new Map<string,RequirementDefinition>();
function define(id:string,label:string,check:RequirementDefinition['check'],extra:Partial<RequirementDefinition>={}) {
 const definition:RequirementDefinition={id,label,description:label,owner:'BUSINESS_UPSTREAM',kind:'DATA',condition:'ALWAYS',check,fact_kinds:[],binding:'SCOPE',validation:'PRESENT',
  next_step:`Aportar y aprobar ${label.toLowerCase()} para este alcance, con fuente y vigencia.`,...extra};
 const prior=defs.get(id);if(prior&&inputSha256(prior)!==inputSha256(definition))throw Error(`CATALOG_DEFINITION_COLLISION:${id}`);defs.set(id,definition);return id;
}
const common=[
 define('business_name','Nombre publicable del negocio','IDENTITY',{binding:'GLOBAL_IDENTITY',validation:'TEXT'}),
 define('active_business','Estado activo del negocio','ACTIVE_BUSINESS',{binding:'GLOBAL_IDENTITY',kind:'EVIDENCE'}),
 define('languages','Idiomas del proyecto','LANGUAGES',{binding:'GLOBAL_IDENTITY',owner:'PROJECT_CONFIGURATION',kind:'CONFIGURATION'}),
 define('capability_assertion','Disponibilidad factual de la función','CAPABILITY_ASSERTION',{kind:'EVIDENCE',next_step:'Confirmar, negar o aclarar esta capacidad con evidencia aprobada y vigente de esta sucursal; la categoría no la confirma.'}),
 define('publication','Publicación y vigencia de todos los datos usados','PUBLICATION',{kind:'EVIDENCE'}),
 define('semantic_support','Soporte de planificación semántica','SEMANTIC_SUPPORT',{kind:'PLATFORM',owner:'PLATFORM',next_step:'Implementar y verificar el soporte semántico compartido sin alterar hechos ni permisos.'}),
];
const frontend=define('frontend_support','Representación frontend disponible','FRONTEND_SUPPORT',{kind:'PLATFORM',owner:'PLATFORM',next_step:'Implementar y auditar la representación compartida; una intención de enlace H2 no es un componente operativo.'});
const backend=define('backend_support','Sistema operativo conectado y probado','BACKEND_SUPPORT',{kind:'PLATFORM',owner:'PLATFORM',next_step:'En una fase autorizada futura, implementar el adaptador, autenticarlo y probar recepción/confirmación/errores; B1 no conecta backend.'});
const media=[define('media_file','Archivo audiovisual pertinente y auténtico para su rol','MEDIA_FILE'),
 define('media_rights','Permisos por archivo, cliente, proyecto, finalidad y tratamiento','MEDIA_RIGHTS',{owner:'PROVIDER_RIGHTS',kind:'PERMISSION',next_step:'Evaluar con H3 el original/hash, documento y versión, atribución, alcance, terceros y transformaciones; DOCUMENTED y un ID no prueban permiso.'})];
const optionalMedia=media.map(id=>{const original=defs.get(id)!;return define(`${id}_if_used`,original.label,original.check,{...original,id:`${id}_if_used`,condition:'MEDIA_PRESENT'});});
function field(kind:string,binding:RequirementDefinition['binding']='SCOPE',condition:RequirementDefinition['condition']='ALWAYS') {
 const id=`fact:${binding.toLowerCase()}:${kind}:${condition.toLowerCase()}`,label=fieldLabels[kind]??kind.replaceAll('_',' ');
 const validation:RequirementDefinition['validation']=kind==='timezone'?'TIMEZONE':kind==='currency'?'CURRENCY':kind==='price'?'NONNEGATIVE_NUMBER':
  /(?:starts_at|updated_at)$/.test(kind)?'ISO_DATETIME':/(?:capacity|duration)$/.test(kind)?'POSITIVE_NUMBER':'TEXT';
 return define(id,label,'FACT',{fact_kinds:[kind],binding,condition,validation});
}
const cards:RequirementCard[]=capabilityRegistry.specs.map(spec=>{
 const documentary=['identity','about','gallery','product_catalog','menu','rooms','professional_profiles','trainer_profiles','portfolio','case_studies','events','branches'].includes(spec.id);
 const illustrative=['service_catalog','membership','programs','class_schedule'].includes(spec.id);
 const richMedia=documentary||illustrative?media:optionalMedia;
 const component=componentRegistry[spec.semantic_module as keyof typeof componentRegistry];
 const data=spec.selector==='IDENTITY'?[]:spec.offering_kinds.length?[define(`offerings:${spec.id}`,'Objetos de oferta aprobados con todas sus referencias','OFFERINGS')]:
  spec.selector==='ACTION'?[define('action_destination','Destino externo aprobado para esta función y sucursal','ACTION_DESTINATION',{validation:'HTTPS'})]:
  spec.selector==='DEFERRED'?media:[define(`content:${spec.id}`,`Contenido aprobado: ${labels[spec.id]}`,'CONTENT_FACTS')];
 const base=[...common,...data];
 const extra=details[spec.id].map(kind=>field(kind,spec.offering_kinds.length&&kind!=='menu_validity'?'EACH_OFFERING':'SCOPE',
  kind==='currency'&&spec.offering_kinds.length?'PRICES_PRESENT':'ALWAYS'));
 if(spec.offering_kinds.length)base.push(field('currency','EACH_OFFERING','PRICES_PRESENT'));
 if(spec.selector==='LOCATIONS')extra.push(define('coordinate_pair','Coordenadas válidas y vinculadas a la sucursal','FACT',{fact_kinds:['latitude','longitude'],validation:'COORDINATE_PAIR',condition:'COORDINATES_PRESENT'}));
 const level=(id:string,label:string,requirements:string[],implementation:RequirementCard['levels'][number]['implementation'],behavior:string):RequirementCard['levels'][number]=>({
  id,label,objective:`${labels[spec.id]}: ${label.toLowerCase()}`,expected_behavior:behavior,requirement_ids:[...new Set(requirements)],specification:'SPECIFIED',implementation,
  verification:'NOT_VERIFIED_OPERATIONALLY',backend:'NOT_CONNECTED',acceptance_criteria:['Todos los requisitos aplicables deben conservar fuente, publicación y vigencia.','No mezclar contenido, operaciones ni permisos entre sucursales.',
   'Conservar todas las dependencias y estados pendientes; ninguna categoría confirma disponibilidad.',spec.selector==='ACTION'?'No anunciar éxito, compra o reserva confirmada sin respuesta verificable del sistema autorizado.':'Renderizar exactamente las referencias aprobadas y conservar diagnósticos.'],
  interaction_states:spec.selector==='ACTION'?['pendiente de datos','recepción o conexión no disponible','solicitud sin confirmar','error explicado','éxito sólo con evidencia futura']:['datos insuficientes','información disponible','contenido retenido o vencido'],
  visitor_inputs:spec.selector==='ACTION'&&!['contact','external_link'].includes(id)?(visitorFields[spec.id]??[]).map(([id,label])=>({id,label,
   value_type:/date$/.test(id)?'DATE' as const:/time$/.test(id)?'TIME' as const:['party_size','quantity'].includes(id)?'POSITIVE_INTEGER' as const:/_id$/.test(id)?'IDENTIFIER' as const:/_ack$/.test(id)?'ACKNOWLEDGEMENT' as const:'TEXT' as const,
   required_when:'Sólo si esta variante y sus reglas documentadas necesitan este dato; recopilar lo mínimo.',
   validation:/_id$/.test(id)?'Referencia a oferta o sucursal válida en este alcance.':/date$/.test(id)?'Fecha válida; turnos, vigencia, entrada/salida y zona horaria según reglas.':/time$/.test(id)?'Hora válida para la sucursal, fecha y zona horaria.':['party_size','quantity'].includes(id)?'Entero positivo dentro de límites y disponibilidad.':'Formato, tamaño, finalidad y tratamiento según configuración revisada.',
   purpose:'Dato del visitante durante una operación futura; no pedir valores personales reales para completar B1.'})):[]});
 let levels:RequirementCard['levels'];
 if(spec.selector==='ACTION') {
  const contact=define('contact_channel','Canal de contacto aprobado de la sucursal','CONTACT_CHANNEL');
  const provider=define('provider_authorization','Contrato, versión y permisos de integración del proveedor','RIGHTS_REVIEW',{owner:'PROVIDER_RIGHTS',kind:'PERMISSION',next_step:'Demostrar alcance por cliente/proyecto, automatización, tratamiento de datos, volumen, costos y restricciones del proveedor antes de conectar.'});
  const requestSchema=define(`request_schema:${spec.id}`,`Configuración de los campos de ${labels[spec.id].toLowerCase()}`,'FACT',{fact_kinds:[`request_field_schema:${spec.id}`],owner:'PROJECT_CONFIGURATION',kind:'CONFIGURATION',validation:'TEXT',
   next_step:'Definir campos, condiciones y validación a partir de los visitor_inputs de esta ficha. No solicitar datos personales de visitantes durante B1.'});
  const integration=define('integration_configuration','Configuración autorizada del sistema conectado','FACT',{fact_kinds:['integration_configuration_reference'],owner:'PROJECT_CONFIGURATION',kind:'CONFIGURATION',validation:'TEXT',
   next_step:'Referenciar sistema, versión, endpoint, sucursal, autenticación privada y política de errores. No copiar secretos al input, repo o logs.'});
  const request=[...common,field('request_receiver'),requestSchema,field('reception_error_policy'),field('personal_data_policy'),frontend,backend];
  const connected=[...common,...extra,...(actionFields[spec.id]??[]).map(kind=>field(kind)),integration,provider,frontend,backend];
  levels=[...(spec.id==='reservation'?[level('contact','Contacto para consultar',[...common,contact,frontend],'SPECIFICATION_ONLY','Mostrar el canal aprobado para consultar; no envía ni confirma una reserva.')]:[]),
   level('request','Solicitud pendiente de confirmación',request,'SPECIFICATION_ONLY','Recoger sólo los datos mínimos y enviarlos a un receptor probado. Una solicitud recibida sigue pendiente de confirmación.'),
   level('external_link','Enlace externo aprobado',base,'EXTERNAL_LINK_SEMANTICS_ONLY','H2 puede planificar un destino aprobado. El clic abre un servicio externo; no demuestra recepción o confirmación ni que este runtime tenga el componente.'),
   level(spec.id==='reservation'?'connected_confirmation':'connected_execution',spec.id==='reservation'?'Reserva confirmada mediante sistema conectado':'Operación mediante sistema conectado',connected,'SPECIFICATION_ONLY',
    'Especificación futura: consultar estado/disponibilidad, prevenir duplicados, confirmar mediante respuesta verificable y permitir cambios/cancelación/errores según reglas. No implementado en B1.')];
 } else levels=[level('public_information','Información pública básica',[...base,frontend],component?'LAB_INFORMATION_PRIMITIVE':'SPECIFICATION_ONLY','Planificar y representar información aprobada con primitivas compartidas; no implica operación comercial.'),
  level('detailed_information','Información completa y medios adecuados',[...base,...extra,...richMedia,frontend],component?'LAB_INFORMATION_PRIMITIVE':'SPECIFICATION_ONLY',
   'Añadir detalle documentado y archivos pertinentes con permiso por uso. No rellenar datos ni cubrir fotos documentales con stock. No prueba calidad estética sin evaluación humana.')];
 return {id:spec.id,label:labels[spec.id],objective:`Definir y diagnosticar ${labels[spec.id].toLowerCase()} sin inventar disponibilidad.`,
  semantic_module:spec.semantic_module,selector:spec.selector,offering_kinds:spec.offering_kinds,offering_fact_requirements:spec.offering_fact_requirements,
  fact_kinds:spec.fact_kinds,candidate_archetypes:spec.candidate_archetypes,depends_on:spec.depends_on,depends_on_any:spec.depends_on_any,
  scope_policy:['identity','branches'].includes(spec.id)?'BUSINESS_ONLY':'EXACT_SCOPE_WITH_GLOBAL_IDENTITY_DEPENDENCY',levels,
  semantic_status:spec.semantic_status,component_path:component?.path??null,semantic_test_reference:'tests/planner.test.ts',
  media_roles:documentary?['DOCUMENTARY']:illustrative?['ILLUSTRATIVE','DOCUMENTARY']:[],
  future_notes:['La cobertura es del vocabulario V1 existente, no una lista definitiva de toda función futura.',
   'Primitiva disponible no significa que cada ficha o nivel haya sido verificado operacionalmente.',spec.id==='reservation'?'Contacto, solicitud, enlace y confirmación son niveles distintos.':'Integraciones futuras requieren un encargo y evidencia nuevos.']};
});
export const commonGoalCapabilities:Capability[]=['identity','about','locations','opening_hours','contact_channels','social_profiles','reputation','gallery','accessibility_info','faqs'];
const body={schema_version:'1.0.0' as const,kind:'MASTER_CAPABILITY_REQUIREMENTS' as const,catalog_id:'capabilities-v1-master-1.0.0',registry_sha256:inputSha256(capabilityRegistry),
 definitions:[...defs.values()].sort((a,b)=>a.id.localeCompare(b.id)),cards,groups:ArchetypeId.options.map(archetype_id=>({archetype_id,capability_ids:cards.filter(c=>c.candidate_archetypes.includes(archetype_id)).map(c=>c.id)})),
 common_capabilities:commonGoalCapabilities,scope_inheritance:'IDENTITY_ONLY_NO_OPERATIONAL_BRANCH_INHERITANCE' as const};
export const requirementCatalog=RequirementCatalogV1.parse({...body,catalog_sha256:inputSha256(body)});
export function validateRequirementCatalog(value:unknown):RequirementCatalog {
 const catalog=RequirementCatalogV1.parse(value),{catalog_sha256,...body}=catalog;
 if(inputSha256(body)!==catalog_sha256)throw Error('CATALOG_HASH_MISMATCH');
 if(catalog.registry_sha256!==inputSha256(validateCapabilityRegistry(capabilityRegistry)))throw Error('CATALOG_REGISTRY_DRIFT');
 if(catalog.cards.length!==CapabilityId.options.length||new Set(catalog.cards.map(c=>c.id)).size!==CapabilityId.options.length||CapabilityId.options.some(id=>!catalog.cards.some(c=>c.id===id)))throw Error('CATALOG_CAPABILITY_COVERAGE');
 if(new Set(catalog.definitions.map(d=>d.id)).size!==catalog.definitions.length)throw Error('CATALOG_DUPLICATE_DEFINITION');
 const definitions=new Set(catalog.definitions.map(d=>d.id));
 for(const card of catalog.cards) {
  const spec=capabilityRegistry.specs.find(s=>s.id===card.id)!;
  for(const key of ['semantic_module','selector','offering_kinds','offering_fact_requirements','fact_kinds','candidate_archetypes','depends_on','depends_on_any','semantic_status'] as const)
   if(inputSha256(card[key])!==inputSha256(spec[key]))throw Error(`CATALOG_SEMANTIC_DRIFT:${card.id}:${key}`);
  if(new Set(card.levels.map(l=>l.id)).size!==card.levels.length||card.levels.some(l=>new Set(l.requirement_ids).size!==l.requirement_ids.length||l.requirement_ids.some(id=>!definitions.has(id))))throw Error('CATALOG_LEVEL_DEFINITION_INVALID');
 }
 if(catalog.groups.length!==ArchetypeId.options.length||new Set(catalog.groups.map(g=>g.archetype_id)).size!==catalog.groups.length||catalog.groups.some(g=>
  inputSha256(g.capability_ids)!==inputSha256(catalog.cards.filter(c=>c.candidate_archetypes.includes(g.archetype_id)).map(c=>c.id))))throw Error('CATALOG_GROUP_DRIFT');
 if(catalog.catalog_id!==requirementCatalog.catalog_id||catalog.catalog_sha256!==requirementCatalog.catalog_sha256)throw Error('CATALOG_UNSUPPORTED_POLICY_REVISION');
 return catalog;
}
