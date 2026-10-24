import {observeRichExperience,auditRichExperience} from './rich-experience-audit.ts';
import {richExperiencePages} from './rich-experience-contracts.ts';
import {experienceRoute} from './experience-contracts.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
export function observeDepthExperience(){const o=observeRichExperience(),root=document.querySelector<HTMLElement>('.depth-experience')!;
 const rect=(e:Element)=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height};};
 return {...o,features_sha256:root.dataset.featuresSha256,revision_feedback_sha256:root.dataset.revisionFeedbackSha256,depth_research_sha256:root.dataset.depthResearchSha256,
  features:[...root.querySelectorAll<HTMLElement>('[data-feature]')].map(e=>({id:e.dataset.feature,text:e.textContent})),
  directory:[...root.querySelectorAll<HTMLAnchorElement>('[data-directory-kind]')].map(e=>({kind:e.dataset.directoryKind,href:e.getAttribute('href'),title:e.querySelector('h3')?.textContent,copy:e.querySelector('p')?.textContent})),
  readings:[...root.querySelectorAll<HTMLElement>('[data-read-id]')].map(e=>({id:e.dataset.readId,label:e.querySelector('.editorial-disclosure')?.textContent,body:[...e.querySelectorAll('[data-read-paragraph]')].map(p=>p.textContent)})),
  navigation:[...root.querySelectorAll<HTMLAnchorElement>('.navigation-groups a')].map(e=>e.getAttribute('href')),
  navigation_open:root.querySelector<HTMLDetailsElement>('[data-depth-nav]')?.open,
  journal_categories:[...root.querySelectorAll<HTMLOptionElement>('.journal-tools option')].map(e=>e.value),
  journal_layout:observeJournalReadingLayout(),
  layout:[...root.querySelectorAll<HTMLElement>('.experience-hero,.experience-overview,.community-heading,.journal-entry,.journal-entry .contextual-photo,.journal-copy,.community-reviews,.community-contact,.exp-header')].map(e=>({class:e.className,...rect(e)})),
  motion_preference:matchMedia('(prefers-reduced-motion:reduce)').matches,
 };
}
export function observeJournalReadingLayout(){const grid=document.querySelector<HTMLElement>('.depth-experience .journal-grid');if(!grid)return null;
 const rect=(e:Element)=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height};};
 return {state:grid.dataset.journalLayout,width:innerWidth,grid:rect(grid),visible:[...grid.querySelectorAll<HTMLElement>('[data-editorial-id]')].filter(e=>!e.hidden).map(e=>({id:e.dataset.editorialId,card:rect(e),copy:rect(e.querySelector('.journal-copy')!),image:rect(e.querySelector('.contextual-photo')!)}))};
}
export function auditDepthExperience(o:any,lab:any){const base=auditRichExperience(o,lab),codes=[...base.codes],home=o.page==='home',reading=home||o.page==='journal',root=lab.site.profiles.find((p:any)=>p.id===o.profile)?.root;
 if(o.features_sha256!==lab.site.features_sha256||o.revision_feedback_sha256!==lab.site.revision_feedback_sha256||o.depth_research_sha256!==lab.site.depth_research_sha256)codes.push('DEPTH_CONTEXT_CHANGED');
 const expected=richExperiencePages.filter(p=>['collection','request','selection','story','visit','faq','journal','reviews','contact'].includes(p.kind)).map(p=>experienceRoute(root,p as any)).sort();
 if(inputSha256([...(o.navigation??[])].sort())!==inputSha256(expected))codes.push('DEPTH_NAVIGATION_LOST');
 const directory=home?lab.features.directory.map((d:any)=>({kind:d.page_kind,href:experienceRoute(root,richExperiencePages.find(p=>p.kind===d.page_kind)! as any),title:d.title,copy:d.copy})):[];
 if(inputSha256(o.directory)!==inputSha256(directory))codes.push('DEPTH_DIRECTORY_LOST');
 const reads=reading?lab.features.reads.map((r:any)=>({id:r.post_id,label:r.label,body:r.body})):[];
 if(inputSha256(o.readings)!==inputSha256(reads))codes.push('DEPTH_READING_BINDING_LOST');
 const featureIds=home?['route-directory']:o.page==='visit'?['visit-preparation']:o.page==='request'?['groups-preview']:[];
 if(inputSha256(o.features?.map((f:any)=>f.id))!==inputSha256(featureIds)||home&&![lab.features.house.title,lab.features.house.copy].every(t=>o.features[0]?.text.includes(t))||o.page==='visit'&&!o.features[0]?.text.includes(lab.features.visit_prompt)||o.page==='request'&&!o.features[0]?.text.includes(lab.features.events_prompt))codes.push('DEPTH_FEATURE_CONTENT_LOST');
 if(o.page==='journal'&&(inputSha256(o.journal_categories)!==inputSha256(['',...lab.features.reads.map((r:any)=>r.category)])||o.journal_layout?.state!=='all'||o.journal_layout.visible.length!==4))codes.push('DEPTH_CATEGORIES_LOST');
 return {success:!codes.length,codes:[...new Set(codes)]};
}
export function auditFilteredJournal(o:any){const codes:string[]=[];if(o?.state!=='filtered'||o.visible?.length!==1)return {success:false,codes:['JOURNAL_FILTER_STATE_INVALID']};
 const item=o.visible[0],w=o.grid?.width;if(!w||item.card.width<w*.95||Math.abs(item.card.x-o.grid.x)>1||item.copy.width<w*(o.width>760?.35:.9)||item.image.width<=0)codes.push('JOURNAL_FILTER_READING_TOO_NARROW');
 return {success:!codes.length,codes};
}
