import {readFile} from 'node:fs/promises';
import {loadContextualScenario,validateContextualPlan,validateContextualPresentation} from '../src/design/contextual.ts';
import {loadContextualMedia} from '../src/media/contextual-review.ts';
import {ArtDirectionV2,ContextualDesignPlanV2} from '../src/design/contextual-contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {validateReferenceApplication} from '../src/design/reference-application.ts';
export async function loadB3Lab(options:{evaluation_time?:string}={}){const scenario=await loadContextualScenario(),media=await loadContextualMedia(process.cwd(),options.evaluation_time);
 const context=JSON.parse(await readFile('data/design/contextual-v2/context.json','utf8')),context_sha256=inputSha256(context);
 const presentation=validateContextualPresentation(JSON.parse(await readFile('fixtures/corrections/b3/presentation.json','utf8')),scenario);
 if(inputSha256(presentation)!==inputSha256(context.presentation))throw Error('B3_PRESENTATION_CONTENT_CHANGED');
 const proposals=ArtDirectionV2.array().parse(JSON.parse(await readFile('data/design/contextual-v2/proposals.json','utf8'))),designs=ContextualDesignPlanV2.array().parse(JSON.parse(await readFile('data/design/contextual-v2/finalists.json','utf8')));
 for(const d of designs)if(!validateContextualPlan(d,scenario,context_sha256,media.review.review_sha256).success||!proposals.some(p=>p.id===d.art_direction_id&&p.context_sha256===context_sha256))throw Error('B3_RENDER_CONTEXT_INVALID');
 const research=JSON.parse(await readFile('data/reference/design/visual-review-2026-10-15.json','utf8'));
 const application=validateReferenceApplication(JSON.parse(await readFile('data/design/reference-application-v1/compositions.json','utf8')),context,research,designs,media.review);
 return {scenario,media,context_sha256,proposals,designs,presentation,application,application_sha256:inputSha256(application)};}
