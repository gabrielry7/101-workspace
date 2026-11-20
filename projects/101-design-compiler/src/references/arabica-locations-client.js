import { mountLocationDirectory } from '../bones/location-directory-client.js';
import { mountArabicaDirectoryMap } from './arabica-directory-map.js';

export function mountArabicaReference(root, catalogue, services = {}) {
  const directory = root.querySelector('.location-directory');
  const map = mountArabicaDirectoryMap(directory, catalogue, services);
  const control = mountLocationDirectory(directory, { onPush() { window.scrollTo(0, 0); }, onViewChange(view) {
    map.select(view.id);
    root.dataset.referenceView = view.id;
    root.dataset.referenceLevel = view.level === 'overview' ? 'world' : view.level === 'area' ? 'country' : 'city';
    document.title = `% Arabica · ${view.level === 'overview' ? 'Locations' : view.id.split('/').at(-1)} · private reference`;
  } });
  const menu = root.querySelector('.reference-menu-button'), nav = root.querySelector('.reference-navigation');
  menu.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); nav.toggleAttribute('data-open', open); });
  root.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.hasAttribute('data-open')) { nav.removeAttribute('data-open'); menu.setAttribute('aria-expanded', 'false'); menu.focus(); } });
  root.querySelector('a[data-reference-view]').addEventListener('click', event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); control.navigate('world', true); });
  return { navigate: control.navigate, activate: map.activate, inspect: map.inspect };
}
const root = document.querySelector('.arabica-reference');
if (root) window.arabicaReference = mountArabicaReference(root, JSON.parse(document.getElementById('arabica-reference-input').textContent));
