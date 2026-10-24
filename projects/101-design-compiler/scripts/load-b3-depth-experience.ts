import {readFile} from 'node:fs/promises';
import {loadB3RichExperience} from './load-b3-rich-experience.ts';
import {DepthExperienceV1,DesignIterationFeedbackV1,ExperienceFeaturesV1,ReferenceDepthResearchV1} from '../src/design/depth-experience-contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {byteSha256} from '../src/media/package.ts';
import {validateReferenceDepth} from '../src/design/reference-depth-validation.ts';
const read=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
export async function loadB3DepthExperience(){
 const base=await loadB3RichExperience(),site=DepthExperienceV1.parse(await read('data/design/experience-v1.2/site.json')),features=ExperienceFeaturesV1.parse(await read('data/design/experience-v1.2/features.json')),revision_feedback=DesignIterationFeedbackV1.parse(await read('data/design/experience-v1.2/human-feedback.json')),research=ReferenceDepthResearchV1.parse(await read('data/reference/design/reference-depth-20261021.json'));
 for(const k of ['source_context_sha256','content_sha256','plan_sha256','media_review_sha256','research_sha256','editorial_sha256','feedback_sha256'] as const)if(site[k]!==base.site[k])throw Error('DEPTH_BASE_CONTEXT_CHANGED');
 if(site.features_sha256!==inputSha256(features)||site.revision_feedback_sha256!==inputSha256(revision_feedback)||site.depth_research_sha256!==inputSha256(research)||research.observations_sha256!==byteSha256(await readFile(research.observations_path))||research.prior_research_sha256!==base.site.research_sha256)throw Error('DEPTH_CONTEXT_INVALID');
 validateReferenceDepth(research,await read('data/reference/design/visual-review-2026-10-15.json'));
 if(new Set(features.reads.map(r=>r.post_id)).size!==4||features.reads.some(r=>!base.community.posts.some(p=>p.id===r.post_id))||new Set(features.directory.map(d=>d.page_kind)).size!==4)throw Error('DEPTH_FEATURE_BINDING_INVALID');
 if(new Set(site.profiles.map(p=>p.id)).size!==4||new Set(site.profiles.map(p=>p.hero)).size!==4||site.profiles.some(p=>p.root!==`/b3/${p.id}/`))throw Error('DEPTH_PROFILES_INVALID');
 for(let i=0;i<2;i++)for(const k of ['hero','palette','type','collection','home_composition'] as const)if(site.profiles[i]![k]!==base.site.profiles[i]![k])throw Error('DEPTH_LIKED_DIRECTION_CHANGED');
 return {...base,site,site_sha256:inputSha256(site),features,revision_feedback,research};
}
