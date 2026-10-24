import type { BusinessInput } from '../contracts/v1/schemas.ts';

export const sorted = (ids: readonly string[]): string[] => [...new Set(ids)].sort();
export function offeringFactIds(item: BusinessInput['offerings'][number]): string[] {
  return sorted(Object.entries(item).flatMap(([key, value]) => {
    if (key.endsWith('_fact_id') && typeof value === 'string') return [value];
    return key === 'fact_ids' && Array.isArray(value) ? value : [];
  }));
}
export function publishable(fact: BusinessInput['facts'][number] | undefined, instant: number): boolean {
  return !!fact && fact.publication === 'APPROVED' && Date.parse(fact.observed_at) <= instant
    && (!fact.expires_at || Date.parse(fact.expires_at) > instant);
}
export function safeExternalUrl(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password; }
  catch { return false; }
}
export function validClass(item: BusinessInput['offerings'][number], facts: Map<string, BusinessInput['facts'][number]>): boolean {
  if (item.kind !== 'class_session') return true;
  const start = facts.get(item.starts_at_fact_id); const zone = facts.get(item.timezone_fact_id);
  if (start?.kind !== 'class_starts_at' || typeof start.value !== 'string' || !Number.isFinite(Date.parse(start.value))) return false;
  try {
    if (zone?.kind !== 'timezone' || typeof zone.value !== 'string') return false;
    new Intl.DateTimeFormat('es', { timeZone: zone.value }); return true;
  } catch { return false; }
}

export function offeringKindsValid(item: BusinessInput['offerings'][number], facts: Map<string, BusinessInput['facts'][number]>): boolean {
  const kinds: Record<string, string> = {
    name_fact_id: 'offering_name', price_fact_id: 'price', sku_fact_id: 'sku', terms_fact_id: 'membership_terms',
    starts_at_fact_id: 'class_starts_at', timezone_fact_id: 'timezone',
  };
  return Object.entries(item).every(([field, ref]) => !kinds[field] || typeof ref === 'string' && facts.get(ref)?.kind === kinds[field])
    && typeof facts.get(item.name_fact_id)?.value === 'string'
    && (!('price_fact_id' in item) || !item.price_fact_id || typeof facts.get(item.price_fact_id)?.value !== 'boolean')
    && (!('terms_fact_id' in item) || !item.terms_fact_id || typeof facts.get(item.terms_fact_id)?.value === 'string')
    && !item.fact_ids.some(id => facts.get(id)?.kind.startsWith('capability:'));
}
