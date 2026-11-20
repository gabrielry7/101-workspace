// Own bounded extractor. DOMParser parses inert reference HTML; no source script is run.
export function parseArabicaReference(html, url) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const clean = el => el?.textContent?.replace(/\s+/g, ' ').trim() || '';
  const absolute = value => {
    const result = new URL(value, url);
    if (result.pathname.startsWith('/location/')) result.pathname = '/en' + result.pathname;
    return result.href;
  };
  const path = new URL(url).pathname.replace(/^\/en\/locations\/?/, '').replace(/\/$/, '');
  const level = !path ? 'world' : path.includes('/') ? 'city' : 'country';
  const opened = doc.querySelector('.filter.set.opened');
  const link = a => ({ name: clean(a.querySelector('.name')) || clean(a),
    count: a.querySelector('.count') ? Number(clean(a.querySelector('.count'))) : null, url: absolute(a.getAttribute('href')) });
  const links = [...opened?.querySelectorAll('.items.list a') || []].map(link);
  const groups = []; let group;
  if (level === 'world') for (const el of opened?.querySelector('.items.list')?.children || []) {
    if (el.tagName === 'SPAN') { group = { name: clean(el), items: [] }; groups.push(group); }
    else if (el.querySelector('a') && group) group.items.push(link(el.querySelector('a')));
  }
  const states = []; let state;
  for (const el of doc.querySelectorAll('.filter.set:not(.opened) .items.list li')) {
    if (el.querySelector('h2')) { state = { name: clean(el.querySelector('h2')), items: [] }; states.push(state); }
    else if (state) state.items.push(clean(el));
  }
  const cards = [...doc.querySelectorAll('.related-item')].map(el => ({
    name: clean(el.querySelector('h3')), url: absolute(el.querySelector('a').getAttribute('href')),
    image: (el.querySelector('.thumb')?.getAttribute('style') || '').match(/url\(['"]?([^'")]+)['"]?\)/)?.[1],
  }));
  const script = [...doc.scripts].filter(s => !s.src).map(s => s.textContent).join('\n');
  const number = '([-\\d.]+)';
  const pointPattern = new RegExp(`case ['"]([^'"]+)['"]:\\s*return new google.maps.LatLng\\(\\s*${number}\\s*,\\s*${number}\\s*\\)`, 'g');
  const points = Object.fromEntries([...script.matchAll(pointPattern)].map(m => [m[1], [Number(m[3]), Number(m[2])]]));
  const quoted = "'((?:\\\\.|[^'\\\\])*)'";
  const decode = value => value.replace(/\\'/g, "'").replace(/\\"/g, '"').replace(/&amp;/g, '&');
  const markers = [];
  const countryPattern = new RegExp(`markCountry\\(\\s*"([^"]+)"\\s*,\\s*${quoted}\\s*,\\s*${quoted}\\s*,\\s*${quoted}\\s*\\)`, 'g');
  for (const m of script.matchAll(countryPattern)) markers.push({ name: decode(m[2]), coordinates: points[m[1]],
    url: m[3] === '#' ? '#' : absolute(decode(m[3])), icon: decode(m[4]), status: m[3] === '#' ? 'opening' : 'open' });
  const block = script.split('function TestMarker()')[1]?.split('// Function for adding')[0] || '';
  const declared = new RegExp(`(Test\\d+)\\s*=\\s*new google.maps.LatLng\\(\\s*${number}\\s*,\\s*${number}\\s*\\)`, 'g');
  for (const m of block.matchAll(declared)) {
    const argumentsPattern = new RegExp(`addMarker\\(\\s*${m[1]}\\s*,\\s*${quoted}\\s*,\\s*${quoted}\\s*,\\s*${quoted}\\s*\\)`);
    const args = block.match(argumentsPattern);
    if (args) markers.push({ name: decode(args[2]), coordinates: [Number(m[3]), Number(m[2])],
      url: args[1] === '#' ? '#' : absolute(decode(args[1])), icon: decode(args[3]), status: args[1] === '#' ? 'opening' : 'open' });
  }
  const country = script.match(/centerOnCountry\('([^']+)'\)/)?.[1];
  const direct = script.match(/var myCenter\s*=\s*new google.maps.LatLng\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)/);
  const declaredCenter = country ? points[country] : direct ? [Number(direct[2]), Number(direct[1])] : null;
  // Macau has no createPoint entry in the retained original. Its own city marker
  // provides a sourced local centre; unresolved world markers are absent there too.
  const center = declaredCenter || markers.find(marker => marker.coordinates)?.coordinates || null;
  const mapStyle = JSON.parse(script.match(/styles:\s*(\[[\s\S]*?\])\s*\n\s*};/)?.[1] || 'null');
  return { id: path || 'world', url, level, groups, links, states, cards,
    markers: [...new Map(markers.filter(marker => marker.coordinates).map(m => [m.name + '|' + m.url, m])).values()], center,
    sourceWarnings: declaredCenter ? [] : ['Centre derived from this reference page\'s first positioned marker'],
    zoom: Number(script.match(/zoom:\s*(\d+)/)?.[1] || 2), mapStyle,
    panelHeading: clean(opened?.querySelector('h2')), cardsHeading: clean(doc.querySelector('.related h1')),
    back: doc.querySelector('.back.panel a') ? absolute(doc.querySelector('.back.panel a').getAttribute('href')) : null };
}
