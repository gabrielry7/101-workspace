import { loadPlannerFixtures } from './load-planner-fixtures.ts';
import { loadMappingRegistry } from './load-taxonomy.ts';
import { planBusiness } from '../src/planner/plan.ts';
import { validateSemanticPlan } from '../src/planner/validate.ts';

export async function checkPlannerFixtures() {
  const registry = await loadMappingRegistry();
  const fixtures = await loadPlannerFixtures();
  return fixtures.map(fixture => {
    const result = planBusiness(fixture.input, { rules: registry.rules, activity_relationships: fixture.activity_relationships });
    const validation = result.status !== 'READY' ? { success: true, diagnostics: [] } : validateSemanticPlan({
      input: result.input, profile: result.profile, capabilities: result.capabilities, plan: result.plan,
    }, result.requirements);
    return { scenario: fixture.scenario, expected_status: fixture.expected_status,
      success: validation.success && result.status === fixture.expected_status, validation, result };
  });
}
