/** Visible-content estimates. CSS pixels; never presented as screenshot pixel measurements. */
export const rect = r => ({x:r.x,y:r.y,width:r.width,height:r.height});
export function unionRects(rs){
 rs=rs.filter(r=>r&&r.width>0&&r.height>0);if(!rs.length)return null;
 const x=Math.min(...rs.map(r=>r.x)),y=Math.min(...rs.map(r=>r.y));
 return {x,y,width:Math.max(...rs.map(r=>r.x+r.width))-x,height:Math.max(...rs.map(r=>r.y+r.height))-y};
}
export function intersectRects(a,b){const x=Math.max(a.x,b.x),y=Math.max(a.y,b.y);return {x,y,width:Math.max(0,Math.min(a.x+a.width,b.x+b.width)-x),height:Math.max(0,Math.min(a.y+a.height,b.y+b.height)-y)};}
export function clipBounds(r,element,viewport=false){
 if(!r)return null;const w=element.ownerDocument.defaultView;r={...r};
 for(let e=element;e;e=e.parentElement){const s=w.getComputedStyle(e),b=e.getBoundingClientRect();
  if(/hidden|clip|auto|scroll/.test(s.overflowX)){const end=Math.min(r.x+r.width,b.right);r.x=Math.max(r.x,b.left);r.width=Math.max(0,end-r.x);}
  if(/hidden|clip|auto|scroll/.test(s.overflowY)){const end=Math.min(r.y+r.height,b.bottom);r.y=Math.max(r.y,b.top);r.height=Math.max(0,end-r.y);}
 }
 return viewport?intersectRects(r,{x:0,y:0,width:w.innerWidth,height:w.innerHeight}):r;
}
export function hasLayout(element){const r=element.getBoundingClientRect();return r.width>0&&r.height>0||element.namespaceURI==='http://www.w3.org/2000/svg'&&(r.width>0||r.height>0);}
export function rendered(element){
 const w=element.ownerDocument.defaultView;
 for(let e=element;e;e=e.parentElement){const s=w.getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse'||Number(s.opacity)===0||e.matches('[hidden],dialog:not([open])'))return false;}
 return hasLayout(element);
}
const canvases=new WeakMap();
function context(doc){if(!canvases.has(doc))canvases.set(doc,doc.createElement('canvas').getContext('2d'));return canvases.get(doc);}
/** Per-grapheme ranges retain real wrapping, mixed inline fonts and alignment. Ink remains estimated. */
export function measureTextBounds(element,{viewport=false,direct=false}={}){
 const doc=element.ownerDocument,w=doc.defaultView,ctx=context(doc),lines=[],ink=[],runs=[];let unresolved=0;
 const walk=doc.createTreeWalker(element,4);let node;
 while((node=walk.nextNode())){
  const p=node.parentElement;if(direct&&p!==element||!node.textContent.trim()||!rendered(p)||p.namespaceURI!=='http://www.w3.org/1999/xhtml'||p.closest('script,style,[data-101-design-overlay]'))continue;
  const whole=doc.createRange();whole.selectNodeContents(node);const raw=[...whole.getClientRects()];
  const clipped=raw.map(r=>clipBounds(rect(r),p,viewport)).filter(r=>r.width&&r.height);lines.push(...clipped);
  const s=w.getComputedStyle(p);if(!ctx||s.writingMode!=='horizontal-tb'||s.textTransform!=='none'&&!['uppercase','lowercase','capitalize'].includes(s.textTransform)){unresolved++;continue;}
  ctx.font=`${s.fontStyle} ${s.fontWeight} ${s.fontSize} ${s.fontFamily}`;ctx.textBaseline='alphabetic';ctx.textAlign='left';ctx.direction=s.direction;
  if('fontKerning' in ctx)ctx.fontKerning=s.fontKerning;if('letterSpacing' in ctx)ctx.letterSpacing=s.letterSpacing==='normal'?'0px':s.letterSpacing;
  const graphemes=typeof Intl.Segmenter==='function'?[...new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(node.textContent)].map(v=>({text:v.segment,start:v.index})):Array.from(node.textContent).reduce((a,text)=>{a.push({text,start:a.length?a.at(-1).start+a.at(-1).text.length:0});return a;},[]);
  const glyphs=[];
  for(const g of graphemes){if(!g.text.trim())continue;const range=doc.createRange();range.setStart(node,g.start);range.setEnd(node,g.start+g.text.length);const r=range.getBoundingClientRect();if(!r.width||!r.height)continue;
   let text=g.text;if(s.textTransform==='uppercase')text=text.toUpperCase();else if(s.textTransform==='lowercase')text=text.toLowerCase();else if(s.textTransform==='capitalize'&&(g.start===0||/\s/.test(node.textContent[g.start-1])))text=text.toUpperCase();
   const m=ctx.measureText(text),fh=m.fontBoundingBoxAscent+m.fontBoundingBoxDescent;
   // Range advance may include letter spacing or shaping. Do not stretch the ink to fill that advance.
   const sy=fh?r.height/fh:0,cssSize=parseFloat(s.fontSize),sx=sy||1;
   if(!fh||!cssSize||!Number.isFinite(m.actualBoundingBoxAscent)){unresolved++;continue;}
   const b=clipBounds({x:r.x-m.actualBoundingBoxLeft*sx,y:r.y+(m.fontBoundingBoxAscent-m.actualBoundingBoxAscent)*sy,width:(m.actualBoundingBoxLeft+m.actualBoundingBoxRight)*sx,height:(m.actualBoundingBoxAscent+m.actualBoundingBoxDescent)*sy},p,viewport);
   if(b.width&&b.height){ink.push(b);glyphs.push(b);}
  }
  runs.push({text:node.textContent.trim().slice(0,120),line_boxes:clipped,ink:unionRects(glyphs)});
 }
 return {line:unionRects(lines),lines,runs,ink:unresolved?null:unionRects(ink),ink_basis:'estimated per-grapheme loaded font metrics anchored to rendered DOM ranges; shaping, optical sizing and rasterization may differ',status:unresolved?'unavailable':ink.length?'estimated':'unavailable',unresolved};
}
/** Alpha envelope in source pixels, with an explicit threshold and bounded sampling. */
export function alphaEnvelope(data,width,height,threshold=0){let left=width,top=height,right=-1,bottom=-1,count=0;
 for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(data[(y*width+x)*4+3]>threshold){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);count++;}
 return count?{x:left,y:top,width:right-left+1,height:bottom-top+1,pixels:count}:null;
}
export function projectImageBounds(source,natural,content,fit='fill',position='50% 50%'){
 if(!['fill','contain','cover','none','scale-down'].includes(fit))return null;
 const tokens=position.trim().split(/\s+/);if(tokens.length!==2||!tokens.every(t=>/^-?[\d.]+(?:%|px)$/.test(t)))return null;
 let sx=content.width/natural.width,sy=content.height/natural.height;
 if(fit!=='fill'){let scale=fit==='cover'?Math.max(sx,sy):Math.min(sx,sy);if(fit==='none')scale=1;if(fit==='scale-down')scale=Math.min(1,scale);sx=sy=scale;}
 const offset=(t,space)=>t.endsWith('%')?parseFloat(t)/100*space:parseFloat(t);
 const x=content.x+offset(tokens[0],content.width-natural.width*sx),y=content.y+offset(tokens[1],content.height-natural.height*sy);
 return intersectRects({x:x+source.x*sx,y:y+source.y*sy,width:source.width*sx,height:source.height*sy},content);
}
const images=new WeakMap();
export function imageBounds(img){
 if(!img.complete||!img.naturalWidth)return {status:'unavailable',reason:'image not decoded'};
 const doc=img.ownerDocument,s=doc.defaultView.getComputedStyle(img),b=img.getBoundingClientRect();
 if(s.transform!=='none'||s.filter!=='none'||s.clipPath!=='none')return {status:'unavailable',reason:'image transform/filter/mask requires pixel capture'};
 let envelope=images.get(img);if(!envelope||envelope.src!==img.currentSrc){
  try{const scale=Math.min(1,1024/Math.max(img.naturalWidth,img.naturalHeight)),c=doc.createElement('canvas');c.width=Math.ceil(img.naturalWidth*scale);c.height=Math.ceil(img.naturalHeight*scale);const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,c.width,c.height);const a=alphaEnvelope(ctx.getImageData(0,0,c.width,c.height).data,c.width,c.height,0);envelope={src:img.currentSrc,scale,alpha:a?{x:a.x/scale,y:a.y/scale,width:a.width/scale,height:a.height/scale}:null};images.set(img,envelope);}
  catch{return {status:'unavailable',reason:'image pixels unavailable (origin or decoding)'};}
 }
 if(!envelope.alpha)return {status:'measured',rect:null,reason:'fully transparent image'};
 const sides=['Top','Right','Bottom','Left'].map(k=>(parseFloat(s['padding'+k])||0)+(parseFloat(s['border'+k+'Width'])||0));
 const content={x:b.x+sides[3],y:b.y+sides[0],width:Math.max(0,b.width-sides[1]-sides[3]),height:Math.max(0,b.height-sides[0]-sides[2])};
 const projected=projectImageBounds(envelope.alpha,{width:img.naturalWidth,height:img.naturalHeight},content,s.objectFit,s.objectPosition);
 return projected?{status:'estimated',rect:clipBounds(projected,img),method:'source-alpha envelope projected through object-fit/position; CSS masks and rounded clipping require pixel capture',sample_scale:envelope.scale,alpha_threshold:0}:{status:'unavailable',reason:'unsupported object-position'};
}
export function svgBounds(svg){
 try{if(typeof svg.getBBox!=='function')return {status:'unavailable',reason:'no SVG geometry API'};const b=svg.getBBox(),m=svg.getScreenCTM();if(!m)return {status:'unavailable',reason:'SVG not rendered'};
  const ps=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
  const style=svg.ownerDocument.defaultView.getComputedStyle(svg),stroke=style.stroke==='none'?0:(parseFloat(style.strokeWidth)||0)/2,scale=style.vectorEffect==='non-scaling-stroke'?1:Math.max(Math.hypot(m.a,m.b),Math.hypot(m.c,m.d)),pad=stroke*scale,x=Math.min(...ps.map(p=>p.x))-pad,y=Math.min(...ps.map(p=>p.y))-pad;return {status:'estimated',rect:clipBounds({x,y,width:Math.max(...ps.map(p=>p.x))+pad-x,height:Math.max(...ps.map(p=>p.y))+pad-y},svg),method:'transformed SVG geometry with stroke envelope estimate; joins, filters, masks and occlusion require pixel capture'};
 }catch{return {status:'unavailable',reason:'SVG geometry unavailable'};}
}
export function visibleContentBounds(element){
 if(!rendered(element))return {status:'unavailable',rect:null,reason:'hidden or empty layout box'};
 const text=measureTextBounds(element),parts=[],unknown=[];if(text.ink)parts.push(text.ink);if(text.unresolved)unknown.push('unsupported text');
 for(const media of [element,...element.querySelectorAll('img,svg,video,canvas')].filter(e=>e.matches('img,svg,video,canvas')||e===element&&e.namespaceURI==='http://www.w3.org/2000/svg'&&typeof e.getBBox==='function')){
  if(!rendered(media)||media.matches('svg')&&media.parentElement?.closest('svg'))continue;
  const r=media.matches('img')?imageBounds(media):media.namespaceURI==='http://www.w3.org/2000/svg'?svgBounds(media):{status:'unavailable',reason:'video/canvas requires frame pixel capture'};
  if(r.rect)parts.push(r.rect);if(r.status==='unavailable')unknown.push(r.reason);
 }
 const bounds=unionRects(parts);return {status:unknown.length?'unavailable':bounds?'estimated':'unavailable',rect:unknown.length?null:bounds,partial_rect:bounds,reason:unknown.join('; ')||(!bounds?'no text/media content; inspect surface separately':null),method:'text ink, SVG geometry and image alpha estimates, separate from surface border boxes',text};
}
