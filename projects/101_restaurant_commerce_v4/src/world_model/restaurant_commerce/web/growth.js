"use strict";
(() => {
const {$, node: h, replace, safeURL, bind, start, money, path} = window.CommerceUI;
const business = $('business'), token = $('token');
const endpoint = tail => `/api/operator/restaurants/${path(business.value)}/${tail}`;
async function api(url, options = {}) {
  const response = await fetch(url, {...options, headers: {
    'X-101-Operator-Token': token.value, 'Content-Type': 'application/json'
  }});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}
const card = (...children) => h('div', {className: 'card'}, children);
const meta = text => h('div', {className: 'meta'}, text);
const button = (label, action) => h('button', {onClick: async event => {
  const el = event.currentTarget;
  el.disabled = true;
  try { await action(); } catch (error) { alert(error.message); }
  finally { el.disabled = false; }
}}, label);

async function loadAnalytics() {
  const a = await api(endpoint('analytics'));
  const values = [['Pedidos completos',a.completed_orders],['Ventas netas',money(a.net_revenue_minor)],
    ['Ticket promedio',money(a.average_order_value_minor)],['Clientes',a.unique_customers],
    ['Clientes repetidos',`${Math.round(a.repeat_customer_rate*100)}%`],['Puntos pendientes',a.loyalty_points_outstanding],
    ['Mensajes en cola',a.queued_messages],['Suprimidos',a.suppressed_messages]];
  replace($('metrics'), values.map(([label,value]) => h('div',{className:'metric'},h('span',{className:'muted'},label),h('strong',{},value))));
}
async function loadPromos() {
  const rows = await api(endpoint('promotions'));
  replace($('promos'), rows.length ? rows.map(p => card(h('strong',{},p.code),' · ',p.name,
    meta(`${p.discount_type === 'percent' ? p.value/100+'%' : money(p.value)} · mínimo ${money(p.minimum_order_minor)}`))) : h('p',{},'Sin promociones.'));
}
async function loadRewards() {
  const rows = await api(endpoint('rewards'));
  replace($('rewards'), rows.length ? rows.map(r => card(h('strong',{},r.name),
    h('div',{},r.points_cost,' puntos → ',money(r.discount_minor)),meta(r.description || ''))) : h('p',{},'Sin rewards.'));
}
async function loadOutbox() {
  const rows = await api(endpoint('outbox'));
  replace($('outbox'), rows.length ? rows.map(m => card(
    h('strong',{className:m.status === 'queued' ? 'queued' : 'suppressed'},m.status),' · ',m.message_kind,
    h('div',{},m.body),meta(`${m.destination} · ${new Date(m.scheduled_at).toLocaleString()}${m.suppression_reason ? ' · '+m.suppression_reason : ''}`),
    ['queued','handed_off'].includes(m.status) ? button('Abrir WhatsApp', () => openWA(m)) : null
  )) : h('p',{},'Outbox vacío.'));
}
async function openWA(message) {
  // Recheck recipient/consent at the server before exposing a composer link.
  const authorized = await api(`/api/operator/outbox/${path(message.id)}/handoff`, {method:'POST'});
  const phone = String(authorized.destination).replace(/\D/g,'');
  if (!phone) throw new Error('Destino inválido');
  window.open(`https://wa.me/${phone}?text=${encodeURIComponent(authorized.body)}`,'_blank','noopener,noreferrer');
  await loadOutbox();
}
async function planWinback() { await api(endpoint('winback/plan'),{method:'POST',body:JSON.stringify({limit:100})}); await refreshAll(); }
async function refreshAll() {
  try { await Promise.all([loadAnalytics(),loadPromos(),loadRewards(),loadOutbox()]); }
  catch(error) { alert(error.message); }
}
bind({refreshAll,planWinback:()=>planWinback().catch(error=>alert(error.message))}); start(refreshAll);
})();
