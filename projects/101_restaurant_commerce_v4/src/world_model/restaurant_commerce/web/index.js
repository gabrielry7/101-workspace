"use strict";
(()=>{

const {node: h, replace, safeURL, bind, start, path} = window.CommerceUI;
const itemDialog = document.getElementById("itemDialog");
const qs=new URLSearchParams(location.search),businessId=qs.get('business_id')||'demo-restaurant-bogota';let store=null,cart=[],activeItem=null,foodQuote=null,deliveryQuote=null,fulfillment='pickup';const money=n=>new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n||0);const $=id=>document.getElementById(id);
let noticeTimer;
function notice(msg,type='success') {
  clearTimeout(noticeTimer);
  replace($('notice'),h('div',{className:'notice '+(type==='error'?'error':'success'),role:'status'},msg));
  noticeTimer=setTimeout(()=>replace($('notice')),7000);
}
async function api(url,opts={}){const r=await fetch(url,{headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d}
async function load(){try{store=await api(`/api/restaurants/${path(businessId)}/storefront`);$('restaurantName').textContent=store.display_name;document.title=`${store.display_name} · Pedido directo`;$('pickupInstructions').textContent=store.pickup_instructions||'';if(!store.delivery_enabled)$('deliveryBtn').disabled=true;if(!store.pickup_enabled&&store.delivery_enabled)setFulfillment('delivery');renderMenu()}catch(e){notice(e.message,'error')}}
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
  const root=$('cartRows'),count=cart.reduce((a,x)=>a+x.quantity,0);
  $('cartCount').textContent=count?`(${count})`:'';
  if(!cart.length){replace(root,h('p',{className:'muted'},'Todavía no has agregado nada.'));foodQuote=null;renderTotals();return;}
  replace(root,cart.map((x,i)=>h('div',{className:'cart-row'},
    h('strong',{},x.quantity,' × ',x.item.name),h('br'),h('small',{},money(x.item.base_price_minor)),
    h('button',{className:'secondary',onClick:()=>removeItem(i)},'Quitar'))));
  quoteCart();
}
function removeItem(i){cart.splice(i,1);renderCart()}
async function quoteCart(){if(!cart.length)return;try{foodQuote=await api(`/api/restaurants/${path(businessId)}/orders/quote`,{method:'POST',body:JSON.stringify({items:cartPayload(),promo_code:$('promoCode').value.trim()||null,customer_phone:$('cPhone').value.trim()||null})});renderTotals()}catch(e){notice(e.message,'error')}}function renderTotals(){const food=foodQuote?.total_minor||0,sub=foodQuote?.subtotal_minor||0,disc=foodQuote?.discounts?.total_discount_minor||0,delivery=fulfillment==='delivery'?(deliveryQuote?.fee_minor||0):0;$('foodTotal').textContent=money(food);$('deliveryLine').classList.toggle('hidden',fulfillment!=='delivery');$('deliveryFee').textContent=deliveryQuote?money(deliveryQuote.fee_minor):'Sin cotizar';$('discountLine').classList.toggle('hidden',!disc);$('discountTotal').textContent=`−${money(disc)}`;$('cartTotal').textContent=money(food+delivery)}
function setFulfillment(type){if(type==='delivery'&&!store?.delivery_enabled)return notice('Domicilios no disponibles.','error');if(type==='pickup'&&!store?.pickup_enabled)return;fulfillment=type;$('pickupBtn').classList.toggle('off',type!=='pickup');$('deliveryBtn').classList.toggle('off',type!=='delivery');$('deliveryPanel').classList.toggle('hidden',type!=='delivery');$('checkoutButton').textContent=type==='delivery'?'Pedir a domicilio':'Hacer pedido para recoger';renderTotals()}
function invalidateDeliveryQuote(){deliveryQuote=null;$('deliveryQuoteText').textContent='La dirección cambió. Cotiza de nuevo.';renderTotals()}function demoAddress(){$('dAddress').value='Calle 85 # 12-34';$('dLat').value='4.6697';$('dLng').value='-74.0549';invalidateDeliveryQuote()}function useLocation(){if(!navigator.geolocation)return notice('Tu navegador no ofrece ubicación.','error');navigator.geolocation.getCurrentPosition(p=>{$('dLat').value=p.coords.latitude;$('dLng').value=p.coords.longitude;invalidateDeliveryQuote();notice('Ubicación capturada. Escribe tu dirección y cotiza.')},e=>notice(e.message,'error'))}
async function quoteDelivery(){const address=$('dAddress').value.trim(),lat=Number($('dLat').value),lng=Number($('dLng').value);if(!address||!Number.isFinite(lat)||!Number.isFinite(lng)||!$('dLat').value||!$('dLng').value)return notice('Completa dirección y coordenadas.','error');try{deliveryQuote=await api(`/api/restaurants/${path(businessId)}/delivery/quote`,{method:'POST',body:JSON.stringify({destination:{address_line:address,city:'Bogotá',latitude:lat,longitude:lng,instructions:$('dInstructions').value.trim()||null}})});$('deliveryQuoteText').textContent=`Domicilio ${money(deliveryQuote.fee_minor)} · aprox. ${Math.round((deliveryQuote.distance_meters||0)/100)/10} km · cotización temporal`;renderTotals()}catch(e){notice(e.message,'error')}}
async function checkout(){if(!cart.length)return notice('Agrega algo al pedido.','error');const name=$('cName').value.trim(),phone=$('cPhone').value.trim();if(!name||!phone)return notice('Necesitamos tu nombre y teléfono.','error');if(fulfillment==='delivery'&&!deliveryQuote)return notice('Cotiza el domicilio antes de continuar.','error');try{const order=await api(`/api/restaurants/${path(businessId)}/orders`,{method:'POST',body:JSON.stringify({customer:{name,phone,email:$('cEmail').value.trim()||null,whatsapp_opt_in:$('whatsappOptIn').checked,marketing_opt_in:$('marketingOptIn').checked,consent_source:'web_checkout'},items:cartPayload(),fulfillment_type:fulfillment,delivery_quote_id:fulfillment==='delivery'?deliveryQuote.id:null,notes:$('cNotes').value.trim()||null,payment_provider:store.payment_provider,promo_code:$('promoCode').value.trim()||null,idempotency_key:crypto.randomUUID()})});if(store.payment_provider==='simulated'){await api(`/api/payments/simulated/${path(order.payments[0].provider_reference)}/complete`,{method:'POST'})}else if(order.payments[0]?.checkout_url){const url=safeURL(order.payments[0].checkout_url,'checkout');if(!url)throw new Error('Enlace de pago no autorizado. Conserva la referencia del pedido: '+order.public_code);window.location.assign(url);return}cart=[];foodQuote=null;deliveryQuote=null;renderCart();$('promoCode').value='';notice(`Pedido #${order.public_code} recibido. ${order.fulfillment_type==='delivery'?`Domicilio: ${money(order.delivery_fee_minor)}. `:'Recogida en restaurante. '}${store.payment_provider==='simulated'?'Pago demo aprobado.':'Continúa con el pago indicado.'}`)}catch(e){notice(e.message,'error')}}
function showReservation(){$('menu').classList.add('hidden');$('reservationPanel').classList.remove('hidden')}function showOrder(){$('menu').classList.remove('hidden');$('reservationPanel').classList.add('hidden')}async function reserve(){const name=$('rName').value.trim(),phone=$('rPhone').value.trim(),starts=$('rDate').value;if(!name||!phone||!starts)return notice('Completa nombre, teléfono y hora.','error');try{const r=await api(`/api/restaurants/${path(businessId)}/reservations`,{method:'POST',body:JSON.stringify({customer:{name,phone,whatsapp_opt_in:true,consent_source:'web_reservation'},starts_at:new Date(starts).toISOString(),party_size:Number($('rParty').value),notes:$('rNotes').value.trim()||null})});notice(`Reserva #${r.public_code} solicitada para ${r.party_size} personas.`)}catch(e){notice(e.message,'error')}}bind({viewCart:()=>$('cart').scrollIntoView(),showOrder,showReservation,reserve,
  pickup:()=>setFulfillment('pickup'),delivery:()=>setFulfillment('delivery'),
  invalidateDeliveryQuote,useLocation,demoAddress,quoteDelivery,quoteCart,checkout,closeItem,addConfiguredItem});
start(load);
})();
