import { useEffect, useState } from 'react';
import { endpoint } from './ui';
import './social.css';
import {SocialCreative, sourceLabels, type CreativeBoard} from './social-creative';
import {SocialContext, type BusinessContext} from './social-context';
import {SocialResults} from './social-results';
import {SocialReview,SocialReviewQueue} from './social-review';
import {SocialProposals} from './social-proposals';
import {ProductionJobs} from './social-jobs';
import {InstagramPanel} from './social-instagram';
import {SocialDesign,SocialHistory,ownedLayerId,designError,type DesignSpec} from './social-design';
type Pack = {id:string;revision:number;digest:string;approved:boolean;stale:boolean;media_available:boolean;stale_reasons:any[];document:{caption:string;brief:any;fixture:boolean;creative_snapshot?:any}};
export function SocialWorkspace({business,csrf,demo}:{business:string;csrf:string;demo:boolean}) {
 const root=endpoint(business)+'/social';
 const [context,setContext]=useState<BusinessContext|null>(null),[selectedFacts,setSelectedFacts]=useState<any[]>([]);
 const [design,setDesign]=useState<DesignSpec|null>(null),[designCopy,setDesignCopy]=useState<Record<string,string>>({});
 const [cropY,setCropY]=useState(.5);
 const [nextLearning,setNextLearning]=useState<any>(null);
 const [handoff,setHandoff]=useState({platform:'unspecified',account_label:''});
 const [proposalDecision,setProposalDecision]=useState<string|null>(null);
 const [contextVersion,setContextVersion]=useState<string|null>(null);
 const [creative,setCreative]=useState<CreativeBoard|null>(null),[creativeVersion,setCreativeVersion]=useState<string|null>(null);
 const [referenceIds,setReferenceIds]=useState<string[]>([]),[questionId,setQuestionId]=useState<string|null>(null);
 const [questionSource,setQuestionSource]=useState('owner_suggestion'),[questionEvidence,setQuestionEvidence]=useState(''),[revisionReason,setRevisionReason]=useState('strategy');
 const [lastFile,setLastFile]=useState<File|null>(null);
 const [progress,setProgress]=useState<number|null>(null),[library,setLibrary]=useState<any[]>([]);
 const [requestId,setRequestId]=useState(()=>crypto.randomUUID());
 const [packs,setPacks]=useState<{id:string;revision:number}[]>([]),[pack,setPack]=useState<Pack|null>(null);
 const [activeJob,setActiveJob]=useState<string|null>(null),[jobPending,setJobPending]=useState(false);
 const [dirty,setDirty]=useState(false);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[asset,setAsset]=useState('');
 const [facts,setFacts]=useState(''),[question,setQuestion]=useState(''),[objective,setObjective]=useState('');
 const [brand,setBrand]=useState(''),[rights,setRights]=useState(''),[confirmed,setConfirmed]=useState(false);
 const [expiry,setExpiry]=useState(''),[crop,setCrop]=useState(.5),[,setReview]=useState(false);
 async function request(path:string,method='GET',body?:unknown) {
  const r=await fetch(root+path,{method,headers:{'Content-Type':'application/json','X-101-CSRF':csrf},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await r.json(); if(!r.ok) throw new Error(designError(data.detail)); return data;
 }
 async function run(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function refresh(){setCreative(await request('/creative'));setContext(await request('/context'));setPacks((await request('')).packs);setLibrary((await request('/assets')).assets)}
 useEffect(()=>{void run(refresh)},[business]);
 function load(p:Pack){setNextLearning(null);setDirty(false);setPack(p);setPacks(old=>[...old.filter(item=>item.id!==p.id),{id:p.id,revision:p.revision}]);const b=p.document.brief;setHandoff(b.handoff||{platform:'unspecified',account_label:''});setDesign(b.design||null);setDesignCopy(Object.fromEntries(['headline','detail'].map(role=>[role,b.facts.find((f:any)=>f.id===ownedLayerId(role))?.text||''])));setCropY(b.focal_y);setProposalDecision(b.proposal_decision_id||null);setRequestId(b.request_id||crypto.randomUUID());setAsset(b.asset_id);setFacts(b.facts.filter((f:any)=>!['headline','detail'].some(role=>f.id===ownedLayerId(role))&&!(b.fact_refs||[]).some((r:any)=>r.fact_id===f.id)).map((f:any)=>f.text).join('\n\n'));setSelectedFacts((b.fact_refs||[]).filter((r:any)=>b.caption_fact_ids.includes(r.fact_id)).map((r:any)=>({...r,...b.facts.find((f:any)=>f.id===r.fact_id)})));setContextVersion(b.context_version_id||null);setCreativeVersion(b.creative_version_id||null);setReferenceIds(b.reference_ids||[]);setQuestionId(b.question_id||null);setQuestionSource(b.question_source);setQuestionEvidence(b.question_evidence);setRevisionReason('strategy');setQuestion(b.question);setObjective(b.objective);setBrand(b.brand_direction);setExpiry(b.facts[0].valid_until.slice(0,10));setCrop(b.focal_x);setConfirmed(false);setReview(false)}
 async function upload(file:File){
  setLastFile(file);setProgress(0);
  if(file.size>12*1024*1024)throw new Error('La fotografía debe pesar menos de 12 MB.');
  if(!rights.trim()||!expiry)throw new Error('Indica el permiso de uso y su fecha de revisión.');
  const buffer=await file.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))).map(b=>b.toString(16).padStart(2,'0')).join('');
  const key='social-upload:'+business+':'+hash+':'+expiry+':'+rights;
  let id=localStorage.getItem(key),state:any=null;
  if(id){try{state=await request('/uploads/'+id)}catch{localStorage.removeItem(key);id=null}}
  if(!id){state=await request('/uploads','POST',{sha256:hash,total:file.size,rights_statement:rights,expires_at:expiry+'T23:59:59Z',permitted_use:'production',fixture:demo});id=state.id;localStorage.setItem(key,id!)}
  if(!state.asset_id){
   for(let offset=state.received;offset<file.size;){const part=new Uint8Array(buffer.slice(offset,offset+262144));let binary='';for(const byte of part)binary+=String.fromCharCode(byte);state=await request('/uploads/'+id,'PUT',{offset,data_base64:btoa(binary)});offset=state.received;setProgress(Math.round(offset/file.size*100));}
   state=await request('/uploads/'+id+'/complete','POST');
  }
  setAsset(state.asset_id||state.id);localStorage.removeItem(key);setProgress(null);await refresh();
 }
 async function save(){
  const statements=facts.split('\n\n').filter(Boolean).map((text,i)=>({id:'fact_'+i,text,source:'Confirmación explícita en el espacio del negocio',valid_until:expiry+'T23:59:59Z'}));
  const activeDesign=design?{...design,layers:design.layers.filter(l=>l.fact_id&&(l.fact_id!==ownedLayerId(l.id)||designCopy[l.id]?.trim()))}:null;
  const overlayIds=activeDesign?.layers.map(l=>l.fact_id)||[];
  const overlayLinked=overlayIds.map(id=>context?.facts.find(f=>f.id===id&&f.current_status==='confirmed')).filter(Boolean).map(f=>({...f,context_version_id:context!.id,fact_revision:f.revision}));
  const usedFacts=[...new Map([...selectedFacts,...overlayLinked].map(f=>[f.id,f])).values()];
  const linked=usedFacts.map(f=>({id:f.id,text:f.text,source:f.source,valid_until:f.valid_until}));
  const customFacts=['headline','detail'].filter(role=>overlayIds.includes(ownedLayerId(role))).map(role=>({id:ownedLayerId(role),text:designCopy[role],source:'Texto confirmado por el negocio para esta imagen',valid_until:expiry+'T23:59:59Z'}));
  const allFacts=[...statements,...linked,...customFacts];
  const brief={learning_decision_id:pack?.document.brief.learning_decision_id||null,handoff,design:activeDesign,proposal_decision_id:proposalDecision,creative_version_id:creativeVersion,reference_ids:referenceIds,question_id:questionId,revision_reason:pack?revisionReason:'initial',context_version_id:contextVersion,fact_refs:usedFacts.map(f=>({context_version_id:f.context_version_id,fact_id:f.id,fact_revision:f.fact_revision})),request_id:!pack&&activeJob?crypto.randomUUID():requestId,asset_id:asset,objective,hypothesis:proposalDecision?pack?.document.brief.hypothesis:'Propuesta del negocio; todavía no hay resultados para evaluarla.',question,question_source:questionSource,question_evidence:questionEvidence||'Idea ingresada por el negocio',facts:allFacts,caption_fact_ids:[...statements,...selectedFacts].map(f=>f.id),focal_x:crop,focal_y:cropY,brand_direction:brand,reference_reason:'Dirección proporcionada por el negocio; revisión humana pendiente.',primary_measure:proposalDecision?pack?.document.brief.primary_measure:'qualified_inquiries',confirmed,expected_revision:pack?.revision||0};
  const job=await request('/jobs','POST',{kind:'photo_render',brief,pack_id:pack?.id||null});setActiveJob(job.id);setJobPending(['queued','running'].includes(job.state));setReview(false);setDirty(false);
 }
 function useQuestion(id:string, board=creative, factsContext=context){
  const q=board?.questions.find(q=>q.id===id&&q.status==='active');if(!q||!factsContext)throw new Error('Guarda primero los datos que responden esta pregunta.');
  const answers=q.answer_fact_ids.map((id:string)=>factsContext.facts.find(f=>f.id===id&&f.current_status==='confirmed'));
  if(!answers.length||answers.some((f:any)=>!f))throw new Error('Confirma o actualiza los datos que responden esta pregunta antes de usarla.');
  setSelectedFacts(answers.map((f:any)=>({...f,context_version_id:factsContext.id,fact_revision:f.revision})));
  setQuestionId(id);setQuestion(q.text);setQuestionSource(q.source_kind);setQuestionEvidence(q.source);setCreativeVersion(board!.id!);
  setDirty(true);setConfirmed(false);setReview(false);
 }
 async function recover(){
  setProposalDecision(null);
  const c=await request('/context'),b=await request('/creative');setContext(c);setCreative(b);
  setSelectedFacts(old=>old.map(f=>{const latest=c.facts.find((v:any)=>v.id===f.id&&v.current_status==='confirmed');return latest?{...latest,context_version_id:c.id,fact_revision:latest.revision}:null}).filter(Boolean));
  if(contextVersion&&c.brief){setContextVersion(c.id);setObjective(c.brief.objective||'')}
  if(creativeVersion){setCreativeVersion(b.id);setReferenceIds(old=>old.filter(id=>b.references.some((r:any)=>r.id===id&&r.status==='active'&&Date.parse(r.valid_until)>Date.now())));if(b.visual_direction||b.voice_rules)setBrand(b.visual_direction||b.voice_rules);if(questionId)useQuestion(questionId,b,c)}
  setRevisionReason(pack?.stale_reasons.some(r=>String(r.reason).startsWith('brand_')||String(r.reason).startsWith('reference_'))?'brand_preference':pack?.stale_reasons.some(r=>String(r.reason).startsWith('question_'))?'strategy':'factual_correction');setConfirmed(false);setReview(false);setDirty(true);
 }
 async function updateDesignPrice(id:string,value:string){
  setBusy(true);try {
  if(!context)throw new Error('Primero guarda los datos del negocio.');
  const fields=['id','label','kind','value','unit','currency','source','effective_at','valid_until','status'];
  const facts=context.facts.map(f=>Object.fromEntries(fields.map(key=>[key,key==='value'&&f.id===id?value:f[key]??null])));
  setError('');
  const c=await request('/context','PUT',{expected_revision:context.revision,location_id:context.location_id||null,brief:context.brief,facts,confirmed:true});
  setContext(c);if(pack)setPack(await request('/packs/'+pack.id));await recover();setRevisionReason('factual_correction');
  }finally{setBusy(false)}
 }
 return <section className="social-workspace"><header><h1>Contenido para tus redes</h1><p>Prepara una fotografía y su texto. Revisa el resultado antes de descargarlo.</p></header>
 <SocialContext context={context} request={request} onSaved={c=>{setContext(c);if(pack)void run(async()=>{setPack(await request('/packs/'+pack.id));setReview(false);setConfirmed(false)})}}/>
 <SocialCreative board={creative} context={context} library={library} request={request} onSaved={b=>{setCreative(b);if(pack)void run(async()=>{setPack(await request('/packs/'+pack.id));setConfirmed(false);setReview(false)})}}/>
 <SocialProposals learning={nextLearning} onClearLearning={()=>setNextLearning(null)} business={business} csrf={csrf} context={context} creative={creative} library={library} onProduction={job=>{setActiveJob(job.id);setJobPending(['queued','running'].includes(job.state));setReview(false);setDirty(false)}}/>
 <InstagramPanel business={business} csrf={csrf}/><p className="social-note">Fotografía protagonista y texto confirmado. Los resultados de esta publicación aparecerán después de publicarla y medirla.</p>
 <ProductionJobs business={business} csrf={csrf} asset={asset} activeJob={activeJob} onState={setJobPending} onComplete={async id=>{const p=await request('/packs/'+id);load(p);setActiveJob(null);await refresh()}}/>
 <SocialReviewQueue business={business} csrf={csrf} refreshKey={pack?pack.id+pack.digest+pack.approved+(pack as any).review_state:''} onOpen={id=>void run(async()=>{load(await request('/packs/'+id));document.getElementById('social-post-review')?.focus({preventScroll:true});document.getElementById('social-post-review')?.scrollIntoView({behavior:'smooth'})})}/>
 {error&&<p role="alert">{error}</p>}
 <div className="social-grid" id="social-production-form"><form onChange={()=>setDirty(true)} onSubmit={e=>{e.preventDefault();void run(save)}}><fieldset className="production-fields" disabled={jobPending}>
 <label>Trabajo guardado<select value={pack?.id||''} onChange={e=>{if(e.target.value)void run(async()=>load(await request('/packs/'+e.target.value)));else{setPack(null);setDesign(null);setDesignCopy({});setProposalDecision(null);setRequestId(crypto.randomUUID());setReview(false)}}}><option value="">Crear una publicación</option>{packs.map(p=><option key={p.id} value={p.id}>Publicación {p.id.slice(0,6)} · versión {p.revision}</option>)}</select></label>
 {context?.brief&&<div className="social-context-choice"><p>Reutiliza los datos guardados del negocio.</p><button type="button" className="button secondary" disabled={!context.brief.objective} onClick={()=>{setObjective(context.brief.objective||'');setContextVersion(context.id||null);setDirty(true);setConfirmed(false)}}>Usar objetivo del negocio</button>
 {context.facts.filter(f=>f.current_status==='confirmed').map(f=><label className="social-check" key={f.id}><input type="checkbox" checked={selectedFacts.some(s=>s.id===f.id)} onChange={e=>{setSelectedFacts(old=>e.target.checked?[...old,{...f,context_version_id:context.id,fact_revision:f.revision}]:old.filter(s=>s.id!==f.id));setConfirmed(false);setDirty(true)}}/>{f.text}</label>)}</div>}
 <label>Destino de publicación manual<select value={handoff.platform} onChange={e=>setHandoff(old=>({...old,platform:e.target.value}))}><option value="unspecified">Por decidir</option><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="tiktok">TikTok</option></select></label><label>Cuenta de destino · opcional<input maxLength={120} value={handoff.account_label} onChange={e=>setHandoff(old=>({...old,account_label:e.target.value}))} placeholder="Nombre o @ de la cuenta"/></label><p>Este destino sirve para la entrega manual. No conecta ni publica en una cuenta.</p>
 <label>¿Qué quieres conseguir?<input required value={objective} onChange={e=>setObjective(e.target.value)}/></label>
 {creative?.id&&<div className="social-context-choice"><p>Dirección y preguntas guardadas</p>{creativeVersion&&<button type="button" className="button secondary" onClick={()=>{setCreativeVersion(null);setReferenceIds([]);setQuestionId(null);setDirty(true);setConfirmed(false)}}>Editar sin contexto guardado</button>}<button type="button" className="button secondary" onClick={()=>{setCreativeVersion(creative.id!);if(creative.visual_direction||creative.voice_rules)setBrand(creative.visual_direction||creative.voice_rules);setDirty(true);setConfirmed(false)}}>Usar voz y estilo guardados</button>
 {creative.references.filter(r=>r.status==='active').map(r=><label className="social-check" key={r.id}><input type="checkbox" checked={referenceIds.includes(r.id)} disabled={Date.parse(r.valid_until)<=Date.now()} onChange={e=>{setCreativeVersion(creative.id!);setReferenceIds(old=>e.target.checked?[...old,r.id]:old.filter(id=>id!==r.id));setDirty(true);setConfirmed(false)}}/>{r.title} · {({positive:'nos gusta',negative:'evitar',borderline:'con reservas'} as any)[r.judgment]}</label>)}
 <label>Pregunta guardada<select aria-label="Pregunta guardada" value={questionId||''} onChange={e=>{if(e.target.value)void run(async()=>useQuestion(e.target.value));else{setQuestionId(null);setDirty(true)}}}><option value="">Escribir una pregunta para este post</option>{creative.questions.filter(q=>q.status==='active').map(q=><option key={q.id} value={q.id}>{q.text}</option>)}</select></label></div>}
 <label>¿Qué pregunta debe responder?<input required value={question} readOnly={!!questionId} onChange={e=>setQuestion(e.target.value)}/></label>
 <label>Origen de esta pregunta<select aria-label="Origen de esta pregunta" disabled={!!questionId} value={questionSource} onChange={e=>setQuestionSource(e.target.value)}>{Object.entries(sourceLabels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
 <label>Fuente de esta pregunta<input readOnly={!!questionId} required={!['owner_suggestion','hypothesis'].includes(questionSource)} value={questionEvidence} placeholder="Tu idea, comentario autorizado u observación fechada" onChange={e=>setQuestionEvidence(e.target.value)}/></label>
 <label>Texto que puedes confirmar<textarea required={!selectedFacts.length} rows={5} value={facts} onChange={e=>setFacts(e.target.value)}/></label>
 <p>Texto adicional confirmado para esta publicación. Separa las afirmaciones con una línea vacía.</p>
 <label>Revisar estos datos y el permiso de la foto antes de<input required type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></label>
 <label>¿Cómo debe verse y sonar?<textarea required value={brand} onChange={e=>setBrand(e.target.value)}/></label>
 <label>Permiso para usar esta fotografía<input value={rights} onChange={e=>setRights(e.target.value)} placeholder="Es nuestra foto y autorizamos su uso en esta publicación"/></label>
 <label>Fotografía · mínimo 1080 × 1350, máximo 12 MB<input type="file" accept="image/jpeg,image/png" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void run(()=>upload(file))}}/></label>
 {progress!==null&&<><p role="status">Carga: {progress} %. Puedes continuar si se interrumpe.</p>{!busy&&lastFile&&<button type="button" className="button secondary" onClick={()=>void run(()=>upload(lastFile))}>Reintentar carga</button>}</>}
 <label>O usa una fotografía guardada<select value={asset} onChange={e=>setAsset(e.target.value)}><option value="">Seleccionar fotografía</option>{library.filter(a=>a.permitted_use==='production').map(a=><option key={a.id} value={a.id}>{a.fixture?'Prueba · ':''}{a.width?`${a.width} × ${a.height} · `:''}{a.id.slice(0,8)}</option>)}</select></label>
 {asset&&<p>Fotografía recibida.</p>}
 <label>Encuadre horizontal<input type="range" min="0" max="1" step=".05" value={crop} onChange={e=>setCrop(Number(e.target.value))}/></label>
 <label>Encuadre vertical<input type="range" min="0" max="1" step=".05" value={cropY} onChange={e=>setCropY(Number(e.target.value))}/></label>
 <SocialDesign business={business} csrf={csrf} context={context} value={design} custom={designCopy} onChange={v=>{setDesign(v);setDirty(true);setConfirmed(false);setReview(false);setError('')}} onCustom={(role,text)=>{setDesignCopy(old=>({...old,[role]:text}));setDirty(true);setConfirmed(false);setReview(false);setError('')}} onPriceChange={updateDesignPrice}/>
 <label className="social-check"><input type="checkbox" disabled={busy} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Confirmo que estas afirmaciones son actuales y correctas.</label>
 {pack&&<label>Motivo de esta versión<select aria-label="Motivo de esta versión" value={revisionReason} onChange={e=>setRevisionReason(e.target.value)}><option value="strategy">Cambio para esta publicación</option><option value="factual_correction">Corrección de un dato</option><option value="brand_preference">Preferencia de estilo</option><option value="layout">Encuadre o composición</option></select></label>}
 <button className="button primary" type="submit" disabled={busy||!asset||!confirmed}>{busy?'Preparando…':pack?'Guardar nueva versión':'Preparar publicación'}</button>{pack&&!jobPending&&<p><a href="#social-post-review">Ver imagen preparada · versión {pack.revision}</a></p>}
 </fieldset></form><aside id="social-post-review" tabIndex={-1}>{pack?<><h2>Revisa la versión {pack.revision}</h2>{dirty&&<p role="status">Hay cambios sin guardar. Guarda una nueva versión para revisarlos.</p>}{pack.stale&&<div role="status" className="social-stale"><p>Esta versión necesita revisión: cambió o venció información que utiliza. Su aprobación anterior ya no permite descargarla.</p>{!pack.media_available&&<p>La fotografía ya no está autorizada. Selecciona otra.</p>}<button type="button" className="button secondary" disabled={busy} onClick={()=>void run(recover)}>Revisar con los datos actuales</button></div>}{selectedFacts.length>0&&dirty&&<p className="social-caption">Datos para la nueva versión: {selectedFacts.map(f=>f.text).join(' · ')}</p>}{pack.document.fixture&&<p>Material de prueba</p>}{pack.media_available&&<img className="social-image" src={root+'/packs/'+pack.id+'/image?v='+pack.revision} alt="Vista previa de la publicación"/>}<p className="social-caption">{pack.document.caption}</p>{(pack.document as any).design&&<p>Diseño editable · {({photo_first:'Fotografía protagonista',information:'Tarjeta informativa',photo_only:'Solo fotografía'} as any)[(pack.document as any).design.layout]}</p>}{pack.document.creative_snapshot&&<details className="creative-receipt"><summary>Contexto de esta versión</summary><p>{pack.document.creative_snapshot.voice_rules}</p>{pack.document.creative_snapshot.references.map((r:any)=><p key={r.id}>{r.title}: {r.reason}</p>)}{pack.document.creative_snapshot.question&&<><p>{sourceLabels[pack.document.creative_snapshot.question.source_kind]}: {pack.document.creative_snapshot.question.source}</p><p>Siguiente paso: {pack.document.creative_snapshot.question.next_action}</p></>}<p>Sin volumen de búsqueda medido.</p></details>}<p>Medida prevista: {({qualified_inquiries:'consultas de compra',orders:'pedidos',reach:'alcance',owner_effort:'esfuerzo del negocio'} as any)[pack.document.brief.primary_measure]}. {((pack as any).publication?.post_id)?'Hay un registro manual; consulta sus resultados abajo.':'Todavía no hay resultados registrados.'}</p>{(pack.document as any).learning_snapshot&&<p className="results-origin">Basado en resultados anteriores: {(pack.document as any).learning_snapshot.observation}</p>}<SocialReview business={business} csrf={csrf} pack={pack} dirty={dirty||busy||jobPending} onChanged={async()=>setPack(await request('/packs/'+pack.id))}/>{(pack.document as any).design&&<p><a href="#social-design-editor">Volver a editar el diseño</a></p>}<SocialHistory business={business} pack={pack.id} revision={pack.revision}/></>:<><h2>Tu publicación aparecerá aquí</h2><p>Usaremos tu fotografía y las afirmaciones que confirmes. Podrás ajustar el encuadre y guardar otra versión.</p></>}</aside></div>{pack&&<SocialResults key={pack.id} business={business} csrf={csrf} pack={pack} dirty={dirty||jobPending} onChanged={async()=>setPack(await request('/packs/'+pack.id))} onLearning={value=>{setNextLearning(value);document.querySelector<HTMLDetailsElement>('.proposal-panel')!.open=true;document.querySelector('.proposal-panel')?.scrollIntoView({behavior:'smooth'})}}/>}</section>
}
