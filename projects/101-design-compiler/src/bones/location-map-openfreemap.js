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

export function openFreeMapStyle(colors, fontURL) {
  const roadWidth = ['interpolate', ['linear'], ['zoom'], 12, 1.2, 16, 4, 18, 9];
  const roadFilter = ['in', ['get', 'class'], ['literal', [
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'minor', 'service', 'track', 'path',
  ]]];
  const lineLayout = { 'line-cap': 'round', 'line-join': 'round' };
  return {
    version: 8,
    sources: { context: { type: 'vector', url: `${origin}/planet`, attribution } },
    'font-faces': { 'Location Map': [{ url: fontURL }] },
    layers: [
      { id: 'paper', type: 'background', paint: { 'background-color': colors.land } },
      { id: 'vegetation', type: 'fill', source: 'context', 'source-layer': 'landcover',
        filter: ['in', ['get', 'class'], ['literal', ['wood', 'grass']]],
        paint: { 'fill-color': colors.building, 'fill-opacity': 0.42 } },
      { id: 'water', type: 'fill', source: 'context', 'source-layer': 'water',
        paint: { 'fill-color': colors.water } },
      { id: 'buildings', type: 'fill', source: 'context', 'source-layer': 'building', minzoom: 13,
        paint: { 'fill-color': colors.building, 'fill-outline-color': colors.roadOutline } },
      { id: 'road-outline', type: 'line', source: 'context', 'source-layer': 'transportation',
        filter: roadFilter, layout: lineLayout,
        paint: { 'line-color': colors.roadOutline, 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2.7, 16, 5.5, 18, 10.5] } },
      { id: 'roads', type: 'line', source: 'context', 'source-layer': 'transportation',
        filter: roadFilter, layout: lineLayout,
        paint: { 'line-color': colors.road, 'line-width': roadWidth } },
      { id: 'road-names', type: 'symbol', source: 'context', 'source-layer': 'transportation_name', minzoom: 13,
        filter: ['all', roadFilter, ['has', 'name']],
        layout: { 'symbol-placement': 'line', 'text-field': ['get', 'name'],
          'text-font': ['Location Map'], 'text-size': 13, 'symbol-spacing': 260 },
        paint: { 'text-color': '#3d302c', 'text-halo-color': colors.road, 'text-halo-width': 1.2 } },
    ],
  };
}
