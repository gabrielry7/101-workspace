import {observeExperience,auditExperience} from './experience-audit.ts';
import {richExperiencePages} from './rich-experience-contracts.ts';
import {inputSha256} from '../upstream/v1/protocol.ts';
export function observeRichExperience(){const o=observeExperience(),root=document.querySelector<HTMLElement>('.rich-experience')!;
 return {...o,editorial_sha256:root.dataset.editorialSha256,feedback_sha256:root.dataset.feedbackSha256,
  editorials:[...root.querySelectorAll<HTMLElement>('[data-editorial-id]')].map(e=>({id:e.dataset.editorialId,text:e.querySelector('.journal-copy')?.textContent,slot:e.querySelector<HTMLElement>('[data-media-slot]')?.dataset.mediaSlot,src:e.querySelector<HTMLImageElement>('img')?.currentSrc.replace(location.origin,''),uses:e.querySelector<HTMLElement>('[data-media-usage]')?.dataset.mediaUsage?.split(' ')})),
  reviews:[...root.querySelectorAll<HTMLElement>('[data-demo-review]')].map(e=>({id:e.dataset.demoReview,quote:e.querySelector('blockquote')?.textContent,author:e.querySelector('.review-byline p')?.textContent,label:e.querySelector('.review-label')?.textContent})),
  review_disclosure:root.querySelector('[data-review-disclosure]')?.textContent,social_disclosure:root.querySelector('[data-social-disclosure]')?.textContent,contact_disclosure:root.querySelector('[data-contact-disclosure]')?.textContent,
  contact_email:root.querySelector('.contact-address')?.textContent,film_control:root.querySelector('[data-film-toggle]')?{label:root.querySelector('[data-film-toggle]')?.getAttribute('aria-label'),text:root.querySelector('[data-film-toggle]')?.textContent,title:root.querySelector('[data-film-toggle]')?.getAttribute('title')}:null,
  embeds:root.querySelectorAll('iframe,form,script[type="application/ld+json"]').length,
  social_placeholders:[...root.querySelectorAll('[data-social-placeholder]')].map(e=>e.textContent),social_controls:root.querySelectorAll('.social-links a,.social-links button,.social-links [role="link"],.social-links [tabindex]').length,
 };
}
export function auditRichExperience(o:any,lab:any){const result=auditExperience(o,lab,{pages:richExperiencePages}),codes=[...result.codes],home=o.page==='home',journal=home||o.page==='journal',reviews=home||o.page==='reviews',contact=home||o.page==='contact';
 if(o.editorial_sha256!==lab.site.editorial_sha256||o.feedback_sha256!==lab.site.feedback_sha256)codes.push('RICH_EDITORIAL_CONTEXT_CHANGED');
 const expectedPosts=journal?lab.community.posts:[],expectedReviews=reviews?lab.community.reviews.slice(0,home?2:3):[];
 if(o.editorials.length!==expectedPosts.length||expectedPosts.some((p:any)=>!o.editorials.some((e:any)=>e.id===p.id&&e.text.includes(p.title)&&e.text.includes(p.caption)))||journal&&!o.social_disclosure?.includes('No son publicaciones de Instagram'))codes.push('RICH_EDITORIAL_CONTENT_INVALID');
 for(const post of expectedPosts){const e=o.editorials.find((e:any)=>e.id===post.id),uses=lab.experience_media.review.usages.filter((u:any)=>u.page===new URL(o.url).pathname&&u.need_id===`b3-need:journal-${post.slot}`),asset=lab.experience_media.review.assets.find((a:any)=>a.uri===e?.src);if(!e||e.slot!==`journal-${post.slot}`||!asset||!uses.some((u:any)=>u.asset_id===asset.id)||inputSha256([...(e.uses??[])].sort())!==inputSha256(uses.map((u:any)=>u.id).sort()))codes.push('RICH_EDITORIAL_MEDIA_MISMATCH');}
 if(inputSha256(o.reviews)!==inputSha256(expectedReviews.map((r:any)=>({id:r.id,quote:r.quote,author:r.author,label:r.label})))||reviews&&!o.review_disclosure?.includes('textos ficticios'))codes.push('RICH_REVIEW_REPRESENTATION_INVALID');
 if(contact&&(!o.contact_disclosure?.includes('sin perfiles reales')||o.social_controls!==0||o.social_placeholders?.length!==2)||o.page==='contact'&&o.contact_email!==lab.community.contact.email||o.embeds||o.links.some((l:any)=>/^(mailto:|tel:|whatsapp:|https?:\/\/(www\.)?(instagram\.|facebook\.|wa\.me|api\.whatsapp\.))/i.test(l.href??'')))codes.push('RICH_CONTACT_OR_EXTERNAL_CLAIM_INVALID');
 if(home&&(!o.film_control?.label||!o.film_control.title||/Pausar|Reproducir/.test(o.film_control.text??'')))codes.push('RICH_MOTION_CONTROL_INVALID');
 return {success:!codes.length,codes:[...new Set(codes)]};
}
