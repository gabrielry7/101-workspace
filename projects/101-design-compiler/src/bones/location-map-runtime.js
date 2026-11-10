import { attachMarkerVisual } from './location-map-marker.js';
import { mountGoogleLocation } from './location-map-google.js';

export const LOCATION_BONE_VERSION = 'location.single-business@0.3.0';
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
  const native = owner.mountLocationMap(root, {
    location, provider, presentation, basemap: config.basemap, workerURL: config.workerURL,
    detailsMode: 'external', navigationId: config.navigationId,
    decorateMap({ map: actualMap }) {
      map = actualMap;
      const pin = root.querySelector('.location-map__marker');
      if (!pin) throw Error('OWNER_BUSINESS_MARKER_MISSING');
      pin.dataset.locationPart = 'business-marker';
      const keyboard = new AbortController();
      pin.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault(); event.stopPropagation(); pin.click();
        }
      }, { signal: keyboard.signal });
      visual = attachMarkerVisual(pin, config.marker, location.name, state => {
        root.dataset.markerKind = state.kind; root.dataset.logoReason = state.reason;
      }, { showLabel: config.markerLabel !== false });
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
        poi_policy: { mode: 'none', limit: 0, ids: [] } };
    },
    setMarkerLabel(visible) {
      if (typeof visible !== 'boolean') throw Error('BOOLEAN_MARKER_LABEL_REQUIRED');
      config.markerLabel = visible; visual?.setLabelVisible(visible);
    },
    setPresentation(next) { native.setPresentation(fixedPresentation(next)); },
    // Workshop-only bounded camera actions use the same provider; they never move the marker.
    panBy(x, y) { map?.panBy([x, y], { duration: 0 }); },
    zoomBy(delta) { if (map) map.jumpTo({ zoom: Math.min(18, Math.max(3, map.getZoom() + delta)) }); },
    destroy() { native.destroy(); visual = undefined; map = undefined; },
  };
}
