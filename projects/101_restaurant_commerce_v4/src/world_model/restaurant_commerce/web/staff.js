"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let identity = null, generation = 0, requestedBusinessApplied = false;
  const status = $('staffStatus'), form = $('staffLogin');
  const sharedLogin = () => location.replace('/workspace/login?next='+encodeURIComponent(location.pathname+location.search));
  function retainBusinessLinks() {
    const business=$('business').value;
    if(!identity?.businesses.some(b=>b.business_id===business))return;
    const staffPaths=['/admin','/delivery','/growth','/campaigns','/whatsapp','/sms','/connections','/customers/signup'];
    document.querySelectorAll('a[href]').forEach(anchor=>{
      const url=new URL(anchor.href,location.origin);
      if(url.origin!==location.origin)return;
      if(staffPaths.includes(url.pathname))url.searchParams.set('business_id',business);
      else if(url.pathname.startsWith('/workspace/'))url.searchParams.set('business',business);
      else return;
      anchor.href=url.pathname+url.search+url.hash;
    });
  }
  function publish(value) {
    identity = value; ++generation;
    form.hidden = !!value; $('staffLogout').hidden = !value; $('staffLogoutAll').hidden = !value;
    status.textContent = value ? 'Sesión de ' + value.username : 'Inicia sesión para acceder a este negocio.';
    const list = $('staffBusinesses'); list.replaceChildren();
    if (value) {
      for (const b of value.businesses) { const o=document.createElement('option');o.value=b.business_id;o.label=b.name+' · '+b.role;list.append(o); }
      const requested=new URLSearchParams(location.search).get('business_id');
      if (!requestedBusinessApplied && requested && value.businesses.some(b=>b.business_id===requested)) $('business').value=requested;
      requestedBusinessApplied = true;
      if (!value.businesses.some(b=>b.business_id===$('business').value)) $('business').value=value.businesses[0]?.business_id || '';
    }
    if ($('customerWorkspace') && value) $('customerWorkspace').href='/workspace/customers?business='+encodeURIComponent($('business').value);
    if(value)retainBusinessLinks();
    window.dispatchEvent(new CustomEvent('staffchange', {detail:{authenticated:!!value}}));
  }
  const boundedFetch=window.CommerceUI.request;
  async function restore() {
    const version=generation;
    try {
      const r = await boundedFetch('/api/staff/me', {credentials:'same-origin',cache:'no-store'});
      const value=r.ok ? await r.json() : null;
      if(version!==generation)return;
      if (r.ok) publish(value); else if (r.status===401) {publish(null);sharedLogin();}
      else throw new Error('No fue posible verificar la sesión.');
    } catch (_) { if(version!==generation)return; publish(null); status.textContent='Sin conexión para verificar la sesión. Vuelve a iniciar sesión.'; }
  }
  const ready=restore();
  async function request(url, options={}) {
    await ready;
    if(!identity) throw new Error('Inicia sesión para continuar.');
    const version=generation;
    const r=await boundedFetch(url,{...options,credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-101-CSRF':identity.csrf,...options.headers}});
    if(r.status===401 && version===generation){publish(null);sharedLogin();}
    if(version!==generation){const e=new Error('La sesión cambió.');e.stale=true;throw e;}
    return r;
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault(); const button=$('staffSignIn');button.disabled=true;
    try {
      const r=await boundedFetch('/api/staff/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-101-Login':'1'},body:JSON.stringify({username:$('staffUsername').value,password:$('staffPassword').value})});
      $('staffPassword').value='';
      if(!r.ok)throw new Error(r.status===429?'Demasiados intentos. Espera un minuto.':'No fue posible iniciar sesión. Verifica tus datos.');
      await restore();
    } catch(error){status.textContent=error.message;}
    finally{$('staffPassword').value='';button.disabled=false;}
  });
  async function logout(all) {
    try {const r=await request('/api/staff/'+(all?'logout-all':'logout'),{method:'POST'});if(!r.ok)throw new Error('No se confirmó el cierre de sesión.');publish(null);try{localStorage.setItem('101-session-ended',String(Date.now()));}catch(_){}sharedLogin();}
    catch(error){publish(null);status.textContent='No se confirmó el cierre en el servidor. Reintenta al recuperar la conexión; no compartas este dispositivo.';}
  }
  $('staffLogout').addEventListener('click',()=>logout(false));
  $('staffLogoutAll').addEventListener('click',()=>logout(true));
  $('business').addEventListener('input',retainBusinessLinks);
  window.addEventListener('pageshow',event=>{if(event.persisted){publish(null);restore();}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && identity)restore();});
  window.addEventListener('storage',event=>{if(event.key==='101-session-ended'){publish(null);sharedLogin();}});
  window.CommerceStaff={request,ready, identity:()=>identity};
})();
