import './experience-client.ts';
const root=document.querySelector<HTMLElement>('.depth-experience');
if(root){
 const nav=root.querySelector<HTMLDetailsElement>('[data-depth-nav]'),summary=nav?.querySelector('summary');
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav?.open){nav.open=false;summary?.focus();}});
 document.addEventListener('click',e=>{if(nav?.open&&e.target instanceof Node&&!nav.contains(e.target))nav.open=false;});
 const tools=root.querySelector<HTMLElement>('[data-journal-tools]'),category=tools?.querySelector<HTMLSelectElement>('[data-journal-category]'),count=tools?.querySelector<HTMLElement>('[data-journal-count]');
 if(tools&&category&&count){tools.hidden=false;category.addEventListener('change',()=>{let n=0;for(const card of root.querySelectorAll<HTMLElement>('[data-editorial-id]')){card.hidden=!!category.value&&card.dataset.journalCategory!==category.value;if(!card.hidden)n++;}const grid=tools.parentElement?.querySelector<HTMLElement>('.journal-grid');if(grid)grid.dataset.journalLayout=category.value?'filtered':'all';count.textContent=`${n} ${n===1?'relato':'relatos'} de muestra`;});}
 const reduced=matchMedia('(prefers-reduced-motion:reduce)');if(!reduced.matches){const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){e.target.classList.add('has-arrived');observer.unobserve(e.target);}},{threshold:.1});for(const e of root.querySelectorAll('[data-reveal]'))observer.observe(e);reduced.addEventListener('change',e=>{if(e.matches){observer.disconnect();for(const el of root.querySelectorAll('.has-arrived'))el.classList.remove('has-arrived');}});}
}
