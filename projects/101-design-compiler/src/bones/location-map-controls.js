import { locationBone, locationSkin, locationVariant } from './location-map.ts';

export const defaultLocationControls = Object.freeze({
  bone: `${locationBone.id}@${locationBone.version}`, skin: 'neutral', variant: 'direct',
  markerLabel: false, zoom: 16, mapHeight: 438, pinPaper: '#f4f4f4', pinInk: '#222222',
});
export function parseLocationControls(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.keys(value).length !== Object.keys(defaultLocationControls).length
    || Object.keys(value).some(key => !Object.hasOwn(defaultLocationControls, key))
    || value.bone !== defaultLocationControls.bone || typeof value.markerLabel !== 'boolean'
    || !Number.isInteger(value.zoom) || value.zoom < 3 || value.zoom > 18
    || !Number.isInteger(value.mapHeight) || value.mapHeight < 280 || value.mapHeight > 560
    || !/^#[a-f0-9]{6}$/i.test(value.pinPaper) || !/^#[a-f0-9]{6}$/i.test(value.pinInk)) {
    throw Error('INVALID_LOCATION_CONTROLS');
  }
  locationSkin(value.skin); locationVariant(value.variant);
  return { ...value };
}

/** Operator-only controls reuse the same component parts and provider instance. */
export function mountLocationControls(panel, section, options = {}) {
  const host = section.querySelector('[data-location-bone-config]');
  const form = panel.querySelector('form');
  const status = panel.querySelector('[data-controls-status]');
  const storageKey = options.storageKey ?? '101-location-controls-v1';
  const initial = parseLocationControls({ ...defaultLocationControls, ...options.initial });
  let state = { ...initial }, lastController, lastZoom;
  const field = name => form.elements.namedItem(name);
  function sync() {
    for (const name of ['skin', 'variant', 'zoom', 'mapHeight', 'pinPaper', 'pinInk']) field(name).value = state[name];
    field('markerLabel').checked = state.markerLabel;
    for (const name of ['zoom', 'mapHeight']) panel.querySelector(`[data-value="${name}"]`).textContent = state[name];
  }
  function apply() {
    section.dataset.skin = state.skin;
    for (const variant of locationBone.variants) section.classList.toggle(`location-bone--${variant}`, state.variant === variant);
    section.dataset.variant = state.variant;
    const information = section.querySelector('.location-bone__information');
    const destination = section.querySelector(state.variant === 'direct' ? '.location-bone__body' : '.location-bone__header');
    if (information.parentElement !== destination) {
      if (state.variant === 'direct') destination.prepend(information); else destination.append(information);
    }
    section.style.setProperty('--map-height', state.mapHeight + 'px');
    host.querySelector('.location-map__canvas')?.style.setProperty('height', state.mapHeight + 'px');
    const config = JSON.parse(host.dataset.locationBoneConfig);
    config.markerLabel = state.markerLabel;
    config.presentation = { ...config.presentation, zoom: state.zoom,
      colors: { ...config.presentation.colors, paper: state.pinPaper, ink: state.pinInk } };
    host.dataset.locationBoneConfig = JSON.stringify(config);
    const controller = host.locationBone;
    if (controller) {
      controller.setPresentation({ colors: { paper: state.pinPaper, ink: state.pinInk },
        ...(controller !== lastController || lastZoom !== state.zoom ? { zoom: state.zoom } : {}) });
      controller.setMarkerLabel(state.markerLabel);
      lastController = controller; lastZoom = state.zoom;
    }
    sync();
    return { ...state };
  }
  function read() {
    return parseLocationControls({ ...defaultLocationControls, skin: field('skin').value,
      variant: field('variant').value, markerLabel: field('markerLabel').checked,
      zoom: Number(field('zoom').value), mapHeight: Number(field('mapHeight').value),
      pinPaper: field('pinPaper').value, pinInk: field('pinInk').value });
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', () => {
    try { state = read(); apply(); status.textContent = 'Cambios aplicados en esta vista, sin recargar el mapa.'; }
    catch { status.textContent = 'Ese ajuste no es compatible. Se conserva la configuración anterior.'; sync(); }
  });
  panel.querySelector('[data-controls-reset]').addEventListener('click', () => {
    state = { ...initial }; apply(); status.textContent = 'Vista inicial restablecida.';
  });
  panel.querySelector('[data-controls-save]').addEventListener('click', () => {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); status.textContent = 'Ajustes guardados en este navegador.'; }
    catch { status.textContent = 'Este navegador no permite guardar los ajustes.'; }
  });
  panel.querySelector('[data-controls-restore]').addEventListener('click', () => {
    try { state = parseLocationControls(JSON.parse(localStorage.getItem(storageKey))); apply();
      status.textContent = 'Ajustes recuperados sin recargar el mapa.'; }
    catch { status.textContent = 'No hay ajustes guardados compatibles con esta versión.'; }
  });
  sync(); apply();
  return { apply, inspect: () => ({ ...state }) };
}
