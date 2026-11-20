const mounted = new WeakMap();

export function mountLocationDirectory(root, services = {}) {
  if (mounted.has(root)) return mounted.get(root);
  const content = JSON.parse(root.querySelector('[data-directory-input]').textContent);
  const views = new Map(content.views.map(view => [view.id, view]));
  const templates = new Map([...root.querySelectorAll('[data-directory-template]')].map(el => [el.dataset.directoryTemplate, el]));
  const panel = root.querySelector('[data-directory-panel]'), cards = root.querySelector('[data-directory-cards]');
  const canvas = root.querySelector('[data-directory-map]');
  const query = root.dataset.directoryQuery;
  const cleanups = [];
  let view;
  function listen(target, type, handler, options) {
    target.addEventListener(type, handler, options); cleanups.push(() => target.removeEventListener(type, handler, options));
  }
  function route(id) {
    const url = new URL(location.href);
    if (id === content.rootId) url.searchParams.delete(query); else url.searchParams.set(query, id);
    url.hash = ''; return url.pathname + url.search;
  }
  function installCarousel() {
    const track = cards.querySelector('.ld-card-track'), dots = cards.querySelector('.ld-card-dots');
    if (!track || !dots) return;
    const items = [...track.children];
    items.forEach((item, index) => {
      const button = document.createElement('button'); button.type = 'button';
      button.setAttribute('aria-label', `${content.labels.cardPage} ${index + 1}`);
      if (!index) button.setAttribute('aria-current', 'true');
      button.addEventListener('click', () => track.scrollTo({ left: item.offsetLeft - track.offsetLeft - 20,
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
      dots.append(button);
    });
    track.addEventListener('scroll', () => {
      const active = items.reduce((best, item, index) => Math.abs(item.offsetLeft - items[0].offsetLeft - track.scrollLeft) <
        Math.abs(items[best].offsetLeft - items[0].offsetLeft - track.scrollLeft) ? index : best, 0);
      [...dots.children].forEach((button, i) => i === active ? button.setAttribute('aria-current', 'true') : button.removeAttribute('aria-current'));
    }, { passive: true });
  }
  function navigate(id, push = false) {
    if (!views.has(id)) id = content.rootId;
    view = views.get(id);
    const fragment = templates.get(id).content.cloneNode(true);
    panel.replaceChildren(fragment.querySelector('.ld-panel'));
    cards.replaceChildren(...fragment.querySelectorAll('.ld-cards'));
    root.dataset.directoryView = id; root.dataset.directoryLevel = view.level;
    root.querySelectorAll('a[data-directory-target]').forEach(link => { link.href = route(link.dataset.directoryTarget); });
    const label = root.querySelector('[data-map-view-label]'); if (label) label.textContent = view.title;
    canvas.setAttribute('aria-label', `${content.mapLabel}: ${view.title}`);
    if (push) {
      history.pushState({ directory: root.id, view: id }, '', route(id));
      if (services.onPush) services.onPush(view); else root.querySelector('.ld-title').scrollIntoView({ block: 'start' });
    }
    installCarousel();
    root.querySelector('[data-directory-status]').textContent = `${view.panelTitle}: ${[...view.entries, ...view.groups.flatMap(g => g.items)].map(item => item.label).join(', ')}`;
    services.onViewChange?.(view);
    root.dispatchEvent(new CustomEvent('directory:viewchange', { detail: { viewId: id, level: view.level } }));
  }
  listen(root, 'click', event => {
    const link = event.target.closest('a[data-directory-target]');
    if (!link || !root.contains(link)) return;
    link.href = route(link.dataset.directoryTarget);
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault(); navigate(link.dataset.directoryTarget, true);
    if (event.detail === 0) panel.querySelector('a')?.focus({ preventScroll: true });
  });
  for (const type of ['pointerdown', 'focusin']) listen(root, type, event => {
    const link = event.target.closest('a[data-directory-target]');
    if (link && root.contains(link)) link.href = route(link.dataset.directoryTarget);
  });
  listen(window, 'popstate', () => {
    const id = new URL(location.href).searchParams.get(query) || content.rootId;
    if (id !== view.id) navigate(id);
  });
  listen(root, 'directory:select', event => { if (views.has(event.detail?.viewId)) navigate(event.detail.viewId, true); });
  const control = { navigate, inspect: () => ({ bone: root.dataset.sectionBone, version: root.dataset.boneVersion,
    view: view.id, map: root.dataset.directoryProvider || 'unbound-slot', mapElements: root.querySelectorAll('[data-directory-map]').length }),
    destroy() { cleanups.forEach(cleanup => cleanup()); mounted.delete(root); } };
  mounted.set(root, control);
  navigate(new URL(location.href).searchParams.get(query) || content.rootId);
  return control;
}

document.querySelectorAll('[data-directory-auto]').forEach(root => mountLocationDirectory(root));
