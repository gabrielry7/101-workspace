import { mountLocationControls } from '../../src/bones/location-map-controls.js';

const host = document.querySelector('[data-location-bone-config]');
const trialStatus = document.querySelector('[data-trial-status]');
const meter = document.querySelector('[data-trial-meter]');
const startButton = document.querySelector('[data-google-start]');
const panel = document.querySelector('[data-location-controls]');
const controls = mountLocationControls(panel, document.getElementById(panel.dataset.controlsTarget));
let started = false;

async function refreshBudget() {
  try {
    const response = await fetch('/trial-status', { cache: 'no-store' });
    if (!response.ok) throw Error('TRIAL_STATUS_UNAVAILABLE');
    const budget = await response.json();
    meter.textContent = `Cargas reservadas: ${budget.reserved}/${budget.limit}. Disponibles: ${budget.remaining}.`;
    startButton.disabled = budget.remaining === 0;
    trialStatus.textContent = budget.remaining === 0
      ? 'Se agotaron las cargas de Google de esta prueba. Puedes seguir probando la sección y sus pieles.'
      : 'Prueba los ajustes abajo. Activa Google una vez para verlos sobre el mapa real.';
    host.querySelector('[data-location-part="status-fallback"]').textContent = budget.remaining === 0
      ? 'Las cargas de Google de esta prueba están agotadas. La dirección y las indicaciones siguen disponibles.'
      : 'Activa Google con el botón de arriba para ver la ubicación. Puedes probar la piel de la sección antes de activarlo.';
  } catch { trialStatus.textContent = 'El cupo de Google no está disponible. Los controles de la sección siguen funcionando.'; }
}

async function start() {
  if (started) return;
  started = true; startButton.disabled = true;
  trialStatus.textContent = 'Conectando Google Maps…';
  try {
    const response = await fetch('/trial-config', { method: 'POST', cache: 'no-store' });
    if (!response.ok) throw Error(response.status === 429 ? 'TRIAL_BUDGET_EXHAUSTED' : 'TRIAL_CONFIGURATION_UNAVAILABLE');
    const { google, budget } = await response.json();
    meter.textContent = `Cargas reservadas: ${budget.reserved}/${budget.limit}. Límite autorizado para la prueba: US$1.`;
    const config = JSON.parse(host.dataset.locationBoneConfig);
    config.google = google;
    host.dataset.locationBoneConfig = JSON.stringify(config);
    // The existing entry hydrates this same Astro component exactly once.
    await import('/location-runtime.js');
    controls.apply();
    const timer = setInterval(() => {
      const state = host.locationBone?.inspect();
      if (state?.state === 'ready') {
        controls.apply();
        startButton.textContent = 'Google activado';
        trialStatus.textContent = 'Google Maps activo. Cambia los ajustes sin recargar la página ni crear otro mapa.';
        clearInterval(timer);
      } else if (state && ['fallback', 'degraded'].includes(state.state)) {
        trialStatus.textContent = `Google no pudo completar la vista (${state.reason}). La dirección y las indicaciones siguen disponibles.`;
        clearInterval(timer);
      }
    }, 500);
  } catch (error) {
    trialStatus.textContent = error.message === 'TRIAL_BUDGET_EXHAUSTED'
      ? 'Se alcanzó el límite de 10 cargas de esta prueba. No se inicia otro mapa.'
      : 'La configuración local de Google no está disponible. No se inicia el proveedor.';
  }
}
startButton.addEventListener('click', () => void start());
void refreshBudget();
