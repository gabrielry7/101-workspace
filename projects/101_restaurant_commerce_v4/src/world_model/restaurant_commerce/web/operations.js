'use strict';
(() => {
  if(window.CommerceSupported===false)return;
  const {$,node:h,replace,money,path,dateTime}=window.CommerceUI;
  let settings=null,generation=0,busy=false;
  const business=$('business'),message=$('settingsMessage');
  function clear(){++generation;settings=null;$('settingsFields').disabled=true;replace($('stockRows'));replace($('dailyResult'));message.textContent='Carga la disponibilidad del negocio seleccionado.';}
  business.addEventListener('input',clear);window.addEventListener('staffchange',clear);
  const endpoint=tail=>`/api/operator/restaurants/${path(business.value)}/${tail}`;
  async function request(url,body){
    const version=generation;
    const response=await window.CommerceStaff.request(url,body?{method:'PUT',body:JSON.stringify(body)}:{});
    const data=await response.json();if(version!==generation){const e=new Error('El negocio cambió');e.stale=true;throw e;}
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Revisa los valores antes de guardar.');return data;
  }
  const manager=()=>window.CommerceStaff.identity()?.businesses.some(b=>b.business_id===business.value&&b.role==='manager');
  const minutes=value=>{const parts=value.split(':').map(Number);return parts[0]*60+parts[1];};
  const clock=value=>String(Math.floor(Math.min(value,1439)/60)).padStart(2,'0')+':'+String(Math.min(value,1439)%60).padStart(2,'0');
  function render(data){
    settings=data;const p=data.policy;
    $('orderingEnabled').checked=p.ordering_enabled;$('scheduledPickup').checked=p.scheduled;
    $('opens').value=clock(p.opens);$('closes').value=clock(p.closes);$('slotMinutes').value=p.slot_minutes;$('leadMinutes').value=p.lead_minutes;$('slotCapacity').value=p.capacity;$('closedDates').value=p.closed_dates.join(', ');
    replace($('weekdayFields'),...['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].map((day,n)=>h('label',{className:'option'},h('input',{type:'checkbox',value:n,checked:p.weekdays.includes(n)}),day)));
    $('settingsFields').disabled=!manager();message.textContent='Hora local: '+data.timezone+(manager()?' · Cambios registrados con tu identidad.':' · Solo lectura.');
    replace($('stockRows'),...data.items.map(item=>{
      const count=h('input',{type:'number',min:0,max:100000,value:item.remaining===null?'':item.remaining,'aria-label':'Unidades de '+item.name,disabled:!manager()});
      const sold=h('input',{type:'checkbox',checked:item.sold_out,disabled:!manager()});
      const reason=h('input',{placeholder:'Motivo del ajuste','aria-label':'Motivo para '+item.name,maxlength:500,disabled:!manager()});
      const save=h('button',{disabled:!manager(),onClick:async()=>{
        if(busy||!reason.value.trim()) {message.textContent='Indica el motivo del ajuste de existencias.';reason.focus();return;}
        busy=true;save.disabled=true;const version=generation;
        try{await request(endpoint('stock/'+path(item.id)),{expected_version:item.version,remaining:count.value===''?null:Number(count.value),sold_out:sold.checked,reason:reason.value.trim()});await load();}
        catch(error){if(!error.stale){await load(false);message.textContent=error.message+' Consulta los datos antes de volver a guardar.';}}
        finally{busy=false;if(version===generation)save.disabled=!manager();}
      }},'Guardar');
      return h('div',{className:'stock-row'},h('strong',{},item.name),count,h('label',{className:'option'},sold,'Agotado'),reason,save);
    }));
  }
  async function load(clearMessage=true){
    try{const data=await request(endpoint('settings'));render(data);}
    catch(error){if(!error.stale){$('settingsFields').disabled=true;if(clearMessage)message.textContent=error.message;}}
  }
  $('loadSettings').addEventListener('click',()=>load());
  $('settingsForm').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!settings)return;busy=true;const version=generation;$('settingsFields').disabled=true;
    const body={expected_version:settings.version,ordering_enabled:$('orderingEnabled').checked,scheduled:$('scheduledPickup').checked,weekdays:[...$('weekdayFields').querySelectorAll('input:checked')].map(i=>Number(i.value)),opens:minutes($('opens').value),closes:minutes($('closes').value),slot_minutes:Number($('slotMinutes').value),lead_minutes:Number($('leadMinutes').value),capacity:Number($('slotCapacity').value),closed_dates:$('closedDates').value.split(',').map(v=>v.trim()).filter(Boolean),reason:$('settingsReason').value.trim()};
    try{render(await request(endpoint('settings'),body));message.textContent='Horarios guardados. Los pedidos existentes conservan su hora.';}
    catch(error){if(!error.stale){message.textContent=error.message+' Carga la disponibilidad antes de reintentar.';}}
    finally{busy=false;if(version!==generation)$('settingsFields').disabled=true;}
  });
  $('loadDaily').addEventListener('click',async()=>{
    const button=$('loadDaily');button.disabled=true;
    try{
      if(!$('financeDate').value){const config=await request(endpoint('settings'));const parts=new Intl.DateTimeFormat('en-CA',{timeZone:config.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const val=t=>parts.find(p=>p.type===t).value;$('financeDate').value=val('year')+'-'+val('month')+'-'+val('day');}
      const data=await request(endpoint('daily-finance')+'?day='+path($('financeDate').value));
      const metric=(label,value)=>h('div',{className:'card metric'},h('span',{className:'meta'},label),h('strong',{},value));
      replace($('dailyResult'),h('p',{className:'meta'},data.date+' · '+data.timezone),h('div',{className:'metrics'},metric('Pagos confirmados (incluye devueltos)',money(data.gross_minor)),metric('Devoluciones completas confirmadas',money(data.confirmed_full_refunds_minor)),metric('Devoluciones parciales confirmadas',money(data.confirmed_partial_refunds_minor)),metric('Balance conocido de esos pedidos',money(data.known_balance_minor))),h('div',{className:'notice'},'Comisiones del proveedor: sin verificar. Neto liquidado: sin verificar. No uses este resumen como cierre bancario.'),h('p',{},data.orders+' pedidos · '+data.unconfirmed_orders+' sin pago confirmado · '+data.open_reviews_all_dates+' revisiones abiertas de todas las fechas.'));
    }catch(error){if(!error.stale)$('dailyResult').textContent=error.message;}
    finally{button.disabled=false;}
  });
})();
