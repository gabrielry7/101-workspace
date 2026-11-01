"use strict";
(() => {
if(window.CommerceSupported===false)return;
const {$, node: h, replace, safeURL, bind, start, money, path} = window.CommerceUI;
const business = $('business');
function publicMenu(){ $('publicMenuLink').href='/?business_id='+path(business.value); }
business.addEventListener('input',publicMenu);window.addEventListener('staffchange',publicMenu);
let merchantTimezone='America/Bogota', metadataBusiness=null, queueReading=false, queueQueued=false;
let scopeVersion = 0, queueGeneration=0, reservationGeneration=0, reviewGeneration=0, queueOffset=0, lastRows=[];
const pendingActions=new Set();
const labels={awaiting_payment:'Esperando pago',placed:'Recibido',accepted:'Aceptado',preparing:'En preparación',ready:'Listo',completed:'Entregado',cancelled:'Cancelado'};
const actions={accepted:'Aceptar',preparing:'Preparar',ready:'Marcar listo',completed:'Entregar',cancelled:'Cancelar'};
const paidLabels={pending:'Por confirmar',paid:'Pagado',unpaid:'Sin pagar',failed:'No aprobado',refunded:'Devuelto'};
const stamp=value=>window.CommerceUI.dateTime(value,merchantTimezone);
function actionMessage(text){$('staffActionStatus').hidden=false;$('staffActionStatus').textContent=text;}

for (const input of [business]) input.addEventListener('input', () => {
  ++scopeVersion;++queueGeneration;++reservationGeneration;++reviewGeneration;queueOffset=0;lastRows=[];
  for (const id of ['orders', 'reservations', 'reconciliation']) $(id).textContent = 'Actualizar para cargar este negocio.';
});
const endpoint = tail => `/api/operator/restaurants/${path(business.value)}/${tail}`;
async function api(url, options = {}) {
  const version = scopeVersion;
  const response = await window.CommerceStaff.request(url, options);
  const data = await response.json();
  if (version !== scopeVersion) { const error = new Error('La selección cambió'); error.stale = true; throw error; }
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}
const card = (...children) => h('div', {className: 'card'}, children);
const meta = text => h('div', {className: 'meta'}, text);
const button = (label, action) => h('button', {onClick: async event => {
  const el = event.currentTarget;
  el.disabled = true;
  try { await action(); } catch (error) { if (!error.stale) alert(error.message); }
  finally { el.disabled = false; }
}}, label);

const orders = $('orders'), reservations = $('reservations');
const next = {placed:['accepted','cancelled'], accepted:['preparing','cancelled'],
  preparing:['ready','cancelled'], ready:['completed','cancelled']};
function renderOrders(rows){
  const query=$('queueSearch').value.trim().toLocaleLowerCase('es'),payment=$('paymentFilter').value;
  const shown=rows.filter(o=>(payment==='all'||o.payment_status===payment)&&(!query||[o.public_code,o.customer_name||''].join(' ').toLocaleLowerCase('es').includes(query)));
  $('queueCount').textContent=shown.length+' visibles · página '+(queueOffset/50+1)+' · máximo 50 por página';
  $('queuePrev').disabled=queueOffset===0;$('queueNext').disabled=rows.length<50;
  replace(orders, shown.length?shown.map(o=>card(
    h('div',{className:'order-top'},h('span',{className:'status'},labels[o.status]||o.status),h('span',{className:'tag'},paidLabels[o.payment_status]||o.payment_status)),
    h('h3',{},'#'+o.public_code+' · '+(o.customer_name||o.customer_phone)),
    h('div',{className:'order-items'},...o.items.map(i=>h('div',{},i.quantity+' × '+i.name))),
    h('p',{className:'total'},money(o.total_minor)),
    meta((o.fulfillment_type==='pickup'?'Recogida':'Domicilio')+' · recibido '+stamp(o.created_at)),
    o.requested_pickup_at?meta('Hora de recogida: '+stamp(o.requested_pickup_at)):meta('Hora de recogida por confirmar'),
    o.reconciliation_required?h('p',{role:'alert'},'Pago requiere revisión. No confirmar ni cobrar de nuevo.'):null,
    h('details',{},h('summary',{},'Detalle y contacto'),h('p',{},o.customer_phone),o.notes?h('p',{},o.notes):null,...o.items.map(i=>h('p',{},i.quantity+' × '+i.name+' · '+money(i.line_total_minor)+(i.modifiers.length?' · '+i.modifiers.map(m=>m.option_name).join(', '):''))),meta('Versión '+o.version)),
    h('div',{className:'actions'},...(!o.reconciliation_required&&next[o.status]?next[o.status]:[]).map(status=>h('button',{disabled:pendingActions.has(o.id),onClick:()=>transition(o,status)},actions[status])),button('Ver pago',async()=>{$('financeOrder').value=o.id;++financeVersion;await financeHistory();$('financialSection').scrollIntoView();}))
  )):h('p',{className:'empty'},'Sin pedidos con estos filtros.'));
}
async function transition(order,status){
  if(pendingActions.has(order.id)||navigator.onLine===false)return actionMessage('Sin conexión o acción en curso. Actualiza antes de continuar.');
  let reason='Cambio de estado desde operación';
  if(status==='cancelled'){reason=prompt('Motivo de cancelación');if(!reason?.trim())return;}
  if(status==='completed'&&order.payments.some(p=>p.provider==='cash_at_pickup')&&!confirm('Confirma que recibiste '+money(order.total_minor)+' en efectivo y entregaste el pedido.'))return;
  if(status==='completed'&&order.payments.some(p=>p.provider==='cash_at_pickup'))reason='Personal confirma cobro en efectivo y entrega';
  pendingActions.add(order.id);++queueGeneration;renderOrders(lastRows);
  try{await api(`/api/operator/orders/${path(order.id)}`,{method:'PATCH',body:JSON.stringify({status,expected_version:order.version,reason})});actionMessage('Cambio guardado.');}
  catch(error){if(!error.stale)actionMessage(error.message+' No repetimos la acción. Consulta el estado actualizado.');}
  finally{pendingActions.delete(order.id);await loadOrders();}
}
async function loadOrders(){
  if(queueReading){queueQueued=true;return false;}
  queueReading=true;
  const generation=++queueGeneration, filter=$('queueFilter').value;
  try{
    const rows=await api(endpoint('orders')+'?limit=50&offset='+queueOffset+(filter==='active'?'&active=true':filter==='all'?'':'&status='+path(filter)));
    if(generation!==queueGeneration)return false;lastRows=rows;renderOrders(rows);return true;
  }catch(error){if(!error.stale&&generation===queueGeneration)actionMessage('No se pudo actualizar la cola. Los pedidos visibles pueden estar desactualizados.');return false;}
  finally{queueReading=false;if(queueQueued){queueQueued=false;setTimeout(loadOrders,0);}}
}
async function loadReservations() {
  const generation=++reservationGeneration;
  try {
    const rows = await api(endpoint('reservations'));if(generation!==reservationGeneration)return false;
    replace(reservations, rows.length ? rows.map(r => card(
      h('div', {className:'status'}, r.status), h('h3', {}, '#', r.public_code),
      h('div', {}, r.customer_name || r.customer_phone), h('div', {}, r.party_size, ' personas'),
      meta(stamp(r.starts_at)),
      h('div', {className:'actions'}, [['Confirmar','confirmed'],['Cancelar','cancelled']].map(([label,status]) =>
        button(label, async () => {
          await api(`/api/operator/reservations/${path(r.id)}`, {method:'PATCH', body:JSON.stringify({status})});
          await loadReservations();
        })))
    )) : h('p', {}, 'Sin reservas.'));
    return true;
  } catch (error) { if (!error.stale)actionMessage('No se pudieron actualizar las reservas.');return false; }
}
const reviewReasons = {
  refund_evidence_review:'Devolución sin verificar: no habilitar la entrega ni devolver de nuevo',
  paid_after_cancellation:'Pago recibido después de cancelar',
  contradictory_payment_notification:'El proveedor reportó estados incompatibles',
  invalid_provider_response:'Respuesta de pago no verificable',
  provider_reference_conflict:'Referencia de pago asociada a otro pedido',
  provider_replay_not_supported:'Pago sin confirmación; consultar al proveedor',
  cancelled_checkout_unknown:'Pedido cancelado con pago por confirmar',
  invalid_payment_notification:'Notificación de pago no válida'
};
async function loadReconciliation() {
  const generation=++reviewGeneration;
  try {
    const rows = await api(endpoint('payment-reconciliation'));if(generation!==reviewGeneration)return false;
    replace($('reconciliation'), rows.length ? rows.map(r => card(
      h('strong', {}, 'Revisión de pago'), meta('Pedido: ' + r.order_id),
      meta(Object.prototype.hasOwnProperty.call(reviewReasons, r.reason) ? reviewReasons[r.reason] : 'Verificar el pago con el proveedor'), meta(stamp(r.created_at)),
      h('p', {}, 'Verifica el pago con el proveedor antes de realizar cualquier cobro o devolución. Esta alerta no confirma una devolución.'),
      button('Abrir resolución',async()=>{$('financeOrder').value=r.order_id;++financeVersion;await financeHistory();})
    )) : h('p', {}, 'Sin revisiones pendientes.'));
    return true;
  } catch (error) { if (!error.stale)actionMessage('No se pudieron actualizar las revisiones de pago.');return false; }
}
let refreshing = false;
async function refreshAll() {
  if (refreshing) return;
  refreshing = true;
  try { if(metadataBusiness!==business.value){const selected=business.value;const profile=await api(`/api/restaurants/${path(selected)}/storefront`);merchantTimezone=profile.timezone;metadataBusiness=selected;}const results=[];for(const load of [loadOrders,loadReservations,loadReconciliation])results.push(await load());return results.every(Boolean); }
  catch(error){if(!error.stale)actionMessage('No se pudo verificar la operación del negocio.');return false;}
  finally { refreshing = false; }
}
const financeResult = $('financeResult');
let financeVersion = 0, financeBusy = false;
let financeCapabilities = null;
function resetFinanceCapabilities() {
  financeCapabilities=null;
  $('financeRefundButton').disabled=true; $('financeInspectButton').disabled=true;
  $('financeRefundReference').value='';
  $('financeAvailability').textContent='Consulta el historial para cargar los permisos y acciones disponibles.';
}
for (const input of [business, $('financeOrder')]) input.addEventListener('input', () => {
  resetFinanceCapabilities();
  ++financeVersion; financeResult.textContent = 'Consultar para cargar el historial de este pedido.';
});
const financeRoot = () => `/api/finance/restaurants/${path(business.value)}/orders/${path($('financeOrder').value.trim())}`;
async function financeAPI(url, body) {
  const version = financeVersion;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await window.CommerceStaff.request(url, {method:body ? 'POST':'GET', signal:controller.signal,
      headers:{'Content-Type':'application/json'},
      ...(body ? {body:JSON.stringify(body)} : {})});
    const data = await response.json();
    if(version !== financeVersion){const e=new Error('La selección cambió');e.stale=true;throw e;}
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`HTTP ${response.status}`);
    return data;
  } finally {clearTimeout(timeout);}
}
const financeStates={pending:'Pendiente',processing:'En proceso',unknown:'Sin confirmación; consultar nuevamente',succeeded:'Confirmado por el proveedor',failed:'Rechazado por el proveedor',withdrawn:'Solicitud retirada tras rechazo confirmado',review_required:'Requiere investigación'};
const financialReviewReasons={refund_environment_unverified:'El proveedor no identifica el reembolso como Sandbox. Requiere aclaración.',refund_amount_mismatch:'El importe devuelto no coincide con el pago completo.',wompi_refund_contract_unverified:'Reembolsos Wompi deshabilitados: el contrato del proveedor sigue sin verificarse.',refund_evidence_requires_review:'El proveedor registra una devolución que requiere inspección.',unsupported_provider_status:'Estado del proveedor sin soporte; requiere investigación.'};
function evidenceView(value) {
  if(!value)return meta('Sin evidencia de resultado');
  const e=value.provider_evidence || value;
  return h('div',{},
    typeof e.amount_minor==='number'?meta('Importe: '+money(e.amount_minor)):null,
    typeof e.provider_reference==='string'?meta('Referencia de pago: '+e.provider_reference):null,
    typeof e.refund_reference==='string'?meta('Referencia de devolución: '+e.refund_reference):null,
    typeof e.refund_amount_minor==='number'?meta('Importe de devolución reportado: '+money(e.refund_amount_minor)):null,
    typeof e.refund_status==='string'?meta('Estado reportado por Wompi: '+e.refund_status+' (no confirma devolución en este sistema)'):null,
    e.review_reason?meta(financialReviewReasons[e.review_reason]||'Evidencia pendiente de revisión.'):null,
    typeof e.evidence_id==='string'?meta('Comprobante del proveedor: '+e.evidence_id):null,
    typeof e.query_started_at==='string'?meta('Consulta iniciada: '+new Date(e.query_started_at).toLocaleString()):null,
    e.error?meta('Aún no hay confirmación verificable. Consulta el historial antes de volver a intentar.'):null);
}
const financialActions={'refund.requested':'Devolución solicitada','refund.succeeded':'Devolución confirmada',
  'refund.unknown':'Devolución sin confirmar','refund.failed':'Devolución rechazada','refund.review_required':'Devolución en revisión',
  'lookup.requested':'Consulta de pago solicitada','lookup.succeeded':'Pago verificado','lookup.unknown':'Pago sin confirmar',
  'lookup.review_required':'Pago en revisión','reconciliation.resolved':'Revisión resuelta','reconciliation.updated':'Nueva evidencia para revisión'};
function financialReviewCard(review, operations) {
  if(review.resolvable===false)return card(meta('Revisión financiera pendiente'),
    meta('La evidencia de devolución sigue sin verificarse. Una consulta de pago normal no resuelve esta revisión.'));
  const choices=operations.filter(o=>o.state==='succeeded'||o.state==='failed').slice(-3);
  return card(meta('Revisión financiera pendiente'), ...choices.map(o=>button('Resolver con evidencia '+o.id.slice(0,8),async()=>{
    const reason=$('financeReason').value.trim();
    if(!reason)throw new Error('Escribe el motivo de la resolución.');
    await financeAPI(financeRoot()+'/resolve/'+path(review.id),{operation_id:o.id,reason});
    await renderFinance();await loadReconciliation();
  })));
}
async function renderFinance() {
  const data=await financeAPI(financeRoot());
  financeCapabilities=data.capabilities || {};
  $('financeRefundButton').disabled=financeCapabilities.refund!==true;
  $('financeInspectButton').disabled=financeCapabilities.inspect_refund!==true;
  $('financeAvailability').textContent=financeCapabilities.refund===true?'Devolución completa disponible según tus permisos.':
    financeCapabilities.refund_block_reason==='wompi_refund_contract_unverified'?financialReviewReasons.wompi_refund_contract_unverified:'Devolución no disponible para este pedido o tus permisos.';
  const operations=data.operations || [];
  replace(financeResult, [h('p',{},'Una solicitud pendiente no confirma una devolución.'),
    ...operations.map(o=>card(h('strong',{},o.kind==='refund'?'Devolución completa':'Consulta de pago'),
      h('p',{},financeStates[o.state] || o.state),meta('Responsable: '+o.actor_id),meta(o.reason),
      evidenceView(o.result))),
    ...(data.reviews||[]).filter(r=>r.status==='open').map(r=>financialReviewCard(r,operations)),
    h('h3',{},'Historial de acciones'),...(data.audit||[]).map(a=>card(meta(new Date(a.created_at).toLocaleString()),
      h('div',{},a.actor_id+' · '+(financialActions[a.action]||'Actualización financiera')),meta(a.reason),evidenceView(a.evidence)))]);
}
async function financeAction(kind) {
  if(financeBusy)return;financeBusy=true;
  const version=financeVersion;
  try {
    if(!$('financeOrder').value.trim())throw new Error('Indica el pedido.');
    if(kind){
      const reason=$('financeReason').value.trim();if(!reason)throw new Error('Escribe el motivo.');
      if(kind==='refund'&&!confirm('¿Solicitar una devolución completa? Si se interrumpe, consulta el historial antes de volver a intentar.'))return;
      const reference=$('financeRefundReference').value.trim();
      if(kind==='inspect'&&(!financeCapabilities?.inspect_refund || !/^[1-9][0-9]{0,19}$/.test(reference)))throw new Error('Consulta el historial e indica un ID numérico de devolución válido.');
      if(!window.crypto || !crypto.getRandomValues)throw new Error('Este navegador no permite una solicitud segura.');
      const bytes=new Uint8Array(24);crypto.getRandomValues(bytes);
      await financeAPI(financeRoot()+'/'+(kind==='inspect'?'lookup':kind),{idempotency_key:Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(''),reason,
        ...(kind==='inspect'?{refund_reference:reference}:{})});
    }
    await renderFinance();
  } catch(error){if(!error.stale && version===financeVersion)financeResult.textContent=error.name==='AbortError'?'Respuesta no recibida. Consulta el historial: la operación puede continuar.':error.message;}
  finally {financeBusy=false;}
}
const financeHistory=()=>financeAction(null), financeLookup=()=>financeAction('lookup'), financeRefund=()=>financeAction('refund');
const financeInspect=()=>financeAction('inspect');
window.addEventListener('staffchange', event => { ++scopeVersion;++queueGeneration;++reservationGeneration;++reviewGeneration;queueOffset=0;lastRows=[]; ++financeVersion; resetFinanceCapabilities(); $('financeOrder').value=''; for(const id of ['orders', 'reservations', 'reconciliation', 'financeResult']) $(id).textContent='Actualizar para cargar datos autorizados.'; if(event.detail.authenticated) refreshAll(); });
const queuePoll=window.CommerceUI.poll(refreshAll,{active:()=>!!window.CommerceStaff.identity(),interval:15000});
$('queueFilter').addEventListener('change',()=>{queueOffset=0;loadOrders();});
for(const id of ['paymentFilter','queueSearch'])$(id).addEventListener('input',()=>renderOrders(lastRows));
$('queuePrev').addEventListener('click',()=>{queueOffset=Math.max(0,queueOffset-50);loadOrders();});
$('queueNext').addEventListener('click',()=>{queueOffset+=50;loadOrders();});
bind({refreshAll:queuePoll.refresh,financeHistory,financeLookup,financeRefund,financeInspect});start(()=>window.CommerceStaff.ready.then(queuePoll.refresh));
})();
