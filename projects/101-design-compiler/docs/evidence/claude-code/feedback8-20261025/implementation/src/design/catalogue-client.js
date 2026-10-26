// Grouped carta enhancement for the 40-dish catalogue (collection + selection). Plain JS, served as-is.
// Search, category filter, counts and local add feedback only. No network, storage or order state:
// the selection itself stays with the shared contextual client ([data-demo-add] / [data-selection-*]).
const menu=document.querySelector('[data-cat-menu]');
if(menu){
 const fold=s=>s.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().trim();
 const tools=menu.querySelector('[data-cat-tools]'),search=menu.querySelector('[data-cat-search]'),filter=menu.querySelector('[data-cat-filter]'),count=menu.querySelector('[data-cat-count]'),empty=menu.querySelector('[data-cat-empty]');
 const rows=[...menu.querySelectorAll('[data-cat-row]')],sections=[...menu.querySelectorAll('[data-cat-section]')],total=rows.length;
 const apply=()=>{
  const terms=fold(search.value).split(/\s+/).filter(Boolean),group=filter.value;let shown=0;
  for(const row of rows){const show=(!group||row.dataset.catGroup===group)&&terms.every(t=>(row.dataset.catSearch||'').includes(t));row.hidden=!show;if(show)shown++;}
  for(const section of sections)section.hidden=!section.querySelector('[data-cat-row]:not([hidden])');
  const filtered=terms.length>0||group!=='';
  count.textContent=filtered?`${shown} de ${total} platos${shown?'':'. Prueba otra búsqueda o quita los filtros.'}`:`${total} platos de ejemplo`;
  empty.hidden=shown>0;menu.dataset.catState=filtered?'filtered':'all';
 };
 const reset=()=>{search.value='';filter.value='';apply();};
 search.addEventListener('input',apply);filter.addEventListener('change',apply);
 search.addEventListener('keydown',e=>{if(e.key==='Escape'&&search.value){search.value='';apply();}});
 for(const button of menu.querySelectorAll('[data-cat-reset]'))button.addEventListener('click',()=>{reset();search.focus();});
 // Category anchors: never leave the native hash pointing at a hidden group.
 const index=menu.querySelector('[data-cat-index]'),selection=document.querySelector('[data-cat-selection]');
 // Native <details> stay the semantic control; JS only sets the responsive default (open when there is room).
 const art=!!document.querySelector('.artistic-site');
 const indexRoom=matchMedia('(min-width:761px)'),selectionRoom=matchMedia(art?'(min-width:1101px)':'(min-width:761px)');
 if(index){index.open=indexRoom.matches;indexRoom.addEventListener('change',e=>{index.open=e.matches;});}
 if(selection){selection.open=selectionRoom.matches;selectionRoom.addEventListener('change',e=>{selection.open=e.matches;});}
 for(const link of menu.querySelectorAll('[data-cat-link]'))link.addEventListener('click',()=>{if(search.value.trim()||(filter.value&&filter.value!==link.dataset.catLink))reset();if(index&&!indexRoom.matches)index.open=false;});
 const query=new URLSearchParams(location.search),q=query.get('q'),cat=query.get('cat');
 if(q)search.value=q;if(cat&&[...filter.options].some(o=>o.value===cat))filter.value=cat;
 tools.hidden=false;apply();

 // Selection page: concise local feedback after the shared client has handled the click.
 const toast=menu.querySelector('[data-cat-toast]');
 if(toast){
  const text=toast.querySelector('[data-cat-toast-text]'),announce=menu.querySelector('[data-cat-announce]'),panel=selection;
  const source=document.querySelector('[data-selection-count]'),mirror=document.querySelector('[data-cat-summary-count]');
  // The shared client owns the count; the summary only mirrors its text (no second state).
  if(source&&mirror){const sync=()=>{mirror.textContent=source.textContent;};sync();new MutationObserver(sync).observe(source,{childList:true,characterData:true,subtree:true});}
  const openForHash=()=>{if(selection&&(location.hash==='#seleccion'||location.hash==='#cat-seleccion'))selection.open=true;};
  openForHash();addEventListener('hashchange',openForHash);
  document.addEventListener('click',e=>{const jump=e.target instanceof Element?e.target.closest('a[href="#cat-seleccion"]'):null;if(jump&&selection)selection.open=true;});
  let panelInView=false;
  if(panel&&'IntersectionObserver' in window)new IntersectionObserver(entries=>{panelInView=entries.some(e=>e.isIntersecting);if(panelInView)toast.hidden=true;}).observe(panel);
  const counter=()=>source?.textContent??'';
  document.addEventListener('click',e=>{
   const target=e.target instanceof Element?e.target:null,add=target?.closest('[data-demo-add]');
   if(add&&menu.contains(add))queueMicrotask(()=>{const message=`${add.dataset.demoAdd} añadido. ${counter()}.`;text.textContent=message;announce.textContent=message;toast.hidden=panelInView;});
   else if(target?.closest('[data-selection-clear]'))queueMicrotask(()=>{toast.hidden=true;announce.textContent='Selección vaciada.';});
  });
 }
}
