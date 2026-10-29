"use strict";
(() => {
const {$, node: h, replace, safeURL, bind, start, money, path} = window.CommerceUI;
const business = $('business'), token = $('token');
let scopeVersion = 0;
for (const input of [business, token]) input.addEventListener('input', () => {
  ++scopeVersion;
  for (const id of ['orders', 'reservations', 'reconciliation']) $(id).textContent = 'Actualizar para cargar este negocio.';
});
const endpoint = tail => `/api/operator/restaurants/${path(business.value)}/${tail}`;
async function api(url, options = {}) {
  const version = scopeVersion;
  const response = await fetch(url, {...options, headers: {
    'X-101-Operator-Token': token.value, 'Content-Type': 'application/json'
  }});
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
async function loadOrders() {
  try {
    const rows = await api(endpoint('orders'));
    replace(orders, rows.length ? rows.map(o => card(
      h('div', {className:'status'}, o.status),
      h('h3', {}, '#', o.public_code, ' · ', o.customer_name || o.customer_phone),
      h('div', {}, o.items.map(i => h('div', {}, i.quantity, ' × ', i.name))),
      h('p', {className:'total'}, money(o.total_minor)),
      meta(`${o.fulfillment_type} · Pago: ${o.payment_status} · ${new Date(o.created_at).toLocaleString()}`),
      o.reconciliation_required ? h('p', {role:'alert'}, 'Pago requiere revisión. No confirmar ni cobrar de nuevo.') : null,
      o.checkout_state && o.checkout_state !== 'ready' ? meta('Pago pendiente de confirmación: ' + o.checkout_state) : null,
      o.delivery ? meta(`Delivery: ${o.delivery.status} · ${money(o.delivery_fee_minor)}`) : null,
      h('div', {className:'actions'}, (!o.reconciliation_required && Object.prototype.hasOwnProperty.call(next, o.status) ? next[o.status] : []).map(s =>
        button(s, async () => {
          await api(`/api/operator/orders/${path(o.id)}`, {method:'PATCH', body:JSON.stringify({status:s})});
          await loadOrders();
        })))
    )) : h('p', {}, 'Sin pedidos.'));
  } catch (error) { if (!error.stale) orders.textContent = error.message; }
}
async function loadReservations() {
  try {
    const rows = await api(endpoint('reservations'));
    replace(reservations, rows.length ? rows.map(r => card(
      h('div', {className:'status'}, r.status), h('h3', {}, '#', r.public_code),
      h('div', {}, r.customer_name || r.customer_phone), h('div', {}, r.party_size, ' personas'),
      meta(new Date(r.starts_at).toLocaleString()),
      h('div', {className:'actions'}, [['Confirmar','confirmed'],['Cancelar','cancelled']].map(([label,status]) =>
        button(label, async () => {
          await api(`/api/operator/reservations/${path(r.id)}`, {method:'PATCH', body:JSON.stringify({status})});
          await loadReservations();
        })))
    )) : h('p', {}, 'Sin reservas.'));
  } catch (error) { if (!error.stale) reservations.textContent = error.message; }
}
const reviewReasons = {
  paid_after_cancellation:'Pago recibido después de cancelar',
  contradictory_payment_notification:'El proveedor reportó estados incompatibles',
  invalid_provider_response:'Respuesta de pago no verificable',
  provider_reference_conflict:'Referencia de pago asociada a otro pedido',
  provider_replay_not_supported:'Pago sin confirmación; consultar al proveedor',
  cancelled_checkout_unknown:'Pedido cancelado con pago por confirmar',
  invalid_payment_notification:'Notificación de pago no válida'
};
async function loadReconciliation() {
  try {
    const rows = await api(endpoint('payment-reconciliation'));
    replace($('reconciliation'), rows.length ? rows.map(r => card(
      h('strong', {}, 'Revisión de pago'), meta('Pedido: ' + r.order_id),
      meta(Object.prototype.hasOwnProperty.call(reviewReasons, r.reason) ? reviewReasons[r.reason] : 'Verificar el pago con el proveedor'), meta(new Date(r.created_at).toLocaleString()),
      h('p', {}, 'Verifica el pago con el proveedor antes de realizar cualquier cobro o devolución. Esta alerta no confirma una devolución.')
    )) : h('p', {}, 'Sin revisiones pendientes.'));
  } catch (error) { if (!error.stale) $('reconciliation').textContent = error.message; }
}
let refreshing = false;
async function refreshAll() {
  if (refreshing) return;
  refreshing = true;
  try { await Promise.all([loadOrders(),loadReservations(),loadReconciliation()]); }
  finally { refreshing = false; }
}
const financeResult = $('financeResult');
let financeVersion = 0, financeBusy = false;
for (const input of [business, $('financeToken'), $('financeOrder')]) input.addEventListener('input', () => {
  ++financeVersion; financeResult.textContent = 'Consultar para cargar el historial de este pedido.';
});
const financeRoot = () => `/api/finance/restaurants/${path(business.value)}/orders/${path($('financeOrder').value.trim())}`;
async function financeAPI(url, body) {
  const version = financeVersion;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, {method:body ? 'POST':'GET', signal:controller.signal,
      headers:{'Content-Type':'application/json','X-101-Financial-Token':$('financeToken').value},
      ...(body ? {body:JSON.stringify(body)} : {})});
    const data = await response.json();
    if(version !== financeVersion){const e=new Error('La selección cambió');e.stale=true;throw e;}
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`HTTP ${response.status}`);
    return data;
  } finally {clearTimeout(timeout);}
}
const financeStates={pending:'Pendiente',processing:'En proceso',unknown:'Sin confirmación; consultar nuevamente',succeeded:'Confirmado por el proveedor',failed:'Rechazado por el proveedor',withdrawn:'Solicitud retirada tras rechazo confirmado',review_required:'Requiere investigación'};
async function renderFinance() {
  const data=await financeAPI(financeRoot());
  const operations=data.operations || [];
  replace(financeResult, [h('p',{},'Una solicitud pendiente no confirma una devolución.'),
    ...operations.map(o=>card(h('strong',{},o.kind==='refund'?'Devolución completa':'Consulta de pago'),
      h('p',{},financeStates[o.state] || o.state),meta('Responsable: '+o.actor_id),meta(o.reason),
      meta(o.result ? JSON.stringify(o.result) : 'Sin evidencia de resultado'))),
    ...((data.reviews||[]).filter(r=>r.status==='open').map(r=>card(meta('Revisión: '+r.reason),
      ...operations.filter(o=>o.state==='succeeded'||o.state==='failed').slice(-3).map(o=>button('Resolver con evidencia '+o.id.slice(0,8),async()=>{
        const reason=$('financeReason').value.trim();if(!reason)throw new Error('Escribe el motivo de la resolución.');
        await financeAPI(financeRoot()+'/resolve/'+path(r.id),{operation_id:o.id,reason});await renderFinance();await loadReconciliation();
      }))))),
    h('h3',{},'Historial de acciones'),...(data.audit||[]).map(a=>card(meta(new Date(a.created_at).toLocaleString()),
      h('div',{},a.actor_id+' · '+a.action),meta(a.reason),meta(JSON.stringify(a.evidence))))]);
}
async function financeAction(kind) {
  if(financeBusy)return;financeBusy=true;
  const version=financeVersion;
  try {
    if(!$('financeOrder').value.trim() || !$('financeToken').value)throw new Error('Indica el pedido y la credencial financiera.');
    if(kind){
      const reason=$('financeReason').value.trim();if(!reason)throw new Error('Escribe el motivo.');
      if(kind==='refund'&&!confirm('¿Solicitar una devolución completa? Si se interrumpe, consulta el historial antes de volver a intentar.'))return;
      if(!window.crypto || !crypto.getRandomValues)throw new Error('Este navegador no permite una solicitud segura.');
      const bytes=new Uint8Array(24);crypto.getRandomValues(bytes);
      await financeAPI(financeRoot()+'/'+kind,{idempotency_key:Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(''),reason});
    }
    await renderFinance();
  } catch(error){if(!error.stale && version===financeVersion)financeResult.textContent=error.name==='AbortError'?'Respuesta no recibida. Consulta el historial: la operación puede continuar.':error.message;}
  finally {financeBusy=false;}
}
const financeHistory=()=>financeAction(null), financeLookup=()=>financeAction('lookup'), financeRefund=()=>financeAction('refund');
bind({refreshAll,financeHistory,financeLookup,financeRefund}); start(() => { refreshAll(); setInterval(refreshAll,5000); });
})();
