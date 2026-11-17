const origin = 'https://tiles.openfreemap.org';
const attribution = '<a href="https://openfreemap.org/">OpenFreeMap</a> · <a href="https://www.openmaptiles.org/">OpenMapTiles</a> · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export function openFreeMapRequest(url, baseURL) {
  const resource = new URL(url, baseURL);
  if (resource.username || resource.password || resource.search || resource.hash) {
    throw Error('OPENFREEMAP_ASSET_NOT_ALLOWED');
  }
  if (resource.origin === new URL(baseURL).origin && ['http:', 'https:'].includes(resource.protocol)) {
    return { url: resource.href };
  }
  const tile = /^\/planet\/\d{8}_\d{6}_pt\/\d+\/\d+\/\d+\.pbf$/;
  if (resource.origin === origin && (resource.pathname === '/planet' || tile.test(resource.pathname))) {
    return { url: resource.href };
  }
  throw Error('OPENFREEMAP_ASSET_NOT_ALLOWED');
}

function visibility(shown) {
  return shown ? 'visible' : 'none';
}

function roadWidth(scale, casing = 0) {
  return ['interpolate', ['linear'], ['zoom'],
    12, 1.2 * scale + casing, 16, 4 * scale + casing, 18, 9 * scale + casing];
}

export function openFreeMapStyle(options, { fontURL, alternateFontURL }) {
  const roadClasses = [
    ...(options.showMainRoads ? ['motorway', 'trunk', 'primary', 'secondary', 'tertiary'] : []),
    ...(options.showLocalRoads ? ['minor', 'service'] : []),
    ...(options.showPaths ? ['track', 'path'] : []),
  ];
  const roadFilter = ['in', ['get', 'class'], ['literal', roadClasses]];
  const lineLayout = { 'line-cap': options.roadCap, 'line-join': options.roadJoin };
  return {
    version: 8,
    light: { anchor: 'viewport', color: options.lightColor, intensity: options.lightIntensity / 100,
      position: [1.5, options.lightDirection, 90 - options.lightElevation] },
    sources: { context: { type: 'vector', url: `${origin}/planet`, attribution } },
    'font-faces': {
      'Location Map': [{ url: fontURL }],
      ...(alternateFontURL ? { 'Location Serif': [{ url: alternateFontURL }] } : {}),
    },
    layers: [
      { id: 'paper', type: 'background', paint: { 'background-color': options.land } },
      { id: 'vegetation', type: 'fill', source: 'context', 'source-layer': 'landcover',
        filter: ['in', ['get', 'class'], ['literal', ['wood', 'grass']]],
        layout: { visibility: visibility(options.showVegetation) },
        paint: { 'fill-color': options.vegetation, 'fill-opacity': options.vegetationOpacity / 100 } },
      { id: 'water', type: 'fill', source: 'context', 'source-layer': 'water',
        layout: { visibility: visibility(options.showWater) },
        paint: { 'fill-color': options.water, 'fill-opacity': options.waterOpacity / 100 } },
      { id: 'buildings', type: 'fill', source: 'context', 'source-layer': 'building', minzoom: options.buildingMinZoom,
        layout: { visibility: visibility(options.showBuildings) },
        paint: { 'fill-color': options.building, 'fill-outline-color': options.buildingOutline,
          'fill-opacity': options.buildingOpacity / 100 } },
      { id: 'road-outline', type: 'line', source: 'context', 'source-layer': 'transportation',
        filter: roadFilter, layout: { ...lineLayout, visibility: visibility(options.roadCasing > 0) },
        paint: { 'line-color': options.roadOutline, 'line-width': roadWidth(options.roadScale / 100, options.roadCasing),
          'line-opacity': options.roadOpacity / 100 } },
      { id: 'roads', type: 'line', source: 'context', 'source-layer': 'transportation',
        filter: roadFilter, layout: lineLayout,
        paint: { 'line-color': options.road, 'line-width': roadWidth(options.roadScale / 100),
          'line-opacity': options.roadOpacity / 100 } },
      { id: 'buildings-3d', type: 'fill-extrusion', source: 'context', 'source-layer': 'building',
        minzoom: options.buildingMinZoom, filter: ['!=', ['get', 'hide_3d'], true],
        layout: { visibility: visibility(options.showBuildings && options.buildings3d) },
        paint: { 'fill-extrusion-color': options.building,
          'fill-extrusion-height': ['*', ['max', 0, ['to-number', ['get', 'render_height'], 0]], options.buildingHeightScale / 100],
          'fill-extrusion-base': ['*', ['max', 0, ['to-number', ['get', 'render_min_height'], 0]], options.buildingHeightScale / 100],
          'fill-extrusion-opacity': options.buildingOpacity / 100 } },
      { id: 'road-names', type: 'symbol', source: 'context', 'source-layer': 'transportation_name', minzoom: options.roadTextMinZoom,
        filter: ['all', roadFilter, ['has', 'name']],
        layout: { 'symbol-placement': options.roadTextPlacement, 'text-field': ['get', 'name'],
          'text-font': [options.roadFont === 'serif' && alternateFontURL ? 'Location Serif' : 'Location Map'],
          'text-size': options.roadTextSize, 'symbol-spacing': options.roadTextSpacing, visibility: visibility(options.showRoadNames) },
        paint: { 'text-color': options.roadText, 'text-halo-color': options.roadHalo,
          'text-halo-width': options.roadHaloWidth, 'text-opacity': options.roadTextOpacity / 100 } },
    ],
  };
}

export function updateOpenFreeMapLayers(map, previous, next) {
  const changed = (before, after) => JSON.stringify(before) !== JSON.stringify(after);
  if (changed(previous.light, next.light)) map.setLight(next.light);
  for (const [index, layer] of next.layers.entries()) {
    const before = previous.layers[index];
    for (const [key, value] of Object.entries(layer.paint ?? {})) {
      if (changed(before.paint?.[key], value)) map.setPaintProperty(layer.id, key, value);
    }
    for (const [key, value] of Object.entries(layer.layout ?? {})) {
      if (changed(before.layout?.[key], value)) map.setLayoutProperty(layer.id, key, value);
    }
    if (changed(before.filter, layer.filter)) map.setFilter(layer.id, layer.filter);
    if (before.minzoom !== layer.minzoom) map.setLayerZoomRange(layer.id, layer.minzoom, 24);
  }
}
