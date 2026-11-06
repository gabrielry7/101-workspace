/** The host element belongs to the real provider marker, never a viewport overlay. */
export function attachMarkerVisual(host, binding, name, onChange = () => {}) {
  host.classList.add('single-business-marker');
  host.setAttribute('aria-label', `Cómo llegar a ${name}`);
  const visual = document.createElement('span');
  visual.className = 'single-business-marker__visual';
  visual.setAttribute('aria-hidden', 'true');
  const label = document.createElement('span');
  label.className = 'location-map__marker-label'; label.textContent = name;
  host.replaceChildren(visual, label);
  let kind = 'pin', reason = binding?.reason || 'LOGO_MISSING', disposed = false;
  function pin() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 36 48'); svg.setAttribute('width', '36'); svg.setAttribute('height', '48');
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', 'M18 48C14 39 0 29 0 18A18 18 0 0 1 36 18C36 29 22 39 18 48Z');
    path.setAttribute('fill', 'currentColor');
    const dot = document.createElementNS(svg.namespaceURI, 'circle');
    dot.setAttribute('cx', '18'); dot.setAttribute('cy', '18'); dot.setAttribute('r', '6'); dot.setAttribute('fill', 'white');
    svg.append(path, dot); visual.replaceChildren(svg); kind = 'pin';
    host.dataset.markerKind = kind; onChange({ kind, reason });
  }
  pin();
  if (binding?.kind === 'logo' && /^\/(?!\/)/.test(binding.url || '')) {
    const image = new Image(); image.alt = ''; image.width = 64; image.height = 64;
    image.className = 'single-business-marker__logo'; image.decoding = 'async';
    image.onload = () => {
      if (disposed) return;
      kind = 'logo'; reason = binding.reason; visual.replaceChildren(image);
      host.dataset.markerKind = kind; onChange({ kind, reason });
    };
    image.onerror = () => { if (!disposed) { reason = 'LOGO_LOAD_FAILED'; pin(); } };
    image.src = binding.url;
  }
  return {
    inspect: () => ({ marker_kind: kind, logo_reason: reason }),
    // Bottom center is identical for a logo badge and the fallback pin.
    anchor: () => { const r = host.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.bottom }; },
    destroy: () => { disposed = true; },
  };
}
