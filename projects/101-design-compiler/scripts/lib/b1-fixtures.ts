import {readFile,readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {z} from 'zod';
import {BusinessInputV1} from '../../src/contracts/v1/schemas.ts';
import {ContextualActivityLinkV1} from '../../src/taxonomy/context-contracts.ts';
import {FunctionalObjectiveDecisionV1} from '../../src/requirements/contracts.ts';
import {ActivityRelationshipV1,TaxonomyObservationV1} from '../../src/taxonomy/contracts.ts';
export const B1FixtureV1=z.strictObject({scenario:z.string().regex(/^[a-z0-9-]+$/),label:z.string().min(1),
 expected_context_status:z.enum(['RESOLVED','HYBRID','MULTISCOPE','AMBIGUOUS','CONFLICTED','UNKNOWN','NON_BUSINESS']),
 expected_planner_status:z.enum(['READY','CONTENT_BLOCKED']),input:BusinessInputV1,
 activity_links:z.array(ContextualActivityLinkV1),activity_relationships:z.array(ActivityRelationshipV1),category_context:z.array(TaxonomyObservationV1),
 objective_decisions:z.array(FunctionalObjectiveDecisionV1)});
export type B1Fixture=z.infer<typeof B1FixtureV1>;
export async function loadB1Fixtures() {
 const folder=resolve('fixtures/corrections/b1'),names=(await readdir(folder)).filter(n=>n.endsWith('.json')).sort();
 const fixtures=await Promise.all(names.map(async name=>B1FixtureV1.parse(JSON.parse(await readFile(resolve(folder,name),'utf8')))));
 if(new Set(fixtures.map(f=>f.scenario)).size!==fixtures.length||fixtures.some(f=>f.input.data_mode!=='SYNTHETIC_FIXTURE'))throw Error('B1_FIXTURE_PROVENANCE_INVALID');
 return fixtures;
}
