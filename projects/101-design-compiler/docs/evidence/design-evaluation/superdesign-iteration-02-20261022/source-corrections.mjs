import {readFile,writeFile} from 'node:fs/promises';
const original=await readFile('docs/evidence/design-evaluation/superdesign-20261022/current.geometry.html','utf8');
const additions={editorial:`
/* Deterministic 101 QA: control separation, token contrast and compact mobile rhythm. */
.pilot-EditorialSpread.experience-Immersive .hero-entry-links{padding-right:9rem;gap:2rem}
.pilot-EditorialSpread .community-journal .journal-reading{color:var(--paper);border-color:var(--line)}
.pilot-EditorialSpread .community-journal .editorial-disclosure{color:var(--paper)}
.pilot-EditorialSpread .community-contact h2{font-size:clamp(3rem,7vw,6rem);max-width:11ch;letter-spacing:-.04em}
@media(max-width:760px){
 .pilot-EditorialSpread.experience-Immersive .hero-title{padding-top:12rem;padding-bottom:10rem;max-width:100%}
 .pilot-EditorialSpread.experience-Immersive .hero-title h1{font-size:5rem;letter-spacing:-.04em}
 .pilot-EditorialSpread.experience-Immersive .hero-entry-links{padding-right:5rem;gap:.75rem}
 .pilot-EditorialSpread .experience-overview{padding:4rem 1.25rem;gap:3rem}
 .pilot-EditorialSpread .route-directory{grid-template-columns:repeat(2,minmax(0,1fr));gap:2rem 1rem}
 .pilot-EditorialSpread .route-directory h3{font-size:1.4rem}
 .pilot-EditorialSpread .route-directory p{font-size:.9rem}
 .pilot-EditorialSpread .community-journal{padding:4rem 1.25rem}
 .pilot-EditorialSpread .journal-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:2.5rem 1rem}
 .pilot-EditorialSpread .journal-entry:nth-child(n){grid-column:auto;margin:0}
 .pilot-EditorialSpread .journal-entry:nth-child(1),.pilot-EditorialSpread .journal-entry:nth-child(2){grid-column:1/-1}
 .pilot-EditorialSpread .journal-entry:nth-child(1){display:block}
 .pilot-EditorialSpread .journal-entry:nth-child(2){display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:1rem;align-items:start}
 .pilot-EditorialSpread .journal-entry .contextual-photo{aspect-ratio:4/3}
 .pilot-EditorialSpread .journal-entry:nth-child(1) .contextual-photo{aspect-ratio:16/9}
 .pilot-EditorialSpread .journal-entry:nth-child(2) .contextual-photo{aspect-ratio:3/4}
 .pilot-EditorialSpread .journal-copy{min-width:0}
 .pilot-EditorialSpread .journal-copy h3{font-size:1.5rem}
 .pilot-EditorialSpread .journal-entry:first-child h3{font-size:2rem}
 .pilot-EditorialSpread .community-reviews{padding:4rem 1.25rem}
 .pilot-EditorialSpread .review-grid{gap:3rem}
 .pilot-EditorialSpread .review-card blockquote{font-size:1.75rem}
 .pilot-EditorialSpread .community-contact{padding:4rem 1.25rem}
 .pilot-EditorialSpread .community-contact h2{font-size:3rem;max-width:12ch;letter-spacing:-.04em}
 .pilot-EditorialSpread .social-panel{margin-top:3rem}
}
`,chapters:`
/* Deterministic 101 QA: bind the existing gutter, place three title children, compact mobile. */
.pilot-ChapterRhythm{--gutter:clamp(1.25rem,4vw,4rem)}
.pilot-ChapterRhythm.experience-Immersive .hero-title{width:100%;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr)}
.pilot-ChapterRhythm.experience-Immersive .hero-title>.eyebrow{grid-column:1/-1;margin:0}
.pilot-ChapterRhythm.experience-Immersive .hero-title h1{grid-column:1;grid-row:2}
.pilot-ChapterRhythm.experience-Immersive .hero-tagline{grid-column:2;grid-row:2}
.pilot-ChapterRhythm.experience-Immersive .hero-entry-links{width:100%;padding-right:6rem}
.pilot-ChapterRhythm .community-reviews{--muted:var(--paper)}
.pilot-ChapterRhythm .community-contact h2{font-size:clamp(3rem,7vw,6rem);max-width:11ch;letter-spacing:-.04em}
.pilot-ChapterRhythm .house-note h2{font-size:clamp(3.5rem,7vw,6rem)}
.pilot-ChapterRhythm .community-reviews .editorial-disclosure{color:var(--paper)}
.pilot-ChapterRhythm .community-reviews .text-link{border-color:var(--paper)}
@media(max-width:760px){
 .pilot-ChapterRhythm.experience-Immersive .hero-title{display:block;text-align:left;padding:10rem 1.25rem 3rem}
 .pilot-ChapterRhythm.experience-Immersive .hero-title>.eyebrow{margin-bottom:1.25rem}
 .pilot-ChapterRhythm.experience-Immersive .hero-title h1{font-size:4.5rem;letter-spacing:-.04em}
 .pilot-ChapterRhythm.experience-Immersive .hero-tagline{margin-top:1.5rem!important;font-size:1.6rem}
 .pilot-ChapterRhythm.experience-Immersive .hero-entry-links{padding:1.25rem;gap:.75rem}
 .pilot-ChapterRhythm.experience-Immersive .film-toggle{bottom:11rem}
 .pilot-ChapterRhythm .experience-overview{padding:4rem 1.25rem}
 .pilot-ChapterRhythm .house-note{margin-bottom:3rem}
 .pilot-ChapterRhythm .house-note h2{font-size:3rem;letter-spacing:-.04em}
 .pilot-ChapterRhythm .route-directory{grid-template-columns:repeat(2,minmax(0,1fr));gap:2rem 1rem}
 .pilot-ChapterRhythm .route-directory h3{font-size:1.4rem}
 .pilot-ChapterRhythm .route-directory p{font-size:.9rem}
 .pilot-ChapterRhythm .journal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2.5rem 1rem}
 .pilot-ChapterRhythm .journal-entry:nth-child(n){grid-column:auto;margin:0!important;width:auto;min-width:0}
 .pilot-ChapterRhythm .journal-entry:nth-child(1),.pilot-ChapterRhythm .journal-entry:nth-child(4){grid-column:1/-1}
 .pilot-ChapterRhythm .journal-copy{min-width:0}
 .pilot-ChapterRhythm .journal-copy h3{font-size:1.5rem}
 .pilot-ChapterRhythm .journal-entry:first-child h3,.pilot-ChapterRhythm .journal-entry:last-child h3{font-size:2rem}
 .pilot-ChapterRhythm .community-reviews{padding:4rem 1.25rem}
 .pilot-ChapterRhythm .community-contact{padding:4rem 1.25rem}
 .pilot-ChapterRhythm .community-contact h2{font-size:3rem;max-width:12ch}
}
`};
for(const [id,op]of Object.entries({editorial:'pilot-EditorialSpread',chapters:'pilot-ChapterRhythm'})){
 const generated=await readFile(`.superdesign/iteration-02/${id}-generated.html`,'utf8');
 let css=generated.match(/<style id="pilot-variation-css">([\s\S]*?)<\/style>/)[1];
 css=css.replace('--muted: #a0a0a0;','--muted: var(--paper);').replaceAll('letter-spacing: -0.05em;','letter-spacing: -0.04em;')+additions[id];
 const html=original.replace(/(class="[^"]*\bexperience-site\b[^"]*)(")/,`$1 ${op}$2`).replace('</body>',`<style id="pilot-variation-css">${css}</style></body>`);
 await writeFile(`.superdesign/iteration-02/${id}-corrected.html`,html);await writeFile(`.superdesign/tmp/${id}.provider.html`,html);
}
console.log('Two geometry-only drafts corrected against the exact source; no generation.');
