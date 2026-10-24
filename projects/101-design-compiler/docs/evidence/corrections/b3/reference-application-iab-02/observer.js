function observeContextual() {
    const root = document.querySelector('.contextual-site'), all = (q, r = root) => [...r.querySelectorAll(q)];
    const rect = (e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; };
    const visible = (e) => { if (!e.getClientRects().length)
        return false; for (let a = e; a; a = a.parentElement) {
        const s = getComputedStyle(a);
        if (s.display === 'none' || s.visibility === 'hidden' || (a.tagName === 'DETAILS' && !a.open && e !== a && !a.querySelector('summary')?.contains(e)))
            return false;
    } return true; };
    function rgb(c) { return c.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0]; }
    function lum(c) { const v = c.slice(0, 3).map(n => { n /= 255; return n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4; }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; }
    const readability = all('h1,h2,h3,p,a,summary,button,label,input,select,figcaption,small').filter(visible).map(e => { const s = getComputedStyle(e); let a = e, bg = [255, 255, 255]; while (a) {
        const c = rgb(getComputedStyle(a).backgroundColor);
        if (c.length === 3 || c[3] !== 0) {
            bg = c;
            break;
        }
        a = a.parentElement;
    } const l1 = lum(rgb(s.color)), l2 = lum(bg); return { tag: e.tagName, text: e.textContent?.trim().slice(0, 60), font_px: +s.fontSize.replace('px',''), contrast: (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05) }; });
    return { reference_application: root.dataset.referenceApplication, offering_media: all('[data-offering-id]').map(e => ({ offering: e.dataset.offeringId, slot: e.querySelector('[data-media-slot]')?.dataset.mediaSlot, src: e.querySelector('img')?.currentSrc.replace(location.origin, ''), usages: e.querySelector('[data-media-usage]')?.dataset.mediaUsage?.split(' ') })), context: { plan: root.dataset.planSha256, content: root.dataset.contentSha256, media: root.dataset.mediaSha256, context: root.dataset.contextSha256 },
        modules: all('[data-module-id]').map(m => ({ id: m.dataset.moduleId, scope: m.dataset.scopeId, page: m.dataset.semanticPage, component: m.dataset.component, required: m.dataset.required,
            facts: all('[data-fact-id]', m).map(f => ({ id: f.dataset.factId, scope: f.dataset.factScope, text: f.textContent?.trim() })), offerings: all('[data-offering-id]', m).map(o => ({ id: o.dataset.offeringId, scope: o.dataset.offeringScope })) })),
        diagnostics: all('[data-diagnostic-sha256]').map(e => JSON.parse(e.dataset.diagnosticSha256)), restrictions: all('[data-restrictions] li').map(e => e.textContent), exclusions: all('[data-exclusions] li').map(e => e.textContent),
        usage_ids: all('[data-media-usage]').flatMap(e => [...e.dataset.mediaUsage.split(' '), ...(e.dataset.posterUsage ? [e.dataset.posterUsage] : [])]),
        images: all('img').map(i => ({ src: i.currentSrc.replace(location.origin, ''), decoded: i.complete && i.naturalWidth > 0, natural_width: i.naturalWidth, natural_height: i.naturalHeight, alt: i.alt, object_fit: getComputedStyle(i).objectFit, filter: getComputedStyle(i).filter, ...rect(i) })),
        video: { autoplay: all('video')[0].autoplay, preload: all('video')[0].getAttribute('preload'), object_fit: getComputedStyle(all('video')[0]).objectFit, ...rect(all('video')[0]) },
        disclosure: all('[data-media-disclosure]')[0]?.textContent, notice: all('[data-provider-notice]')[0]?.textContent, credits: all('figcaption').map(e => e.textContent),
        geometry: { width: innerWidth, document_width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight, nav: rect(all('.contextual-nav')[0]), title: rect(document.querySelector('h1')), hero: rect(all('.hero-photo')[0]), collection: rect(all('.contextual-collection')[0]), items: all('[data-offering-id]').map(rect),
            overflow: all('*').filter(visible).filter(e => { const r = e.getBoundingClientRect(); return r.left < -.6 || r.right > innerWidth + .6 || (getComputedStyle(e).display !== 'inline' && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1); }).map(e => ({ tag: e.tagName, class: e.className, ...rect(e) })) },
        readability, small_controls: all('.button,nav a,summary,button,input,select').filter(visible).filter(e => e.getBoundingClientRect().height < 43).map(e => ({ tag: e.tagName, text: e.textContent?.slice(0, 60), ...rect(e) })),
        main: document.querySelectorAll('main').length, h1: document.querySelectorAll('h1').length, lang: document.documentElement.lang, forms: document.forms.length,
        links: all('a[href^="#"]').map(a => ({ href: a.hash, exists: !!document.getElementById(a.hash.slice(1)) })), text: root.textContent,
        resources: [], navigation_ms: null,
    };
}
