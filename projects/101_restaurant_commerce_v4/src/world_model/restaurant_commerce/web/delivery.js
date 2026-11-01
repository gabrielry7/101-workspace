"use strict";
(() => {
if(window.CommerceSupported===false)return;
const {$, node: h, replace, safeURL, bind, start, money, path} = window.CommerceUI;
const business = $('business');
let scopeVersion = 0;
for (const input of [business]) input.addEventListener('input', () => {
  ++scopeVersion;
  for (const id of ['rows']) $(id).textContent = 'Actualizar para cargar este negocio.';
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

const rows = $('rows');
let refreshing = false;
async function loadAll() {
  if (refreshing) return;
  refreshing = true;
  try {
    const [deliveries, orders] = await Promise.all([api(endpoint('deliveries')),api(endpoint('orders'))]);
    const byID = new Map(orders.map(o => [o.id,o]));
    replace(rows, deliveries.length ? deliveries.map(d => {
      const o = byID.get(d.order_id), actions = [];
      const perform = async (url, method, body) => { await api(url,{method,body}); await loadAll(); };
      if (d.status === 'quoted' && o && ['accepted','preparing','ready'].includes(o.status))
        actions.push(button('Despachar courier', () => perform(`/api/operator/orders/${path(o.id)}/delivery/dispatch`,'POST')));
      if (d.status === 'courier_assigned' || d.status === 'picked_up') {
        const status = d.status === 'courier_assigned' ? 'picked_up' : 'delivered';
        actions.push(button(status === 'picked_up' ? 'Recogido' : 'Entregado', () =>
          perform(`/api/operator/deliveries/${path(d.id)}/status`,'PATCH',JSON.stringify({status}))));
      }
      if (!['delivered','cancelled','failed','picked_up'].includes(d.status))
        actions.push(button('Cancelar delivery', () => perform(`/api/operator/orders/${path(d.order_id)}/delivery/cancel`,'POST')));
      const tracking = safeURL(d.tracking_url,'tracking');
      return card(h('div', {className:'cols'},
        h('div', {}, h('div',{className:'status'},d.status),h('h3',{},o ? '#'+o.public_code : d.order_id),
          h('div',{},d.destination_address),meta(`${d.destination_city} · ${d.provider}`),h('p',{className:'money'},money(d.fee_minor))),
        h('div', {},meta(`Courier: ${d.courier_name || '—'}`),meta(`Ref: ${d.provider_delivery_reference || 'sin despachar'}`),
          meta(`ETA: ${d.estimated_dropoff_at ? new Date(d.estimated_dropoff_at).toLocaleString() : '—'}`),
          meta(`Pedido: ${o?.status || '—'} · pago ${o?.payment_status || '—'}`),
          tracking ? h('a',{href:tracking,rel:'noopener noreferrer'},'Tracking provider') :
            (d.tracking_url ? meta('Enlace de tracking no autorizado.') : null))),
        h('div',{className:'actions'},actions));
    }) : h('p',{},'Sin entregas.'));
  } catch(error) { if (!error.stale) rows.textContent = error.message; }
  finally { refreshing = false; }
}
window.addEventListener('staffchange', event => { ++scopeVersion; for(const id of ['rows']) $(id).textContent='Actualizar para cargar datos autorizados.'; if(event.detail.authenticated) loadAll(); });
const refresh=window.CommerceUI.poll(loadAll,{active:()=>!!window.CommerceStaff.identity()});bind({loadAll:refresh.refresh});start(()=>window.CommerceStaff.ready.then(refresh.refresh));
})();
