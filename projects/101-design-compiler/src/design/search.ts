import { SearchBudgetV1, type ArtDirection, type DesignPlan, type SearchBudget } from './contracts.ts';
import type { GeneralCompositionLab as CompositionLab } from '../composition/lab.ts';
import { inputSha256 } from '../upstream/v1/protocol.ts';
import { contextHash,validateDirection,validateDesign,structuralDistance } from './validate.ts';
export { designContext,contextHash,validateDirection,validateDesign,structuralDistance,structuralSignature,designPreviewPath } from './validate.ts';
// Seeded local PRNG; output artifacts, not seed alone, are preserved. Priors are heuristics, not learned probabilities.
function rng(seed: number) { let state = seed >>> 0; return () => { state = (Math.imul(1664525, state) + 1013904223) >>> 0; return state / 4294967296; }; }
export function searchDesigns(raw: unknown, lab: CompositionLab, rawBudget: SearchBudget, seed: number) {
  const budget = SearchBudgetV1.parse(rawBudget);
  if (!Number.isInteger(seed) || seed < 0 || seed > 4294967295) throw new Error('INVALID_SEARCH_SEED');
  const serialized = JSON.stringify(raw);
  if (!serialized || Buffer.byteLength(serialized, 'utf8') > budget.max_output_bytes) throw new Error('PROPOSAL_BYTES_BUDGET');
  if (!Array.isArray(raw) || raw.length > budget.proposals) throw new Error('PROPOSAL_COUNT_BUDGET');
  const rejections: { stage: string; id: string; codes: string[] }[] = [];
  const directions: ArtDirection[] = [];
  for (let i = 0; i < raw.length; i++) {
    const checked = validateDirection(raw[i], lab);
    if (!checked.success || !checked.direction) rejections.push({ stage: 'proposal', id: `input-${i}`, codes: checked.codes });
    else if (directions.some(d => d.id === checked.direction!.id)) rejections.push({ stage: 'proposal', id: checked.direction.id, codes: ['DUPLICATE_DIRECTION'] });
    else directions.push(checked.direction);
  }
  const random = rng(seed), candidates: DesignPlan[] = [], attempts: unknown[] = [];
  const hasMedia = lab.content.pages.some(p => p.path === lab.media?.usage.page);
  const dense = lab.content.pages.some(p => p.modules.length > 3 || p.modules.some(m => m.offerings.length > 8));
  const seen = new Set<string>();
  for (let i = 0; i < budget.samples && directions.length; i++) {
    const d = directions[i % directions.length]!;
    // Coherent whole-page topology from a direction, conditioned on available medium and content density.
    const weights = d.topologies.map(t => t.stage === 'Split' ? (!hasMedia ? 0 : dense ? 1 : 2) : dense ? 3 : 2);
    const total = weights.reduce<number>((a, b) => a + b, 0);
    if (!total) { rejections.push({stage:'sampling',id:d.id,codes:['NO_CONTEXTUAL_TOPOLOGY']}); continue; }
    let draw = random() * total, index = weights.length - 1;
    for (let j = 0; j < weights.length; j++) { draw -= weights[j]!; if (draw < 0) { index = j; break; } }
    const topology = d.topologies[index]!;
    const plan: DesignPlan = { schema_version:'1.0.0', id:`candidate-${String(i+1).padStart(2,'0')}`, art_direction_id:d.id,
      site_plan_id:lab.content.site_plan_id, plan_sha256:lab.content.plan_sha256, content_sha256:lab.content.content_sha256,
      manifest_sha256:lab.manifest_sha256, context_sha256:contextHash(lab), registry_version:'h5-lab-1.0.0', tokens:d.tokens, motion:'quiet',
      pages:lab.content.pages.map(p=>({path:p.path,composition:{operator:topology.frame,navigation:'before-content',
        child:{operator:topology.stage,module_refs:p.modules.map(m=>m.id),media_usage_refs:p.path===lab.media?.usage.page?[lab.media.usage.id]:[]}}})) };
    const checked = validateDesign(plan, lab, d);
    const key = inputSha256({ ...plan, id: 'deduplicated' });
    const estimate = { nodes: plan.pages.reduce((n,p)=>n+2+p.composition.child.module_refs.length+p.composition.child.media_usage_refs.length,0),
      client_js_bytes: 0, media_dimensions: [lab.media?.asset.inspection.width ?? null, lab.media?.asset.inspection.height ?? null], dense, has_media: hasMedia, weights,
      geometry: [360,768,801,1280].map(width=>{
        const stacked=width<=800;
        const contentWidth=width-80-(topology.frame==='Rail'&&!stacked?208:0);
        const textWidth=topology.stage==='Split'&&!stacked?(contentWidth-32)/2.1:contentWidth;
        return {viewport:width,reflow:stacked?'stack':'desktop',estimated_text_width:textWidth,min_text_width:180};
      }), estimate_status:'REGISTRY_HEURISTIC_NOT_BROWSER_MEASUREMENT' };
    const codes = checked.codes;
    if (estimate.nodes > 500) codes.push('COMPLEXITY_PREFILTER');
    if (estimate.geometry.some(g=>g.estimated_text_width<g.min_text_width)) codes.push('GEOMETRY_PREFILTER');
    if (seen.has(key)) codes.push('DUPLICATE_CANDIDATE');
    attempts.push({ id:plan.id, direction_id:d.id, topology, estimate, status:codes.length?'REJECTED':'PREFILTER_PASSED', codes });
    if (codes.length) rejections.push({stage:'prefilter',id:plan.id,codes}); else { seen.add(key); candidates.push(plan); }
  }
  // Farthest-first structural selection. Cosmetic/token differences cannot create a finalist slot.
  const selected: DesignPlan[] = [];
  const pool = [...candidates];
  while (pool.length && selected.length < Math.min(budget.renders,budget.finalists)) {
    pool.sort((a,b)=>{
      const score=(p:DesignPlan)=>selected.length?Math.min(...selected.map(s=>structuralDistance(p,s))):0;
      return score(b)-score(a)||a.id.localeCompare(b.id);
    });
    const best = pool.shift()!;
    if (!selected.length || selected.every(s=>structuralDistance(best,s)>0)) selected.push(best);
  }
  return { schema_version:'1.0.0', status:selected.length?'FINALISTS_READY_FOR_BROWSER':'NO_ACCEPTABLE_DESIGN',
    context_sha256:contextHash(lab), seed, budget, priors:'CONTEXTUAL_HEURISTICS_NOT_CALIBRATED',
    directions, attempts, candidates, finalists:selected, rejections,
    usage:{ proposals:raw.length, sample_attempts:attempts.length, render_slots:selected.length, actual_provider_calls:0,
      tokens:null, llm_cost:null, new_spend:0, human_preference:'NOT_COLLECTED' },
    diversity:selected.map((a,i)=>selected.slice(i+1).map(b=>({a:a.id,b:b.id,distance:structuralDistance(a,b)}))).flat(),
  };
}
