'use strict';
(async()=>{
 const params=new URLSearchParams(location.search);history.replaceState(null,'','/connections/google/callback');
 const body={state:params.get('state'),code:params.get('code'),error:params.get('error')};
 try{const me=await window.CommerceUI.request('/api/staff/me',{credentials:'same-origin',cache:'no-store'});if(!me.ok)throw Error('Inicia sesión y vuelve a conectar Google.');const identity=await me.json();const r=await window.CommerceUI.request('/connections/google/complete',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-101-CSRF':identity.csrf},body:JSON.stringify(body)});if(!r.ok)throw Error('Esta autorización venció o ya se utilizó. Vuelve a iniciar la conexión.');location.replace('/connections');}catch(e){document.getElementById('callbackStatus').textContent=e.message;}
})();
