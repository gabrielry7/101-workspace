// Offline API double. This does not emulate Google's cartography or prove cloud styling.
import { mountGoogleLocation, owner } from '/location-runtime.js';
export async function runGoogleChecks(source) {
  const results = [], maps = [], markers = [];
  const check = (condition, name) => { if (!condition) throw Error(name); results.push(name); };
  const wait = () => new Promise(resolve => setTimeout(resolve, 100));
  const section = document.createElement('section'); section.className = 'location-bone';
  const navigation = document.createElement('nav'); navigation.id = 'google-test-directions';
  const link = document.createElement('a'); link.href = '#'; link.dataset.mapApp = 'google'; link.textContent = 'Acción sintética';
  navigation.append(link); section.append(navigation); document.body.append(section);
  const makeRoot = () => { const root = document.createElement('div'); section.append(root); return root; };
  const location = structuredClone(source.location);
  location.coordinate.purpose = 'owner_pin'; location.coordinate.source.kind = 'owner_confirmed';
  location.coordinate.source.reference = 'synthetic:offline-google-contract-test-not-real';
  const google = { enabled: true, apiKey: 'OFFLINE_TEST_VALUE_NOT_A_KEY', mapId: 'offline-map',
    styleReview: { mapId: 'offline-map', pois: 'none', reference: 'synthetic:offline-review', reviewedAt: '2026-11-05T00:00:00Z' } };
  const base = { location, marker: source.marker, presentation: { zoom: 16, pois: { mode: 'none', ids: [], limit: 0 } },
    navigationId: navigation.id, google };
  const api = {
    Map: class {
      constructor(canvas, options) { this.canvas = canvas; this.options = options;canvas.style.position='relative';maps.push(this); }
      setZoom(zoom) { this.options.zoom = zoom; }
    },
    LatLng: class { constructor(lat, lng) { this.lat = lat; this.lng = lng; } },
    OverlayView: class {
      setMap(map) { this.map = map; }
      getProjection() { return this.map ? { fromLatLngToContainerPixel: () => ({ x: this.map.canvas.clientWidth / 2, y: this.map.canvas.clientHeight / 2 }) } : null; }
    },
    marker: { AdvancedMarkerElement: class extends EventTarget {
      constructor(options) { super();Object.assign(this,options);this.wrapper=document.createElement('div');
        this.wrapper.style.cssText='position:absolute;left:50%;top:50%;transform:translate(-50%,-100%)';
        options.map.canvas.append(this.wrapper);markers.push(this); }
      append(child) { this.wrapper.append(child); }
    } },
    event: { addListenerOnce(_map,_type,callback) { queueMicrotask(callback); }, clearInstanceListeners() {}, trigger() {} },
  };
  let loads = 0;
  const services = { load: async () => { loads++; return api; }, verification: 'offline-google-api-double' };
  const missing = mountGoogleLocation(makeRoot(), { ...base, google: undefined }, owner, services);
  check(loads === 0 && missing.inspect().reason === 'GOOGLE_CONFIGURATION_REQUIRED', 'no configuration makes zero Google calls');
  missing.destroy();
  let finish;
  const late = mountGoogleLocation(makeRoot(), base, owner, { load: () => new Promise(resolve => { finish=resolve; }) });
  late.destroy(); finish(api); await wait();
  check(maps.length === 0, 'destroy before loader completion never mounts');
  const control = mountGoogleLocation(makeRoot(), base, owner, services);
  await wait(); await wait();
  const info = control.inspect();
  check(info.state === 'ready' && info.marker_kind === 'logo', 'configured Google adapter renders logo');
  check(markers[0].wrapper.querySelector('[data-location-part="marker-pin"]')
    && markers[0].wrapper.querySelector('[data-location-part="brand-logo-slot"]'), 'logo remains inside a pin on the actual provider marker');
  check(maps[0].options.clickableIcons === false && maps[0].options.mapTypeControl === false
    && maps[0].options.mapId === 'offline-map' && !('styles' in maps[0].options), 'cloud style mode never mixes inline styles');
  check(markers[0].gmpDraggable === false && markers[0].gmpClickable === true, 'marker remains accessible and non-draggable');
  check(info.marker_anchor_offset_px <= 1, 'logo uses measured geographic anchor');
  markers[0].dispatchEvent(new Event('gmp-click'));
  check(document.activeElement === link, 'marker activation focuses directions');
  control.setPresentation({ zoom: 17 });
  check(JSON.stringify(control.inspect().marker_coordinate) === JSON.stringify(info.marker_coordinate), 'zoom preserves destination');
  let rejected = false; try { control.setPresentation({ pois: { mode: 'all' } }); } catch { rejected=true; }
  check(rejected, 'Google adapter rejects restoring POIs');
  control.destroy(); check(markers[0].map === null, 'destroy detaches provider marker');
  const broken = mountGoogleLocation(makeRoot(), { ...base, marker: { ...source.marker, url: '/missing-google-logo.svg' } }, owner, services);
  for(let i=0;i<50&&broken.inspect().logo_reason!=='LOGO_LOAD_FAILED';i++) await wait();
  check(broken.inspect().marker_kind === 'pin' && broken.inspect().logo_reason === 'LOGO_LOAD_FAILED', 'Google image error keeps neutral marker');
  check(JSON.stringify(broken.inspect().marker_coordinate) === JSON.stringify(info.marker_coordinate), 'failed logo preserves coordinate');
  broken.destroy();
  const failed = mountGoogleLocation(makeRoot(), base, owner, { load: async () => { throw Error('offline failure'); } });
  await wait(); check(failed.inspect().state === 'fallback', 'Google loader failure retains fallback');
  failed.destroy(); section.remove();
  return { results, google_live_verified: false, api_double: true };
}
