import { mkdir, writeFile } from 'node:fs/promises';
import { z } from 'zod';
import { contracts } from '../src/contracts/v1/schemas.ts';
import { CategoryRecordV1, MappingRegistryV1, TaxonomyObservationV1, ActivityRelationshipV1, CandidateCapabilityV1 } from '../src/taxonomy/contracts.ts';
import { UpstreamEnvelopeV1 } from '../src/upstream/v1/protocol.ts';
import { CapabilitySpecV1, CapabilityRegistryV1, SiteRequirementsV1 } from '../src/planner/contracts.ts';
import { mediaContracts } from '../src/media/contracts.ts';
import { designContracts, designContractsV1_1 } from '../src/design/contracts.ts';
import { lockContracts } from '../src/lock/contracts.ts';
import { auditContracts } from '../src/audit/contracts.ts';
import { contextContracts } from '../src/taxonomy/context-contracts.ts';
import { requirementContracts } from '../src/requirements/contracts.ts';
import { HumanReviewCatalogV1, ReviewFeatureV1 } from '../src/requirements/review-contracts.ts';
import {libraryContracts} from '../src/media/library-contracts.ts';
import {ReferenceCorpusV1} from '../src/media/reference-corpus.ts';
import {FictionalMediaPackageV1} from '../src/media/demo-contracts.ts';
import {contextualContracts,ContextualPresentationV1,ReferenceCompositionV1} from '../src/design/contextual-contracts.ts';
import {ContextualMediaReviewV1} from '../src/media/contextual-review.ts';
import {ExperienceV1} from '../src/design/experience-contracts.ts';
import {ExperienceMediaReviewV1} from '../src/media/experience-review.ts';
import {RichExperienceV1,DemoCommunityV1,HumanDesignFeedbackV1} from '../src/design/rich-experience-contracts.ts';
import {RichExperienceMediaV1} from '../src/media/rich-experience-review.ts';
import {DepthExperienceV1,DesignIterationFeedbackV1,ExperienceFeaturesV1,ReferenceDepthResearchV1} from '../src/design/depth-experience-contracts.ts';

for(const [name,schema] of Object.entries({DepthExperienceV1,DesignIterationFeedbackV1,ExperienceFeaturesV1,ReferenceDepthResearchV1})){const folder=new URL('../contracts/design/experience-v1.2/',import.meta.url);await mkdir(folder,{recursive:true});await writeFile(new URL(`${name}.schema.json`,folder),JSON.stringify({...z.toJSONSchema(schema,{target:'draft-2020-12'}),$id:`urn:unocerouno:contracts:${name}:${name==='DepthExperienceV1'?'1.2.0':'1.0.0'}`,title:name,description:'Associated B3 iteration after human rejection; reference observations, fictional presentation and evidence bindings. No aesthetic approval, rights grant, backend or training.'},null,2)+'\n');}

for(const [name,schema,group,version] of [['RichExperienceV1',RichExperienceV1,'design/experience-v1.1','1.1.0'],['DemoCommunityV1',DemoCommunityV1,'design/experience-v1.1','1.0.0'],['HumanDesignFeedbackV1',HumanDesignFeedbackV1,'design/experience-v1.1','1.0.0'],['RichExperienceMediaV1',RichExperienceMediaV1,'media/experience-v1.1','1.1.0']] as const){const folder=new URL(`../contracts/${group}/`,import.meta.url);await mkdir(folder,{recursive:true});await writeFile(new URL(`${name}.schema.json`,folder),JSON.stringify({...z.toJSONSchema(schema,{target:'draft-2020-12'}),$id:`urn:unocerouno:contracts:${name}:${version}`,title:name,description:'Associated B3 human feedback and fictional editorial scope; not final approval or a live social/review integration.'},null,2)+'\n');}

const referenceDirectory=new URL('../contracts/design/reference-application-v1/',import.meta.url);
await mkdir(referenceDirectory,{recursive:true});
await writeFile(new URL('ReferenceCompositionV1.schema.json',referenceDirectory),JSON.stringify({...z.toJSONSchema(ReferenceCompositionV1,{target:'draft-2020-12'}),$id:'urn:unocerouno:contracts:ReferenceCompositionV1:1.0.0',title:'ReferenceCompositionV1'},null,2)+'\n');
const directory = new URL('../contracts/v1/', import.meta.url);
for(const [name,schema,group] of [['ExperienceV1',ExperienceV1,'design/experience-v1'],['ExperienceMediaReviewV1',ExperienceMediaReviewV1,'media/experience-v1']] as const){const folder=new URL(`../contracts/${group}/`,import.meta.url);await mkdir(folder,{recursive:true});await writeFile(new URL(`${name}.schema.json`,folder),JSON.stringify({...z.toJSONSchema(schema,{target:'draft-2020-12'}),$id:`urn:unocerouno:contracts:${name}:1.0.0`,title:name,description:'B3 associated multipage/background/credits revision; no operational backend or human aesthetic approval. Current byte and rights gates required.'},null,2)+'\n');}
await mkdir(directory, { recursive: true });
for (const [name, schema] of Object.entries(contracts)) {
  const json = z.toJSONSchema(schema, { target: 'draft-2020-12' });
  await writeFile(new URL(`${name}.schema.json`, directory), JSON.stringify({
    ...json, $id: `urn:unocerouno:contracts:${name}:1.0.0`,
    title: name, description: 'H0 candidate contract; semantic validation is required in addition to JSON Schema.',
  }, null, 2) + '\n');
  console.log(`Exported ${name}`);
}

// Associated V2 expansion; historical V1 schemas and renderer stay byte-stable.
for(const [group,version,schemas] of [['design/contextual-v2','2.0.0',contextualContracts],['design/presentation-v1','1.0.0',{ContextualPresentationV1}],['media/contextual-v1','1.0.0',{ContextualMediaReviewV1}]] as const){
 const folder=new URL(`../contracts/${group}/`,import.meta.url);await mkdir(folder,{recursive:true});
 for(const [name,schema] of Object.entries(schemas))await writeFile(new URL(`${name}.schema.json`,folder),JSON.stringify({...z.toJSONSchema(schema,{target:'draft-2020-12'}),$id:`urn:unocerouno:contracts:${name}:${version}`,title:name,description:'B3 associated contextual local-lab grammar/review; semantic, byte and current-use gates required. No human approval or commercial integration.'},null,2)+'\n');
}

for (const [group, schemas] of Object.entries({
  'taxonomy/v1': { CategoryRecordV1, MappingRegistryV1, TaxonomyObservationV1, ActivityRelationshipV1, CandidateCapabilityV1 },
  'upstream/v1': { UpstreamEnvelopeV1 },
  'planner/v1': { CapabilitySpecV1, CapabilityRegistryV1, SiteRequirementsV1 },
  'media/v1': mediaContracts,
  'design/v1': designContracts,
  'design/v1.1': designContractsV1_1,
  'audit/v1': auditContracts,
  'lock/v1': lockContracts,
  'taxonomy/context-v1': contextContracts,
  'requirements/v1': requirementContracts,
  'requirements/review-v1': {HumanReviewCatalogV1,ReviewFeatureV1},
  'media/library-v1': {...libraryContracts,ReferenceCorpusV1,FictionalMediaPackageV1},
})) {
  const folder = new URL(`../contracts/${group}/`, import.meta.url);
  await mkdir(folder, { recursive: true });
  for (const [name, schema] of Object.entries(schemas)) {
    await writeFile(new URL(`${name}.schema.json`, folder), JSON.stringify({
      ...z.toJSONSchema(schema, { target: 'draft-2020-12' }),
      $id: `urn:unocerouno:contracts:${name}:${group === 'design/v1.1' ? '1.1.0' : '1.0.0'}`, title: name,
      description: group === 'media/library-v1' ? 'B2 associated byte-pinned media library and reference corpus; semantic, source, scope and current-use verification required. No rights conferred by fixture flags or reference URLs.' : group === 'requirements/review-v1' ? 'B1 proposed human review supplement; partial V1 references, no business evaluation, commercial frontend or operational support. Semantic validation required.' : group === 'requirements/v1' ? 'B1 associated master catalogue/objective diagnostic; complete V1 registry, no live integrations or fabricated permissions.' : group === 'taxonomy/context-v1' ? 'B1 associated activity interpretation; exact references/scopes and semantic verification required, not operational confirmation.' : group === 'lock/v1' ? 'H8 technical laboratory design lock; exact source/toolchain and rights checks, no human approval or production readiness.' : group === 'design/v1.1' ? 'H7 media-free art direction extension; explicit typography-only materiality, no media permission or production readiness.' : group === 'audit/v1' ? 'H6 laboratory audit/mutation/preference contract; hard gates and evidence required. No production approval or manufactured human votes.' : group === 'design/v1' ? 'H5 lab declarative design contract; semantic bindings, rights and budget checks required. No arbitrary code or production readiness.' : group === 'media/v1' ? 'H3 media contract; deterministic rights and suitability checks required; no rights conferred by URLs.' : group === 'planner/v1' ? 'H2 semantic contract; no visual representation or operational integration.' : 'H1 candidate protocol; semantic checks required. No upstream integration.',
    }, null, 2) + '\n');
    console.log(`Exported ${name}`);
  }
}
