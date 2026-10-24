import {readFile,writeFile} from 'node:fs/promises';
import {DesignRefinementV1} from '../../src/design/evaluators/contracts.ts';
// A compiler binding for experimental preview mounts, not a second renderer.
// The frozen V1 renderer and every historical route remain byte-identical.
export function bindRefinement(html,{lab,variant,caseId,styles}){
 const refinement=DesignRefinementV1.parse(variant.refinement);
 if(!/^[a-z][a-z0-9-]{0,40}$/.test(caseId)||!['A','B','C','D'].includes(variant.condition))throw Error('QUALITY_UNSAFE_MOUNT');
 const id=`${caseId}-${variant.condition.toLowerCase()}`,prefix=`/h7/${id}`;
 if(!html.includes(`data-content-sha256="${lab.content.content_sha256}"`)||!html.includes('data-composition="h5"'))throw Error('QUALITY_COMPILED_CONTEXT_MISMATCH');
 if(!html.includes(`<span>H7 · ${variant.design.id} · Ficticio</span>`))throw Error('QUALITY_ALREADY_BOUND_OR_RENDERER_DRIFT');
 const facts=s=>[...s.matchAll(/<(?:h[1-6]|p)\b[^>]*data-fact-id="[^"]+"[^>]*>.*?<\/(?:h[1-6]|p)>/gs)].map(m=>m[0]);
 const before=facts(html);let navCount=0;
 html=html.replaceAll(`href="${prefix}`,`href="/quality/${id}`).replaceAll('href="/h7/"','href="/quality/"');
 html=html.replace('· laboratorio H7</title>','· laboratorio QUALITY</title>').replace(`<span>H7 · ${variant.design.id} · Ficticio</span>`,`<span>QUALITY · ${variant.design.id} · Ficticio</span>`);
 html=html.replace(/(<a\b[^>]*data-route="([^"]+)"[^>]*>.*?<\/span>)([^<]*)(<\/a>)/gs,(_match,start,path,_old,end)=>{
  const page=lab.content.pages.find(p=>p.path===path);if(!page)throw Error('QUALITY_UNKNOWN_NAVIGATION');navCount++;
  const label=lab.media?(path==='/'?'Identidad':'Oferta de la sucursal'):(path==='/'?'Identidad':page.modules.map(m=>m.capability_id.replaceAll('_',' ')).join(' / '));return start+label+end;
 });
 if(navCount!==lab.content.pages.length)throw Error('QUALITY_NAVIGATION_BINDING_DRIFT');
 if(variant.condition!=='A'){
  const classes=Object.entries(refinement).filter(([k,v])=>k!=='schema_version'&&v!=='incumbent').map(([k,v])=>`quality-${k}-${v}`);
  let found=0;html=html.replace(/class="lab h5 [^"]*"/,m=>{found++;return m.slice(0,-1)+(classes.length?' '+classes.join(' '):'')+'"';});
  let styleBound=false;
  html=html.replace(/(<style>\/\* Shared laboratory grammar:[\s\S]*?)(<\/style>)/,(_match,body,end)=>{styleBound=true;return body+'\n'+styles.replaceAll('\r\n','\n')+end;});
  if(!found||!styleBound)throw Error('QUALITY_RENDERER_BINDING_DRIFT');
 }
 if(JSON.stringify(before)!==JSON.stringify(facts(html)))throw Error('QUALITY_FACT_MUTATION');
 return html;
}
export default function designEvaluationPreview(){return{name:'101-design-evaluation-preview',hooks:{'astro:build:generated':async({dir})=>{
 const loader=new URL('../../scripts/load-quality-lab.ts',import.meta.url).href;const {loadQualityLab,qualityPath}=await import(loader);
 const run=await loadQualityLab(),styles=await readFile(new URL('../../src/design/evaluators/refinement.css',import.meta.url),'utf8');
 for(const c of run.cases)for(const variant of c.variants)for(const page of variant.design.pages){const file=new URL('.'+qualityPath(c.id,variant.condition,page.path)+'index.html',dir);
  await writeFile(file,bindRefinement(await readFile(file,'utf8'),{lab:c.lab,variant,caseId:c.id,styles}));}
}}};}
