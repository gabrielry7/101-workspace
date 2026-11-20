import { loadGoogleMaps } from '../bones/location-map-google.js';
import { offsetCamera, referenceViewId } from './arabica-locations.js';

// Map provider only; composition and navigation belong to LocationDirectory.
export function mountArabicaDirectoryMap(root, catalogue, services = {}) {
  const views = new Map(catalogue.pages.map(page => [page.id, page]));
  const canvas = root.querySelector('[data-directory-map]');
  const gate = root.querySelector('[data-map-gate]');
  const status = root.querySelector('[data-map-status]');
  const activate = root.querySelector('[data-activate-map]');
  let api, map, markers = [], view = views.get('world'), activationStarted = false;
  root.dataset.directoryProvider = 'google';
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
        if (id && views.has(id)) root.dispatchEvent(new CustomEvent('directory:select', { detail: { viewId: id } }));
        else location.assign(pin.url);
      });
      return marker;
    });
    camera();
  }

  const observer = new ResizeObserver(() => { if (api && map) api.event.trigger(map, 'resize'); });
  observer.observe(canvas);
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
        gestureHandling: 'greedy', keyboardShortcuts: true, streetViewControl: true, mapTypeId: 'roadmap',
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
  return { select(id) { view = views.get(id) || views.get('world'); plot(); }, activate: start, inspect: () => ({ version: '0.2.0', view: view.id,
    provider: 'google', mapInstances: map ? 1 : 0, markerCount: markers.length,
    gestureHandling: map?.get('gestureHandling') ?? null,
    markerCoordinates: markers.map(marker => marker.getPosition().toJSON()),
    camera: map ? { center: map.getCenter().toJSON(), zoom: map.getZoom() } : null,
    state: root.dataset.mapState || 'inactive' }) };
}
