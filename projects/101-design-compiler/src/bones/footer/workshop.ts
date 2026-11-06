import {collectFooterCoverage} from './measure.ts';
import {footerAnatomy, measurementOwners, FOOTER_BONE} from './anatomy.ts';

const frame=document.querySelector<HTMLIFrameElement>('#footer-frame')!;
const stage=document.querySelector<HTMLElement>('#preview-stage')!;
const widthSelect=document.querySelector<HTMLSelectElement>('#viewport-width')!;
let guides=false, shared: any=null, guideModule: any=null, provenance: unknown=null;
let lastReport: unknown=null, selectedRole: string|undefined;
const put=(id:string,value:string)=>{document.getElementById(id)!.textContent=value;};
const percent=(n:number|null|undefined)=>n==null?'—':n.toFixed(2)+'%';
const host=()=>frame.contentDocument?.querySelector<HTMLElement>('[data-footer-bone]');
function fit(){
  const footer=host();if(!footer)return;
  const height=Math.ceil(footer.getBoundingClientRect().height);
  frame.height=String(height);
  const width=Number(widthSelect.value), container=frame.parentElement!;
  const scale=Math.min(1,container.clientWidth/width);
  if(scale>0){frame.style.transform='scale('+scale+')';container.style.height=height*scale+'px';}
  put('frame-dimensions',width+' × '+height+' px');
}
function drawGuides(){
  const footer=host();if(!footer)return;
  frame.contentDocument?.querySelector('[data-101-design-overlay]')?.remove();
  if(guides&&guideModule)guideModule.showGuides(footer,footerAnatomy,{all:!selectedRole,role:selectedRole});
}
async function measure(){
  const footer=host();if(!footer)return null;
  await frame.contentDocument!.fonts.ready;
  fit();
  await new Promise<void>(resolve=>frame.contentWindow!.requestAnimationFrame(()=>resolve()));
  const coverage=collectFooterCoverage(footer), m=coverage.metrics;
  const sharedReport=shared?shared.measureDesign(footer,footerAnatomy):null;
  const report={
    schema:'101-footer-observation-v1',bone:FOOTER_BONE,
    configuration:{reference:'caretta/08',skin:'neutral',width:Number(widthSelect.value),cookieAction:'unbound',motion:'none added; source motion unobserved'},
    anatomy:footerAnatomy,owners:measurementOwners,coverage,
    shared_inspector:sharedReport?{available:true,provenance,report:sharedReport}:{available:false,reason:'Prepare the pinned local component-preview modules; no measurements fabricated.'},
  };
  lastReport=report;
  put('metric-text',percent(m.text_line_boxes.percent));put('metric-no-text',percent(m.without_text.percent));
  put('metric-occupied',percent(m.occupied_layout.percent));put('metric-free',percent(m.free_layout.percent));
  put('measurement-details',coverage.footer_bounds.width+' × '+coverage.footer_bounds.height+' px · '+coverage.denominator_css_px2.toLocaleString('es')+' px² · '+coverage.text_line_box_count+' cajas de línea.');
  put('secondary-metrics','Controles: '+percent(m.controls.percent)+'. Slots de logos: '+percent(m.functional_media_slots.percent)+'. Decoración: '+percent(m.decoration_slots.percent)+'.');
  put('shared-inspector-state',sharedReport?'Módulo original de Tomás disponible · geometría, contraste y muestreo 40 × 28.':'Inspector compartido no preparado. La extensión de texto sigue disponible.');
  put('shared-summary',sharedReport?'Espacio sin texto/controles (proxy de Tomás): '+percent(sharedReport.layout_space.empty_percent)+'. Superficies: '+sharedReport.surface_coverage.colors.map((c:any)=>c.color+' '+percent(c.percent)).join(', ')+'.':'');
  put('measurement-report',JSON.stringify(report));
  drawGuides();
  return report;
}
async function setWidth(width:number){
  if(![...widthSelect.options].some(option=>option.value===String(width)))widthSelect.add(new Option(width+' px',String(width)));
  widthSelect.value=String(width);frame.width=String(width);
  await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
  return measure();
}
const api={measure,setWidth,getReport:()=>lastReport};
Object.assign(window,{footerBoneWorkbench:api});
widthSelect.addEventListener('change',()=>void setWidth(Number(widthSelect.value)));
document.getElementById('refresh-measurements')!.addEventListener('click',()=>void measure());
document.getElementById('toggle-guides')!.addEventListener('click',event=>{
  guides=!guides;selectedRole=undefined;(event.currentTarget as HTMLElement).setAttribute('aria-pressed',String(guides));drawGuides();
});
for(const button of document.querySelectorAll<HTMLButtonElement>('[data-view-choice]'))button.addEventListener('click',()=>{
  stage.dataset['view']=button.dataset['viewChoice'];
  document.querySelectorAll('[data-view-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));fit();
});
const list=document.getElementById('anatomy-list')!;
for(const part of footerAnatomy){
  const button=document.createElement('button');button.type='button';button.textContent=part.label;
  button.addEventListener('click',()=>{selectedRole=part.role;guides=true;document.getElementById('toggle-guides')!.setAttribute('aria-pressed','true');drawGuides();});
  list.append(button);
}
document.getElementById('download-measurements')!.addEventListener('click',async()=>{
  const report=await measure();if(!report)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='footer-001-'+widthSelect.value+'px.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
window.addEventListener('resize',fit);
frame.addEventListener('load',()=>void measure());
void(async()=>{
  try{
    const measurementUrl='/__bone-tools/measure.js', guidesUrl='/__bone-tools/guides.js';
    shared=await import(/* @vite-ignore */ measurementUrl);
    guideModule=await import(/* @vite-ignore */ guidesUrl);
    const response=await fetch('/__bone-tools/provenance.json');if(response.ok)provenance=await response.json();
  }catch{shared=null;guideModule=null;}
  if(host())await measure();
})();
