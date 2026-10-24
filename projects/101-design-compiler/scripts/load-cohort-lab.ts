import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { MappingRegistryV1 } from '../src/taxonomy/contracts.ts';
import { validateRegistry } from '../src/taxonomy/resolve.ts';
import { planBusiness } from '../src/planner/plan.ts';
import { projectContent } from '../src/composition/content.ts';
import { buildMediaManifest, inventoryMedia, proposeUsage } from '../src/media/plan.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
import { contextHash, designContext, searchDesigns } from '../src/design/search.ts';
import type { GeneralCompositionLab } from '../src/composition/lab.ts';
export const cohortBudget={proposals:2,samples:12,renders:2,finalists:2,max_output_bytes:24000,new_provider_calls:0,new_spend:0} as const;
export async function loadCohortLab(proposals=false){
 const reservation=JSON.parse(await readFile('fixtures/cohort/h7/reservation.json','utf8'));
 const registry=MappingRegistryV1.parse(JSON.parse(await readFile('taxonomy/v1/mappings.json','utf8')));validateRegistry(registry.rules);const cases=[];
 for(const file of reservation.files){
  const bytes=await readFile(file.path);if(createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('COHORT_HASH_MISMATCH');
  const fixture=JSON.parse(bytes.toString('utf8'));const result=planBusiness(fixture.input,{rules:registry.rules,activity_relationships:fixture.activity_relationships});
  if(result.status!=='READY'){cases.push({scenario:fixture.scenario,input_sha256:file.sha256,result,lab:null,media:null,search:null});continue;}
  const bundle={input:result.input,profile:result.profile,capabilities:result.capabilities,plan:result.plan};
  const context={client_id:`synthetic-h7-${fixture.scenario}`,project_id:`h7-cohort-${fixture.scenario}`,evaluated_at:'2026-10-08T00:00:00Z'};
  const assets=inventoryMedia(result.input);let media=buildMediaManifest(bundle,result.requirements,{assets,grants:[],usages:[]},context);
  // Preserve and explicitly reject attempted use of UNKNOWN inventory; never fetch its URI.
  if(assets.length&&media.manifest.needs.length){const need=media.manifest.needs[0]!;const usage=proposeUsage(need,assets[0]!,{...context,business_id:result.input.business_id},null);media=buildMediaManifest(bundle,result.requirements,{assets,grants:[],usages:[usage]},context);if(media.manifest.decisions.some(d=>d.status==='ALLOWED'))throw Error('UNKNOWN_RIGHTS_ALLOWED');}
  const lab:GeneralCompositionLab={content:projectContent(bundle,result.requirements),media:null,gaps:media.brief.gaps,constraints:media.brief.constraints,manifest_sha256:inputSha256(media.manifest),...context};
  let search=null;
  if(proposals){const dir=`fixtures/cohort/h7/proposals/${fixture.scenario}`;const output=JSON.parse(await readFile(`${dir}/output.json`,'utf8'));const provenance=JSON.parse(await readFile(`${dir}/provenance.json`,'utf8'));const prompt=JSON.parse(await readFile(`${dir}/prompt.json`,'utf8'));const savedContext=JSON.parse(await readFile(`${dir}/context.json`,'utf8'));if(provenance.context_sha256!==contextHash(lab)||provenance.output_sha256!==inputSha256(output)||provenance.prompt_sha256!==inputSha256(prompt)||inputSha256(savedContext)!==contextHash(lab)||inputSha256(prompt.context)!==inputSha256(designContext(lab)))throw Error('COHORT_PROVENANCE_MISMATCH');search=searchDesigns(output,lab,cohortBudget,1010708);}
  cases.push({scenario:fixture.scenario,input_sha256:file.sha256,result,lab,media,search});
 }
 return {reservation,cases,budget:cohortBudget};
}
export type CohortLab=Awaited<ReturnType<typeof loadCohortLab>>;
export function cohortPath(scenario:string,id:string,page:string){if(!/^[a-z0-9-]+$/.test(scenario)||!/^[a-z0-9-]+$/.test(id)||!/^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/.test(page))throw Error('INVALID_COHORT_ROUTE');return `/h7/${scenario}-${id}${page==='/'?'/':`${page}/`}`;}
