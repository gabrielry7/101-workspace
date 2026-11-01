// Sandbox-only durable delivery receipt. The commerce backend still independently
// verifies Wompi transaction/merchant/amount before settling any payment.
const encoder = new TextEncoder();
const json = (body, status = 200) => Response.json(body, {status, headers: {'cache-control': 'no-store'}});
const hex = bytes => [...new Uint8Array(bytes)].map(b => b.toString(16).padStart(2, '0')).join('');
const digest = value => crypto.subtle.digest('SHA-256', encoder.encode(value));
async function equal(a, b) {
  return crypto.subtle.timingSafeEqual(await digest(a), await digest(b));
}
async function boundedJSON(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('body');
  let size = 0; const chunks = [];
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 32768) throw new Error('body');
      chunks.push(value);
    }
  } finally { await reader.cancel(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
}
async function verified(event, secret) {
  if (!secret?.startsWith('test_events_') || event?.environment !== 'test' || event?.event !== 'transaction.updated') throw new Error('signature');
  const fields = event.signature?.properties;
  const required = ['transaction.id', 'transaction.status', 'transaction.amount_in_cents'];
  const allowed = new Set([...required, 'transaction.reference', 'transaction.currency']);
  if (!Array.isArray(fields) || fields.length > 5 || new Set(fields).size !== fields.length ||
      !required.every(f => fields.includes(f)) || !fields.every(f => allowed.has(f))) throw new Error('signature');
  if (!Number.isSafeInteger(event.timestamp) || event.timestamp < Date.now()/1000 - 172800 || event.timestamp > Date.now()/1000 + 300) throw new Error('timestamp');
  const clean = {}; const values = [];
  for (const field of fields) {
    const key = field.split('.')[1]; const value = event.data?.transaction?.[key];
    if (!(typeof value === 'string' && value.length <= 255 || Number.isSafeInteger(value))) throw new Error('signature');
    clean[key] = value; values.push(String(value));
  }
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(clean.id) || typeof clean.status !== 'string' || !Number.isSafeInteger(clean.amount_in_cents) || clean.amount_in_cents <= 0) throw new Error('signature');
  const supplied = event.signature.checksum;
  if (typeof supplied !== 'string' || !/^[a-fA-F0-9]{64}$/.test(supplied)) throw new Error('signature');
  const checksum = hex(await digest(values.join('') + event.timestamp + secret));
  if (!await equal(checksum, supplied.toLowerCase())) throw new Error('signature');
  return {event: 'transaction.updated', environment: 'test', timestamp: event.timestamp,
    signature: {properties: fields, checksum}, data: {transaction: clean}};
}
export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    try {
      if (request.method === 'GET' && path === '/health') {
        await env.DB.prepare('SELECT 1').first();
        return json({service: '101-wompi-sandbox-receiver', version: 1, sandbox: true});
      }
      if (request.method === 'POST' && path === '/events') {
        let event;
        try { event = await verified(await boundedJSON(request), env.EVENTS_SECRET); }
        catch { return json({error: 'invalid_sandbox_event'}, 401); }
        // Await durable insertion BEFORE acknowledging. Duplicate deliveries retain
        // their original ack state; replay cannot resurrect a consumed receipt.
        await env.DB.prepare('INSERT OR IGNORE INTO receipts(id, event_json, received_at) VALUES (?, ?, ?)')
          .bind(event.signature.checksum, JSON.stringify(event), Date.now()).run();
        return json({status: 'accepted'});
      }
      if (path === '/private/events' || path === '/private/ack') {
        if (!env.READER_TOKEN || !await equal(request.headers.get('authorization') || '', 'Bearer ' + env.READER_TOKEN)) return json({error: 'unauthorized'}, 401);
        if (request.method === 'GET' && path === '/private/events') {
          const result = await env.DB.prepare('SELECT id, event_json FROM receipts WHERE acked_at IS NULL ORDER BY received_at, id LIMIT 20').all();
          return json({events: result.results.map(r => ({id: r.id, event: JSON.parse(r.event_json)}))});
        }
        if (request.method === 'POST' && path === '/private/ack') {
          let body;
          try { body = await boundedJSON(request); } catch { return json({error: 'invalid_ack'}, 400); }
          if (!Array.isArray(body.ids) || !body.ids.length || body.ids.length > 20 || !body.ids.every(id => typeof id === 'string' && /^[a-f0-9]{64}$/.test(id))) return json({error: 'invalid_ack'}, 400);
          await env.DB.batch(body.ids.map(id => env.DB.prepare('UPDATE receipts SET acked_at = COALESCE(acked_at, ?) WHERE id = ?').bind(Date.now(), id)));
          return json({status: 'acknowledged'});
        }
      }
      return json({error: 'not_found'}, 404);
    } catch {
      // No bodies, authorization headers, customer fields or exception text.
      console.error(JSON.stringify({event: 'sandbox_receiver_unavailable'}));
      return json({error: 'temporarily_unavailable'}, 503);
    }
  },
};
