export interface Rect {x: number; y: number; width: number; height: number}
const clip = (a: Rect, b: Rect): Rect => ({
  x: Math.max(a.x, b.x), y: Math.max(a.y, b.y),
  width: Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)),
  height: Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y)),
});

/** Area of an axis-aligned union, clipped to its declared denominator. Not ink. */
export function unionArea(input: Rect[], bounds: Rect): number {
  const rects = input.map(r => clip(r, bounds)).filter(r => r.width > 0 && r.height > 0);
  const xs = [...new Set(rects.flatMap(r => [r.x, r.x + r.width]))].sort((a,b) => a-b);
  let total = 0;
  for (let i = 1; i < xs.length; i++) {
    const left = xs[i-1]!, right = xs[i]!;
    const intervals = rects.filter(r => r.x < right && r.x+r.width > left)
      .map(r => [r.y, r.y+r.height] as const).sort((a,b) => a[0]-b[0]);
    let end = -Infinity, covered = 0;
    for (const [top, bottom] of intervals) { covered += Math.max(0, bottom - Math.max(top,end)); end = Math.max(end,bottom); }
    total += (right-left)*covered;
  }
  return total;
}
const rect = (r: DOMRect): Rect => ({x:r.x,y:r.y,width:r.width,height:r.height});
const round = (n: number) => Math.round(n*100)/100;

export function collectFooterCoverage(host: HTMLElement) {
  const doc = host.ownerDocument, win = doc.defaultView!;
  const bounds = rect(host.getBoundingClientRect());
  const shown = (e: Element): boolean => {
    for (let p: Element | null = e; p; p=p.parentElement) {
      const s = win.getComputedStyle(p);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0 || p.hasAttribute('hidden')) return false;
    }
    return e.getBoundingClientRect().width > 0;
  };
  const text: Rect[] = [];
  const walker = doc.createTreeWalker(host, win.NodeFilter.SHOW_TEXT);
  for (let node=walker.nextNode(); node; node=walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || !node.textContent?.trim() || !shown(parent) ||
      parent.closest('script,style,.bf-sr-only,[aria-hidden=true],[data-footer-asset],[data-footer-decoration],[data-101-design-overlay]')) continue;
    const range = doc.createRange(); range.selectNodeContents(node);
    for (const line of range.getClientRects()) {
      let box = rect(line);
      for (let ancestor: Element | null=parent; ancestor && ancestor!==host; ancestor=ancestor.parentElement) {
        const s=win.getComputedStyle(ancestor);
        if (s.overflowX!=='visible' || s.overflowY!=='visible') box=clip(box,rect(ancestor.getBoundingClientRect()));
      }
      text.push(box);
    }
  }
  const boxes = (selector: string) => [...host.querySelectorAll(selector)].filter(shown).map(e=>rect(e.getBoundingClientRect()));
  const controls=boxes('a,button'), media=boxes('[data-footer-asset]'), decoration=boxes('[data-footer-decoration]');
  const denominator=bounds.width*bounds.height;
  const metric=(items: Rect[]) => {const area=unionArea(items,bounds);return {area_css_px2:round(area),percent:denominator?round(area/denominator*100):null};};
  const textMetric=metric(text), occupied=metric([...text,...controls,...media]);
  return {
    schema: '101-footer-coverage-v1', measured_at: new Date().toISOString(),
    viewport: {width:win.innerWidth,height:win.innerHeight}, footer_bounds: bounds,
    denominator_css_px2: round(denominator), scope: 'entire footer bounds in the inspected document',
    metrics: {
      text_line_boxes:textMetric, without_text:{percent:textMetric.percent===null?null:round(100-textMetric.percent)},
      controls:metric(controls), functional_media_slots:metric(media), decoration_slots:metric(decoration),
      occupied_layout:occupied, free_layout:{percent:occupied.percent===null?null:round(100-occupied.percent)},
    },
    text_line_box_count:text.length,
    method:'Exact clipped union of DOM Range line rectangles; control/media/decorative bounds reported separately.',
    limitations:[
      'Text is line-box area, not literal glyph ink. Logos and decorative wordmark are excluded.',
      'Without text is not empty: it includes controls, media, decoration and backgrounds.',
      'Controls, media and decoration may overlap text or each other; do not add their percentages.',
      'Free layout excludes functional text, controls and media; decorative backgrounds are not occupied content.',
      'Values depend on content, font, width and configuration; they are observations, not ideal percentages.',
    ],
  };
}
