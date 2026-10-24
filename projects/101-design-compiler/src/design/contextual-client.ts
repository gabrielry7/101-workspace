// Shared enhancement only. No fetch, analytics, storage, forms or backend.
const root=document.querySelector<HTMLElement>('.contextual-site');
if(root){
 const disclosure=root.querySelector<HTMLDetailsElement>('.nav-disclosure');
 disclosure?.addEventListener('keydown',event=>{if(event.key==='Escape'&&matchMedia('(max-width:760px)').matches&&getComputedStyle(disclosure.querySelector('summary')!).display!=='none'){disclosure.open=false;disclosure.querySelector('summary')!.focus();event.preventDefault();}});
 const search=root.querySelector<HTMLInputElement>('[data-menu-search]'),category=root.querySelector<HTMLSelectElement>('[data-menu-category]');
 const cards=[...root.querySelectorAll<HTMLElement>('[data-offering-id]')];
 const normalized=(s:string)=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 function filter(){let count=0;for(const card of cards){card.hidden=Boolean((category?.value&&card.dataset.offeringId!==category.value)||!normalized(card.dataset.search??'').includes(normalized(search?.value??'')));if(!card.hidden)count++;}
  const status=root!.querySelector('[data-menu-count]');if(status)status.textContent=`${count} platos de ejemplo`;
 }
 search?.addEventListener('input',filter);category?.addEventListener('change',filter);
 root.querySelector<HTMLElement>('[data-menu-tools]')?.removeAttribute('hidden');
 const selection:string[]=[];const update=()=>{const list=root.querySelector('[data-selection-list]')!;list.replaceChildren(...selection.map(name=>{const li=document.createElement('li');li.textContent=name;return li;}));
  root.querySelector('[data-selection-count]')!.textContent=`${selection.length} platos elegidos`;root.querySelector('[data-selection-status]')!.textContent=selection.length?'Selección local de ejemplo. No se ha enviado ningún pedido.':'Una carta para imaginar.';
 };
 for(const button of root.querySelectorAll<HTMLButtonElement>('[data-demo-add]')){button.hidden=!root.querySelector('[data-selection-list]');button.addEventListener('click',()=>{selection.push(button.dataset.demoAdd!);update();});}
 const clear=root.querySelector<HTMLButtonElement>('[data-selection-clear]');if(clear){clear.hidden=false;clear.addEventListener('click',()=>{selection.length=0;update();});}
 for(const button of root.querySelectorAll<HTMLButtonElement>('[data-demo-table]:not(:disabled)'))button.addEventListener('click',()=>{for(const b of root.querySelectorAll('[data-demo-table]'))b.setAttribute('aria-pressed',String(b===button));});
 const request=root.querySelector<HTMLButtonElement>('.demo-request');if(request){request.hidden=false;request.addEventListener('click',()=>{const table=root.querySelector('[data-demo-table][aria-pressed=true]')?.getAttribute('data-demo-table');
  root.querySelector('[data-request-status]')!.textContent=`Resumen de ejemplo: ${root.querySelector<HTMLSelectElement>('[data-party]')!.value}${table?`, mesa ${table}`:''}. No se ha reservado ni enviado nada.`;
 });}
}
