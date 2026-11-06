import { mountLocationMap } from '@101/location-map/client';
import { locationInput, rendererEligibility, presentation, navigationLinks } from '@101/location-map/contract';
import { mountSingleBusinessLocation } from './location-map-runtime.js';
export { mountGoogleLocation } from './location-map-google.js';
export { mountSingleBusinessLocation } from './location-map-runtime.js';
export const owner = { mountLocationMap, locationInput, rendererEligibility, presentation, navigationLinks };

export function hydrateLocationBones(scope = document) {
  for (const host of scope.querySelectorAll('[data-location-bone-config]')) {
    if (host.locationBone) continue;
    try {
      const config = JSON.parse(host.dataset.locationBoneConfig);
      const bound = locationInput(config.location);
      const navigation = document.getElementById(config.navigationId);
      const links = navigationLinks(bound);
      // Use the original direction builder; server fallback remains if hydration fails.
      for (const link of navigation.querySelectorAll('[data-map-app]')) {
        const destination = links.find(item => item.provider === link.dataset.mapApp);
        if (destination && link.href !== destination.url) throw Error('DIRECTIONS_BINDING_MISMATCH');
      }
      host.locationBone = mountSingleBusinessLocation(host, config, owner);
    } catch {
      host.dataset.mapState = 'fallback'; host.dataset.mapReason = 'INVALID_LOCATION_BONE_INPUT';
    }
  }
}
hydrateLocationBones();
document.addEventListener('astro:before-swap', () => {
  for (const host of document.querySelectorAll('[data-location-bone-config]')) host.locationBone?.destroy();
});
document.addEventListener('astro:page-load', () => hydrateLocationBones());
