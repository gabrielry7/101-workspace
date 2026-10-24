import {inputSha256} from '../upstream/v1/protocol.ts';
import type {ContextualDesignPlan} from './contextual-contracts.ts';
import type {contextualMediaData} from '../media/contextual-review.ts';
export function observeContextual(){
 const root=document.querySelector<HTMLElement>('.contextual-site')!,all=<T extends Element=HTMLElement>(q:string,r:ParentNode=root)=>[...r.querySelectorAll<T>(q)];
 const rect=(e:Element)=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height};};
 const visible=(e:HTMLElement)=>{if(!e.getClientRects().length)return false;for(let a:HTMLElement|null=e;a;a=a.parentElement){const s=getComputedStyle(a);if(s.display==='none'||s.visibility==='hidden'||(a.tagName==='DETAILS'&&!(a as HTMLDetailsElement).open&&e!==a&&!a.querySelector('summary')?.contains(e)))return false;}return true;};
 function rgb(c:string){return c.match(/[\d.]+/g)?.map(Number)??[0,0,0];}function lum(c:number[]){const v=c.slice(0,3).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;});return .2126*v[0]!+.7152*v[1]!+.0722*v[2]!;}
 const readability=all<HTMLElement>('h1,h2,h3,p,a,summary,button,label,input,select,figcaption,small').filter(visible).map(e=>{const s=getComputedStyle(e);let a:HTMLElement|null=e,bg=[255,255,255];while(a){const c=rgb(getComputedStyle(a).backgroundColor);if(c.length===3||c[3]!==0){bg=c;break;}a=a.parentElement;}const l1=lum(rgb(s.color)),l2=lum(bg);return {tag:e.tagName,text:e.textContent?.trim().slice(0,60),font_px:parseFloat(s.fontSize),contrast:(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05)};});
 return {reference_application:root.dataset.referenceApplication,offering_media:all<HTMLElement>('[data-offering-id]').map(e=>({offering:e.dataset.offeringId,slot:e.querySelector<HTMLElement>('[data-media-slot]')?.dataset.mediaSlot,src:e.querySelector<HTMLImageElement>('img')?.currentSrc.replace(location.origin,''),usages:e.querySelector<HTMLElement>('[data-media-usage]')?.dataset.mediaUsage?.split(' ')})),context:{plan:root.dataset.planSha256,content:root.dataset.contentSha256,media:root.dataset.mediaSha256,context:root.dataset.contextSha256},
  modules:all<HTMLElement>('[data-module-id]').map(m=>({id:m.dataset.moduleId,scope:m.dataset.scopeId,page:m.dataset.semanticPage,component:m.dataset.component,required:m.dataset.required,
   facts:all<HTMLElement>('[data-fact-id]',m).map(f=>({id:f.dataset.factId,scope:f.dataset.factScope,text:f.textContent?.trim()})),offerings:all<HTMLElement>('[data-offering-id]',m).map(o=>({id:o.dataset.offeringId,scope:o.dataset.offeringScope}))})),
  diagnostics:all<HTMLElement>('[data-diagnostic-sha256]').map(e=>JSON.parse(e.dataset.diagnosticSha256!)),restrictions:all('[data-restrictions] li').map(e=>e.textContent),exclusions:all('[data-exclusions] li').map(e=>e.textContent),
  usage_ids:all<HTMLElement>('[data-media-usage]').flatMap(e=>[...e.dataset.mediaUsage!.split(' '),...(e.dataset.posterUsage?[e.dataset.posterUsage]:[])]),
  images:all<HTMLImageElement>('img').map(i=>({src:i.currentSrc.replace(location.origin,''),decoded:i.complete&&i.naturalWidth>0,natural_width:i.naturalWidth,natural_height:i.naturalHeight,alt:i.alt,object_fit:getComputedStyle(i).objectFit,filter:getComputedStyle(i).filter,...rect(i)})),
  video:{autoplay:all<HTMLVideoElement>('video')[0]!.autoplay,preload:all<HTMLVideoElement>('video')[0]!.getAttribute('preload'),object_fit:getComputedStyle(all('video')[0]!).objectFit,...rect(all('video')[0]!)},
  disclosure:all('[data-media-disclosure]')[0]?.textContent,notice:all('[data-provider-notice]')[0]?.textContent,credits:all('figcaption').map(e=>e.textContent),
  geometry:{width:innerWidth,document_width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,nav:rect(all('.contextual-nav')[0]!),title:rect(document.querySelector('h1')!),hero:rect(all('.hero-photo')[0]!),collection:rect(all('.contextual-collection')[0]!),items:all('[data-offering-id]').map(rect),
   overflow:all<HTMLElement>('*').filter(visible).filter(e=>{const r=e.getBoundingClientRect();return r.left<-.6||r.right>innerWidth+.6||(getComputedStyle(e).display!=='inline'&&e.clientWidth>0&&e.scrollWidth>e.clientWidth+1);}).map(e=>({tag:e.tagName,class:e.className,...rect(e)}))},
  readability,small_controls:all<HTMLElement>('.button,nav a,summary,button,input,select').filter(visible).filter(e=>e.getBoundingClientRect().height<43).map(e=>({tag:e.tagName,text:e.textContent?.slice(0,60),...rect(e)})),
  main:document.querySelectorAll('main').length,h1:document.querySelectorAll('h1').length,lang:document.documentElement.lang,forms:document.forms.length,
  links:all<HTMLAnchorElement>('a[href^="#"]').map(a=>({href:a.hash,exists:!!document.getElementById(a.hash.slice(1))})),text:root.textContent,
  resources:performance.getEntriesByType('resource').map(e=>{const r=e as PerformanceResourceTiming;return {url:r.name.replace(location.origin,''),type:r.initiatorType,bytes:r.encodedBodySize,duration_ms:r.duration};}),
  navigation_ms:(performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming).duration,
 };
}
const sorted=(v:any[])=>[...v].sort((a,b)=>inputSha256(a).localeCompare(inputSha256(b)));
export function auditContextual(o:ReturnType<typeof observeContextual>,s:any,d:ContextualDesignPlan,review:ReturnType<typeof contextualMediaData>){
 const codes:string[]=[];const same=(a:unknown,b:unknown)=>inputSha256(a)===inputSha256(b);
 if(!same(o.context,{plan:d.plan_sha256,content:d.content_sha256,media:d.media_sha256,context:d.context_sha256}))codes.push('B3_RENDER_CONTEXT_CHANGED');
 const expected=s.content.pages.flatMap((p:any)=>p.modules).map((m:any)=>({id:m.id,scope:m.scope_id,page:m.page,component:m.component,required:String(m.required),facts:sorted([...m.facts,...m.offerings.flatMap((v:any)=>v.facts)].map((f:any)=>({id:f.id,scope:f.scope_id,text:f.text}))),offerings:sorted(m.offerings.map((v:any)=>({id:v.id,scope:v.scope_id})))}));
 const actual=o.modules.map(m=>({...m,facts:sorted(m.facts),offerings:sorted(m.offerings)}));
 if(!same(sorted(actual),sorted(expected)))codes.push('B3_BINDING_LOSS_OR_INVENTION');
 if(!same(o.diagnostics,s.content.diagnostics)||!same(o.restrictions,s.content.restrictions)||!same(o.exclusions,s.content.exclusions.map((e:any)=>`${e.scope_id} · ${e.id} · ${e.reason}`)))codes.push('B3_DIAGNOSTIC_OR_RESTRICTION_LOSS');
 const uses=review.usages.filter(u=>u.page===d.route);
 // Archived qa-08 predates this observation. Current-revision QA additionally
 // requires its application hash; do not retrospectively invent observations.
 if(o.reference_application){
  const offerings=expected.flatMap((m:any)=>m.offerings).map((v:any)=>v.id).sort();
  if(!o.offering_media||!same(o.offering_media.map(v=>v.offering).sort(),offerings)||o.offering_media.some(v=>{
   const asset=review.assets.find(a=>a.uri===v.src),bound=uses.filter(u=>u.need_id===`b3-need:${v.offering}`);
   return v.slot!==v.offering||!asset||!bound.some(u=>u.asset_id===asset.id)||!same([...(v.usages??[])].sort(),bound.map(u=>u.id).sort());
  }))codes.push('B3_OFFERING_MEDIA_MISMATCH');
 }
 // srcset naturalWidth/naturalHeight are density-corrected and integer-rounded
 // by Chromium. Compare rendered ratio with the inspected served-file bytes.
 if(!same([...o.usage_ids].sort(),uses.map(u=>u.id).sort())||o.images.length!==5||o.images.some(i=>{const a=review.assets.find(a=>a.uri===i.src);return !a||!i.decoded||!i.alt||i.object_fit!=='contain'||i.filter!=='none'||Math.abs(i.height-i.width*a.inspection.height!/a.inspection.width!)>.6;}))codes.push('B3_MEDIA_BINDING_OR_TREATMENT_INVALID');
 if(o.disclosure!==uses[0]!.generic_label||o.notice!==uses[0]!.context_notices?.[0]||uses.some(u=>!o.credits.some(c=>c?.includes(u.attribution_text!))))codes.push('B3_MEDIA_CONTEXT_OR_CREDIT_LOST');
 if(o.video.autoplay||o.video.preload!=='none'||o.video.width>640.5||o.video.object_fit!=='contain'||Math.abs(o.video.height-o.video.width*9/16)>.6)codes.push('B3_VIDEO_POLICY_INVALID');
 if(o.geometry.document_width>o.geometry.width||o.geometry.overflow.length)codes.push('B3_OVERFLOW');
 if(o.readability.some(v=>v.font_px<14||v.contrast<4.5)||o.small_controls.length)codes.push('B3_READABILITY_OR_TARGET_FAILED');
 if(o.main!==1||o.h1!==1||o.lang!=='es'||o.forms||o.links.some(a=>!a.exists))codes.push('B3_LANDMARK_OR_NAVIGATION_FAILED');
 return {success:!codes.length,codes};
}
