// Current-B3 only: background motion policy, example-map actions and the reservation summary.
// No network except the OpenStreetMap iframe mounted after an explicit click. No coordinates are stored or sent.
const reduced=matchMedia('(prefers-reduced-motion: reduce)'),conn=navigator.connection;
const saveData=()=>!!(conn&&conn.saveData);
const heroes=[...document.querySelectorAll('[data-feedback-background]')];
const toggle=document.querySelector('[data-motion-toggle]');
let userChoice=null; // null = follow preferences; 'pause' | 'play' = explicit utility choice
const state=new WeakMap();
const inView=el=>{const r=el.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth};
const allowed=h=>{if(userChoice==='pause')return false;const ok=!document.hidden&&state.get(h).visible;if(userChoice==='play')return ok;return ok&&!reduced.matches&&!saveData()};
const mark=(h,p)=>{const v=p?'playing':'poster';h.dataset.filmState=v;h.dataset.artFilmState=v;h.dataset.bgState=v};
function label(){
 if(!toggle)return;
 const playing=heroes.some(h=>h.dataset.bgState==='playing');
 toggle.hidden=!heroes.length;
 toggle.setAttribute('aria-pressed',String(!playing));
 toggle.textContent=playing?'Pausar vídeo de fondo':'Reproducir vídeo de fondo';
}
function sync(h){
 const v=h.querySelector('video');if(!v)return;
 if(!allowed(h)){if(!v.paused)v.pause();mark(h,false);label();return}
 if(!v.paused&&!v.ended){mark(h,true);label();return}
 if(!v.getAttribute('src')&&v.dataset.src){v.src=v.dataset.src;v.load()}
 const p=v.play();
 if(p&&p.then)p.then(()=>{mark(h,!v.paused);label()},()=>{mark(h,false);label()});
}
for(const h of heroes){
 state.set(h,{visible:inView(h)});
 const v=h.querySelector('video');
 if(v){
  v.addEventListener('playing',()=>{mark(h,true);label()});
  for(const e of ['pause','ended','error'])v.addEventListener(e,()=>{mark(h,false);label()});
 }
 if('IntersectionObserver' in window){
  state.get(h).visible=false;
  new IntersectionObserver(e=>{state.get(h).visible=e[e.length-1].isIntersecting;sync(h)},{threshold:.15}).observe(h);
 }
 mark(h,false);
}
label();
const all=()=>heroes.forEach(sync);
if(!('IntersectionObserver' in window))all();
document.addEventListener('visibilitychange',all);
reduced.addEventListener('change',all);
if(conn&&conn.addEventListener)conn.addEventListener('change',all);
if(toggle)toggle.addEventListener('click',()=>{const playing=heroes.some(h=>h.dataset.bgState==='playing');userChoice=playing?'pause':'play';all()});
// ---- Example location ----
const loc=document.querySelector('[data-location]');
if(loc){
 const d=loc.dataset,lat=Number(d.lat),lon=Number(d.lon);
 const mapBtn=loc.querySelector('[data-map-load]'),frame=loc.querySelector('[data-map-frame]'),distBtn=loc.querySelector('[data-distance]'),out=loc.querySelector('[data-distance-out]');
 for(const el of loc.querySelectorAll('[data-js-only]'))el.hidden=false;
 if(mapBtn&&frame)mapBtn.addEventListener('click',()=>{
  if(frame.querySelector('iframe'))return;
  const f=document.createElement('iframe');f.src=d.embed;f.title='Mapa de OpenStreetMap con el punto de ejemplo';f.loading='lazy';f.referrerPolicy='no-referrer';f.width='600';f.height='400';
  frame.prepend(f);frame.dataset.mounted='true';
  const cap=loc.querySelector('[data-map-attribution]');if(cap)cap.hidden=false;
  mapBtn.disabled=true;mapBtn.textContent='Mapa mostrado';
 });
 const rad=v=>v*Math.PI/180;
 const km=(a,b,c,e)=>{const dl=rad(c-a),dn=rad(e-b),v=Math.sin(dl/2)**2+Math.cos(rad(a))*Math.cos(rad(c))*Math.sin(dn/2)**2;return 6371.0088*2*Math.atan2(Math.sqrt(Math.min(1,Math.max(0,v))),Math.sqrt(Math.min(1,Math.max(0,1-v))))};
 if(distBtn&&out){
  if(!('geolocation' in navigator)){distBtn.disabled=true;out.textContent='Tu navegador no permite calcular la distancia. Puedes abrir el mapa o las indicaciones.'}
  else distBtn.addEventListener('click',()=>{
   out.textContent='Esperando el permiso de ubicación del navegador…';distBtn.disabled=true;
   navigator.geolocation.getCurrentPosition(p=>{
    const v=km(p.coords.latitude,p.coords.longitude,lat,lon);
    out.textContent=`Aproximadamente ${v<10?v.toFixed(1):Math.round(v)} km en línea recta hasta el punto de ejemplo. No es la distancia en coche ni un tiempo de viaje.`;
    distBtn.disabled=false;distBtn.textContent='Calcular de nuevo';
   },e=>{
    out.textContent=e.code===1?'No diste permiso de ubicación. Puedes intentarlo de nuevo o abrir las indicaciones en Google Maps.':e.code===3?'La ubicación tardó demasiado. Inténtalo de nuevo.':'No se pudo obtener tu ubicación. Inténtalo de nuevo.';
    distBtn.disabled=false;distBtn.textContent='Reintentar';
   },{timeout:10000,maximumAge:0,enableHighAccuracy:false});
  });
 }
}
// ---- Reservation summary (local text only) ----
const form=document.querySelector('[data-visit-form]');
if(form){
 const out=form.querySelector('[data-visit-summary]'),val=n=>{const el=form.elements[n];return el?el.value:''};
 const upd=()=>{const date=val('fecha');out.textContent=`${val('personas')} · ${date?new Date(date+'T12:00').toLocaleDateString('es',{weekday:'long',day:'numeric',month:'long'}):'sin fecha elegida'} · ${val('momento')} · ${val('ocasion')}. Resumen de ejemplo: no se envía ni se reserva nada.`};
 form.addEventListener('input',upd);form.addEventListener('submit',e=>{e.preventDefault();upd();const s=form.querySelector('[data-request-status]');if(s)s.textContent='Resumen preparado en esta pantalla. No se ha enviado ninguna reserva.'});upd();
}
