// B1 inspector observation only; shared Astro shell/browser, not a website renderer.
export function observeInspector() {
 const all=<T extends Element=HTMLElement>(selector:string)=>[...document.querySelectorAll<T>(selector)];
 const visible=(e:Element)=>{
  let ancestor:Element|null=e.parentElement;
  while(ancestor){if(ancestor.tagName==='DETAILS'&&!(ancestor as HTMLDetailsElement).open&&!ancestor.querySelector(':scope > summary')?.contains(e))return false;ancestor=ancestor.parentElement;}
  const r=e.getBoundingClientRect(),style=getComputedStyle(e);return r.width>0&&r.height>0&&style.display!=='none'&&style.visibility!=='hidden';
 };
 const rect=(e:Element)=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height};};
 const overflow=all('.b1 *').filter(visible).filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+.5;}).map(e=>({tag:e.tagName,...rect(e)}));
 const rgb=(value:string)=>value.match(/[\d.]+/g)?.map(Number)??[0,0,0];
 const luminance=(c:number[])=>{const v=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return .2126*v[0]!+.7152*v[1]!+.0722*v[2]!;};
 const readability=all<HTMLElement>('.b1 h1,.b1 h2,.b1 h3,.b1 p,.b1 a,.b1 summary,.b1 li').filter(visible).map(e=>{
  const style=getComputedStyle(e);let ancestor:HTMLElement|null=e,bg=[255,255,255];
  while(ancestor){const color=rgb(getComputedStyle(ancestor).backgroundColor);if(color.length===3||color[3]!==0){bg=color;break;}ancestor=ancestor.parentElement;}
  const a=luminance(rgb(style.color)),b=luminance(bg);return {tag:e.tagName,text:e.textContent!.trim().slice(0,80),font_px:parseFloat(style.fontSize),contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),...rect(e)};
 });
 return {lang:document.documentElement.lang,main_count:all('main').length,h1_count:all('h1').length,
  root:{...document.querySelector<HTMLElement>('[data-b1-page]')!.dataset},viewport:{width:innerWidth,height:innerHeight},
  document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,client_width:document.documentElement.clientWidth},overflow,readability,
  scopes:all<HTMLElement>('[data-goal-scope]').map(e=>e.dataset.scopeId!),
  goals:all<HTMLElement>('[data-goal-card]').map(e=>({scope_id:e.dataset.scopeId!,capability_id:e.dataset.capabilityId!,relevance:e.dataset.relevance!,emitted:e.dataset.emitted!})),
  fields:all<HTMLElement>('[data-requirement-id]').map(e=>({scope_id:e.closest<HTMLElement>('[data-goal-card]')!.dataset.scopeId!,
   capability_id:e.closest<HTMLElement>('[data-goal-card]')!.dataset.capabilityId!,level_id:e.closest<HTMLElement>('[data-level-id]')!.dataset.levelId!,
   requirement_id:e.dataset.requirementId!,status:e.dataset.requirementStatus!,owner:e.dataset.owner!})),
  catalog_cards:all<HTMLElement>('[data-catalog-card]').map(e=>e.dataset.capabilityId!),
  links:all<HTMLAnchorElement>('.b1 a').map(e=>({href:e.getAttribute('href')!,text:e.textContent!.trim()})),
  forms:all('form').length,buttons:all('button').length,scripts:document.scripts.length,media:all('img,video,audio').length,
  resources:performance.getEntriesByType('resource').map(e=>{const r=e as PerformanceResourceTiming;return {path:new URL(r.name).pathname,local:new URL(r.name).origin===location.origin,type:r.initiatorType,bytes:r.decodedBodySize,duration_ms:r.duration};}),
  navigation_duration_ms:(performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming).duration};
}
