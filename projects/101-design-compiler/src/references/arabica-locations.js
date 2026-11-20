export const referenceVersion = '0.1.1';

export function referenceViewId(value) {
  const url = new URL(value, 'https://arabica.com');
  if (url.origin !== 'https://arabica.com' || !/^\/en\/locations(?:\/|$)/.test(url.pathname)) return null;
  const id = url.pathname.replace(/^\/en\/locations\/?/, '').replace(/\/$/, '');
  return !id ? 'world' : /^[a-z0-9-]+(?:\/[a-z0-9-]+)?$/.test(id) ? id : null;
}

export function referenceHref(id) {
  if (id === 'world') return '/arabica/';
  if (!/^[a-z0-9-]+(?:\/[a-z0-9-]+)?$/.test(id)) throw Error('INVALID_REFERENCE_VIEW');
  return `/arabica/?view=${encodeURIComponent(id)}`;
}

export function offsetCamera(coordinates, zoom, width) {
  if (width < 560) return [...coordinates];
  const [longitude, latitude] = coordinates;
  const scale = 256 * 2 ** zoom;
  const sine = Math.sin(latitude * Math.PI / 180);
  const y = (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) + 100 / scale;
  return [longitude - 100 / scale * 360, Math.atan(Math.sinh(Math.PI * (1 - 2 * y))) * 180 / Math.PI];
}

export function validateReferenceCatalogue(input) {
  if (input?.schema !== '101-arabica-reference-v1' || input.referenceOnly !== true
    || input.publicationAllowed !== false || !Number.isFinite(Date.parse(input.observedAt))
    || !Array.isArray(input.pages) || !input.pages.length) throw Error('PRIVATE_REFERENCE_INPUT_REQUIRED');
  const ids = new Set();
  const coordinate = value => Array.isArray(value) && value.length === 2 && value.every(Number.isFinite)
    && Math.abs(value[0]) <= 180 && Math.abs(value[1]) < 90;
  const official = value => {
    const url = new URL(value);
    if (url.origin !== 'https://arabica.com') throw Error('REFERENCE_URL_REQUIRED');
  };
  for (const page of input.pages) {
    if (referenceViewId(page.url) !== page.id || ids.has(page.id) || !coordinate(page.center)
      || !Number.isInteger(page.zoom) || page.zoom < 0 || page.zoom > 22
      || !['world', 'country', 'city'].includes(page.level) || !Array.isArray(page.mapStyle)) {
      throw Error(`INVALID_REFERENCE_PAGE:${page.id}`);
    }
    ids.add(page.id);
    for (const link of page.links) {
      official(link.url);
      if (!link.name || link.count !== null && (!Number.isInteger(link.count) || link.count < 0)) throw Error('INVALID_REFERENCE_LINK');
    }
    for (const marker of page.markers) {
      if (!coordinate(marker.coordinates) || !marker.name) throw Error(`INVALID_REFERENCE_MARKER:${page.id}:${marker.name}`);
      if (marker.url !== '#') official(marker.url);
    }
    for (const card of page.cards) {
      official(card.url);
      if (!/^\/arabica\/assets\/[a-f0-9]{20}\.(?:png|jpg|jpeg|webp)$/.test(card.image)) official(card.image);
    }
  }
  if (!ids.has('world')) throw Error('WORLD_REFERENCE_REQUIRED');
  for (const page of input.pages) for (const link of page.links) {
    const id = referenceViewId(link.url);
    if (id && !ids.has(id)) throw Error(`REFERENCE_VIEW_MISSING:${id}`);
  }
  return input;
}
