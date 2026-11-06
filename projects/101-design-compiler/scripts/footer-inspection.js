(() => {
  const root=document.querySelector('[data-footer-bone]'), box=root.getBoundingClientRect();
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT), brokenWords=[];
  for(let node=walker.nextNode();node;node=walker.nextNode()){
    if(!node.textContent.trim()||node.parentElement.closest('script,style,.bf-sr-only,[aria-hidden=true]'))continue;
    for(const match of node.textContent.matchAll(/\S+/g)){
      const range=document.createRange();range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
      const ys=[...range.getClientRects()].map(r=>Math.round(r.y));
      if(new Set(ys).size>1)brokenWords.push(match[0]);
    }
  }
  return {
    height:box.height,
    overflow:document.documentElement.scrollWidth>innerWidth+1,
    brokenWords,
    groups:root.querySelectorAll('[data-footer-part=group]').length,
    soon:root.querySelectorAll('[aria-disabled=true]').length,
    cookieDisabled:root.querySelector('[data-footer-cookie]').disabled,
    links:[...root.querySelectorAll('a')].map(a=>({href:a.href,name:a.getAttribute('aria-label')||a.textContent.trim()})),
    regions:['transition','directory','legal'].map(role=>root.querySelector('[data-footer-part='+role+']').getBoundingClientRect().height),
    inspectorLoaded:[...document.scripts].some(s=>s.src.includes('measure')||s.src.includes('workshop')),
  };
})()
