// Serialized into the local browser by the QA harness; observes DOM, not planned metadata.
export function observePage() {
  const lab = document.querySelector<HTMLElement>('.lab')!;
  const all = <T extends Element = HTMLElement>(selector: string, root: ParentNode = document) => Array.from(root.querySelectorAll<T>(selector));
  const text = (selector: string, root: ParentNode = document) => root.querySelector(selector)?.textContent?.trim() ?? '';
  const rect = (e: Element) => { const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height}; };
  const visible = (e: HTMLElement) => { const r=e.getBoundingClientRect(),s=getComputedStyle(e),d=e.closest('details');return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&(!d||d.open||e.tagName==='SUMMARY'); };
  const unboundMedia=all('img,video,audio').filter(e=>!e.closest('figure[data-usage-id]')).length;
  const observation = {
    ...(unboundMedia ? {unbound_media:unboundMedia} : {}),
    semantic_page:lab.dataset.semanticPage!,plan_sha256:lab.dataset.planSha256!,content_sha256:lab.dataset.contentSha256!,manifest_sha256:lab.dataset.manifestSha256!,client_id:lab.dataset.clientId!,project_id:lab.dataset.projectId!,
    modules:all<HTMLElement>('[data-module-id]').map(m=>({id:m.dataset.moduleId!,scope:m.dataset.scopeId!,page:m.dataset.semanticPage!,required:m.dataset.required!,component:m.dataset.component!,
      facts:all<HTMLElement>('[data-fact-id]',m).map(f=>({id:f.dataset.factId!,scope:f.dataset.factScope!,text:f.textContent!.trim()})),
      offerings:all<HTMLElement>('[data-offering-id]',m).map(o=>({id:o.dataset.offeringId!,scope:o.dataset.offeringScope!}))})),
    diagnostics:all<HTMLElement>('[data-diagnostic-index]').map(d=>({code:d.dataset.diagnosticCode!,scope:d.dataset.diagnosticScope!,capability:d.dataset.diagnosticCapability??'',reason:d.dataset.diagnosticReason!})),
    exclusions:all<HTMLElement>('[data-exclusion-index]').map(e=>({id:e.dataset.exclusionId!,scope:e.dataset.exclusionScope!,reason:e.dataset.exclusionReason!})),
    bindings:all<HTMLElement>('[data-binding-id]').map(b=>({id:b.dataset.bindingId!,scope:b.dataset.bindingScope!,status:b.dataset.bindingStatus!})),
    restrictions:all('[data-restriction]').map(e=>e.textContent!.trim()),constraints:all('[data-media-constraint]').map(e=>e.textContent!.trim()),gaps:all<HTMLElement>('[data-gap-id]').map(e=>e.dataset.gapId!),
    media:all<HTMLElement>('figure[data-usage-id]').map(f=>{const i=f.querySelector('img')!,r=i.getBoundingClientRect(),s=getComputedStyle(i);return {
      asset_id:f.dataset.assetId!,usage_id:f.dataset.usageId!,grant_id:f.dataset.grantId!,module:f.dataset.mediaModule!,page:f.dataset.semanticPage!,role:f.dataset.role!,hash:f.dataset.originalSha256!,src:i.getAttribute('src')!,alt:i.alt,
      caption:text('[data-context]',f),credit:text('[data-credit]',f),notices:all('[data-notice]',f).map(e=>e.textContent!.trim()),decoded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight,display_width:r.width,display_height:r.height,object_fit:s.objectFit,filter:s.filter};}),
    navigation:all<HTMLAnchorElement>('.site-nav a').map(a=>({page:a.dataset.route!,href:a.getAttribute('href')!,current:a.getAttribute('aria-current')==='page'})),
    scripts:document.scripts.length,forms:all('form').length,buttons:all('button').length,gap_visible:visible(document.querySelector<HTMLElement>('.gap')!),lang:document.documentElement.lang,h1_count:all('h1').length,main_count:all('main').length,
  };
  const overflow = all<HTMLElement>('.lab *').filter(visible).filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+.5||(getComputedStyle(e).display!=='inline'&&e.clientWidth>0&&e.scrollWidth>e.clientWidth+1);}).map(e=>({tag:e.tagName,class:e.className,...rect(e),scroll_width:e.scrollWidth,client_width:e.clientWidth}));
  function rgb(c:string){return c.match(/[\d.]+/g)?.map(Number) ?? [0,0,0];}
  function luminance(c:number[]){const l=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return .2126*l[0]!+.7152*l[1]!+.0722*l[2]!;}
  const readability = all<HTMLElement>('h1,h2,p,a,summary',lab).filter(visible).map(e=>{
    const s=getComputedStyle(e);let ancestor:HTMLElement|null=e,bg=[255,255,255];
    while(ancestor){const c=rgb(getComputedStyle(ancestor).backgroundColor);if(c.length===3||c[3]!==0){bg=c;break;}ancestor=ancestor.parentElement;}
    const l1=luminance(rgb(s.color)),l2=luminance(bg),ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
    return {tag:e.tagName,text:e.textContent!.trim().slice(0,80),font_px:parseFloat(s.fontSize),contrast:ratio,...rect(e)};
  });
  return { observation, geometry:{viewport:{width:innerWidth,height:innerHeight},document_width:document.documentElement.scrollWidth,document_height:document.documentElement.scrollHeight,
    header:rect(document.querySelector('.lab-header')!),nav:rect(document.querySelector('.site-nav')!),stage:rect(document.querySelector('.stage')!),title:rect(document.querySelector('h1')!),
    image:document.querySelector('img')?rect(document.querySelector('img')!):null,overflow,
    modules:all<HTMLElement>('[data-module-id]').map(m=>({id:m.dataset.moduleId,visible:visible(m),...rect(m)}))},readability,
    resources:performance.getEntriesByType('resource').map(e=>{const r=e as PerformanceResourceTiming;return {path:new URL(r.name).pathname,type:r.initiatorType,bytes:r.decodedBodySize,transfer_bytes:r.transferSize,duration_ms:r.duration,local:new URL(r.name).origin===location.origin};}),
    navigation_duration_ms:(performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming).duration,
    reduced_motion:matchMedia('(prefers-reduced-motion:reduce)').matches,
    animated_elements:all<HTMLElement>('.lab *').filter(e=>getComputedStyle(e).animationName!=='none').length,
  };
}
