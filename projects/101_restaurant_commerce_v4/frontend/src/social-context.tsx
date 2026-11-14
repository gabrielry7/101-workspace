import {useEffect, useState} from 'react';
import {SocialOnboarding} from './social-onboarding';
export type BusinessContext = {id?:string;revision:number;brief:any;facts:any[];location_id?:string|null;onboarding?:any};
export function SocialContext({request,onSaved,context}:{request:(path:string,method?:string,body?:unknown)=>Promise<any>;onSaved:(c:BusinessContext)=>void;context:BusinessContext|null}) {
 const [guide,setGuide]=useState<boolean|null>(null);
 const [brief,setBrief]=useState<any>({offering:'',objective:'',buying_destination:'',constraints:'',locale:'es-CO',capacity:null,margin:null});
 const [facts,setFacts]=useState<any[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[confirmed,setConfirmed]=useState(false);
 useEffect(()=>{if(context){if(context.brief)setBrief(context.brief);setFacts(context.facts);setConfirmed(false)}},[context]);
 function patch(i:number,key:string,value:string){setFacts(old=>old.map((f,n)=>n===i?{...f,[key]:value}:f));setConfirmed(false)}
 async function save(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{
  const fields=['id','label','kind','value','unit','currency','source','effective_at','valid_until','status'];
  const payload=facts.map(f=>Object.fromEntries(fields.map(k=>[k,k==='currency'?(f.kind==='money'?f.currency:null):f[k]??null])));
  onSaved(await request('/context','PUT',{expected_revision:context?.revision||0,location_id:context?.location_id||null,brief:{...brief,...Object.fromEntries(['offering','objective','buying_destination','locale'].map(k=>[k,brief[k]||null]))},facts:payload,confirmed:true}));
 }catch(e){setError(String(e))}finally{setBusy(false)}}
 if(!context)return <section className="social-context" aria-busy="true">Cargando información del negocio…</section>;
 return <details className="social-context business-context" open={!context?.brief}><summary>Información de tu negocio {context?.revision?`· versión ${context.revision}`:''}</summary>
 <p>Guarda lo que ofreces y cómo comprarlo. Podrás reutilizarlo en tus publicaciones y corregirlo cuando cambie.</p>
 {context&&(guide??!context.brief)?<SocialOnboarding context={context} request={request} onSaved={onSaved} onClose={()=>setGuide(false)}/>:<button type="button" className="button secondary" disabled={!context} onClick={()=>setGuide(true)}>Responder con opciones</button>}
 {context?.onboarding&&guide!==true&&<p role="status">Tus respuestas están guardadas. Puedes cambiarlas con la guía o <a href="#social-production-form">preparar una publicación con una foto</a>.</p>}
 <details className="social-context-manual" open={!!context?.brief&&guide!==true}><summary>Editar información y datos confirmados</summary>
 <form onSubmit={e=>void save(e)}>
 {context?.onboarding&&<p>Para cambiar tus respuestas iniciales, usa «Responder con opciones».</p>}
 <div className="social-context-fields">{[['offering','¿Qué quieres ofrecer?'],['objective','Objetivo del negocio'],['buying_destination','¿Cómo pueden comprar o pedir?'],['constraints','Condiciones o restricciones'],['locale','Idioma y región']].map(([key,label])=><label key={key}>{label}<input readOnly={!!context?.onboarding} value={brief[key]??''} onChange={e=>{setBrief({...brief,[key]:e.target.value});setConfirmed(false)}}/></label>)}
 {['capacity','margin'].map(key=><label key={key}>{key==='capacity'?'Capacidad disponible':'Margen'} · opcional<input value={brief[key]??''} placeholder="Sin confirmar" onChange={e=>{setBrief({...brief,[key]:e.target.value||null});setConfirmed(false)}}/></label>)}</div>
 <h3>Datos que puedes confirmar</h3><p>Por ejemplo, un producto, su precio o una condición de compra. Indica de dónde viene cada dato y cuándo revisarlo.</p>
 {facts.map((f,i)=><fieldset key={f.id} className="social-fact"><legend>Dato {i+1}{f.revision?` · versión ${f.revision}`:''}</legend><div className="social-context-fields">
 <label>Nombre del dato<input required value={f.label} onChange={e=>patch(i,'label',e.target.value)}/></label>
 <label>Tipo<select aria-label="Tipo" value={f.kind} onChange={e=>patch(i,'kind',e.target.value)}><option value="text">Texto</option><option value="money">Precio</option><option value="number">Cantidad</option><option value="boolean">Sí o no</option></select></label>
 <label>Valor{f.kind==='boolean'?<select aria-label="Valor" required value={f.value} onChange={e=>patch(i,'value',e.target.value)}><option value="">Seleccionar</option><option value="true">Sí</option><option value="false">No</option></select>:<input required type={f.kind==='money'||f.kind==='number'?'number':'text'} step={f.kind==='money'?'0.01':'any'} min={f.kind==='money'?'0':undefined} value={f.value} onChange={e=>patch(i,'value',e.target.value)}/>}</label>
 {f.kind==='money'&&<label>Moneda<input required pattern="[A-Z]{3}" placeholder="COP" value={f.currency||''} onChange={e=>patch(i,'currency',e.target.value)}/></label>}
 {f.kind==='number'&&<label>Unidad<input value={f.unit||''} onChange={e=>patch(i,'unit',e.target.value)}/></label>}
 <label>Fuente<input required value={f.source} onChange={e=>patch(i,'source',e.target.value)}/></label>
 <label>Vigente desde<input required type="date" value={f.effective_at.slice(0,10)} onChange={e=>patch(i,'effective_at',e.target.value+'T00:00:00Z')}/></label>
 <label>Revisar antes de<input required type="date" value={f.valid_until.slice(0,10)} onChange={e=>patch(i,'valid_until',e.target.value+'T23:59:59Z')}/></label>
 <label>Estado<select aria-label="Estado" value={f.status} onChange={e=>patch(i,'status',e.target.value)}><option value="confirmed">Confirmado</option><option value="withdrawn">Ya no usar</option></select></label></div>
 {f.current_status==='expired'&&<p>Este dato venció. Revisa el valor y su fecha antes de volver a usarlo.</p>}
 </fieldset>)}
 <button type="button" className="button secondary" onClick={()=>setFacts([...facts,{id:'k_'+crypto.randomUUID().replaceAll('-',''),label:'',kind:'text',value:'',unit:null,currency:null,source:'Confirmación del negocio',effective_at:new Date().toISOString().slice(0,10)+'T00:00:00Z',valid_until:'',status:'confirmed'}])}>Añadir dato</button>
 <label className="social-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>He revisado esta información y sus fechas.</label>
 {error&&<p role="alert">{error}</p>}<button className="button primary" disabled={!context||busy||!confirmed}>{busy?'Guardando…':'Guardar información del negocio'}</button>
 </form></details></details>
}
