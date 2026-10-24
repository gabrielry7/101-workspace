// Fixed, small progressive enhancement for the local HUMAN comparison form only.
// Candidate pages still ship zero JS. No network writes, external storage, analytics or backend.
export function panelRuntime(){
 const form=document.querySelector<HTMLFormElement>('#preference-form')!,data=document.querySelector('#pair-data')!.textContent!;
 const pair=JSON.parse(data),qa=new URLSearchParams(location.search).get('qa')==='1';
 const output=document.querySelector<HTMLElement>('#preference-output')!,status=document.querySelector<HTMLElement>('#preference-status')!,download=document.querySelector<HTMLAnchorElement>('#download-preference')!;
 let url:string|null=null;
 form.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled=false;
 if(qa)status.textContent='TEST_SIMULATION: esta página no registra votos humanos.';
 form.addEventListener('submit',event=>{
  event.preventDefault();if(!form.reportValidity())return;
  const fields=new FormData(form),decision=String(fields.get('decision'));
  if(!['A','B','TIE','NONE'].includes(decision))return;
  const record={schema_version:'1.0.0',source:qa?'TEST_SIMULATION':'HUMAN_LOCAL_PANEL',comparison_id:pair.id,context_sha256:pair.context_sha256,
   left_id:pair.left_id,right_id:pair.right_id,left_sha256:pair.left_sha256,right_sha256:pair.right_sha256,
   left_screenshot_sha256:pair.left_screenshot_sha256,right_screenshot_sha256:pair.right_screenshot_sha256,
   semantic_page:pair.semantic_page,viewport:pair.viewport,decision,reason:String(fields.get('reason')??''),recorded_at:new Date().toISOString(),acceptance_scope:'THIS_PAIR_ROUTE_VIEWPORT_ONLY'};
  output.textContent=JSON.stringify(record,null,2);output.hidden=false;
  if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(new Blob([output.textContent+'\n'],{type:'application/json'}));
  download.href=url;download.hidden=false;download.download=qa?'test-simulation.json':`${pair.id}-preference.json`;
  status.textContent=qa?'TEST_SIMULATION; no cuenta como voto humano.':'Decisión local preparada. Descarga el JSON para conservarla; no se envía a ningún servidor.';
 });
}
