import { attachMarkerVisual } from './location-map-marker.js';
import { mountGoogleLocation } from './location-map-google.js';
import { openFreeMapRequest, openFreeMapStyle, updateOpenFreeMapLayers } from './location-map-openfreemap.js';
import { openFreeMapDefaults, parseOpenFreeMapOptions } from './location-map-editor.ts';

export const LOCATION_BONE_VERSION = 'location.single-business@0.5.0';
export function fixedPresentation(value = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.keys(value).some(key => !['colors', 'zoom', 'pois'].includes(key))) {
    throw Error('BONE_PRESENTATION_MAY_NOT_CHANGE_IDENTITY');
  }
  const poi = value.pois;
  if (poi && (poi.mode !== 'none' || (poi.ids?.length ?? 0) > 0 || (poi.limit ?? 0) !== 0)) {
    throw Error('SINGLE_BUSINESS_POIS_MUST_BE_NONE');
  }
  return { ...value, pois: { mode: 'none', ids: [], limit: 0 } };
}

/** owner is the actual pinned package, injected by the private local build. */
export function mountSingleBusinessLocation(root, config, owner) {
  if (config.contextPreview || config.decorateMap) throw Error('BONE_REQUIRES_CANONICAL_BUSINESS_PIN');
  const location = owner.locationInput(config.location);
  const presentation = fixedPresentation(config.presentation);
  const provider = config.provider || 'maplibre';
  if (provider === 'google_js') return mountGoogleLocation(root, { ...config, location, presentation }, owner);
  if (provider !== 'maplibre') {
    root.dataset.mapState = 'fallback'; root.dataset.mapReason = 'PROVIDER_CANNOT_HIDE_POIS_AND_REPLACE_PIN';
    return { inspect: () => ({ version: LOCATION_BONE_VERSION, provider, state: 'fallback',
      reason: root.dataset.mapReason, marker_coordinate: null, business_pin_plotted: false }),
      setPresentation: () => { throw Error('INCOMPATIBLE_MAP_PROVIDER'); }, destroy() {} };
  }
  let map, visual;
  const openFreeMap = config.basemap?.format === 'openfreemap';
  const sample = openFreeMap && location.coordinate?.purpose === 'synthetic';
  let openPresentation = openFreeMap ? owner.presentation(presentation) : null;
  let mapOptions = openFreeMap ? openFreeMapDefaults(openPresentation.colors) : null;
  let appliedStyle;
  const basemap = openFreeMap ? { ...config.basemap, format: 'geojson' } : config.basemap;
  function applyLayers() {
    if (!appliedStyle) return;
    const nextStyle = openFreeMapStyle(mapOptions, basemap);
    updateOpenFreeMapLayers(map, appliedStyle, nextStyle);
    appliedStyle = nextStyle;
  }
  const native = owner.mountLocationMap(root, {
    location, provider, presentation, basemap, workerURL: config.workerURL,
    detailsMode: 'external', navigationId: config.navigationId,
    decorateMap({ map: actualMap }) {
      map = actualMap;
      if (openFreeMap) {
        map.setTransformRequest(url => openFreeMapRequest(url, document.baseURI));
        const initialStyle = openFreeMapStyle(mapOptions, basemap);
        map.once('style.load', () => {
          appliedStyle = initialStyle;
          applyLayers();
        });
        map.setStyle(initialStyle, { diff: false });
      }
      const pin = root.querySelector('.location-map__marker');
      if (!pin) throw Error('OWNER_BUSINESS_MARKER_MISSING');
      pin.dataset.locationPart = 'business-marker';
      const keyboard = new AbortController();
      if (sample) {
        pin.setAttribute('tabindex', '-1');
        pin.setAttribute('aria-disabled', 'true');
        root.addEventListener('location-map-state', event => {
          const status = root.querySelector('.location-map__status');
          if (event.detail.state === 'ready') {
            status.textContent = 'Cartografía real de OpenStreetMap. El pin señala un punto de muestra.';
          }
          if (['fallback', 'degraded'].includes(event.detail.state)) {
            status.textContent = 'Mapa no disponible. Puedes consultar la dirección de la sucursal.';
          }
        }, { signal: keyboard.signal });
      }
      pin.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault(); event.stopPropagation(); pin.click();
        }
      }, { signal: keyboard.signal });
      visual = attachMarkerVisual(pin, config.marker, location.name, state => {
        root.dataset.markerKind = state.kind; root.dataset.logoReason = state.reason;
      }, { showLabel: config.markerLabel !== false });
      if (sample) pin.setAttribute('aria-label', `Pin de muestra de ${location.name}`);
      return { destroy: () => { keyboard.abort(); visual?.destroy(); } };
    },
  });
  root.querySelector('.location-map__status')?.setAttribute('data-location-part', 'status-fallback');
  root.querySelector('.maplibregl-ctrl-attrib')?.setAttribute('data-location-part', 'provider-attribution');
  return {
    inspect() {
      const state = native.inspect();
      let offset = null;
      if (map && visual && state.marker_coordinate) {
        const p = map.project(state.marker_coordinate), r = map.getCanvas().getBoundingClientRect(), a = visual.anchor();
        offset = Math.hypot(a.x - r.left - p.x, a.y - r.top - p.y);
      }
      return { ...state, bone_version: LOCATION_BONE_VERSION, ...visual?.inspect(),
        marker_anchor_offset_px: offset, verification: 'native-source-bound',
        ...(openFreeMap ? { cartography: 'openfreemap',
          cartography_layers: map?.getStyle()?.layers?.map(layer => layer['source-layer']).filter(Boolean) ?? [] } : {}),
        poi_policy: { mode: 'none', limit: 0, ids: [] } };
    },
    setMarkerLabel(visible) {
      if (typeof visible !== 'boolean') throw Error('BOOLEAN_MARKER_LABEL_REQUIRED');
      config.markerLabel = visible; visual?.setLabelVisible(visible);
    },
    setPresentation(next) {
      const changes = fixedPresentation(next);
      if (!openFreeMap) {
        native.setPresentation(changes);
        return;
      }
      const previous = openPresentation.colors;
      openPresentation = owner.presentation({ ...openPresentation, ...changes,
        colors: { ...previous, ...changes.colors } });
      for (const color of ['paper', 'ink', 'pin']) {
        if (previous[color] !== openPresentation.colors[color]) root.style.setProperty(`--map-${color}`, openPresentation.colors[color]);
      }
      const previousDefaults = openFreeMapDefaults(previous);
      const updatedDefaults = openFreeMapDefaults(openPresentation.colors);
      for (const key of Object.keys(previousDefaults)) {
        if (previousDefaults[key] !== updatedDefaults[key]) mapOptions[key] = updatedDefaults[key];
      }
      applyLayers();
      if (Object.hasOwn(changes, 'zoom')) map?.jumpTo({ zoom: openPresentation.zoom });
    },
    ...(openFreeMap ? {
      setOpenFreeMapOptions(options) {
        const next = parseOpenFreeMapOptions(options);
        const camera = {};
        for (const key of ['bearing', 'pitch']) {
          if (next[key] !== mapOptions[key]) camera[key] = next[key];
        }
        for (const key of ['scrollZoom', 'dragPan']) {
          if (next[key] !== mapOptions[key]) map?.[key][next[key] ? 'enable' : 'disable']();
        }
        mapOptions = next;
        if (Object.keys(camera).length) map?.jumpTo(camera);
        applyLayers();
      },
      recenter() {
        if (location.coordinate) map?.jumpTo({ center: [location.coordinate.longitude, location.coordinate.latitude] });
      },
      inspectEditor() {
        return { bearing: map?.getBearing(), pitch: map?.getPitch(),
          scrollZoom: map?.scrollZoom.isEnabled(), dragPan: map?.dragPan.isEnabled(),
          layers: map?.getStyle()?.layers };
      },
    } : {}),
    // Workshop-only bounded camera actions use the same provider; they never move the marker.
    panBy(x, y) { map?.panBy([x, y], { duration: 0 }); },
    zoomBy(delta) { if (map) map.jumpTo({ zoom: Math.min(18, Math.max(3, map.getZoom() + delta)) }); },
    destroy() { native.destroy(); visual = undefined; map = undefined; appliedStyle = undefined; },
  };
}
