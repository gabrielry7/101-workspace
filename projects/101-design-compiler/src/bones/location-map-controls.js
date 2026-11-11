import { locationBone, locationSkin, locationVariant } from './location-map.ts';
import { locationEditorFields, mapEditorOptions, parseLocationEditor } from './location-map-editor.ts';

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
  const initialEditor = options.editor ? parseLocationEditor(options.editor) : null;
  let editor = initialEditor;
  let state = { ...initial }, lastController, lastZoom, lastMarkerLabel;
  const field = name => form.elements.namedItem(name);
  const editorFields = initialEditor ? Object.entries(locationEditorFields) : [];
  const sectionColors = ['sectionPaper', 'sectionInk', 'sectionLine', 'sectionAccent'];
  if (editor) section.dataset.locationEditor = '';

  function sync() {
    for (const name of ['skin', 'variant', 'zoom', 'mapHeight', 'pinPaper', 'pinInk']) field(name).value = state[name];
    field('markerLabel').checked = state.markerLabel;
    for (const name of ['zoom', 'mapHeight']) panel.querySelector(`[data-value="${name}"]`).textContent = state[name];
    for (const [name, { kind }] of editorFields) {
      if (kind === 'checkbox') field(name).checked = editor[name];
      else field(name).value = editor[name];
      if (kind === 'range') panel.querySelector(`[data-value="${name}"]`).textContent = editor[name];
    }
  }
  function applyEditor(controller) {
    const css = {
      'pin-dot': editor.pinDot,
      'pin-dot-radius': editor.pinDotSize / 2 + 'px',
      'pin-scale': editor.pinScale / 100,
      'pin-stroke': editor.pinStroke,
      'logo-scale': editor.logoScale + '%',
      'label-paper': editor.labelPaper,
      'label-ink': editor.labelInk,
      'label-line': editor.labelLine,
      'label-size': editor.labelSize + 'px',
      'title-scale': editor.titleScale / 100,
    };
    for (const [name, value] of Object.entries(css)) section.style.setProperty('--editor-' + name, value);
    for (const name of sectionColors) {
      const variable = '--editor-section-' + name.slice('section'.length).toLowerCase();
      if (editor.sectionCustom) section.style.setProperty(variable, editor[name]);
      else section.style.removeProperty(variable);
    }
    section.dataset.editorFont = editor.sectionFont;
    section.toggleAttribute('data-hide-map-zoom', !editor.showZoomButtons);
    section.toggleAttribute('data-hide-pin-logo', !editor.showLogo);
    controller?.setOpenFreeMapOptions?.(mapEditorOptions(editor));
  }
  function apply({ resetZoom = false } = {}) {
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
        ...(resetZoom || controller !== lastController || lastZoom !== state.zoom ? { zoom: state.zoom } : {}) });
      if (controller !== lastController || lastMarkerLabel !== state.markerLabel) controller.setMarkerLabel(state.markerLabel);
      lastController = controller; lastZoom = state.zoom; lastMarkerLabel = state.markerLabel;
    }
    if (editor) applyEditor(controller);
    sync();
    return { ...state };
  }
  function read() {
    return parseLocationControls({ ...defaultLocationControls, skin: field('skin').value,
      variant: field('variant').value, markerLabel: field('markerLabel').checked,
      zoom: Number(field('zoom').value), mapHeight: Number(field('mapHeight').value),
      pinPaper: field('pinPaper').value, pinInk: field('pinInk').value });
  }
  function readEditor(changedField) {
    const next = Object.fromEntries(editorFields.map(([name, { kind }]) => {
      const input = field(name);
      const value = kind === 'checkbox' ? input.checked : kind === 'range' ? input.valueAsNumber : input.value;
      return [name, value];
    }));
    if (sectionColors.includes(changedField)) next.sectionCustom = true;
    return parseLocationEditor(next);
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', event => {
    try {
      const next = read();
      if (editor) editor = readEditor(event.target.name);
      state = next;
      apply();
      status.textContent = 'Ajustes aplicados.';
    }
    catch { status.textContent = 'Ese ajuste no es compatible. Se conserva la configuración anterior.'; sync(); }
  });
  panel.querySelector('[data-controls-reset]').addEventListener('click', () => {
    state = { ...initial }; editor = initialEditor;
    apply({ resetZoom: true });
    if (editor) host.locationBone?.recenter?.();
    status.textContent = 'Vista inicial restablecida.';
  });
  panel.querySelector('[data-controls-recenter]')?.addEventListener('click', () => host.locationBone?.recenter?.());
  panel.querySelector('[data-controls-save]').addEventListener('click', () => {
    try { localStorage.setItem(storageKey, JSON.stringify(editor ? { ...state, editor } : state)); status.textContent = 'Ajustes guardados en este navegador.'; }
    catch { status.textContent = 'Este navegador no permite guardar los ajustes.'; }
  });
  panel.querySelector('[data-controls-restore]').addEventListener('click', () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      const { editor: savedEditor, ...savedControls } = saved;
      if (savedControls.bone === 'location.single-business@0.4.0') savedControls.bone = defaultLocationControls.bone;
      const next = parseLocationControls(savedControls);
      const nextEditor = savedEditor === undefined ? initialEditor : parseLocationEditor(savedEditor);
      if (nextEditor && !initialEditor) throw Error('LOCATION_EDITOR_UNAVAILABLE');
      state = next;
      editor = nextEditor;
      apply({ resetZoom: true });
      status.textContent = 'Ajustes recuperados.';
    }
    catch { status.textContent = 'No hay ajustes guardados compatibles con esta versión.'; }
  });
  sync(); apply();
  return { apply, inspect: () => ({ ...state }) };
}
