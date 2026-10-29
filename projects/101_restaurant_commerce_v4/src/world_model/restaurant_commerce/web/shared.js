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
  async function start(run) {
    try {
      const response = await fetch('/api/browser-policy');
      if (!response.ok) throw new Error('policy unavailable');
      policy = await response.json();
    } catch (_) { /* Fail closed for external navigation; local UI still works. */ }
    run();
  }
  const money = n => new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', maximumFractionDigits: 0
  }).format(Number(n) || 0);
  const path = value => encodeURIComponent(String(value));
  return {$, node, replace, safeURL, bind, start, money, path};
})();
