// Extends the existing B3 client. No network, persistence, provider SDK or business mutation.
const site=document.querySelector<HTMLElement>('.depth-experience');
if(site){
 const skip=document.querySelector<HTMLAnchorElement>('a.skip'),content=site.querySelector<HTMLElement>('#experience-main');
 if(skip&&content)skip.href='#experience-main';
 if(site.dataset.pageKind==='collection'){
  const search=site.querySelector<HTMLInputElement>('[data-menu-search]'),category=site.querySelector<HTMLSelectElement>('[data-menu-category]'),grid=site.querySelector<HTMLElement>('.contextual-collection'),count=site.querySelector<HTMLElement>('[data-menu-count]');
  const update=()=>{
   if(!grid)return;
   grid.dataset.collectionState=search?.value.trim()||category?.value?'filtered':'all';
   const n=[...grid.querySelectorAll<HTMLElement>('[data-offering-id]')].filter(c=>!c.hidden).length;
   if(count)count.textContent=`${n} ${n===1?'plato':'platos'} de ejemplo${n===0?'. Prueba otra búsqueda o cambia la categoría.':''}`;
  };
  search?.addEventListener('input',update);category?.addEventListener('change',update);update();
 }
}
