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
      o.delivery ? meta(`Delivery: ${o.delivery.status} · ${money(o.delivery_fee_minor)}`) : null,
      h('div', {className:'actions'}, (Object.prototype.hasOwnProperty.call(next, o.status) ? next[o.status] : []).map(s =>
        button(s, async () => {
          await api(`/api/operator/orders/${path(o.id)}`, {method:'PATCH', body:JSON.stringify({status:s})});
          await loadOrders();
        })))
    )) : h('p', {}, 'Sin pedidos.'));
  } catch (error) { orders.textContent = error.message; }
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
  } catch (error) { reservations.textContent = error.message; }
}
let refreshing = false;
async function refreshAll() {
  if (refreshing) return;
  refreshing = true;
  try { await Promise.all([loadOrders(),loadReservations()]); }
  finally { refreshing = false; }
}
bind({refreshAll}); start(() => { refreshAll(); setInterval(refreshAll,5000); });
})();
