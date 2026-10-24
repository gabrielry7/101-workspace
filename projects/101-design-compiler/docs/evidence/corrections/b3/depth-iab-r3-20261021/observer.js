function observeExperience() {
    const root = document.querySelector('.experience-site'), all = (q, r = root) => [...r.querySelectorAll(q)];
    const rect = (e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; };
    const visible = (e) => { if (!e.getClientRects().length)
        return false; for (let a = e; a; a = a.parentElement) {
        const c = getComputedStyle(a);
        if (c.display === 'none' || c.visibility === 'hidden' || (a.tagName === 'DETAILS' && !a.open && !a.querySelector('summary')?.contains(e)))
            return false;
    } return true; };
    const rgb = (s) => s.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0];
    const lum = (c) => { const v = c.slice(0, 3).map(n => { n /= 255; return n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4; }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
    const readability = all('h1,h2,h3,p,a,summary,button,label,input,select,small,blockquote').filter(visible).map(e => {
        let bg = [255, 255, 255], method = 'OPAQUE_COMPUTED_SURFACE';
        for (let a = e; a; a = a.parentElement) {
            if (a.classList.contains('hero-title') && root.classList.contains('experience-Immersive') && root.dataset.pageKind === 'home') {
                bg = [112.2, 112.2, 112.2];
                method = 'WHITE_WORST_CASE_UNDER_MINIMUM_056_BLACK_MEDIA_OVERLAY';
                break;
            }
            const c = rgb(getComputedStyle(a).backgroundColor);
            if (c.length === 3 || c[3] === 1) {
                bg = c;
                break;
            }
            if (c[3] > 0 && c.slice(0, 3).every(n => n === 0)) {
                bg = [255 * (1 - c[3]), 255 * (1 - c[3]), 255 * (1 - c[3])];
                method = 'WHITE_WORST_CASE_UNDER_BLACK_ALPHA_BACKPLATE';
                break;
            }
        }
        const s = getComputedStyle(e), l1 = lum(rgb(s.color)), l2 = lum(bg);
        return { tag: e.tagName, text: e.textContent?.trim().slice(0, 60), font_px: +s.fontSize.replace('px', ''), contrast: (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05), method };
    });
    const film = root.querySelector('.hero-film'), video = root.querySelector('video');
    return { url: location.href, profile: root.dataset.profileId, page: root.dataset.pageKind, site_sha256: root.dataset.experienceSha256, content_sha256: root.dataset.contentSha256, plan_sha256: root.dataset.planSha256, media_sha256: root.dataset.mediaSha256,
        modules: all('[data-module-id]').map(m => ({ id: m.dataset.moduleId, scope: m.dataset.scopeId, page: m.dataset.semanticPage, component: m.dataset.component, required: m.dataset.required, facts: all('[data-fact-id]', m).map(f => ({ id: f.dataset.factId, scope: f.dataset.factScope, text: f.textContent?.trim() })), offerings: all('[data-offering-id]', m).map(e => ({ id: e.dataset.offeringId, scope: e.dataset.offeringScope, slot: e.querySelector('[data-media-slot]')?.dataset.mediaSlot, src: e.querySelector('img')?.currentSrc.replace(location.origin, ''), uses: e.querySelector('[data-media-usage]')?.dataset.mediaUsage?.split(' ') })) })),
        usage_ids: all('[data-media-usage]').flatMap(e => [...e.dataset.mediaUsage.split(' '), ...(e.dataset.posterUsage ? [e.dataset.posterUsage] : [])]),
        images: all('img').map(i => ({ src: i.currentSrc.replace(location.origin, ''), decoded: i.complete && i.naturalWidth > 0, alt: i.alt, fit: getComputedStyle(i).objectFit, filter: getComputedStyle(i).filter, ...rect(i) })),
        video: video ? { src: video.getAttribute('src'), muted: video.muted, loop: video.loop, controls: video.controls, autoplay: video.autoplay, paused: video.paused, time: video.currentTime, native_width: video.videoWidth, native_height: video.videoHeight, duration: video.duration, fit: getComputedStyle(video).objectFit, preload: video.getAttribute('preload'), inline: video.hasAttribute('playsinline'), ...rect(video) } : null,
        film: film ? { ...rect(film), state: film.dataset.filmState } : null,
        links: all('a[href]').map(a => ({ href: a.getAttribute('href'), text: a.textContent?.trim(), current: a.getAttribute('aria-current') })), credit_hrefs: all('[data-credit-href]').map(e => e.dataset.creditHref),
        inline_credits: all('figcaption').length, credits: all('[data-credit-original]').map(e => e.textContent), notice: root.querySelector('[data-provider-notice]')?.textContent, disclosure: root.querySelector('[data-media-disclosure]')?.textContent,
        diagnostics: all('[data-diagnostic-sha256]').map(e => JSON.parse(e.dataset.diagnosticSha256)), restrictions: all('[data-restrictions] li').map(e => e.textContent), exclusions: all('[data-exclusions] li').map(e => e.textContent),
        geometry: { width: innerWidth, document_width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight, root: rect(root), overflow: all('*').filter(visible).filter(e => { const r = e.getBoundingClientRect(); return r.left < -.6 || r.right > innerWidth + .6 || (getComputedStyle(e).display !== 'inline' && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1); }).map(e => ({ tag: e.tagName, class: e.className, ...rect(e) })) },
        readability, small_controls: all('button,input,select,summary,nav a,.hero-entry-links a,.footer-links a,.text-link').filter(visible).filter(e => e.getBoundingClientRect().height < 43).map(e => ({ tag: e.tagName, text: e.textContent, ...rect(e) })),
        main: document.querySelectorAll('main').length, h1: document.querySelectorAll('h1').length, lang: document.documentElement.lang, forms: document.forms.length, operation: all('[data-operation]').map(e => e.dataset.operation), text: root.textContent, };
}
function observeRichExperience() {
    const o = observeExperience(), root = document.querySelector('.rich-experience');
    return { ...o, editorial_sha256: root.dataset.editorialSha256, feedback_sha256: root.dataset.feedbackSha256,
        editorials: [...root.querySelectorAll('[data-editorial-id]')].map(e => ({ id: e.dataset.editorialId, text: e.querySelector('.journal-copy')?.textContent, slot: e.querySelector('[data-media-slot]')?.dataset.mediaSlot, src: e.querySelector('img')?.currentSrc.replace(location.origin, ''), uses: e.querySelector('[data-media-usage]')?.dataset.mediaUsage?.split(' ') })),
        reviews: [...root.querySelectorAll('[data-demo-review]')].map(e => ({ id: e.dataset.demoReview, quote: e.querySelector('blockquote')?.textContent, author: e.querySelector('.review-byline p')?.textContent, label: e.querySelector('.review-label')?.textContent })),
        review_disclosure: root.querySelector('[data-review-disclosure]')?.textContent, social_disclosure: root.querySelector('[data-social-disclosure]')?.textContent, contact_disclosure: root.querySelector('[data-contact-disclosure]')?.textContent,
        contact_email: root.querySelector('.contact-address')?.textContent, film_control: root.querySelector('[data-film-toggle]') ? { label: root.querySelector('[data-film-toggle]')?.getAttribute('aria-label'), text: root.querySelector('[data-film-toggle]')?.textContent, title: root.querySelector('[data-film-toggle]')?.getAttribute('title') } : null,
        embeds: root.querySelectorAll('iframe,form,script[type="application/ld+json"]').length,
        social_placeholders: [...root.querySelectorAll('[data-social-placeholder]')].map(e => e.textContent), social_controls: root.querySelectorAll('.social-links a,.social-links button,.social-links [role="link"],.social-links [tabindex]').length, };
}
function observeDepthExperience() {
    const o = observeRichExperience(), root = document.querySelector('.depth-experience');
    const rect = (e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; };
    return { ...o, features_sha256: root.dataset.featuresSha256, revision_feedback_sha256: root.dataset.revisionFeedbackSha256, depth_research_sha256: root.dataset.depthResearchSha256,
        features: [...root.querySelectorAll('[data-feature]')].map(e => ({ id: e.dataset.feature, text: e.textContent })),
        directory: [...root.querySelectorAll('[data-directory-kind]')].map(e => ({ kind: e.dataset.directoryKind, href: e.getAttribute('href'), title: e.querySelector('h3')?.textContent, copy: e.querySelector('p')?.textContent })),
        readings: [...root.querySelectorAll('[data-read-id]')].map(e => ({ id: e.dataset.readId, label: e.querySelector('.editorial-disclosure')?.textContent, body: [...e.querySelectorAll('[data-read-paragraph]')].map(p => p.textContent) })),
        navigation: [...root.querySelectorAll('.navigation-groups a')].map(e => e.getAttribute('href')),
        navigation_open: root.querySelector('[data-depth-nav]')?.open,
        journal_categories: [...root.querySelectorAll('.journal-tools option')].map(e => e.value),
        journal_layout: observeJournalReadingLayout(),
        layout: [...root.querySelectorAll('.experience-hero,.experience-overview,.community-heading,.journal-entry,.journal-entry .contextual-photo,.journal-copy,.community-reviews,.community-contact,.exp-header')].map(e => ({ class: e.className, ...rect(e) })),
        motion_preference: matchMedia('(prefers-reduced-motion:reduce)').matches, };
}
function observeJournalReadingLayout() {
    const grid = document.querySelector('.depth-experience .journal-grid');
    if (!grid)
        return null;
    const rect = (e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; };
    return { state: grid.dataset.journalLayout, width: innerWidth, grid: rect(grid), visible: [...grid.querySelectorAll('[data-editorial-id]')].filter(e => !e.hidden).map(e => ({ id: e.dataset.editorialId, card: rect(e), copy: rect(e.querySelector('.journal-copy')), image: rect(e.querySelector('.contextual-photo')) })) };
}
