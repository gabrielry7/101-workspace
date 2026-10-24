import { validateBundle } from '../validation/validate.ts';
import type { Diagnostic } from '../validation/validate.ts';
import { SiteRequirementsV1 } from './contracts.ts';
import { capabilityRegistry, validateCapabilityRegistry } from './registry.ts';
import { offeringFactIds, offeringKindsValid, sorted } from './content.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';

// Independent invariants for the H2 producer/consumer boundary. No renderer claims.
export function validateSemanticPlan(bundle: unknown, requirements: unknown, registryValue: unknown = capabilityRegistry): {
  success: boolean; diagnostics: Diagnostic[];
} {
  const parsed = SiteRequirementsV1.safeParse(requirements);
  if (!parsed.success) return { success: false, diagnostics: parsed.error.issues.map(x => ({ code: 'REQUIREMENTS_SCHEMA_INVALID', path: x.path.join('.'), message: x.message })) };
  const reqs = parsed.data;
  const base = validateBundle(bundle, reqs.evaluated_at);
  const diagnostics = [...base.diagnostics];
  const issue = (code: string, path: string, message: string) => diagnostics.push({ code, path, message });
  if (!base.data) return { success: false, diagnostics };
  const { input, profile, capabilities, plan } = base.data;
  const registry = validateCapabilityRegistry(registryValue);
  if (reqs.business_id !== input.business_id || reqs.snapshot_id !== input.snapshot_id || reqs.business_profile_id !== profile.id || reqs.capability_profile_id !== capabilities.id || reqs.registry_sha256 !== inputSha256(registry) || reqs.business_input_sha256 !== inputSha256(input)) issue('REQUIREMENTS_MISMATCH', 'requirements', 'Requirements must reference these artifacts, input and registry');
  const specifications = new Map(registry.specs.map(x => [x.id, x]));
  const requirementsById = new Map(reqs.requirements.map(x => [x.id, x]));
  if (requirementsById.size !== reqs.requirements.length) issue('DUPLICATE_ID', 'requirements', 'Requirement IDs must be unique');
  const modules = plan.pages.flatMap(page => page.modules.map(module => ({ page, module })));
  const byId = new Map(modules.map(x => [x.module.id, x]));
  for (const req of reqs.requirements) {
    const actual = byId.get(req.id); const spec = specifications.get(req.capability_id);
    if (!spec || req.semantic_module !== spec.semantic_module || req.priority !== spec.priority || req.policy !== spec.policy) issue('SEMANTIC_SPEC_MISMATCH', req.id, 'Requirement must preserve registry semantics');
    if (req.disposition === 'INCLUDED' && !actual) issue(req.required ? 'REQUIRED_MODULE_OMITTED' : 'MODULE_OMITTED', req.id, 'Included semantic module must survive');
    if (req.disposition !== 'INCLUDED' && actual) issue('BLOCKED_MODULE_USED', req.id, 'Blocked/omitted requirement cannot have a module');
    if (actual) {
      const module = actual.module;
      if (module.capability_id !== req.capability_id || module.scope_id !== req.scope_id || module.required !== req.required || actual.page.path !== req.route
        || JSON.stringify(sorted(module.fact_ids)) !== JSON.stringify(sorted(req.fact_ids))
        || JSON.stringify(sorted(module.offering_ids)) !== JSON.stringify(sorted(req.offering_ids))
        || module.action_destination_id !== req.action_destination_id) issue('BINDING_LOSS', req.id, 'Content/scope/requirement binding changed');
      if (spec?.policy === 'REQUIRED_IF_PRESENT' && !module.required) issue('REQUIRED_MODULE_DOWNGRADED', req.id, 'Mandatory semantics cannot become optional');
      if (spec?.selector === 'ACTION' && module.presentation !== 'REAL_APPROVED_EXTERNAL_LINK') issue('ACTION_PRESENTATION_INVALID', req.id, 'Actions can only be approved external links in H2');
      if (spec?.selector !== 'ACTION' && module.presentation !== 'STATIC_PUBLIC_INFORMATION') issue('STATIC_PRESENTATION_REQUIRED', req.id, 'Information cannot claim functional integration');
      for (const dependency of req.depends_on) {
        if (!byId.has(dependency)) issue('DEPENDENCY_MISSING', req.id, `Missing module ${dependency}`);
        if (!requirementsById.has(dependency)) issue('UNKNOWN_REQUIREMENT', req.id, `Missing requirement ${dependency}`);
      }
    }
  }
  for (const { module } of modules) {
    if (!requirementsById.has(module.id)) issue('UNPLANNED_MODULE', module.id, 'Module has no semantic requirement');
    const spec = specifications.get(module.capability_id);
    if (!spec || spec.semantic_status !== 'AVAILABLE') issue('SEMANTIC_SPEC_UNAVAILABLE', module.id, 'Module is outside the supported semantic registry');
    if (spec?.selector === 'FACTS' && module.fact_ids.some(id => !spec.fact_kinds.includes(input.facts.find(x => x.id === id)?.kind ?? ''))) issue('FACT_KIND_MISMATCH', module.id, 'Assertion/category is not substantive content');
    if (spec?.selector === 'OFFERINGS' && module.offering_ids.some(id => !spec.offering_kinds.includes(input.offerings.find(x => x.id === id)?.kind ?? 'menu_item'))) issue('OFFERING_KIND_MISMATCH', module.id, 'Commercial object incompatible with specification');
    if (spec?.selector === 'OFFERINGS' && module.offering_ids.some(id => {
      const item = input.offerings.find(x => x.id === id); if (!item) return false;
      return !spec.offering_fact_requirements.every(requirement => offeringFactIds(item).some(ref => {
        const fact = input.facts.find(x => x.id === ref);
        return fact?.kind === requirement.kind && (!requirement.value || fact.value === requirement.value);
      }));
    })) issue('MISSING_OFFERING_FACT', module.id, 'Required role/typed offering data absent');
    if (module.offering_ids.some(id => {
      const item = input.offerings.find(x => x.id === id);
      return !!item && !offeringKindsValid(item, new Map(input.facts.map(x => [x.id, x])));
    })) issue('FACT_KIND_MISMATCH', module.id, 'Offering fact reference has an incompatible kind');
    if (module.fact_ids.some(id => input.facts.find(x => x.id === id)?.kind.startsWith('capability:'))) issue('ASSERTION_AS_CONTENT', module.id, 'Capability assertion is evidence, not public content');
    if (spec) {
      const dependencyExists = (id: string) => modules.some(x => x.module.capability_id === id
        && x.module.scope_id === (id === 'identity' ? input.business_id : module.scope_id));
      if (spec.depends_on.some(id => !dependencyExists(id)) || spec.depends_on_any.length && !spec.depends_on_any.some(dependencyExists)) issue('DEPENDENCY_MISSING', module.id, 'Registry dependencies must be present in the correct scope');
      const req = requirementsById.get(module.id);
      const declared = (id: string) => req?.depends_on.some(ref => {
        const dependency = byId.get(ref)?.module;
        return dependency?.capability_id === id && dependency.scope_id === (id === 'identity' ? input.business_id : module.scope_id);
      });
      if (spec.depends_on.some(id => !declared(id)) || spec.depends_on_any.length && !spec.depends_on_any.some(declared)) issue('DEPENDENCY_NOT_DECLARED', module.id, 'Requirements must retain registry dependencies');
    }
    if (spec?.policy === 'REQUIRED_IF_PRESENT' && !module.required) issue('REQUIRED_MODULE_DOWNGRADED', module.id, 'Mandatory semantics cannot become optional');
  }
  // Every eligible central capability has a mandatory module, even if someone drops
  // the requirement as well as its page. An exclusion cannot conceal eligible data.
  for (const cap of capabilities.capabilities) {
    const spec = specifications.get(cap.id);
    if (cap.status === 'CONFIRMED_PRESENT' && spec?.policy === 'REQUIRED_IF_PRESENT' && !cap.missing_inputs.length
      && !modules.some(x => x.module.capability_id === cap.id && x.module.scope_id === cap.scope_id && x.module.required)) issue('REQUIRED_MODULE_OMITTED', `${cap.scope_id}:${cap.id}`, 'Central approved capability is not represented');
  }
  const bound = new Map<string, string[]>();
  for (const { module } of modules) for (const id of sorted([...module.fact_ids, ...module.offering_ids.flatMap(ref => {
    const item = input.offerings.find(x => x.id === ref); return item ? offeringFactIds(item) : [];
  })])) bound.set(id, [...(bound.get(id) ?? []), module.id]);
  if (new Set(reqs.bindings.map(x => x.fact_id)).size !== input.facts.length || reqs.bindings.length !== input.facts.length) issue('BINDING_LEDGER_INCOMPLETE', 'bindings', 'Every input fact needs one disposition');
  for (const binding of reqs.bindings) {
    const fact = input.facts.find(x => x.id === binding.fact_id);
    if (!fact || binding.scope_id !== fact.scope_id || JSON.stringify(sorted(binding.module_ids)) !== JSON.stringify(sorted(bound.get(binding.fact_id) ?? []))
      || (binding.status === 'BOUND') !== bound.has(binding.fact_id)) issue('BINDING_LEDGER_MISMATCH', binding.fact_id, 'Fact disposition does not match plan');
  }
  return { success: !diagnostics.length, diagnostics };
}
