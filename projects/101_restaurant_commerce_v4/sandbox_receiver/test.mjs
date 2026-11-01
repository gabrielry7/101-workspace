import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {Miniflare, convertV4MiniflareOptions} from 'miniflare';
const key = 'test_events_synthetic', token = 'test-reader-token-'.repeat(4);
const event = () => {
  const timestamp = Math.floor(Date.now()/1000);
  return {event:'transaction.updated', environment:'test', timestamp,
    data:{transaction:{id:'tx-1', status:'APPROVED', amount_in_cents:10000, customer_email:'must-not-persist@example.invalid'}},
    signature:{properties:['transaction.id','transaction.status','transaction.amount_in_cents'],
      checksum:createHash('sha256').update('tx-1APPROVED10000'+timestamp+key).digest('hex')}};
};
const mf = new Miniflare(convertV4MiniflareOptions({workers:[{name:'receiver', modules:true, scriptPath:new URL('./worker.mjs', import.meta.url).pathname,
  compatibilityDate:'2026-10-29', d1Databases:['DB'], bindings:{EVENTS_SECRET:key, READER_TOKEN:token}}]}));
await (await mf.getD1Database('DB')).exec((await readFile(new URL('./schema.sql', import.meta.url),'utf8')).replaceAll('\n',' '));
const call = (path, options={}) => mf.dispatchFetch('https://receiver.test'+path,options);
const post = (path, body, auth=false) => call(path,{method:'POST',body:JSON.stringify(body),headers:{'content-type':'application/json',...(auth?{authorization:'Bearer '+token}:{})}});
try {
  await test('durable ack, replay dedupe, privacy, authenticated consumption', async () => {
    assert.equal((await call('/health')).status,200);
    assert.equal((await call('/private/events')).status,401);
    const e=event();
    assert.equal((await post('/events',e)).status,200);
    assert.equal((await post('/events',e)).status,200);
    const read=async()=> (await call('/private/events',{headers:{authorization:'Bearer '+token}})).json();
    const rows=(await read()).events;
    assert.equal(rows.length,1);
    assert.equal(JSON.stringify(rows).includes('must-not-persist'),false);
    assert.equal((await post('/private/ack',{ids:[rows[0].id]},true)).status,200);
    assert.equal((await post('/events',e)).status,200);
    assert.equal((await read()).events.length,0);
  });
  await test('forged/production/stale/oversize events rejected without persistence',async()=> {
    for (const mutate of [e=>{e.environment='prod'},e=>{e.data.transaction.amount_in_cents++},e=>{e.timestamp=1},e=>{e.signature.properties=[]},e=>{e.signature.checksum='x'.repeat(40000)}]) {
      const e=event(); mutate(e); assert.equal((await post('/events',e)).status,401);
    }
    assert.equal((await post('/private/ack',{ids:['bad']},true)).status,400);
    const result=await (await mf.getD1Database('DB')).prepare('SELECT COUNT(*) AS n FROM receipts').first();
    assert.equal(result.n,1);
  });
  await test('database failure is not acknowledged',async()=> {
    await (await mf.getD1Database('DB')).exec('DROP TABLE receipts');
    assert.equal((await post('/events',event())).status,503);
  });
} finally {await mf.dispose();}
