// Browser review only: measured roles, not a visual taste or certification score.
(selectors) => {
  const rgba = (value) => {
    const m = value.match(/^rgba?\(([^)]+)\)$/);
    if (!m) return null;
    const a = m[1].split(",").map(Number);
    return [a[0], a[1], a[2], a.length === 4 ? a[3] : 1];
  };
  const blend = (a, b) =>
    a.slice(0, 3).map((v, i) => v * a[3] + b[i] * (1 - a[3]));
  const luminance = (rgb) => {
    const v = rgb.map((n) => {
      n /= 255;
      return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  };
  const contrast = (node) => {
    const layers = [];
    for (let e = node; e; e = e.parentElement) {
      const style = getComputedStyle(e);
      if (style.backgroundImage !== "none" || Number(style.opacity) !== 1)
        return null;
      const c = rgba(style.backgroundColor);
      if (!c) return null;
      layers.push(c);
    }
    let background = [255, 255, 255];
    layers.reverse().forEach((c) => (background = blend(c, background)));
    const foreground = rgba(getComputedStyle(node).color);
    if (!foreground) return null;
    const a = luminance(blend(foreground, background)),
      b = luminance(background);
    return Number(
      ((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)).toFixed(3),
    );
  };
  return {
    width: innerWidth,
    height: innerHeight,
    overflow: document.documentElement.scrollWidth > innerWidth,
    roles: selectors.flatMap((selector) => {
      const e = document.querySelector(selector);
      if (!e) return [];
      const c = getComputedStyle(e),
        b = e.getBoundingClientRect();
      return [
        {
          selector,
          font: c.fontSize,
          color: c.color,
          background: c.backgroundColor,
          radius: c.borderRadius,
          x: b.x,
          width: b.width,
          height: b.height,
          solid_contrast: contrast(e),
        },
      ];
    }),
  };
};
