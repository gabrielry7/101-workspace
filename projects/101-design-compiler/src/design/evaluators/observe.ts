// Read-only snapshot, compiled by the existing TypeScript/browser workflow.
export function observeEvaluatorPage(){
 const visible=(e:Element)=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e),d=e.closest('details');return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&(!d||d.open||e.tagName==='SUMMARY');};
 const selector=(e:Element):string=>e.id?`#${CSS.escape(e.id)}`:e.parentElement?`${selector(e.parentElement)}>${e.tagName.toLowerCase()}:nth-of-type(${Array.from(e.parentElement.children).filter(c=>c.tagName===e.tagName).indexOf(e)+1})`:'html';
 const elements=Array.from(document.querySelectorAll('body *')).filter(visible);
 const texts=elements.filter(e=>e.matches('h1,h2,h3,p,a,summary,li,figcaption')&&e.textContent?.trim());
 const contrast:unknown[]=[],indeterminate:string[]=[];
 for(const e of texts){let node:Element|null=e,bg:string|null=null;while(node){const s=getComputedStyle(node),c=s.backgroundColor;if(s.backgroundImage!=='none'){break;}if(c!=='transparent'&&c!=='rgba(0, 0, 0, 0)'){if(c.startsWith('rgba('))break;bg=c;break;}node=node.parentElement;}
  const s=getComputedStyle(e);if(bg)contrast.push({selector:selector(e),color:s.color,bgColor:bg,fontPx:parseFloat(s.fontSize),bold:parseInt(s.fontWeight)>=700,text:e.textContent!.trim().slice(0,100)});else indeterminate.push(selector(e));}
 return {viewport:{w:innerWidth,h:innerHeight},url:location.href,document_width:document.documentElement.scrollWidth,document_height:document.documentElement.scrollHeight,
  layout:elements.slice(0,400).map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return{selector:selector(e),rect:{x:r.x,y:r.y+scrollY,w:r.width,h:r.height},computed:{padding:s.padding,margin:s.margin,gap:s.gap,fontSize:s.fontSize,color:s.color,background:s.backgroundColor}};}),
  typography:texts.map(e=>{const s=getComputedStyle(e);return{selector:selector(e),fontPx:parseFloat(s.fontSize),lineHeightPx:parseFloat(s.lineHeight)||parseFloat(s.fontSize)*1.2,fontWeight:parseInt(s.fontWeight),tag:e.tagName.toLowerCase(),text:e.textContent!.trim().slice(0,100)};}),
  targets:elements.filter(e=>e.matches('a,button,summary,input,select,[role=button]')).map(e=>{const r=e.getBoundingClientRect();return{selector:selector(e),x:r.x,y:r.y+scrollY,w:r.width,h:r.height,role:e.tagName.toLowerCase(),text:e.textContent!.trim().slice(0,100)};}),contrast,indeterminate,
  resource_measurement:'NOT_EXPOSED_IN_CUA_DOM_SCOPE',
  media:Array.from(document.images).map(i=>({src:i.getAttribute('src'),complete:i.complete,naturalWidth:i.naturalWidth,naturalHeight:i.naturalHeight})),
  tracked:elements.filter(e=>parseFloat(getComputedStyle(e).letterSpacing)>parseFloat(getComputedStyle(e).fontSize)*.05).map(e=>selector(e)),
 };
}
