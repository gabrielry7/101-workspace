/** The host element belongs to the real provider marker, never a viewport overlay. */
export function attachMarkerVisual(host, binding, name, onChange = () => {}, { showLabel = true } = {}) {
  host.classList.add('single-business-marker');
  host.setAttribute('aria-label', `Cómo llegar a ${name}`);
  const visual = document.createElement('span');
  visual.className = 'single-business-marker__visual';
  visual.setAttribute('aria-hidden', 'true');
  const frame = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  frame.setAttribute('viewBox', '0 0 64 80');
  frame.setAttribute('width', '64'); frame.setAttribute('height', '80');
  frame.classList.add('single-business-marker__frame');
  frame.dataset.locationPart = 'marker-pin';
  const outline = document.createElementNS(frame.namespaceURI, 'path');
  outline.setAttribute('d', 'M32 80C25 69 1 49 1 32a31 31 0 0 1 62 0c0 17-24 37-31 48Z');
  outline.setAttribute('fill', 'var(--map-paper, white)');
  outline.setAttribute('stroke', 'var(--map-ink, currentColor)');
  outline.setAttribute('stroke-width', '1.5');
  const dot = document.createElementNS(frame.namespaceURI, 'circle');
  dot.setAttribute('cx', '32'); dot.setAttribute('cy', '32'); dot.setAttribute('r', '7');
  dot.setAttribute('fill', 'currentColor'); frame.append(outline, dot);
  host.replaceChildren(visual);
  if (showLabel) {
    const label = document.createElement('span');
    label.className = 'location-map__marker-label'; label.textContent = name;
    host.append(label);
  }
  let kind = 'pin', reason = binding?.reason || 'LOGO_MISSING', disposed = false;
  function pin() {
    dot.removeAttribute('visibility');
    visual.replaceChildren(frame); kind = 'pin';
    host.dataset.markerKind = kind; onChange({ kind, reason });
  }
  pin();
  if (binding?.kind === 'logo' && /^\/(?!\/)/.test(binding.url || '')) {
    const image = new Image(); image.alt = ''; image.width = 64; image.height = 64;
    image.className = 'single-business-marker__logo'; image.decoding = 'async';
    image.dataset.locationPart = 'brand-logo-slot';
    image.onload = () => {
      if (disposed) return;
      kind = 'logo'; reason = binding.reason; dot.setAttribute('visibility', 'hidden');
      visual.replaceChildren(frame, image);
      host.dataset.markerKind = kind; onChange({ kind, reason });
    };
    image.onerror = () => { if (!disposed) { reason = 'LOGO_LOAD_FAILED'; pin(); } };
    image.src = binding.url;
  }
  return {
    inspect: () => ({ marker_kind: kind, logo_reason: reason,
      marker_label_visible: showLabel }),
    // The same bottom-center tip anchors the logo pin and its neutral fallback.
    anchor: () => {
      const matrix = frame.getScreenCTM();
      if (matrix) {
        const tip = frame.createSVGPoint(); tip.x = 32; tip.y = 80;
        const point = tip.matrixTransform(matrix); return { x: point.x, y: point.y };
      }
      const r = host.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.bottom };
    },
    destroy: () => { disposed = true; },
  };
}
