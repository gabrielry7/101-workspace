import { locationDirectorySchema } from '../bones/location-directory.ts';
import { validateReferenceCatalogue, referenceViewId } from './arabica-locations.js';

// Retained reference content only, not a grant to publish its original media.
export function bindArabicaDirectory(value: any) {
  const catalogue = validateReferenceCatalogue(value);
  const names = new Map<string,string>();
  for (const page of catalogue.pages) for (const item of page.links) names.set(referenceViewId(item.url)!, item.name);
  const entry = (item: any) => ({ label: item.name, count: item.count, viewId: referenceViewId(item.url)! });
  const images = new Map<string,{url:string;label:string}>();
  const views = catalogue.pages.map((page: any) => ({ id: page.id, title: names.get(page.id) || 'Locations',
    level: page.level === 'world' ? 'overview' : page.level === 'country' ? 'area' : 'locality',
    parentId: page.back ? referenceViewId(page.back) : null, panelTitle: page.panelHeading,
    groups: page.groups.map((group: any) => ({ label: group.name, items: group.items.map(entry) })),
    entries: page.level === 'world' ? [] : page.links.map(entry),
    openings: page.states.map((state: any) => ({ label: state.name, items: state.items })),
    cardsTitle: page.cardsHeading?.replace(/^%\s*/, '') || 'Locations',
    cards: page.cards.map((card: any, index: number) => {
      const id = `card-${index + 1}`; images.set(`${page.id}:${id}`, { url: card.image, label: card.name });
      return { id, title: card.name, imageLabel: card.name, action: { state: 'available', href: card.url } };
    }),
  }));
  return { content: locationDirectorySchema.parse({ rootId: 'world', title: 'Locations', mapLabel: '% Arabica locations map',
    labels: { back: 'Go Back', cardPage: 'Show location', navigation: 'Locations map and regions' }, views }), images };
}
