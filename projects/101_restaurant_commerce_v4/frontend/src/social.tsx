import { useEffect, useState } from 'react';
import { endpoint } from './ui';
import './social.css';
type Pack = {id:string;revision:number;digest:string;approved:boolean;document:{caption:string;brief:any;fixture:boolean}};
export function SocialWorkspace({business,csrf,demo}:{business:string;csrf:string;demo:boolean}) {
 const root=endpoint(business)+'/social';
 const [requestId,setRequestId]=useState(()=>crypto.randomUUID());
 const [packs,setPacks]=useState<{id:string;revision:number}[]>([]),[pack,setPack]=useState<Pack|null>(null);
 const [dirty,setDirty]=useState(false);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[asset,setAsset]=useState('');
 const [facts,setFacts]=useState(''),[question,setQuestion]=useState(''),[objective,setObjective]=useState('');
 const [brand,setBrand]=useState(''),[rights,setRights]=useState(''),[confirmed,setConfirmed]=useState(false);
 const [expiry,setExpiry]=useState(''),[crop,setCrop]=useState(.5),[review,setReview]=useState(false);
 async function request(path:string,method='GET',body?:unknown) {
  const r=await fetch(root+path,{method,headers:{'Content-Type':'application/json','X-101-CSRF':csrf},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await r.json(); if(!r.ok) throw new Error(typeof data.detail==='string'?data.detail:'Revisa los campos y vuelve a intentar.'); return data;
 }
 async function run(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function refresh(){setPacks((await request('')).packs)}
 useEffect(()=>{void run(refresh)},[business]);
 function load(p:Pack){setDirty(false);setPack(p);const b=p.document.brief;setRequestId(b.request_id);setAsset(b.asset_id);setFacts(b.facts.map((f:any)=>f.text).join('\n\n'));setQuestion(b.question);setObjective(b.objective);setBrand(b.brand_direction);setExpiry(b.facts[0].valid_until.slice(0,10));setCrop(b.focal_x);setConfirmed(false);setReview(false)}
 async function upload(file:File){
  if(file.size>500000)throw new Error('Por ahora admite fotos JPEG o PNG de hasta 500 KB. Conserva el original; las cargas grandes están pendientes.');
  if(!rights.trim()||!expiry)throw new Error('Indica el permiso de uso y su fecha de revisión.');
  const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
  const result=await request('/assets','POST',{data_base64:btoa(binary),rights_statement:rights,expires_at:expiry+'T23:59:59Z',permitted_use:'production',fixture:demo});setAsset(result.id);
 }
 async function save(){
  const statements=facts.split('\n\n').filter(Boolean).map((text,i)=>({id:'fact_'+i,text,source:'Confirmación explícita en el espacio del negocio',valid_until:expiry+'T23:59:59Z'}));
  const brief={request_id:requestId,asset_id:asset,objective,hypothesis:'Propuesta del negocio; todavía no hay resultados para evaluarla.',question,question_source:'owner_suggestion',question_evidence:question,facts:statements,caption_fact_ids:statements.map(f=>f.id),focal_x:crop,focal_y:.5,brand_direction:brand,reference_reason:'Dirección proporcionada por el negocio; revisión humana pendiente.',primary_measure:'qualified_inquiries',confirmed,expected_revision:pack?.revision||0};
  setPack(await request('/packs'+(pack?'/'+pack.id:''),pack?'PUT':'POST',brief));setReview(false);setDirty(false);await refresh();
 }
 return <section className="social-workspace"><header><h1>Contenido para tus redes</h1><p>Prepara una fotografía y su texto. Revisa el resultado antes de descargarlo.</p></header>
 <p className="social-note">Primera versión · fotografía sin texto superpuesto. Instagram no está conectado aquí. Los resultados aún no están disponibles.</p>
 {error&&<p role="alert">{error}</p>}
 <div className="social-grid"><form onChange={()=>setDirty(true)} onSubmit={e=>{e.preventDefault();void run(save)}}>
 <label>Trabajo guardado<select value={pack?.id||''} onChange={e=>{if(e.target.value)void run(async()=>load(await request('/packs/'+e.target.value)));else{setPack(null);setRequestId(crypto.randomUUID());setReview(false)}}}><option value="">Crear una publicación</option>{packs.map(p=><option key={p.id} value={p.id}>Publicación {p.id.slice(0,6)} · versión {p.revision}</option>)}</select></label>
 <label>¿Qué quieres conseguir?<input required value={objective} onChange={e=>setObjective(e.target.value)}/></label>
 <label>¿Qué pregunta debe responder?<input required value={question} onChange={e=>setQuestion(e.target.value)}/></label>
 <label>Texto que puedes confirmar<textarea required rows={5} value={facts} onChange={e=>setFacts(e.target.value)}/></label>
 <p>Separa las afirmaciones con una línea vacía. Este texto será el pie de foto.</p>
 <label>Revisar estos datos y el permiso de la foto antes de<input required type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></label>
 <label>¿Cómo debe verse y sonar?<textarea required value={brand} onChange={e=>setBrand(e.target.value)}/></label>
 <label>Permiso para usar esta fotografía<input value={rights} onChange={e=>setRights(e.target.value)} placeholder="Es nuestra foto y autorizamos su uso en esta publicación"/></label>
 <label>Fotografía · mínimo 1080 × 1350, máximo 500 KB<input type="file" accept="image/jpeg,image/png" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void run(()=>upload(file))}}/></label>
 {asset&&<p>Fotografía recibida.</p>}
 <label>Encuadre horizontal<input type="range" min="0" max="1" step=".05" value={crop} onChange={e=>setCrop(Number(e.target.value))}/></label>
 <label className="social-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Confirmo que estas afirmaciones son actuales y correctas.</label>
 <button className="button primary" type="submit" disabled={busy||!asset||!confirmed}>{busy?'Preparando…':pack?'Guardar nueva versión':'Preparar publicación'}</button>
 </form><aside>{pack?<><h2>Revisa la versión {pack.revision}</h2>{dirty&&<p role="status">Hay cambios sin guardar. Guarda una nueva versión para revisarlos.</p>}{pack.document.fixture&&<p>Material de prueba</p>}<img className="social-image" src={root+'/packs/'+pack.id+'/image?v='+pack.revision} alt="Vista previa de la publicación"/><p className="social-caption">{pack.document.caption}</p><p>Mediremos consultas de compra. Sin publicación ni mediciones todavía.</p><label className="social-check"><input type="checkbox" checked={review} onChange={e=>setReview(e.target.checked)}/>Revisé la fotografía, el texto, el encuadre y su relación con el objetivo.</label><button className="button primary" disabled={busy||dirty||!review||pack.approved} onClick={()=>void run(async()=>setPack(await request('/packs/'+pack.id+'/approve','POST',{digest:pack.digest,craft_reviewed:true,brand_reviewed:true,purpose_reviewed:true})))}>{pack.approved?'Versión aprobada':'Aprobar esta versión'}</button>{pack.approved&&<p><a href={root+'/packs/'+pack.id+'/export'}>Descargar foto, texto y archivo editable</a></p>}</>:<><h2>Tu publicación aparecerá aquí</h2><p>Usaremos tu fotografía y las afirmaciones que confirmes. Podrás ajustar el encuadre y guardar otra versión.</p></>}</aside></div></section>
}
