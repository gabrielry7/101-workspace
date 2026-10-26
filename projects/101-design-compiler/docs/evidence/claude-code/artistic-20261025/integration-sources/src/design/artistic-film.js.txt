// Loaded only with an artistic film. Never autoload video or enable audio.
for(const box of document.querySelectorAll('[data-art-film]')){
 const video=box.querySelector('[data-art-video]'),button=box.querySelector('[data-art-film-toggle]'),status=box.querySelector('[data-art-film-status]');
 if(!(video instanceof HTMLVideoElement)||!button)continue;button.hidden=false;
 const sync=()=>{const playing=!video.paused;box.dataset.artFilmState=playing?'playing':'poster';button.textContent=playing?'Pausar película':'Ver película';button.setAttribute('aria-label',playing?'Pausar película ilustrativa':'Reproducir película ilustrativa sin audio');};
 button.addEventListener('click',async()=>{if(!video.paused){video.pause();return;}video.muted=true;if(!video.src)video.src=video.dataset.src;try{await video.play();if(status)status.textContent='';}catch{if(status)status.textContent='La película no está disponible. Puedes seguir explorando las imágenes.';}sync();});
 video.addEventListener('play',sync);video.addEventListener('pause',sync);document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();});matchMedia('(prefers-reduced-motion:reduce)').addEventListener('change',e=>{if(e.matches)video.pause();});
}
