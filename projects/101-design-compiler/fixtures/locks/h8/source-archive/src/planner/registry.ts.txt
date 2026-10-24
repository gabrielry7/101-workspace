import { ArchetypeId, CapabilityId } from '../contracts/v1/schemas.ts';
import type { Capability } from '../contracts/v1/schemas.ts';
import { candidateCapabilitiesByArchetype } from '../taxonomy/resolve.ts';
import { CapabilityRegistryV1 } from './contracts.ts';
import type { CapabilityRegistry, CapabilitySpec } from './contracts.ts';

type Configuration = Pick<CapabilitySpec, 'selector' | 'semantic_module' | 'route' | 'policy' | 'priority'>
  & Partial<Pick<CapabilitySpec, 'offering_kinds' | 'offering_fact_requirements' | 'fact_kinds' | 'depends_on_any' | 'semantic_status'>>;
const collection = (route: string, offering_kinds: CapabilitySpec['offering_kinds'], priority = 10): Configuration => ({
  selector: 'OFFERINGS', semantic_module: 'offering_collection', route, offering_kinds, priority, policy: 'REQUIRED_IF_PRESENT',
});
const information = (fact_kinds: string[], route = '/', priority = 40): Configuration => ({
  selector: 'FACTS', semantic_module: 'fact_collection', route, fact_kinds, priority, policy: 'CONDITIONAL',
});
const action = (route: string, depends_on_any: Capability[] = []): Configuration => ({
  selector: 'ACTION', semantic_module: 'external_action', route, depends_on_any, priority: 60, policy: 'CONDITIONAL',
});

// Semantic capabilities, never a renderer, component library or vertical template.
const configurations: Record<Capability, Configuration> = {
  identity: { selector: 'IDENTITY', semantic_module: 'identity', route: '/', priority: 0, policy: 'REQUIRED_IF_PRESENT' },
  about: information(['about_text']),
  locations: { ...information(['address'], '/ubicacion', 30), selector: 'LOCATIONS', semantic_module: 'location_information' },
  opening_hours: { ...information(['opening_hours', 'opening_hours_exception'], '/ubicacion', 31), selector: 'OPENING_HOURS' },
  contact_channels: { ...information(['phone', 'email', 'whatsapp', 'contact_url'], '/contacto', 35), selector: 'CONTACT' },
  social_profiles: information(['social_profile']), reputation: information(['reputation_statement']),
  gallery: { ...information([], '/galeria'), selector: 'DEFERRED', semantic_module: 'deferred_media', semantic_status: 'DEFERRED', policy: 'OPTIONAL' },
  service_catalog: collection('/servicios', ['service']),
  product_catalog: collection('/catalogo', ['product', 'product_category']),
  menu: collection('/menu', ['menu_item']),
  product_variants: { ...information(['product_variant'], '/catalogo', 20), depends_on_any: ['product_catalog'] },
  price_list: information(['price_list'], '/precios', 20), packages: information(['package_description'], '/paquetes', 20),
  rooms: collection('/habitaciones', ['room']), programs: collection('/programas', ['program']),
  professional_profiles: collection('/equipo', ['professional'], 20),
  trainer_profiles: { ...collection('/equipo', ['professional'], 20), offering_fact_requirements: [{ kind: 'professional_role', value: 'trainer' }] },
  portfolio: information(['portfolio_entry'], '/portafolio', 20), case_studies: information(['case_study'], '/casos', 20),
  reservation: action('/contacto'), appointment: action('/contacto', ['service_catalog', 'professional_profiles']),
  quote_request: action('/contacto'), contact_request: action('/contacto'),
  purchase: action('/catalogo', ['product_catalog']), order: action('/pedidos', ['menu', 'product_catalog']),
  delivery: information(['delivery_description'], '/modalidades', 30), pickup: information(['pickup_policy'], '/modalidades', 30),
  membership: collection('/membresias', ['membership_plan']),
  membership_signup: action('/membresias', ['membership']),
  class_enrollment: action('/clases', ['class_schedule', 'programs']), ticketing: action('/eventos', ['events']),
  room_booking: action('/habitaciones', ['rooms']), visit_booking: action('/contacto', ['locations', 'portfolio']),
  service_request: action('/contacto', ['service_catalog']),
  class_schedule: { ...collection('/clases', ['class_session'], 15), semantic_module: 'schedule' },
  events: collection('/eventos', ['event']), availability_display: information(['availability_statement'], '/disponibilidad', 30),
  service_area: { ...information(['service_area'], '/cobertura', 30), selector: 'SERVICE_AREA' },
  delivery_policy: information(['delivery_policy'], '/modalidades', 31),
  visit_policy: { ...information(['visit_policy'], '/ubicacion', 32), selector: 'VISIT_POLICY' },
  payment_methods: information(['payment_method'], '/modalidades', 40), amenities: information(['amenity'], '/comodidades', 20),
  accessibility_info: information(['accessibility_statement'], '/ubicacion', 33),
  branches: information(['branch_directory'], '/sedes', 30),
  faqs: information(['faq_answer'], '/preguntas', 45), documents: information(['document_description'], '/documentos', 40),
};

export const capabilityRegistry: CapabilityRegistry = CapabilityRegistryV1.parse({
  schema_version: '1.0.0', specs: CapabilityId.options.map(id => ({
    id, version: '1.0.0', semantic_status: 'AVAILABLE', offering_kinds: [], offering_fact_requirements: [], fact_kinds: [], depends_on_any: [],
    candidate_archetypes: ArchetypeId.options.filter(archetype => candidateCapabilitiesByArchetype[archetype]?.includes(id)),
    depends_on: id === 'identity' ? [] : ['identity'], ...configurations[id],
  })),
});

export function validateCapabilityRegistry(value: unknown): CapabilityRegistry {
  const registry = CapabilityRegistryV1.parse(value);
  const specs = new Map(registry.specs.map(x => [x.id, x]));
  if (specs.size !== registry.specs.length) throw new Error('DUPLICATE_CAPABILITY_SPEC');
  if (!specs.has('identity')) throw new Error('IDENTITY_SPEC_REQUIRED');
  for (const spec of registry.specs) {
    if (new Set([...spec.depends_on, ...spec.depends_on_any]).size !== spec.depends_on.length + spec.depends_on_any.length) throw new Error('DUPLICATE_DEPENDENCY');
    for (const dependency of [...spec.depends_on, ...spec.depends_on_any]) if (!specs.has(dependency)) throw new Error(`UNKNOWN_DEPENDENCY:${dependency}`);
    if (spec.selector === 'OFFERINGS' && !spec.offering_kinds.length) throw new Error(`MISSING_OFFERING_SPEC:${spec.id}`);
    if (spec.fact_kinds.some(x => x.startsWith('capability:')) || spec.offering_fact_requirements.some(x => x.kind.startsWith('capability:'))) throw new Error('ASSERTION_AS_CONTENT_SPEC');
    if (spec.selector === 'FACTS' && (!spec.fact_kinds.length || spec.fact_kinds.some(x => x.startsWith('capability:')))) throw new Error(`MISSING_CONTENT_SPEC:${spec.id}`);
    if (spec.selector === 'ACTION' && spec.semantic_module !== 'external_action') throw new Error(`ACTION_SPEC_MISMATCH:${spec.id}`);
    if (spec.selector === 'OFFERINGS' && !['offering_collection', 'schedule'].includes(spec.semantic_module)) throw new Error('OFFERING_MODULE_MISMATCH');
    if (spec.selector === 'IDENTITY' && (spec.id !== 'identity' || spec.semantic_module !== 'identity')) throw new Error('IDENTITY_MODULE_MISMATCH');
    if (spec.selector === 'LOCATIONS' && spec.semantic_module !== 'location_information') throw new Error('LOCATION_MODULE_MISMATCH');
    if (spec.selector === 'DEFERRED' && spec.semantic_module !== 'deferred_media') throw new Error('MEDIA_MODULE_MISMATCH');
    if ((spec.selector === 'DEFERRED') !== (spec.semantic_status === 'DEFERRED')) throw new Error(`SUPPORT_SPEC_MISMATCH:${spec.id}`);
    if (spec.id === 'identity' && (spec.selector !== 'IDENTITY' || spec.route !== '/' || spec.policy !== 'REQUIRED_IF_PRESENT' || spec.depends_on.length || spec.depends_on_any.length)) throw new Error('INVALID_IDENTITY_SPEC');
    if (spec.id !== 'identity' && !spec.depends_on.includes('identity')) throw new Error('IDENTITY_DEPENDENCY_REQUIRED');
  }
  const visiting = new Set<Capability>(); const visited = new Set<Capability>();
  const visit = (id: Capability): void => {
    if (visiting.has(id)) throw new Error(`DEPENDENCY_CYCLE:${id}`);
    if (visited.has(id)) return;
    visiting.add(id);
    const spec = specs.get(id)!;
    for (const dependency of [...spec.depends_on, ...spec.depends_on_any]) visit(dependency);
    visiting.delete(id); visited.add(id);
  };
  for (const spec of registry.specs) visit(spec.id);
  return registry;
}
