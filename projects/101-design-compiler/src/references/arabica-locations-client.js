import { loadGoogleMaps } from '../bones/location-map-google.js';
import { offsetCamera, referenceViewId, referenceHref } from './arabica-locations.js';

export function mountArabicaReference(root, catalogue, services = {}) {
  const views = new Map(catalogue.pages.map(page => [page.id, page]));
  const panel = root.querySelector('[data-reference-panel]');
  const cards = root.querySelector('[data-reference-cards]');
  const canvas = root.querySelector('[data-reference-map]');
  const gate = root.querySelector('[data-map-gate]');
  const status = root.querySelector('[data-map-status]');
  const activate = root.querySelector('[data-activate-map]');
  const announcement = root.querySelector('[data-view-announcement]');
  let api, map, markers = [], view, activationStarted = false;
  const templates = new Map([...document.querySelectorAll('[data-reference-template]')].map(el => [el.dataset.referenceTemplate, el]));
  function camera() {
    if (!map || !view) return;
    const [lng, lat] = offsetCamera(view.center, view.zoom, innerWidth);
    map.setOptions({ center: { lat, lng }, zoom: view.zoom, styles: view.mapStyle });
  }
  function plot() {
    if (!map) return;
    for (const marker of markers) { api.event.clearInstanceListeners(marker); marker.setMap(null); }
    markers = view.markers.map(pin => {
      const opening = pin.status === 'opening';
      const marker = new api.Marker({ map, position: { lng: pin.coordinates[0], lat: pin.coordinates[1] },
        title: pin.name, optimized: false, clickable: !opening,
        animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? undefined : api.Animation.DROP,
        icon: { url: pin.icon, scaledSize: new api.Size(opening ? 14 : 25, opening ? 21 : 34), anchor: new api.Point(opening ? 7 : 12.5, opening ? 21 : 34) } });
      if (!opening) marker.addListener('click', () => {
        const id = referenceViewId(pin.url);
        if (id && views.has(id)) navigate(id, true);
        else location.assign(pin.url);
      });
      return marker;
    });
    camera();
  }
  function installCarousel() {
    const track = cards.querySelector('.reference-card-track');
    const dots = cards.querySelector('.reference-card-dots');
    if (!track || !dots) return;
    const items = [...track.children];
    items.forEach((item, index) => {
      const button = document.createElement('button'); button.type = 'button';
      button.setAttribute('aria-label', `Show location ${index + 1}`);
      if (!index) button.setAttribute('aria-current', 'true');
      button.addEventListener('click', () => track.scrollTo({ left: item.offsetLeft - track.offsetLeft - 20,
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
      dots.append(button);
    });
    track.addEventListener('scroll', () => {
      const active = Math.round(track.scrollLeft / (items[0]?.getBoundingClientRect().width || 1));
      [...dots.children].forEach((button, index) => index === active ? button.setAttribute('aria-current', 'true') : button.removeAttribute('aria-current'));
    }, { passive: true });
  }
  function navigate(id, push = false) {
    if (!views.has(id)) id = 'world';
    view = views.get(id);
    const fragment = templates.get(id).content.cloneNode(true);
    panel.replaceChildren(fragment.querySelector('.reference-panel'));
    cards.replaceChildren(...fragment.querySelectorAll('.reference-cards'));
    root.dataset.referenceView = id;
    root.dataset.referenceLevel = view.level;
    document.title = `% Arabica · ${view.level === 'world' ? 'Locations' : view.id.split('/').at(-1)} · private reference`;
    if (push) { history.pushState({ arabicaView: id }, '', referenceHref(id)); window.scrollTo(0, 0); }
    plot(); installCarousel();
    announcement.textContent = `${view.panelHeading}: ${view.links.map(link => link.name).join(', ')}`;
  }
  root.addEventListener('click', event => {
    const link = event.target.closest('[data-reference-view]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault(); const id = link.dataset.referenceView;
    navigate(id, true);
    if (event.detail === 0) panel.querySelector('a')?.focus({ preventScroll: true });
  });
  const readURL = () => new URL(location.href).searchParams.get('view') || 'world';
  window.addEventListener('popstate', () => navigate(readURL()));
  const observer = new ResizeObserver(() => { if (api && map) { api.event.trigger(map, 'resize'); camera(); } });
  observer.observe(canvas);
  const menu = root.querySelector('.reference-menu-button');
  const nav = root.querySelector('.reference-navigation');
  menu.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); nav.toggleAttribute('data-open', open); });
  root.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.hasAttribute('data-open')) { nav.removeAttribute('data-open'); menu.setAttribute('aria-expanded', 'false'); menu.focus(); } });
  async function start() {
    if (activationStarted) return;
    activationStarted = true; activate.disabled = true; status.textContent = 'Cargando Google Maps…';
    try {
      const response = await (services.reserve || (() => fetch('/arabica/trial-config', { method: 'POST' })))();
      if (!response.ok) throw Error(response.status === 429 ? 'BUDGET' : 'CONFIG');
      const { google } = await response.json();
      api = await (services.load || loadGoogleMaps)(google);
      const [lng, lat] = offsetCamera(view.center, view.zoom, innerWidth);
      map = new api.Map(canvas, { center: { lat, lng }, zoom: view.zoom, styles: view.mapStyle,
        draggable: true, scrollwheel: false, streetViewControl: true, mapTypeId: 'roadmap',
        disableDefaultUI: true, scaleControl: true, zoomControl: true });
      plot();
      api.event.addListenerOnce(map, 'idle', () => { gate.hidden = true; root.dataset.mapState = 'ready'; });
      root.dataset.mapState = 'loading';
    } catch (error) {
      root.dataset.mapState = 'unavailable';
      status.textContent = error.message === 'BUDGET'
        ? 'La prueba de Google alcanzó su límite. Puedes seguir consultando las ubicaciones.'
        : 'Google Maps no está disponible. Puedes seguir consultando las ubicaciones.';
    }
  }
  activate.addEventListener('click', start);
  navigate(readURL());
  return { navigate, activate: start, inspect: () => ({ version: '0.1.0', view: view.id,
    provider: 'google', mapInstances: map ? 1 : 0, markerCount: markers.length,
    markerCoordinates: markers.map(marker => marker.getPosition().toJSON()),
    camera: map ? { center: map.getCenter().toJSON(), zoom: map.getZoom() } : null,
    state: root.dataset.mapState || 'inactive' }) };
}

const root = document.querySelector('.arabica-reference');
if (root) {
  const catalogue = JSON.parse(document.getElementById('arabica-reference-input').textContent);
  window.arabicaReference = mountArabicaReference(root, catalogue);
}
