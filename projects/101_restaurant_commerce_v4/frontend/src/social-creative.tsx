import {useEffect, useState} from 'react';
import type {BusinessContext} from './social-context';
export type CreativeBoard = {id?:string;revision:number;visual_direction:string;voice_rules:string;references:any[];questions:any[]};
export const sourceLabels:Record<string,string>={owner_suggestion:'Idea del negocio',customer_question:'Pregunta de un cliente',platform_observation:'Observación en una plataforma',manual_research:'Investigación manual',hypothesis:'Hipótesis por comprobar'};
const groups:Record<string,string>={local_competitor:'Alternativa local',remote_comparable:'Negocio similar de otro lugar',creative_reference:'Referencia creativa',own_brand:'Ejemplo del propio negocio'};
export function SocialCreative({board,context,library,request,onSaved}:{board:CreativeBoard|null;context:BusinessContext|null;library:any[];request:(path:string,method?:string,body?:unknown)=>Promise<any>;onSaved:(b:CreativeBoard)=>void}) {
 const [draft,setDraft]=useState<CreativeBoard>({revision:0,visual_direction:'',voice_rules:'',references:[],questions:[]});
 const [tab,setTab]=useState('references'),[active,setActive]=useState(''),[reason,setReason]=useState(''),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{if(board){setDraft(board);setConfirmed(false)}},[board]);
 function change(key:string,value:unknown){setDraft(d=>({...d,[key]:value}));setConfirmed(false)}
 function itemChange(key:string,value:unknown){const list=tab==='references'?'references':'questions';change(list,draft[list].map(item=>item.id===active?{...item,[key]:value}:item))}
 function add(){const common={id:'c_'+crypto.randomUUID().replaceAll('-',''),source:'',observed_at:new Date().toISOString().slice(0,10)+'T00:00:00Z',valid_until:'',status:'active'};
  const item=tab==='references'?{...common,title:'',kind:'writing',judgment:'positive',purpose:'creative_reference',reason:'',permission:'',allowed_use:'internal_reference_only',url:null,excerpt:'',asset_id:null}:{...common,text:'',source_kind:'owner_suggestion',intent:'how_to_buy',answer_fact_ids:[],next_action:''};
  const key=tab==='references'?'references':'questions';change(key,[...draft[key],item]);setActive(item.id);
 }
 async function save(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{
  const clean=(items:any[])=>items.map(({revision,reviewed_by,reviewed_at,...item})=>item);
  onSaved(await request('/creative','PUT',{expected_revision:board?.revision||0,visual_direction:draft.visual_direction,voice_rules:draft.voice_rules,references:clean(draft.references),questions:clean(draft.questions),change_kind:tab==='style'?'brand_preference':tab==='references'?'reference_review':'question_research',change_reason:reason,confirmed:true}));setReason('');
 }catch(e){setError(String(e))}finally{setBusy(false)}}
 const items=tab==='references'?draft.references:draft.questions,item=items.find(r=>r.id===active);
 return <details className="social-context creative-board"><summary>Referencias, voz y preguntas {board?.revision?`· versión ${board.revision}`:''}</summary>
 <p>Guarda ejemplos que encajan —o no— con tu negocio y las preguntas que vale la pena responder.</p>
 <div className="creative-tabs" role="group" aria-label="Tipo de contexto">{[['references','Referencias'],['style','Voz y estilo'],['questions','Preguntas']].map(([key,label])=><button type="button" className="button secondary" aria-pressed={tab===key} key={key} onClick={()=>{setTab(key);setActive('')}}>{label}</button>)}</div>
 <form onSubmit={e=>void save(e)}>
 {tab==='style'?<div className="social-context-fields"><label>Dirección visual<textarea aria-label="Dirección visual" rows={3} value={draft.visual_direction} onChange={e=>change('visual_direction',e.target.value)} placeholder="Luz natural, producto protagonista…"/></label><label>Cómo hablamos<textarea aria-label="Cómo hablamos" rows={3} value={draft.voice_rules} onChange={e=>change('voice_rules',e.target.value)} placeholder="Palabras propias del negocio y expresiones que evitamos…"/></label></div>:<>
 <div className="creative-cards">{items.map(r=><button type="button" className="creative-card" key={r.id} aria-pressed={active===r.id} onClick={()=>setActive(r.id)}><strong>{r.title||r.text||'Sin terminar'}</strong><span>{tab==='references'?groups[r.purpose]:sourceLabels[r.source_kind]} · {r.status==='withdrawn'?'Retirado':tab==='references'?({positive:'Nos gusta',negative:'Evitar',borderline:'Con reservas'} as any)[r.judgment]:'Sin volumen de búsqueda medido'}</span>{r.reason&&<span>{r.reason}</span>}</button>)}</div>
 {!items.length&&<p>Aún no hay {tab==='references'?'referencias guardadas':'preguntas guardadas'}. Puedes añadir una sin conectar ninguna cuenta.</p>}
 <button type="button" className="button secondary" onClick={add}>{tab==='references'?'Añadir referencia':'Añadir pregunta'}</button>
 {item&&<fieldset className="social-fact"><legend>{tab==='references'?'Editar referencia':'Editar pregunta'}</legend><div className="social-context-fields">
 {tab==='references'?<>
 <label>Título de la referencia<input required value={item.title} onChange={e=>itemChange('title',e.target.value)}/></label>
 <label>Formato<select aria-label="Formato de referencia" value={item.kind} onChange={e=>itemChange('kind',e.target.value)}>{[['writing','Texto'],['photography','Fotografía'],['layout','Diseño'],['video','Video']].map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
 <label>¿Qué opinamos?<select aria-label="Juicio de referencia" value={item.judgment} onChange={e=>itemChange('judgment',e.target.value)}><option value="positive">Nos gusta</option><option value="negative">Evitar</option><option value="borderline">Con reservas</option></select></label>
 <label>¿Para qué sirve?<select aria-label="Propósito de referencia" value={item.purpose} onChange={e=>itemChange('purpose',e.target.value)}>{Object.entries(groups).map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
 <label>Por qué encaja o no<textarea aria-label="Por qué encaja o no" required value={item.reason} onChange={e=>itemChange('reason',e.target.value)}/></label>
 <label>Ejemplo o descripción<textarea aria-label="Ejemplo o descripción" value={item.excerpt} onChange={e=>itemChange('excerpt',e.target.value)}/></label>
 <label>Enlace de referencia · opcional<input type="url" value={item.url||''} onChange={e=>itemChange('url',e.target.value||null)}/></label>
 {item.url&&<p><a href={item.url} target="_blank" rel="noopener noreferrer">Abrir referencia original</a></p>}
 <label>Material guardado · opcional<select aria-label="Material de referencia" value={item.asset_id||''} onChange={e=>itemChange('asset_id',e.target.value||null)}><option value="">Sin archivo</option>{library.map(a=><option key={a.id} value={a.id}>{a.fixture?'Prueba · ':''}{a.id.slice(0,8)}</option>)}</select></label>
 <label>Permiso para revisar este ejemplo<input required minLength={8} value={item.permission} onChange={e=>itemChange('permission',e.target.value)}/></label>
 </>:<>
 <label>Pregunta a responder<input required value={item.text} onChange={e=>itemChange('text',e.target.value)}/></label>
 <label>Origen de la pregunta<select aria-label="Origen de la pregunta" value={item.source_kind} onChange={e=>itemChange('source_kind',e.target.value)}>{Object.entries(sourceLabels).map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
 <label>Intención<select aria-label="Intención" value={item.intent} onChange={e=>itemChange('intent',e.target.value)}>{[['local_discovery','Encontrar un negocio cercano'],['product_understanding','Entender un producto'],['comparison','Comparar opciones'],['buying_occasion','Planear una compra'],['how_to_buy','Saber cómo comprar']].map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
 <label>Siguiente paso útil<input required value={item.next_action} onChange={e=>itemChange('next_action',e.target.value)}/></label>
 <div><p>Datos confirmados que permiten responder</p>{!context?.facts.length&&<p>Primero guarda los datos del negocio. La pregunta puede esperar; no inventaremos su respuesta.</p>}{context?.facts.map(f=><label className="social-check" key={f.id}><input type="checkbox" checked={item.answer_fact_ids.includes(f.id)} onChange={e=>itemChange('answer_fact_ids',e.target.checked?[...item.answer_fact_ids,f.id]:item.answer_fact_ids.filter((id:string)=>id!==f.id))}/>{f.text}{f.current_status!=='confirmed'?' · necesita revisión':''}</label>)}</div>
 </>}
 <label>Fuente y contexto<textarea aria-label="Fuente y contexto" required rows={2} value={item.source} onChange={e=>itemChange('source',e.target.value)}/></label>
 <label>Fecha de observación<input required type="date" value={item.observed_at.slice(0,10)} onChange={e=>itemChange('observed_at',e.target.value+'T00:00:00Z')}/></label>
 <label>Volver a revisar antes de<input required type="date" value={item.valid_until.slice(0,10)} onChange={e=>itemChange('valid_until',e.target.value+'T23:59:59Z')}/></label>
 <label>Estado<select aria-label="Estado del ejemplo" value={item.status} onChange={e=>itemChange('status',e.target.value)}><option value="active">Usar como contexto</option><option value="withdrawn">Retirar</option></select></label>
 </div><p>{tab==='references'?'Este ejemplo orienta la revisión. Su material no se convierte automáticamente en una publicación.':'El origen queda registrado. Una idea o una búsqueda observada no equivale a un volumen de búsqueda medido.'}</p></fieldset>}
 </>}
 <label>Motivo de este cambio<input required value={reason} onChange={e=>setReason(e.target.value)} placeholder="Qué aprendimos o qué queremos corregir"/></label>
 <label className="social-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Revisé las fuentes, los permisos y las razones.</label>
 {error&&<p role="alert">{error}</p>}<button className="button primary" disabled={busy||!confirmed}>{busy?'Guardando…':'Guardar referencias y preguntas'}</button>
 </form></details>
}
