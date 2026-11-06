import { mapSkins } from './location-map.ts';
const section = document.getElementById('comparison-brand');
const host = section?.querySelector('[data-location-bone-config]');
const status = document.querySelector('[data-workshop-status]');
let saved = null;
function message(value) { status.textContent = value; }
for (const button of document.querySelectorAll('[data-workshop-skin]')) {
  button.addEventListener('click', () => {
    const skin = button.dataset.workshopSkin;
    try {
      host.locationBone?.setPresentation({ colors: mapSkins[skin] });
      section.dataset.skin = skin;
      message('Piel aplicada. La coordenada y la política sin establecimientos no cambian.');
    } catch { message('Esta piel necesita una configuración compatible del proveedor.'); }
  });
}
document.querySelector('[data-workshop-pan]')?.addEventListener('click', () => host.locationBone?.panBy(90, 35));
document.querySelector('[data-workshop-zoom]')?.addEventListener('click', () => host.locationBone?.zoomBy(1));
document.querySelector('[data-workshop-save]')?.addEventListener('click', () => {
  saved = { version: 'location.single-business@0.1.0', skin: section.dataset.skin,
    zoom: host.locationBone?.inspect().camera_zoom ?? 16 };
  try { localStorage.setItem('location-bone-workshop-v1', JSON.stringify(saved));
    message('Configuración guardada en este navegador.');
  } catch { message('Configuración guardada sólo durante esta visita.'); }
});
document.querySelector('[data-workshop-restore]')?.addEventListener('click', () => {
  if (!saved) {
    try { saved = JSON.parse(localStorage.getItem('location-bone-workshop-v1')); } catch { /* no saved configuration */ }
  }
  if (!saved || saved.version !== 'location.single-business@0.1.0' || !Object.hasOwn(mapSkins,saved.skin)
    || !Number.isFinite(saved.zoom) || saved.zoom < 3 || saved.zoom > 18) { message('Primero guarda una configuración compatible.'); return; }
  section.dataset.skin = saved.skin;
  host.locationBone?.setPresentation({ colors: mapSkins[saved.skin], zoom: saved.zoom });
  message('Configuración restaurada; se conserva el mismo negocio y destino.');
});
document.querySelector('[data-workshop-anatomy]')?.addEventListener('change', event => {
  document.body.dataset.anatomy = String(event.target.checked);
});
