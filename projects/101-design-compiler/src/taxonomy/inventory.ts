import { createHash } from 'node:crypto';
import { CategoryRecordV1, canonicalProvider, splitHierarchy } from './contracts.ts';
import type { CategoryRecord } from './contracts.ts';

const requiredHeaders = [
  'source', 'category_field', 'category_value', 'provider_category_id',
  'source_observations', 'business_candidates', 'other_observations',
];
export class InventoryError extends Error {
  code: string;
  constructor(code: string, message: string) { super(message); this.code = code; this.name = 'InventoryError'; }
}
type TableRow = { cells: string[]; line_start: number; line_end: number };

// RFC-style quoted fields, including delimiter/newline/escaped quote in a cell.
// Empty records are ignored; source records and physical line spans are retained.
export function parseDelimited(text: string, delimiter: string): TableRow[] {
  const rows: TableRow[] = [];
  let cells: string[] = [], cell = '', quoted = false, closed = false, line = 1, start = 1;
  const pushCell = () => { cells.push(cell); cell = ''; closed = false; };
  const pushRow = () => {
    pushCell();
    if (cells.some(value => value.length)) rows.push({ cells, line_start: start, line_end: line });
    cells = [];
  };
  for (let index = 0; index < text.length; index++) {
    const char = text[index]!;
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') { cell += '"'; index++; }
        else { quoted = false; closed = true; }
      } else if (char === '\r' && text[index + 1] === '\n') { cell += '\r\n'; index++; line++; }
      else { cell += char; if (char === '\n' || char === '\r') line++; }
    } else if (char === delimiter) pushCell();
    else if (char === '\n' || char === '\r') {
      pushRow();
      if (char === '\r' && text[index + 1] === '\n') index++;
      line++; start = line;
    } else if (char === '"' && !cell && !closed) quoted = true;
    else {
      if (char === '"' || closed) throw new InventoryError('INVALID_QUOTING', `Invalid quotation at physical line ${line}`);
      cell += char;
    }
  }
  if (quoted) throw new InventoryError('INVALID_QUOTING', 'Unterminated quoted field');
  if (cell || cells.length || closed) pushRow();
  return rows;
}

export function loadInventoryBytes(bytes: Uint8Array, file: string): CategoryRecord[] {
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes).replace(/^\uFEFF/, '');
  const headerLine = decoded.split(/\r?\n/).find(line => line.trim());
  if (!headerLine) throw new InventoryError('EMPTY_INVENTORY', `Empty inventory: ${file}`);
  const delimiters = ['\t', ',', ';'].filter(delimiter => {
    try {
      const row = parseDelimited(headerLine, delimiter)[0];
      return row && requiredHeaders.every(header => row.cells.map(x => x.trim()).includes(header));
    } catch { return false; }
  });
  if (delimiters.length !== 1) throw new InventoryError('INVALID_HEADERS', `Expected all seven inventory columns in ${file}`);
  const rows = parseDelimited(decoded, delimiters[0]!);
  const headers = rows[0]!.cells.map(value => value.trim());
  if (new Set(headers).size !== headers.length) throw new InventoryError('DUPLICATE_HEADERS', 'Duplicate inventory headers');
  return rows.slice(1).map((row, index) => {
    if (row.cells.length !== headers.length) throw new InventoryError('COLUMN_COUNT', `Wrong column count at ${file}:${row.line_start}`);
    const raw = Object.fromEntries(headers.map((header, index) => [header, row.cells[index]!]));
    const count = (column: string) => {
      const value = raw[column]!.trim();
      if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value))) throw new InventoryError('INVALID_COUNT', `Invalid ${column} at ${file}:${row.line_start}`);
      return Number(value);
    };
    const value = raw['category_value']!;
    const field = raw['category_field']!;
    return CategoryRecordV1.parse({
      id: `inventory:${sha256}:${index + 1}`,
      provider: canonicalProvider(raw['source']!), provider_label: raw['source'],
      category_field: field, category_value: value,
      provider_category_id: raw['provider_category_id'] || null,
      hierarchy: field.trim() === '101.normalized_category' ? value.split('/').map(x => x.trim()).filter(Boolean) : splitHierarchy(value),
      normalized_category: field.trim() === '101.normalized_category' ? value : null,
      provenance: { file, sha256, row: index + 1, line_start: row.line_start, line_end: row.line_end },
      counts: { source_observations: count('source_observations'), business_candidates: count('business_candidates'), other_observations: count('other_observations') },
      raw,
    });
  });
}
