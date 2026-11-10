import { attachMarkerVisual } from './location-map-marker.js';

let sharedLoad, loadedKey;
export function googleConfiguration(value) {
  if (value?.enabled !== true || typeof value.apiKey !== 'string' || !value.apiKey.trim()
    || typeof value.mapId !== 'string' || !/^[a-zA-Z0-9_-]{5,80}$/.test(value.mapId) || value.mapId === 'DEMO_MAP_ID'
    || value.styleReview?.mapId !== value.mapId || value.styleReview?.pois !== 'none'
    || typeof value.styleReview?.reference !== 'string' || !value.styleReview.reference.trim()
    || !/(?:Z|[+-]\d\d:\d\d)$/.test(value.styleReview?.reviewedAt || '')
    || !Number.isFinite(Date.parse(value.styleReview.reviewedAt))) return null;
  return value;
}

export function loadGoogleMaps(config) {
  if (sharedLoad) {
    if (loadedKey !== config.apiKey) return Promise.reject(Error('GOOGLE_LOADER_CONFIG_CONFLICT'));
    return sharedLoad;
  }
  loadedKey = config.apiKey;
  sharedLoad = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    const callback = '__singleBusinessGoogleReady';
    const timer = setTimeout(() => fail(), 20000);
    function cleanup() { clearTimeout(timer); delete globalThis[callback]; }
    function fail() { cleanup(); script.remove(); sharedLoad = undefined; reject(Error('GOOGLE_API_UNAVAILABLE')); }
    globalThis[callback] = async () => {
      cleanup();
      try {
        await Promise.all([globalThis.google.maps.importLibrary('maps'), globalThis.google.maps.importLibrary('marker')]);
        resolve(globalThis.google.maps);
      } catch { fail(); }
    };
    const url = new URL('https://maps.googleapis.com/maps/api/js');
    url.searchParams.set('key', config.apiKey); url.searchParams.set('v', 'weekly');
    url.searchParams.set('loading', 'async'); url.searchParams.set('callback', callback);
    script.src = url.href; script.async = true; script.onerror = fail;
    document.head.append(script);
  });
  return sharedLoad;
}

/** Provider adapter in the same location capability, not an iframe or duplicate service. */
export function mountGoogleLocation(root, config, owner, services = {}) {
  const location = owner.locationInput(config.location);
  const googleConfig = googleConfiguration(config.google);
  const eligible = owner.rendererEligibility(location, 'google_embed'); // Existing Google source-use rules.
  let destroyed = false, map, marker, overlay, visual, observer, api, timer;
  let state = 'fallback', reason = !eligible.render ? eligible.reason : 'GOOGLE_CONFIGURATION_REQUIRED';
  let presentation = owner.presentation(config.presentation);
  let markerLabel = config.markerLabel !== false;
  root.replaceChildren(); root.classList.add('location-map'); root.dataset.mapProvider = 'google_js';
  const canvas = document.createElement('div'); canvas.className = 'location-map__canvas';
  canvas.setAttribute('role', 'region'); canvas.setAttribute('aria-label', `Mapa de ${location.name}`);
  const status = document.createElement('p'); status.className = 'location-map__status'; status.setAttribute('role', 'status');
  status.dataset.locationPart = 'status-fallback';
  root.append(canvas, status);
  function update(next, why) {
    if (destroyed) return;
    state = next; reason = why; root.dataset.mapState = state; root.dataset.mapReason = reason;
    canvas.hidden = state === 'fallback';
    status.textContent = state === 'loading' ? 'Cargando mapa…' : state === 'ready'
      ? 'Ubicación de referencia; la entrada exacta puede variar.'
      : 'Mapa no disponible. Puedes consultar la dirección y abrir las indicaciones.';
  }
  function colors() {
    for (const key of ['pin', 'paper', 'ink']) root.style.setProperty(`--map-${key}`, presentation.colors[key]);
  }
  colors(); update(state, reason);
  const control = {
    inspect() {
      let offset = null;
      const projected = overlay?.getProjection()?.fromLatLngToContainerPixel(
        new api.LatLng(location.coordinate.latitude, location.coordinate.longitude));
      if (visual && projected) {
        const a = visual.anchor(), r = canvas.getBoundingClientRect();
        offset = Math.hypot(a.x - r.left - projected.x, a.y - r.top - projected.y);
      }
      const position = marker?.position;
      const actual = position ? [typeof position.lng === 'function' ? position.lng() : position.lng,
        typeof position.lat === 'function' ? position.lat() : position.lat] : null;
      return { bone_version: 'location.single-business@0.3.0', provider: 'google_js', state, reason,
        camera_zoom: map?.getZoom?.() ?? presentation.zoom,
        location_id: location.location_id, expected_coordinate: location.coordinate
          ? [location.coordinate.longitude, location.coordinate.latitude] : null,
        marker_coordinate: actual, coordinate_source: location.coordinate?.source || null,
        business_pin_plotted: !!marker, ...visual?.inspect(), marker_anchor_offset_px: offset,
        poi_policy: { mode: 'none', ids: [], limit: 0 }, rendered_poi_ids: null,
        verification: services.verification || 'google-live-style-not-machine-verified',
        style_review_reference: googleConfig?.styleReview.reference || null,
        publication_allowed: location.publication_allowed };
    },
    setMarkerLabel(visible) {
      if (typeof visible !== 'boolean') throw Error('BOOLEAN_MARKER_LABEL_REQUIRED');
      markerLabel = visible; visual?.setLabelVisible(visible);
    },
    setPresentation(next) {
      if (destroyed) throw Error('MAP_DESTROYED');
      if (!next || Object.keys(next).some(k => !['zoom', 'colors', 'pois'].includes(k))
        || next.pois && (next.pois.mode !== 'none' || next.pois.ids?.length || next.pois.limit)) {
        throw Error('SINGLE_BUSINESS_POIS_MUST_BE_NONE');
      }
      if (next.colors && Object.keys(next.colors).some(k => !['pin', 'paper', 'ink'].includes(k))) {
        throw Error('GOOGLE_BASEMAP_COLORS_REQUIRE_REVIEWED_CLOUD_STYLE');
      }
      presentation = owner.presentation({ ...presentation, ...next,
        colors: { ...presentation.colors, ...next.colors }, pois: { mode: 'none', ids: [], limit: 0 } });
      colors(); if (map && next.zoom !== undefined) map.setZoom(presentation.zoom);
    },
    destroy() {
      if (destroyed) return;
      destroyed = true; state = 'destroyed'; clearTimeout(timer); observer?.disconnect(); visual?.destroy();
      if (marker) { marker.map = null; api.event.clearInstanceListeners(marker); }
      overlay?.setMap(null); if (map) api.event.clearInstanceListeners(map);
      root.replaceChildren(); root.dataset.mapState = state; marker = undefined; map = undefined;
    },
  };
  if (!eligible.render || !googleConfig) return control;
  update('loading', 'GOOGLE_API_REQUESTED');
  timer = setTimeout(() => update('degraded', 'GOOGLE_MAP_LOAD_TIMEOUT'), 30000);
  (services.load || loadGoogleMaps)(googleConfig).then(maps => {
    if (destroyed) return;
    api = maps;
    map = new api.Map(canvas, { mapId: googleConfig.mapId,
      center: { lat: location.coordinate.latitude, lng: location.coordinate.longitude }, zoom: presentation.zoom,
      minZoom: 3, maxZoom: 18, mapTypeId: 'roadmap', mapTypeControl: false, streetViewControl: false,
      clickableIcons: false, gestureHandling: 'cooperative', disableDoubleClickZoom: false });
    const host = document.createElement('div');
    host.dataset.locationPart = 'business-marker';
    visual = attachMarkerVisual(host, config.marker, location.name, info => {
      root.dataset.markerKind = info.kind; root.dataset.logoReason = info.reason;
    }, { showLabel: markerLabel });
    marker = new api.marker.AdvancedMarkerElement({ map,
      position: { lat: location.coordinate.latitude, lng: location.coordinate.longitude },
      title: `Cómo llegar a ${location.name}`, gmpClickable: true, gmpDraggable: false,
      anchorLeft: '-50%', anchorTop: '-100%' });
    marker.append(host);
    marker.addEventListener('gmp-click', () => document.getElementById(config.navigationId)
      ?.querySelector('[data-map-app="google"]')?.focus());
    overlay = new api.OverlayView(); overlay.onAdd = () => {}; overlay.draw = () => {}; overlay.onRemove = () => {};
    overlay.setMap(map);
    api.event.addListenerOnce(map, 'idle', () => { clearTimeout(timer); update('ready', 'GOOGLE_STYLE_REQUIRES_LIVE_REVIEW'); });
    observer = new ResizeObserver(() => api.event.trigger(map, 'resize')); observer.observe(canvas);
  }).catch(() => { clearTimeout(timer); update('fallback', 'GOOGLE_API_UNAVAILABLE'); });
  return control;
}
