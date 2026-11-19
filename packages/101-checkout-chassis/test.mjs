import {test} from 'node:test';import assert from 'node:assert/strict';
import {checkoutProfile,contract,preset,CHECKOUT_ANATOMY} from './checkout-chassis.js';
test('all coats use the same strict contract and typed anatomy',()=>{
 for(const name of Object.keys(contract.presets))assert.deepEqual(checkoutProfile(preset(name)),preset(name));
 assert.equal(CHECKOUT_ANATOMY.length,new Set(CHECKOUT_ANATOMY.map(x=>x.role)).size);
 assert(CHECKOUT_ANATOMY.some(x=>x.status==='new'));assert(CHECKOUT_ANATOMY.some(x=>x.status==='reused'));
});
test('reject data/actions/CSS execution and invalid geometry',()=>{
 for(const extra of [{checkout_url:'https://evil.test'},{colors:{ink:'url(x)'}},{geometry:{gap:true}},{geometry:{formWidth:999999}},{bones:{surfaces:{panel:{opacity:0}}}},{typography:{bodyFont:'unknown'}}])assert.throws(()=>checkoutProfile({...preset('neutral'),...extra}));
});
test('independent overrides preserve other roles and do not mutate the preset',()=>{
 const p=preset('warm'),before=JSON.stringify(p);const copy=structuredClone(p);copy.bones.surfaces.panel.radius=0;
 const checked=checkoutProfile(copy);assert.equal(checked.bones.surfaces.panel.radius,0);assert.deepEqual(checked.colors,p.colors);assert.equal(JSON.stringify(p),before);
});
