import {readFile} from 'node:fs/promises';
import {loadB3Lab} from './load-b3-lab.ts';
import {loadExperienceMedia} from '../src/media/experience-review.ts';
import {ExperienceV1,experiencePages,experienceRoute} from '../src/design/experience-contracts.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
export async function loadB3Experience(){const base=await loadB3Lab(),media=await loadExperienceMedia(),site=ExperienceV1.parse(JSON.parse(await readFile('data/design/experience-v1/site.json','utf8'))),research=JSON.parse(await readFile('data/reference/design/visual-review-2026-10-15.json','utf8'));
 if(site.source_context_sha256!==base.context_sha256||site.content_sha256!==base.scenario.content.content_sha256||site.plan_sha256!==base.scenario.content.plan_sha256||site.media_review_sha256!==media.review.review_sha256||site.research_sha256!==inputSha256(research)||new Set(site.profiles.map(p=>p.id)).size!==4||new Set(site.profiles.map(p=>p.hero)).size!==4||site.profiles.some(p=>p.root!==`/b3/${p.id}/`||p.references.some(id=>!research.references.some((r:any)=>r.id===id))))throw Error('EXPERIENCE_CONTEXT_OR_DIVERSITY_INVALID');
 const routes=site.profiles.flatMap(p=>experiencePages.map(page=>experienceRoute(p.root,page)));if(inputSha256(routes)!==inputSha256(media.review.routes))throw Error('EXPERIENCE_MEDIA_ROUTE_COVERAGE_INVALID');
 return {...base,site,experience_media:media,site_sha256:inputSha256(site)};
}
