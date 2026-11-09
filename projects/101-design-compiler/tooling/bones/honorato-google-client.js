const host = document.querySelector('[data-location-bone-config]');
const trialStatus = document.querySelector('[data-trial-status]');
const meter = document.querySelector('[data-trial-meter]');

async function start() {
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
    const timer = setInterval(() => {
      const state = host.locationBone?.inspect();
      if (state?.state === 'ready') {
        trialStatus.textContent = 'Google Maps cargado. Revisa el pin y la ausencia de lugares ajenos al mover o ampliar.';
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
void start();
