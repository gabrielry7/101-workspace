import './contextual-client.ts';
import {allowBackgroundMotion} from './background-policy.ts';
const site=document.querySelector<HTMLElement>('.experience-site');
if(site){
 const nav=site.querySelector<HTMLDetailsElement>('.exp-nav'),narrow=matchMedia('(max-width:760px)');if(nav)nav.open=!narrow.matches;narrow.addEventListener('change',e=>{if(nav)nav.open=!e.matches;});
 const chosen=new URLSearchParams(location.search).get('plato');if(chosen&&site.dataset.pageKind==='selection')site.querySelector<HTMLButtonElement>(`[data-offering-id="${CSS.escape(chosen)}"] [data-demo-add]`)?.click();
 const video=site.querySelector<HTMLVideoElement>('[data-background-video]'),toggle=site.querySelector<HTMLButtonElement>('[data-film-toggle]');
 if(video&&toggle){const film=video.closest<HTMLElement>('.hero-film')!,reduced=matchMedia('(prefers-reduced-motion:reduce)'),connection=(navigator as Navigator&{connection?:{saveData?:boolean}}).connection;let manualPause=false,inView=true;
  const mayStart=()=>allowBackgroundMotion({reducedMotion:reduced.matches,saveData:!!connection?.saveData,documentVisible:!document.hidden,inView,manualPause});
  const sync=()=>{const playing=!video.paused&&!video.ended;film.dataset.filmState=playing?'playing':'poster';const label=playing?'Pausar vídeo de fondo':'Reproducir vídeo de fondo',icon=toggle.querySelector('[data-film-icon]');if(icon)icon.textContent=playing?'Ⅱ':'▷';else toggle.textContent=playing?'Pausar vídeo Ⅱ':'Reproducir vídeo ▷';toggle.setAttribute('aria-label',label);toggle.setAttribute('title',label);toggle.setAttribute('aria-pressed',String(playing));};
  const play=async()=>{if(!video.src){video.src=video.dataset.src!;video.load();}video.muted=true;try{await video.play();}catch{sync();}};
  toggle.hidden=false;toggle.addEventListener('click',()=>{manualPause=!video.paused;if(video.paused)void play();else video.pause();});for(const event of ['playing','pause','ended','error'])video.addEventListener(event,sync);
  if(mayStart()){video.autoplay=true;void play();}else sync();reduced.addEventListener('change',e=>{if(e.matches){video.autoplay=false;video.pause();}});
  new IntersectionObserver(entries=>{for(const e of entries){inView=e.isIntersecting;if(!inView)video.pause();else if(mayStart())void play();}},{threshold:.05}).observe(video);
  document.addEventListener('visibilitychange',()=>{if(!mayStart())video.pause();else void play();});
 }
}
