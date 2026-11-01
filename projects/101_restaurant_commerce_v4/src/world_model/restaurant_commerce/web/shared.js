"use strict";
// No HTML parsing or dynamic code generation: remote values are always text.
window.CommerceUI = (() => {
  let policy = {demo_mode: false, checkout_origins: [], tracking_origins: []};
  const $ = id => document.getElementById(id);
  function node(tag, props = {}, ...children) {
    const el = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === 'className') el.className = value;
      else if (key === 'onClick' || key === 'onChange') {
        el.addEventListener(key === 'onClick' ? 'click' : 'change', value);
      } else if (key === 'disabled' || key === 'checked') el[key] = Boolean(value);
      else if (value !== null && value !== undefined) el.setAttribute(key, String(value));
    });
    children.flat(Infinity).forEach(child => {
      if (child !== null && child !== undefined) el.appendChild(
        child instanceof Node ? child : document.createTextNode(String(child))
      );
    });
    return el;
  }
  function replace(el, ...children) {
    while (el.firstChild) el.removeChild(el.firstChild);
    children.flat(Infinity).forEach(child => el.appendChild(child));
  }
  function safeURL(value, kind) {
    if (typeof value !== 'string' || /[\\\u0000-\u0020\u007f]/.test(value)) return null;
    try {
      const url = new URL(value, location.origin);
      if (url.username || url.password) return null;
      // Simulators only: do not allow arbitrary same-origin navigation.
      const prefix = kind === 'checkout' ? '/demo/pay/' : '/demo/delivery/';
      if (policy.demo_mode && url.origin === location.origin &&
          url.pathname.startsWith(prefix) &&
          /^[a-zA-Z0-9_-]+$/.test(url.pathname.slice(prefix.length)) &&
          !url.search && !url.hash) return url.href;
      const allowed = kind === 'checkout' ? policy.checkout_origins : policy.tracking_origins;
      return url.protocol === 'https:' && allowed.includes(url.origin) ? url.href : null;
    } catch (_) { return null; }
  }
  function bind(actions) {
    ['click', 'input'].forEach(event => {
      document.querySelectorAll('[data-' + event + ']').forEach(el => {
        const action = actions[el.getAttribute('data-' + event)];
        if (typeof action !== 'function') throw new Error('Unknown UI action');
        el.addEventListener(event, action);
      });
    });
  }
  let lastSuccess = null;
  const unconfirmed=new Set();
  function connection(state, message) {
    const banner=$('networkStatus'); if(!banner)return;
    banner.hidden=false; banner.dataset.state=navigator.onLine===false?'offline':state;
    banner.textContent=navigator.onLine===false?'Sin conexión. Los datos pueden estar desactualizados; no se enviarán acciones automáticamente.':message;
  }
  async function request(url,options={}) {
    const controller=new AbortController(), outer=options.signal;
    const abort=()=>controller.abort();
    if(outer){if(outer.aborted)abort();else outer.addEventListener('abort',abort,{once:true});}
    const timer=setTimeout(abort,options.timeout || 15000);
    try {
      const response=await fetch(url,{...options,signal:controller.signal,cache:'no-store'});
      const data=await response.json();
      if(response.ok){unconfirmed.delete(url);lastSuccess=Date.now();connection(unconfirmed.size?'stale':'fresh',unconfirmed.size?'Hay consultas o acciones sin confirmar. Revisa los avisos de cada sección antes de actuar.':'Servidor accesible · última respuesta '+new Date(lastSuccess).toLocaleTimeString('es-CO'));}
      else {if(response.status>=500)unconfirmed.add(url);connection('stale','No se pudo actualizar. Conservamos los últimos datos; revisa antes de actuar.');}
      return {ok:response.ok,status:response.status,json:async()=>data};
    } catch(error){unconfirmed.add(url);connection('stale','No llegó la respuesta. Conserva esta página y consulta el estado antes de reintentar.');throw error;}
    finally{clearTimeout(timer);if(outer)outer.removeEventListener('abort',abort);}
  }
  function poll(run,{interval=15000,active=()=>true}={}) {
    let timer=null,busy=false,queued=false,failures=0,stopped=false;
    function schedule(){clearTimeout(timer);if(!stopped)timer=setTimeout(tick,Math.min(60000,interval*Math.pow(2,failures)));}
    async function tick(){
      clearTimeout(timer);
      if(stopped)return;
      if(busy){queued=true;return;}
      if(document.hidden||navigator.onLine===false||!active()){schedule();return;}
      busy=true;queued=false;
      try{const result=await run();failures=result===false?Math.min(3,failures+1):0;}
      catch(_){failures=Math.min(3,failures+1);}
      finally{busy=false;if(queued){queued=false;timer=setTimeout(tick,0);}else schedule();}
    }
    const resume=()=>{if(!document.hidden && navigator.onLine!==false)tick();};
    document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);
    schedule();return {refresh:tick,stop:()=>{stopped=true;clearTimeout(timer);document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume);}};
  }
  window.addEventListener('offline',()=>connection('offline',''));
  window.addEventListener('online',()=>connection('stale','Conexión disponible. Verificando el estado…'));
  async function start(run) {
    if(window.CommerceSupported===false)return;
    try{const response=await request('/api/browser-policy',{timeout:3000});if(response.ok)policy=await response.json();}
    catch(_){/* Fail closed for external navigation; the catalog still loads. */}
    const badge=$('demoBadge');if(badge)badge.hidden=!(policy.demo_mode||policy.wompi_sandbox);
    const demo=$('demoAddressButton');if(demo)demo.hidden=!policy.demo_mode;
    await run();const boot=$('bootNotice');if(boot)boot.hidden=true;
  }
  const dateTime=(value,zone='America/Bogota')=>new Intl.DateTimeFormat('es-CO',{timeZone:zone,month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value));
  const money = n => new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', maximumFractionDigits: 0
  }).format(Number(n) || 0);
  const path = value => encodeURIComponent(String(value));
  return {$, node, replace, safeURL, bind, start, money, path, request, poll, dateTime, connection};
})();
