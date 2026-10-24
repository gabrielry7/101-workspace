import {readFile} from 'node:fs/promises';
import {loadB3Experience} from './load-b3-experience.ts';
import {loadRichExperienceMedia} from '../src/media/rich-experience-review.ts';
import {RichExperienceV1,DemoCommunityV1,HumanDesignFeedbackV1,richExperiencePages} from '../src/design/rich-experience-contracts.ts';
import {experienceRoute} from '../src/design/experience-contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const read=async(p:string)=>JSON.parse(await readFile(p,'utf8'));
export async function loadB3RichExperience(){const base=await loadB3Experience(),media=await loadRichExperienceMedia(),site=RichExperienceV1.parse(await read('data/design/experience-v1.1/site.json')),community=DemoCommunityV1.parse(await read('data/design/experience-v1.1/community.json')),feedback=HumanDesignFeedbackV1.parse(await read('data/design/experience-v1.1/human-feedback.json'));
 if(site.editorial_sha256!==inputSha256(community)||site.feedback_sha256!==inputSha256(feedback)||site.source_context_sha256!==base.context_sha256||site.content_sha256!==base.scenario.content.content_sha256||site.plan_sha256!==base.scenario.content.plan_sha256||site.research_sha256!==base.site.research_sha256||site.media_review_sha256!==media.review.review_sha256||new Set(site.profiles.map(p=>p.id)).size!==4||new Set(site.profiles.map(p=>p.hero)).size!==4||site.profiles.some(p=>p.root!==`/b3/${p.id}/`))throw Error('RICH_CONTEXT_INVALID');
 if(inputSha256(site.profiles.flatMap(p=>richExperiencePages.map(page=>experienceRoute(p.root,page as any))))!==inputSha256(media.review.routes))throw Error('RICH_ROUTES_INVALID');
 return {...base,site,site_sha256:inputSha256(site),experience_media:media,community,feedback};
}
