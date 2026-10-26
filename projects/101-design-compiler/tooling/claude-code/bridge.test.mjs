import test from 'node:test';
import assert from 'node:assert/strict';
import {run,limits,responseSucceeded} from './bridge.mjs';

// Local transport/guard tests only. These are NOT Claude communication evidence.
test('stdin and arguments travel literally without shell interpolation',async()=>{
  const value='$(not-a-command) `literal` & spaces\nsecond line';
  const r=await run(process.execPath,['-e',`let text='';process.stdin.on('data',x=>text+=x);process.stdin.on('end',()=>console.log(JSON.stringify({text,arg:process.argv[1]})))`,value],{input:value});
  assert.equal(r.code,0);assert.deepEqual(JSON.parse(r.stdout),{text:value,arg:value});
});
test('nonzero exit retains diagnostics',async()=>{
  const r=await run(process.execPath,['-e',"process.stderr.write('failure detail');process.exit(7)"]);
  assert.equal(r.code,7);assert.equal(r.stderr,'failure detail');
});
test('timeout stops a hung invocation',async()=>{
  const r=await run(process.execPath,['-e','setInterval(()=>{},1000)'],{timeoutMs:200});
  assert.equal(r.timedOut,true);assert.notEqual(r.code,0);
});
test('limits reject disabled, nonnumeric and fractional call counts',()=>{
  const c={maxCalls:2,maxTurns:4,timeoutMs:1000,maxBudgetUsdPerCall:0.1,maxBudgetUsdTotal:0.2};
  assert.equal(limits(c),c);
  for(const key of Object.keys(c))assert.throws(()=>limits({...c,[key]:0}));
  assert.throws(()=>limits({...c,maxCalls:1.5}));assert.throws(()=>limits({...c,timeoutMs:NaN}));
});
test('response validation rejects auth errors even with session IDs and success subtype',()=>{
  const transport={code:0};
  const sample={type:'result',subtype:'success',result:'test fixture only',session_id:'fixture-session'};
  assert.equal(responseSucceeded(transport,sample),true);
  assert.equal(responseSucceeded(transport,{...sample,is_error:true}),false);
  assert.equal(responseSucceeded({...transport,code:1},sample),false);
  assert.equal(responseSucceeded({...transport,timedOut:true},sample),false);
  assert.equal(responseSucceeded({...transport,overflow:true},sample),false);
  assert.equal(responseSucceeded(transport,{...sample,session_id:null}),false);
  assert.equal(responseSucceeded(transport,{...sample,subtype:'error_max_turns'}),false);
});
test('resume requires exactly the original session ID',()=>{
  const sample={type:'result',subtype:'success',result:'test fixture only',session_id:'original'};
  assert.equal(responseSucceeded({code:0},sample,'original'),true);
  assert.equal(responseSucceeded({code:0},sample,'different'),false);
});
