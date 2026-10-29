"use strict";
(()=>{

const {node: h, replace, safeURL, bind, start, path} = window.CommerceUI;
const itemDialog = document.getElementById("itemDialog");
const qs=new URLSearchParams(location.search),businessId=qs.get('business_id')||'demo-restaurant-bogota';let store=null,cart=[],activeItem=null,foodQuote=null,deliveryQuote=null,fulfillment='pickup';const money=n=>new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n||0);const $=id=>document.getElementById(id);
let noticeTimer, foodGeneration=0, deliveryGeneration=0;
const returnHint=qs.get('id'); let wompiReturnId=returnHint&&/^[A-Za-z0-9_-]{1,100}$/.test(returnHint)?returnHint:null;
let checkoutBusy=false, checkoutIntent=null, reservationBusy=false, reservationIntent=null;
const recoveryStorageKey='101.checkout.v1:'+businessId, recoveryTtlMs=24*60*60*1000;
let recoveryRecord=null, recoveryState='idle', recoveredOrder=null, recoveryBusy=false, recoveryStorageAvailable=true;
function readPendingCheckout(){
  try {
    const raw=localStorage.getItem(recoveryStorageKey);
    if(!raw)return;
    let record;try {record=JSON.parse(raw);}catch {recoveryState='invalid';return;}
    if(!record||typeof record!=='object'){recoveryState='invalid';return;}
    if(record.version!==1||record.business_id!==businessId||!/^[a-f0-9]{32}$/.test(record.idempotency_key)||!/^[a-f0-9]{64}$/.test(record.recovery_secret)||!Number.isFinite(record.created_at)){
      recoveryState='invalid';return;
    }
    recoveryRecord=record;
    recoveryState=record.created_at>Date.now()||Date.now()-record.created_at>=recoveryTtlMs?'expired':'checking';
  } catch {recoveryStorageAvailable=false;}
}
function persistRecovery(){
  if(!recoveryRecord)return;
  try {localStorage.setItem(recoveryStorageKey,JSON.stringify(recoveryRecord));}
  catch {recoveryStorageAvailable=false;}
}
function clearRecovery(){
  recoveryRecord=null;recoveredOrder=null;recoveryState='idle';
  try {localStorage.removeItem(recoveryStorageKey);}catch {recoveryStorageAvailable=false;}
  replace($('checkoutRecovery'));
}
function newRecovery(){
  const bytes=new Uint8Array(32);crypto.getRandomValues(bytes);
  recoveryRecord={version:1,business_id:businessId,idempotency_key:intentKey(),
    recovery_secret:Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(''),created_at:Date.now()};
  persistRecovery();renderRecovery();return recoveryRecord;
}
function recoveryAction(label,callback,disabled=false){return h('button',{className:'secondary','data-recovery-action':'true',disabled,onClick:callback},label);}
function renderRecovery(){
  const root=$('checkoutRecovery');replace(root);
  if(recoveryState==='idle'){
    if(wompiReturnId)root.append(h('p',{className:'notice',role:'status'},'Volviste del pago, pero no tenemos la recuperación guardada. Contacta al restaurante; no vuelvas a pagar.'));
    if(!recoveryStorageAvailable)root.append(h('p',{className:'notice',role:'status'},'Este navegador no permite recuperar el pedido después de recargar. Mantén esta página abierta hasta confirmar el resultado.'));
    return;
  }
  const panel=h('div',{className:'notice',role:'status'});
  if(recoveryState==='found'&&recoveredOrder){
    panel.append(h('strong',{},'Pedido #'+recoveredOrder.public_code),h('p',{},'Total: '+money(recoveredOrder.total_minor)));
    if(recoveredOrder.reconciliation_required||recoveredOrder.checkout_state==='review_required'){
      panel.append(h('p',{},'El restaurante debe revisar este pago. No vuelvas a pagar ni hagas otro pedido para resolverlo.'));
    } else if(!recoveredOrder.payments?.length||['pending','processing','unknown'].includes(recoveredOrder.checkout_state)){
      panel.append(h('p',{},'Tu solicitud está guardada. Estamos confirmando el pago; todavía no podemos confirmar el pedido.'));
    } else if(recoveredOrder.payment_status==='paid'){
      panel.append(h('p',{},'Pago confirmado. Estado del pedido: '+recoveredOrder.status));
    } else {
      panel.append(h('p',{},'Estado del pedido: '+recoveredOrder.status+'. Pago: '+recoveredOrder.payment_status));
      if(!wompiReturnId&&!['cancelled','completed'].includes(recoveredOrder.status)&&!['failed','refunded'].includes(recoveredOrder.payment_status))panel.append(recoveryAction('Continuar con el pago',continueRecoveredPayment,recoveryBusy));
    }
    panel.append(recoveryAction('Actualizar estado',recoverCheckout,recoveryBusy));
    if(canStartAnotherOrder())panel.append(recoveryAction('Hacer otro pedido',startAnotherOrder,recoveryBusy));
  } else if(recoveryState==='absent'){
    panel.append(h('p',{},'No encontramos un pedido guardado para esta solicitud. Completa de nuevo tus datos; conservaremos la misma referencia para evitar duplicados.'));
  } else if(['expired','invalid'].includes(recoveryState)){
    panel.append(h('p',{},'No podemos recuperar con seguridad la solicitud anterior. Contacta al restaurante para comprobarla antes de volver a pedir.'));
    if(recoveryState==='expired')panel.append(recoveryAction('Iniciar una compra diferente',startDifferentPurchase));
  } else {
    panel.append(h('p',{},recoveryBusy?'Buscando tu pedido anterior…':'No pudimos comprobar tu pedido anterior. No hemos enviado otro pedido.'));
    if(!recoveryBusy)panel.append(recoveryAction('Reintentar consulta',recoverCheckout));
  }
  if(!recoveryStorageAvailable)panel.append(h('p',{},'Este navegador no permite guardar la recuperación. Mantén esta página abierta y conserva la referencia del pedido.'));
  root.append(panel);
}
function updateCheckoutControls(){
  const recovering=['checking','uncertain','expired','invalid','found'].includes(recoveryState)&&!checkoutIntent;
  lockInputs(checkoutFields,checkoutBusy||recovering||!!checkoutIntent);
  $('checkoutButton').disabled=!!(wompiReturnId&&!recoveryRecord)||checkoutBusy||recoveryBusy||['expired','invalid'].includes(recoveryState);
  $('checkoutButton').textContent=recovering?'Consultar pedido anterior':fulfillment==='delivery'?'Pedir a domicilio':'Hacer pedido para recoger';
}
async function recoverCheckout(){
  if(!recoveryRecord||recoveryBusy||['expired','invalid'].includes(recoveryState))return;
  recoveryBusy=true;recoveryState='checking';renderRecovery();updateCheckoutControls();
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
  try {
    const order=await api(`/api/restaurants/${path(businessId)}/orders/recover`,{method:'POST',signal:controller.signal,body:JSON.stringify({idempotency_key:recoveryRecord.idempotency_key,recovery_secret:recoveryRecord.recovery_secret,...(wompiReturnId?{wompi_transaction_id:wompiReturnId}:{})})});
    if(!order.id||order.business_id!==businessId)throw new Error('Respuesta de recuperación inválida');
    recoveredOrder=order;checkoutIntent=null;recoveryState='found';
  } catch(e){
    recoveryState=e.status===404?'absent':e.status===410?'expired':'uncertain';
  } finally {clearTimeout(timer);recoveryBusy=false;renderRecovery();updateCheckoutControls();}
}
function canStartAnotherOrder(){return recoveredOrder&&!recoveredOrder.reconciliation_required&&recoveredOrder.checkout_state!=='review_required'&&(['paid','refunded','failed'].includes(recoveredOrder.payment_status)||recoveredOrder.status==='cancelled');}
function clearPaymentReturn(){wompiReturnId=null;const url=new URL(location.href);url.searchParams.delete('id');history.replaceState(null,'',url);}
function startDifferentPurchase(){
  if(recoveryState!=='expired'||!window.confirm('Esto inicia una compra diferente. No cancela, confirma ni resuelve el pedido anterior. ¿Quieres continuar con una compra diferente?'))return;
  clearPaymentReturn();clearRecovery();checkoutIntent=null;cart=[];foodQuote=null;deliveryQuote=null;++deliveryGeneration;renderCart();updateCheckoutControls();
}
function startAnotherOrder(){
  if(!canStartAnotherOrder())return;
  clearPaymentReturn();clearRecovery();checkoutIntent=null;cart=[];foodQuote=null;deliveryQuote=null;++deliveryGeneration;renderCart();updateCheckoutControls();
}
async function continueRecoveredPayment(){
  if(wompiReturnId||!recoveredOrder||recoveryBusy||recoveredOrder.reconciliation_required||recoveredOrder.checkout_state==='review_required'||['cancelled','completed'].includes(recoveredOrder.status)||['failed','refunded'].includes(recoveredOrder.payment_status))return;
  recoveryBusy=true;renderRecovery();updateCheckoutControls();
  try {
    const payment=recoveredOrder.payments?.[0];
    if(!payment)throw new Error('El pago aún está pendiente de confirmación.');
    if(payment.provider==='simulated'){
      const paid=await api(`/api/payments/simulated/${path(payment.provider_reference)}/complete`,{method:'POST'});
      recoveredOrder={...recoveredOrder,...paid};
    } else if(payment.checkout_url){
      if(!recoveryStorageAvailable)throw new Error('No podemos guardar la recuperación. Contacta al restaurante antes de pagar.');
      const url=safeURL(payment.checkout_url,'checkout');
      if(!url)throw new Error('Enlace de pago no autorizado. Contacta al restaurante.');
      window.location.assign(url);
    } else notice('El restaurante te indicará cómo continuar con el pago.');
  } catch(e){notice(e.message,'error');}
  finally {recoveryBusy=false;renderRecovery();updateCheckoutControls();}
}
function lockInputs(selector, locked) {
  document.querySelectorAll(selector).forEach(el=>{
    if(locked){if(!el.disabled){el.dataset.intentLocked='true';el.disabled=true;}}
    else if(el.dataset.intentLocked){el.disabled=false;delete el.dataset.intentLocked;}
  });
}
function intentKey(){
  // Secure contexts without randomUUID still have getRandomValues. Never Math.random.
  const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);
  return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
function notice(msg,type='success') {
  clearTimeout(noticeTimer);
  replace($('notice'),h('div',{className:'notice '+(type==='error'?'error':'success'),role:'status'},msg));
  noticeTimer=setTimeout(()=>replace($('notice')),7000);
}
async function api(url,opts={}){const r=await fetch(url,{headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts});let d={};try{d=await r.json()}catch{}if(!r.ok){const e=new Error(d.detail||`HTTP ${r.status}`);e.status=r.status;throw e}return d}
async function load(){try{store=await api(`/api/restaurants/${path(businessId)}/storefront`);$('restaurantName').textContent=store.display_name;document.title=`${store.display_name} · Pedido directo`;$('pickupInstructions').textContent=store.pickup_instructions||'';if(!store.delivery_enabled)$('deliveryBtn').disabled=true;if(!store.pickup_enabled&&store.delivery_enabled)setFulfillment('delivery');renderMenu()}catch(e){notice(e.message,'error')}finally{if(recoveryState==='checking')await recoverCheckout();else{renderRecovery();updateCheckoutControls();}}}
function renderMenu() {
  const root=$('menu'); replace(root);
  for(const menu of store.menus) for(const cat of menu.categories) {
    root.appendChild(h('h2',{className:'section-title'},cat.name));
    if(cat.description) root.appendChild(h('p',{},cat.description));
    for(const item of cat.items) root.appendChild(h('article',{className:'item '+(!item.available?'sold':'')},
      h('div',{},h('h3',{},item.name),h('p',{},item.description||''),h('div',{className:'price'},money(item.base_price_minor))),
      h('div',{},h('button',{disabled:!item.available,onClick:()=>openItem(item)},item.modifier_groups.length?'Elegir':'Agregar'))));
  }
}
function openItem(item) {
  activeItem=item;
  if(!item.modifier_groups.length){cart.push({item,quantity:1,selections:[]});renderCart();return;}
  $('modalName').textContent=item.name; $('modalDescription').textContent=item.description||'';
  replace($('modifierGroups'),item.modifier_groups.map((g,index)=>h('div',{className:'modifier'},
    h('strong',{},g.name),' ',h('small',{},g.required?'(obligatorio)':''),
    h('div',{},g.options.map(o=>h('label',{className:'option'},
      h('input',{type:g.max_selections===1?'radio':'checkbox',name:'group_'+index,value:o.id,
        'data-price':o.price_delta_minor,'data-group':g.id,onChange:updateModalTotal}),
      h('span',{},o.name,o.price_delta_minor?' (+'+money(o.price_delta_minor)+')':'')))))));
  updateModalTotal();
  if(typeof itemDialog.showModal==='function') itemDialog.showModal();
  else itemDialog.setAttribute('open','');
}
function closeItem(){if(typeof itemDialog.close==='function') itemDialog.close();else itemDialog.removeAttribute('open');}

function updateModalTotal(){let total=activeItem.base_price_minor;document.querySelectorAll('#modifierGroups input:checked').forEach(x=>total+=Number(x.dataset.price));$('modalTotal').textContent=money(total)}function addConfiguredItem(){const selections=[];for(const g of activeItem.modifier_groups){const ids=[...document.querySelectorAll('#modifierGroups input:checked')].filter(x=>x.dataset.group===String(g.id)).map(x=>x.value),min=Math.max(g.min_selections,g.required?1:0);if(ids.length<min)return notice(`Elige ${min} opción(es) en ${g.name}`,'error');if(ids.length>g.max_selections)return notice(`Máximo ${g.max_selections} opción(es) en ${g.name}`,'error');selections.push({group_id:g.id,option_ids:ids})}cart.push({item:activeItem,quantity:1,selections});closeItem();renderCart()}
function cartPayload(){return cart.map(x=>({menu_item_id:x.item.id,quantity:x.quantity,modifiers:x.selections}))}function renderCart(){
  ++foodGeneration;foodQuote=null;renderTotals();
  const root=$('cartRows'),count=cart.reduce((a,x)=>a+x.quantity,0);
  $('cartCount').textContent=count?`(${count})`:'';
  if(!cart.length){replace(root,h('p',{className:'muted'},'Todavía no has agregado nada.'));foodQuote=null;renderTotals();return;}
  replace(root,cart.map((x,i)=>h('div',{className:'cart-row'},
    h('strong',{},x.quantity,' × ',x.item.name),h('br'),h('small',{},money(x.item.base_price_minor)),
    h('button',{className:'secondary',onClick:()=>removeItem(i)},'Quitar'))));
  quoteCart();
}
function removeItem(i){cart.splice(i,1);renderCart()}
async function quoteCart(){
  const generation=++foodGeneration;
  foodQuote=null;renderTotals();
  if(!cart.length)return;
  try {
    const result=await api(`/api/restaurants/${path(businessId)}/orders/quote`,{method:'POST',body:JSON.stringify({items:cartPayload(),promo_code:$('promoCode').value.trim()||null,customer_phone:$('cPhone').value.trim()||null})});
    if(generation!==foodGeneration)return;
    foodQuote=result;renderTotals();
  } catch(e){if(generation===foodGeneration)notice(e.message,'error')}
}
function renderTotals(){const food=foodQuote?.total_minor||0,sub=foodQuote?.subtotal_minor||0,disc=foodQuote?.discounts?.total_discount_minor||0,delivery=fulfillment==='delivery'?(deliveryQuote?.fee_minor||0):0;$('foodTotal').textContent=money(food);$('deliveryLine').classList.toggle('hidden',fulfillment!=='delivery');$('deliveryFee').textContent=deliveryQuote?money(deliveryQuote.fee_minor):'Sin cotizar';$('discountLine').classList.toggle('hidden',!disc);$('discountTotal').textContent=`−${money(disc)}`;$('cartTotal').textContent=money(food+delivery)}
function setFulfillment(type){if(type==='delivery'&&!store?.delivery_enabled)return notice('Domicilios no disponibles.','error');if(type==='pickup'&&!store?.pickup_enabled)return;fulfillment=type;$('pickupBtn').classList.toggle('off',type!=='pickup');$('deliveryBtn').classList.toggle('off',type!=='delivery');$('deliveryPanel').classList.toggle('hidden',type!=='delivery');$('checkoutButton').textContent=type==='delivery'?'Pedir a domicilio':'Hacer pedido para recoger';renderTotals()}
function invalidateDeliveryQuote(){++deliveryGeneration;deliveryQuote=null;$('deliveryQuoteText').textContent='La dirección cambió. Cotiza de nuevo.';renderTotals()}function demoAddress(){$('dAddress').value='Calle 85 # 12-34';$('dLat').value='4.6697';$('dLng').value='-74.0549';invalidateDeliveryQuote()}function useLocation(){if(!navigator.geolocation)return notice('Tu navegador no ofrece ubicación.','error');navigator.geolocation.getCurrentPosition(p=>{if(checkoutIntent)return;$('dLat').value=p.coords.latitude;$('dLng').value=p.coords.longitude;invalidateDeliveryQuote();notice('Ubicación capturada. Escribe tu dirección y cotiza.')},e=>notice(e.message,'error'))}
async function quoteDelivery(){
  const generation=++deliveryGeneration;
  deliveryQuote=null;renderTotals();
  const address=$('dAddress').value.trim(),lat=Number($('dLat').value),lng=Number($('dLng').value);
  if(!address||!Number.isFinite(lat)||!Number.isFinite(lng)||!$('dLat').value||!$('dLng').value)return notice('Completa dirección y coordenadas.','error');
  try {
    const result=await api(`/api/restaurants/${path(businessId)}/delivery/quote`,{method:'POST',body:JSON.stringify({destination:{address_line:address,city:'Bogotá',latitude:lat,longitude:lng,instructions:$('dInstructions').value.trim()||null}})});
    if(generation!==deliveryGeneration)return;
    deliveryQuote=result;
    $('deliveryQuoteText').textContent=`Domicilio ${money(deliveryQuote.fee_minor)} · aprox. ${Math.round((deliveryQuote.distance_meters||0)/100)/10} km · cotización temporal`;renderTotals();
  } catch(e){if(generation===deliveryGeneration)notice(e.message,'error')}
}
const checkoutFields='#cart input, #cart textarea, #cart button:not(#checkoutButton):not([data-recovery-action]), #menu button';
function checkoutNeedsStatusOnly(order){return order.reconciliation_required||['cancelled','completed'].includes(order.status)||['failed','refunded'].includes(order.payment_status)||!order.payments?.length||['pending','processing','unknown','review_required'].includes(order.checkout_state);}
function showKnownOrder(order){
  recoveredOrder=order;recoveryState='found';checkoutIntent=null;clearTimeout(noticeTimer);replace($('notice'));renderRecovery();
}
async function checkout(){
  if(wompiReturnId&&!recoveryRecord)return notice('Contacta al restaurante para recuperar el pago anterior.','error');
  if(checkoutBusy||recoveryBusy)return;
  if(!checkoutIntent&&['checking','uncertain','expired','invalid','found'].includes(recoveryState)){await recoverCheckout();return;}
  if(!store)return notice('Espera a que cargue el menú.','error');
  if(!checkoutIntent){
    if(!cart.length)return notice('Agrega algo al pedido.','error');
    const name=$('cName').value.trim(),phone=$('cPhone').value.trim();
    if(!name||!phone)return notice('Necesitamos tu nombre y teléfono.','error');
    if(fulfillment==='delivery'&&!deliveryQuote)return notice('Cotiza el domicilio antes de continuar.','error');
    let recovery;
    try {recovery=recoveryRecord||newRecovery();}catch {return notice('Tu navegador no permite crear una referencia segura. Contacta al restaurante.','error');}
    checkoutIntent={customer:{name,phone,email:$('cEmail').value.trim()||null,whatsapp_opt_in:$('whatsappOptIn').checked,marketing_opt_in:$('marketingOptIn').checked,consent_source:'web_checkout'},items:cartPayload(),fulfillment_type:fulfillment,delivery_quote_id:fulfillment==='delivery'?deliveryQuote.id:null,notes:$('cNotes').value.trim()||null,payment_provider:store.payment_provider,promo_code:$('promoCode').value.trim()||null,idempotency_key:recovery.idempotency_key,recovery_secret:recovery.recovery_secret};
  }
  let orderAccepted=false;
  checkoutBusy=true;$('checkoutButton').disabled=true;lockInputs(checkoutFields,true);
  try {
    let order=await api(`/api/restaurants/${path(businessId)}/orders`,{method:'POST',body:JSON.stringify(checkoutIntent)});
    orderAccepted=true;
    // Keep the same intent through payment-navigation/completion failures too.
    if(checkoutNeedsStatusOnly(order)){showKnownOrder(order);return;}
    if(store.payment_provider==='simulated'){const paid=await api(`/api/payments/simulated/${path(order.payments[0].provider_reference)}/complete`,{method:'POST'});order={...order,...paid};}
    else if(order.payments[0]?.checkout_url){
      if(!recoveryStorageAvailable)throw new Error('No podemos guardar la recuperación en este navegador. Conserva la referencia '+order.public_code+' y contacta al restaurante antes de pagar.');
      const url=safeURL(order.payments[0].checkout_url,'checkout');
      if(!url)throw new Error('Enlace de pago no autorizado. Conserva la referencia del pedido: '+order.public_code);
      window.location.assign(url);return;
    }
    if(checkoutNeedsStatusOnly(order)){showKnownOrder(order);return;}
    recoveredOrder=order;recoveryState='found';checkoutIntent=null;cart=[];foodQuote=null;deliveryQuote=null;++deliveryGeneration;renderCart();$('promoCode').value='';renderRecovery();
    notice(`Pedido #${order.public_code} recibido. ${order.fulfillment_type==='delivery'?`Domicilio: ${money(order.delivery_fee_minor)}. `:'Recogida en restaurante. '}${store.payment_provider==='simulated'?'Pago demo aprobado.':'Continúa con el pago indicado.'}`);
  } catch(e){
    if(!orderAccepted&&(e.status===422||e.status===404)){checkoutIntent=null;clearRecovery();}
    notice(e.message+(checkoutIntent?' No pudimos confirmar el pedido. Reintenta aquí; conservamos la misma solicitud.'+(recoveryStorageAvailable?'':' No recargues: este navegador no permite guardar la recuperación.') :''),'error');
  } finally {
    checkoutBusy=false;updateCheckoutControls();
  }
}
function showReservation(){$('menu').classList.add('hidden');$('reservationPanel').classList.remove('hidden')}function showOrder(){$('menu').classList.remove('hidden');$('reservationPanel').classList.add('hidden')}async function reserve(){
  if(reservationBusy)return;
  const name=$('rName').value.trim(),phone=$('rPhone').value.trim(),starts=$('rDate').value;
  if(!name||!phone||!starts)return notice('Completa nombre, teléfono y hora.','error');
  const button=document.querySelector('[data-click="reserve"]');
  const body={customer:{name,phone,whatsapp_opt_in:$('rWhatsappOptIn').checked,consent_source:'web_reservation'},starts_at:new Date(starts).toISOString(),party_size:Number($('rParty').value),notes:$('rNotes').value.trim()||null};
  const fingerprint=JSON.stringify(body);
  if(!reservationIntent||reservationIntent.fingerprint!==fingerprint)reservationIntent={fingerprint,body:{...body,idempotency_key:intentKey()}};
  reservationBusy=true;button.disabled=true;lockInputs('#reservationPanel input, #reservationPanel textarea',true);
  try {
    const r=await api(`/api/restaurants/${path(businessId)}/reservations`,{method:'POST',body:JSON.stringify(reservationIntent.body)});
    lockInputs('#reservationPanel input, #reservationPanel textarea',false);
    notice(`Reserva #${r.public_code} solicitada para ${r.party_size} personas.`);
  } catch(e){
    if(e.status===422||e.status===404){reservationIntent=null;lockInputs('#reservationPanel input, #reservationPanel textarea',false);}
    notice(e.message+(reservationIntent?' No pudimos confirmar la reserva. Reintenta aquí sin recargar.':''),'error');
  } finally {reservationBusy=false;button.disabled=false;}
}
bind({viewCart:()=>$('cart').scrollIntoView(),showOrder,showReservation,reserve,
  pickup:()=>setFulfillment('pickup'),delivery:()=>setFulfillment('delivery'),
  invalidateDeliveryQuote,useLocation,demoAddress,quoteDelivery,quoteCart,checkout,closeItem,addConfiguredItem});
start(async()=>{readPendingCheckout();await load();});
})();
