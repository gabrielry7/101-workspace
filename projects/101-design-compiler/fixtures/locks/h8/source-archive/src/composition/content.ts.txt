import type { FixtureBundle, SitePlan } from '../contracts/v1/schemas.ts';
import type { SiteRequirements } from '../planner/contracts.ts';
import { validateSemanticPlan } from '../planner/validate.ts';
import { offeringFactIds } from '../planner/content.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
import { componentRegistry } from './registry.ts';

export type BoundFact = { id: string; scope_id: string; kind: string; text: string };
export type ModuleView = {
  id: string; capability_id: string; scope_id: string; required: boolean; page: string;
  component: 'Identity' | 'OfferingCollection' | 'FactCollection' | 'Schedule'; facts: BoundFact[];
  offerings: { id: string; scope_id: string; facts: BoundFact[] }[];
};
// A projection of approved bindings, never a second business model or sector template.
export function projectContent(bundle: FixtureBundle, requirements: SiteRequirements) {
  const check = validateSemanticPlan(bundle, requirements);
  if (!check.success) throw new Error(`COMPOSITION_SEMANTIC_INVALID:${JSON.stringify(check.diagnostics)}`);
  function fact(id: string): BoundFact {
    const f = bundle.input.facts.find(f => f.id === id);
    if (!f || f.publication !== 'APPROVED' || typeof f.value !== 'string') throw new Error(`UNSUPPORTED_DISPLAY_FACT:${id}`);
    return { id: f.id, scope_id: f.scope_id, kind: f.kind, text: f.value };
  }
  const pages = bundle.plan.pages.map(page => ({ path: page.path, modules: page.modules.map((m): ModuleView => {
    const req = requirements.requirements.find(r => r.id === m.id);
    const key = req?.semantic_module as keyof typeof componentRegistry;
    const registration = componentRegistry[key];
    if (!registration || m.presentation !== 'STATIC_PUBLIC_INFORMATION' || m.action_destination_id) throw new Error(`UNSUPPORTED_LAB_MODULE:${m.id}`);
    return { id: m.id, capability_id: m.capability_id, scope_id: m.scope_id, required: m.required, page: page.path,
      component: registration.component, facts: m.fact_ids.map(fact),
      offerings: m.offering_ids.map(id => {
        const o = bundle.input.offerings.find(o => o.id === id);
        if (!o) throw new Error(`MISSING_OFFERING:${id}`);
        const ids = [o.name_fact_id, ...offeringFactIds(o).filter(id => id !== o.name_fact_id)];
        return { id: o.id, scope_id: o.scope_id, facts: ids.map(fact) };
      }) };
  }) }));
  const bound = pages.flatMap(p => p.modules.flatMap(m => [...m.facts, ...m.offerings.flatMap(o => o.facts)].map(f => `${m.id}:${f.id}:${f.scope_id}`)));
  const expected = requirements.bindings.filter(b => b.status === 'BOUND').flatMap(b => b.module_ids.map(id => `${id}:${b.fact_id}:${b.scope_id}`));
  if (JSON.stringify([...bound].sort()) !== JSON.stringify([...expected].sort())) throw new Error('COMPOSITION_BINDINGS_LOST');
  return { site_plan_id: bundle.plan.id, plan_sha256: inputSha256(bundle.plan), requirements_sha256: inputSha256(requirements),
    content_sha256: inputSha256(pages), pages, bindings: requirements.bindings,
    diagnostics: requirements.omissions, exclusions: bundle.plan.excluded_capabilities,
    restrictions: [...new Set([...bundle.input.restrictions, ...bundle.profile.restrictions])],
  };
}
export type ContentProjection = ReturnType<typeof projectContent>;
export type SemanticPage = SitePlan['pages'][number];
