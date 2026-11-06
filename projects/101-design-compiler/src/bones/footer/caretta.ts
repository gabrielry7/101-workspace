import {parseFooterContent} from './contract.ts';

const link = (id: string, label: string, path: string, newTab = false) => ({
  id, label, href: new URL(path, 'https://caretta.so/').href, state: 'available' as const, newTab,
});
const soon = (id: string, label: string) => ({id, label, state: 'soon' as const});
const prompt = encodeURIComponent('Read https://www.caretta.so/ and summarise this page for me. Explain what Caretta offers here, who it is for, the problems it solves, and the most important reasons to choose it. Cite the URL in your answer.');

// Real reference content. Source logos/skin are deliberately not reproduced.
export const carettaFooter = parseFooterContent({
  schemaVersion: '101-footer-content-v1',
  source: {
    key: 'caretta/08', url: 'https://caretta.so/',
    image: 'https://iyvuzolgrnbninocubps.supabase.co/storage/v1/object/public/agg-sections/caretta/sec-08-0-1440w-307eab1ec3ec.avif',
    capturedAt: '2026-10-19T03:18:17.681+00:00', destinationsObservedOn: '2026-11-05',
  },
  brand: {
    name: 'Caretta',
    description: 'Real-time intelligence for the moments that decide whether the deal moves forward.',
    backersHeading: 'Backed by', copyright: 'Caretta Inc. © 2026', wordmark: 'Caretta',
  },
  assistantsLabel: 'Ask an AI to summarise this page',
  assistants: [
    link('ai-chatgpt', 'ChatGPT', 'https://chatgpt.com/?q=' + prompt, true),
    link('ai-claude', 'Claude', 'https://claude.ai/new?q=' + prompt, true),
    link('ai-perplexity', 'Perplexity', 'https://www.perplexity.ai/?q=' + prompt, true),
    link('ai-google', 'Google AI Mode', 'https://www.google.com/search?udm=50&q=' + prompt, true),
    link('ai-grok', 'Grok', 'https://grok.com/?q=' + prompt, true),
  ],
  backers: [
    link('backer-yc', 'Y Combinator', 'https://www.ycombinator.com', true),
    link('backer-robinhood', 'Robinhood', 'https://robinhood.com', true),
    link('backer-longjourney', 'Long Journey', 'https://www.longjourney.vc', true),
  ],
  groups: [
    {id: 'product', label: 'Product', items: [
      link('before', 'Before the call', '/product/before'),
      link('during', 'During the call', '/product/during'),
      link('after', 'After the call', '/product/after'),
      link('metrics', 'Caretta Metrics', '/product/metrics'),
      link('brain', 'Brain', '/product/knowledge'),
    ]},
    {id: 'teams', label: 'Teams', items: [
      soon('sdrs', 'SDRs'), soon('aes', 'AEs'),
      link('gtm', 'GTM Leaders', '/product/metrics'),
      link('founders', 'Founders', '/industries/startups'),
    ]},
    {id: 'industries', label: 'Industries', items: [
      link('compute', 'Compute & Inference', '/industries/compute'),
      soon('voice-ai', 'Voice AI'),
      link('insurance', 'Insurance', '/industries/insurance'),
      link('startups', 'Startups', '/industries/startups'),
      link('cybersecurity', 'Cybersecurity', '/industries/cybersecurity'),
    ]},
    {id: 'resources', label: 'Resources', items: [
      link('pricing', 'Pricing', '/pricing'), link('blog', 'Blog', '/blog'),
      link('docs', 'Docs', 'https://caretta.mintlify.dev/docs'),
      link('resources-link', 'Resources', '/resources'), soon('customers', 'Customers'),
      link('about', 'About', '/about'), link('contact', 'Contact', '/contact'),
      link('brand-guidelines', 'Brand guidelines', '/brand'),
      link('careers', 'Careers', '/careers'), soon('security', 'Security'),
    ]},
  ],
  legal: [
    link('privacy', 'Privacy', '/privacy'), link('terms', 'Terms', '/terms'),
    link('trust', 'Trust Center', 'https://trust.caretta.so', true),
    link('linkedin', 'LinkedIn', 'https://www.linkedin.com/company/carettaai/', true),
    link('email', 'Email', 'mailto:founders@caretta.so'),
  ],
});
