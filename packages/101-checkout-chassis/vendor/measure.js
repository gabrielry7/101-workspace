import {measureTextBounds,visibleContentBounds,hasLayout} from './content-bounds.js';
/** Browser measurements, not an aesthetic score. All geometry is in the inspected viewport's CSS px. */
export function contrastRatio(a,b){
 const luminance=c=>c.slice(0,3).map(v=>{const n=v/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}
export const contrastThreshold=(size,weight)=>size>=24||(size>=56/3&&weight>=700)?3:4.5;
const round=n=>Math.round(n*100)/100;
const box=r=>({x:r.x,y:r.y,width:r.width,height:r.height});
const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
const inside=(x,y,r)=>x>=r.x&&x<=r.x+r.width&&y>=r.y&&y<=r.y+r.height;
function intersection(a,b){const x=Math.max(a.x,b.x),y=Math.max(a.y,b.y),right=Math.min(a.x+a.width,b.x+b.width),bottom=Math.min(a.y+a.height,b.y+b.height);return {x,y,width:Math.max(0,right-x),height:Math.max(0,bottom-y)};}
export function visible(element){
 const doc=element.ownerDocument,w=doc.defaultView,r=element.getBoundingClientRect(),s=w.getComputedStyle(element);
 const dialog=doc.querySelector('dialog[open]');if(dialog&&!dialog.contains(element)&&!element.contains(dialog))return false;
 for(let e=element;e;e=e.parentElement)if(Number(w.getComputedStyle(e).opacity)===0)return false;
 return !!(r.width&&r.height&&s.display!=='none'&&s.visibility!=='hidden'&&!element.closest('[hidden],dialog:not([open])')&&overlap(box(r),{x:0,y:0,width:w.innerWidth,height:w.innerHeight}));
}
export function colorChannels(value,doc){
 const rgb=value.match(/^rgba?\(([^)]+)\)$/),srgb=value.match(/^color\(srgb\s+([^)]+)\)$/);
 if(rgb||srgb){
  const parts=(rgb||srgb)[1].trim().split(/[\s,/]+/),channels=parts.slice(0,3).map(v=>parseFloat(v)*(v.endsWith('%')?2.55:srgb?255:1));
  const alpha=parts[3]===undefined?1:parseFloat(parts[3])/(parts[3].endsWith('%')?100:1);return [...channels,alpha];
 }
 if(!colorCache.has(doc)){const canvas=doc.createElement('canvas');canvas.width=canvas.height=1;colorCache.set(doc,{ctx:canvas.getContext('2d',{willReadFrequently:true}),values:new Map()});}
 const {ctx,values}=colorCache.get(doc);if(values.has(value))return values.get(value);
 ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);const channels=[...ctx.getImageData(0,0,1,1).data].map((v,i)=>i===3?v/255:v);values.set(value,channels);return channels;
}
const colorCache=new WeakMap();
export const hexColor=c=>'#'+c.slice(0,3).map(v=>Math.round(v).toString(16).padStart(2,'0')).join('');
/** Alpha layers compose only over a known solid backdrop. Photos/gradients/filters remain unknown. */
export function effectiveBackground(element){
 const doc=element.ownerDocument,w=doc.defaultView,r=box(element.getBoundingClientRect());
 const chain=[];for(let e=element;e;e=e.parentElement)chain.push(e);
 if(chain.some(e=>{const s=w.getComputedStyle(e);return Number(s.opacity)<1-1e-9||(s.filter!=='none'&&!/^blur\(0(?:px)?\)$/.test(s.filter))||s.mixBlendMode!=='normal';}))return {known:false,reason:'opacity/filter/blend'};
 let accumulated=[0,0,0,0];
 for(const e of chain){
  const style=w.getComputedStyle(e),c=colorChannels(style.backgroundColor,doc);
  // Fixed transparent layers can sit over a sibling photo rather than a child.
  // An opaque edited fill resolves the backdrop; translucency still needs pixels.
  if(e.hasAttribute('data-101-media-backdrop')&&c[3]<1-1e-9)return {known:false,reason:'photo/gradient'};
  // A decorative child image can paint over its ancestor's nominal background.
  const media=[...e.querySelectorAll(':scope > img,:scope > video,:scope > [data-101-bone=media],:scope > .panorama-photo')].some(m=>visible(m)&&overlap(box(m.getBoundingClientRect()),r));
  if(media||style.backgroundImage!=='none')return {known:false,reason:'photo/gradient'};
  const a=accumulated[3],alpha=a+c[3]*(1-a);
  accumulated=[0,1,2].map(i=>alpha?(accumulated[i]*a+c[i]*c[3]*(1-a))/alpha:0).concat(alpha);
  if(alpha>=1-1e-9)return {known:true,color:accumulated.slice(0,3)};
 }
 return {known:false,reason:'no opaque backdrop'};
}
function textRects(root){
 const doc=root.ownerDocument,w=doc.defaultView,walker=doc.createTreeWalker(root,w.NodeFilter.SHOW_TEXT),rects=[];
 for(let node=walker.nextNode();node;node=walker.nextNode()){
  if(!node.textContent.trim()||!visible(node.parentElement)||node.parentElement.closest('[data-101-design-overlay],script,style'))continue;
  const range=doc.createRange();range.selectNodeContents(node);
  for(const raw of range.getClientRects()){
   let r=box(raw);
   for(let e=node.parentElement;e&&e!==root.parentElement;e=e.parentElement){const s=w.getComputedStyle(e);if(s.overflowX!=='visible'||s.overflowY!=='visible')r=intersection(r,box(e.getBoundingClientRect()));}
   if(r.width&&r.height)rects.push(r);
  }
 }
 return rects;
}
export function measureDesign(host,anatomy){
 const doc=host.ownerDocument,w=doc.defaultView,viewport={width:w.innerWidth,height:w.innerHeight};
 const definitions=anatomy.flatMap(def=>[...host.querySelectorAll(def.selector)].filter(visible).map((element,index)=>({def,element,index})));
 const boxes=definitions.map(({def,element,index})=>{
  const s=w.getComputedStyle(element),r=element.getBoundingClientRect();
  return {bone_id:def.id,role:def.role,status:def.status,source:def.source,index,record_id:element.closest('[data-review-id]')?.dataset.reviewId??null,
   rect:Object.fromEntries(Object.entries(box(r)).map(([k,v])=>[k,round(v)])),radius:s.borderRadius,
   padding:[s.paddingTop,s.paddingRight,s.paddingBottom,s.paddingLeft],border:{width:[s.borderTopWidth,s.borderRightWidth,s.borderBottomWidth,s.borderLeftWidth],style:s.borderStyle,color:s.borderColor},fill:s.backgroundColor,shadow:s.boxShadow,
   typography:{size:parseFloat(s.fontSize),weight:s.fontWeight,line_height:s.lineHeight,color:s.color}};
 });
 const contrast=definitions.filter(({def})=>def.kind==='text'||def.kind==='action').map(({def,element,index})=>{
  const s=w.getComputedStyle(element),foreground=colorChannels(s.color,doc),background=effectiveBackground(element),threshold=contrastThreshold(parseFloat(s.fontSize),Number(s.fontWeight));
  if(!background.known||foreground[3]<1-1e-9)return {role:def.role,index,status:'unknown',reason:background.reason??'transparent foreground',threshold};
  const ratio=contrastRatio(foreground,background.color);return {role:def.role,index,status:ratio>=threshold?'pass':'fail',ratio,threshold,foreground:hexColor(foreground),background:hexColor(background.color)};
 });
 const area=intersection(box(host.getBoundingClientRect()),{x:0,y:0,...viewport}),occupied=textRects(host).concat([...host.querySelectorAll('button,[data-101-action],.review-initials')].filter(visible).map(e=>box(e.getBoundingClientRect())));
 const counts=new Map(),backgrounds=new Map(),cols=40,rows=28;let empty=0,total=0;
 if(area.width&&area.height)for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){
  const px=area.x+(x+.5)*area.width/cols,py=area.y+(y+.5)*area.height/rows;total++;
  if(!occupied.some(r=>inside(px,py,r)))empty++;
  const e=doc.elementsFromPoint(px,py).find(n=>host.contains(n)&&!n.closest('[data-101-design-overlay]'));
  if(e&&!backgrounds.has(e))backgrounds.set(e,effectiveBackground(e));
  const bg=backgrounds.get(e)??{known:false},key=bg.known?hexColor(bg.color):'photo/gradient/unresolved';counts.set(key,(counts.get(key)||0)+1);
 }
 const first=selector=>[...host.querySelectorAll(selector)].find(visible)?.getBoundingClientRect();
 const intro=first('[data-101-bone-role=intro]'),deck=first('[data-101-bone-role=collection]'),heading=first('.reviews-title,.panorama-heading'),quote=first('[data-101-bone-role=collection] .review-quote,[data-101-bone-role=collection] .panorama-quote'),name=first('.review-author'),date=first('.review-date'),stars=first('[data-101-bone-role=collection] .review-stars');
 const alignment={intro_collection_left_delta_px:intro&&deck?round(intro.left-deck.left):null,heading_quote_left_delta_px:heading&&quote?round(heading.left-quote.left):null,name_date_gap_px:name&&date?round(date.top-name.bottom):null,stars_quote_gap_px:stars&&quote?round(quote.top-stars.bottom):null};
 return {schema:'101-design-measurement-v1',measured_at:new Date().toISOString(),viewport,scroll_y:w.scrollY,scope:'visible component viewport',boxes,contrast,alignment,
  layout_space:{method:'40x28 cell sampling outside visible text line boxes, actions and avatars; decorative backgrounds excluded',empty_percent:total?round(empty/total*100):null,samples:total},
  surface_coverage:{method:'DOM hit-test and composited solid CSS backgrounds; photos/gradients unresolved, not pixel color analysis',samples:total,colors:[...counts].map(([color,count])=>({color,percent:round(count/total*100)}))},
  limitations:['Snapshot in CSS px, not human taste or a symmetry score.','Space uses line/control rectangles, not glyph pixels or ideal spacing.','Photo/gradient contrast is unknown; inspect the rendered backdrop.','Color coverage is sampled CSS surface coverage, not image color percentages.']};
}

/** Relationship geometry uses rendered border boxes, never sums declared margins. */
export function relationshipGeometry(a,b){
 const r=v=>({x:v.x??v.left,y:v.y??v.top,width:v.width,height:v.height});a=r(a);b=r(b);
 const contains=(p,c)=>c.x>=p.x-.1&&c.y>=p.y-.1&&c.x+c.width<=p.x+p.width+.1&&c.y+c.height<=p.y+p.height+.1;
 const insets=(p,c)=>({top:round(c.y-p.y),right:round(p.x+p.width-c.x-c.width),bottom:round(p.y+p.height-c.y-c.height),left:round(c.x-p.x)});
 const overlapX=Math.max(0,Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)),overlapY=Math.max(0,Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y));
 return {kind:contains(b,a)?'a-inside-b':contains(a,b)?'b-inside-a':overlapX&&overlapY?'overlap':'separate',
  a,b,gap:{x:round(Math.max(0,b.x-a.x-a.width,a.x-b.x-b.width)),y:round(Math.max(0,b.y-a.y-a.height,a.y-b.y-b.height))},
  overlap:{x:round(overlapX),y:round(overlapY)},
  centers:{x:round(a.x+a.width/2-b.x-b.width/2),y:round(a.y+a.height/2-b.y-b.height/2)},
  edges:{left:round(a.x-b.x),right:round(a.x+a.width-b.x-b.width),top:round(a.y-b.y),bottom:round(a.y+a.height-b.y-b.height)},
  insets:contains(b,a)?insets(b,a):contains(a,b)?insets(a,b):null};
}
/** DOM ranges retain wrapping; glyph ink remains explicitly estimated. */
export const textPlacement=element=>measureTextBounds(element,{viewport:true});
/** Find the nearest owned, visible surface; fall back to an actual owned DOM ancestor. */
export function spacingContainer(host,definitions,element){
 let fallback=null;const w=host.ownerDocument.defaultView;
 for(let e=element.parentElement;e&&(e===host||host.contains(e));e=e.parentElement){
  if(!visible(e))continue;const r=e.getBoundingClientRect(),a=element.getBoundingClientRect();if(r.width<a.width-.5||r.height<a.height-.5||Math.abs(r.width-a.width)<.5&&Math.abs(r.height-a.height)<.5)continue;
  const definition=definitions.find(d=>!d.pseudo&&e.matches(d.selector));if(!definition)continue;
  const entry={definition,element:e};fallback??=entry;const s=w.getComputedStyle(e);
  if(definition.kind==='surface'||definition.category==='surface'||colorChannels(s.backgroundColor,host.ownerDocument)[3]>.01)return entry;
 }
 return fallback;
}
function rhythmFor(element,host){
 const w=host.ownerDocument.defaultView;
 for(let e=element;e&&(e===host||host.contains(e));e=e.parentElement){
  const s=w.getComputedStyle(e);if(!/flex|grid/.test(s.display))continue;
  const children=[...e.children].filter(c=>visible(c)&&!['absolute','fixed'].includes(w.getComputedStyle(c).position));if(children.length<2)continue;
  const rects=children.slice(0,40).map(c=>box(c.getBoundingClientRect())),axes=[];
  for(const axis of ['x','y']){
   const size=axis==='x'?'width':'height',other=axis==='x'?'y':'x',otherSize=axis==='x'?'height':'width';
   const ordered=rects.filter(r=>Math.min(r[other]+r[otherSize],rects[0][other]+rects[0][otherSize])-Math.max(r[other],rects[0][other])>.5).sort((a,b)=>a[axis]-b[axis]);
   const gaps=ordered.slice(1).map((r,i)=>round(r[axis]-ordered[i][axis]-ordered[i][size]));
   if(gaps.length)axes.push({axis,gaps,min:Math.min(...gaps),max:Math.max(...gaps),spread:round(Math.max(...gaps)-Math.min(...gaps)),consistent:gaps.length>1?Math.max(...gaps)-Math.min(...gaps)<=.5:null});
  }
  return {layout:s.display,declared_gap:s.gap,axes,tolerance_px:.5,method:'adjacent rendered children in the first intersecting row/column; not a prescribed spacing scale'};
 }
 return null;
}
export function measureRelationship(host,a,b){
 const base={schema:'101-spacing-relationship-v1',measured_at:new Date().toISOString(),view_path:host.ownerDocument.location.pathname,units:'CSS px in the inspected viewport',a_role:a?.definition.role??null,b_role:b?.definition.role??null,a_pseudo:a?.definition.pseudo??null,b_pseudo:b?.definition.pseudo??null};
 if(a?.definition.kind==='backdrop'||b?.definition.kind==='backdrop')return {...base,available:false,reason:'El backdrop no tiene una caja DOM independiente. Selecciona el diálogo o una superficie.'};
 if(!a?.element||!b?.element)return {...base,available:false,reason:'Selecciona otra pieza o un contenedor visible.'};
 if(a.element.ownerDocument!==b.element.ownerDocument||!host.contains(a.element)&&a.element!==host||!host.contains(b.element)&&b.element!==host)return {...base,available:false,reason:'Las dos piezas deben pertenecer a esta vista.'};
 const viewportBox={x:0,y:0,width:host.ownerDocument.defaultView.innerWidth,height:host.ownerDocument.defaultView.innerHeight};
 if(!hasLayout(a.element)||!hasLayout(b.element)||!overlap(a.element.getBoundingClientRect(),viewportBox)||!overlap(b.element.getBoundingClientRect(),viewportBox))return {...base,available:false,reason:'Una pieza está oculta o fuera del viewport. Muéstrala para medirla.'};
 const geometry=relationshipGeometry(a.element.getBoundingClientRect(),b.element.getBoundingClientRect()),style=b.element.ownerDocument.defaultView.getComputedStyle(b.element),padding={},border={};
 for(const side of ['Top','Right','Bottom','Left']){padding[side.toLowerCase()]=parseFloat(style['padding'+side])||0;border[side.toLowerCase()]=parseFloat(style['border'+side+'Width'])||0;}
 const br=geometry.b,cssWidth=parseFloat(style.width),cssHeight=parseFloat(style.height),sx=cssWidth>0?br.width/(cssWidth+(style.boxSizing==='border-box'?0:padding.left+padding.right+border.left+border.right)):1,sy=cssHeight>0?br.height/(cssHeight+(style.boxSizing==='border-box'?0:padding.top+padding.bottom+border.top+border.bottom)):1;
 const content={x:br.x+(padding.left+border.left)*sx,y:br.y+(padding.top+border.top)*sy,width:Math.max(0,br.width-(padding.left+padding.right+border.left+border.right)*sx),height:Math.max(0,br.height-(padding.top+padding.bottom+border.top+border.bottom)*sy)};
 const text=textPlacement(a.element),visualA=visibleContentBounds(a.element),visualB=visibleContentBounds(b.element);let common=a.element;while(common&&!common.contains(b.element))common=common.parentElement;const cr=(common||host).getBoundingClientRect();
 return {...base,available:true,viewport:{width:host.ownerDocument.defaultView.innerWidth,height:host.ownerDocument.defaultView.innerHeight},...geometry,
  a_label:a.definition.label,b_label:b.definition.label,a_bone_id:a.definition.id,b_bone_id:b.definition.id,a_index:a.element===host?0:[...host.querySelectorAll(a.definition.selector)].indexOf(a.element),b_index:b.element===host?0:[...host.querySelectorAll(b.definition.selector)].indexOf(b.element),a_record_id:a.element.closest('[data-review-id]')?.dataset.reviewId??null,b_record_id:b.element.closest('[data-review-id]')?.dataset.reviewId??null,scroll:{x:host.ownerDocument.defaultView.scrollX,y:host.ownerDocument.defaultView.scrollY},reference_content:content,reference_css:{padding,border,margin:style.margin},
  content_relationship:geometry.kind==='a-inside-b'?relationshipGeometry(geometry.a,content):null,
  visual:{a:visualA,b:visualB,relationship:visualA.rect&&visualB.rect?relationshipGeometry(visualA.rect,visualB.rect):null,a_to_b_frame:visualA.rect?relationshipGeometry(visualA.rect,geometry.b):null},
  text:{...text,line_relationship:text.line?relationshipGeometry(text.line,geometry.b):null,ink_relationship:text.ink?relationshipGeometry(text.ink,geometry.b):null},
  common_ancestor:box(cr),normalized_gap_percent:{x:cr.width?round(geometry.gap.x/cr.width*100):null,y:cr.height?round(geometry.gap.y/cr.height*100):null,basis:'common DOM ancestor border box'},
  rhythm:rhythmFor(a.element,host),limitations:['Axis-aligned rendered boxes; transforms/rounded clipping can require optical review.','Declared padding/margin is separate from rendered separation.','Glyph placement is estimated from rendered ranges; unsupported treatments may have no ink estimate.','Consistency and centering observations are not a professional-design score.']};
}
