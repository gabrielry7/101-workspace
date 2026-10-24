import {test} from 'node:test';
import assert from 'node:assert/strict';
import {humanReviewCatalog as catalog,reviewFeaturesForProfile} from '../src/requirements/review-catalog.ts';
import {validateHumanReviewCatalog} from '../src/requirements/review-contracts.ts';
import {requirementCatalog} from '../src/requirements/catalog.ts';
import {ArchetypeId} from '../src/contracts/v1/schemas.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const reseal=(value:typeof catalog)=>{const {catalog_sha256:_,...body}=value;return {...body,catalog_sha256:inputSha256(body)};};
test('human goals preserve every restaurant request without claiming data or commercial software',()=>{
 const selected=reviewFeaturesForProfile('food_hospitality'),ids=new Set(selected.map(e=>e.feature.id));
 for(const id of catalog.restaurant_requested_feature_ids)assert(ids.has(id),id);
 for(const f of catalog.features){assert.equal(f.frontend_status,'NOT_BUILT');assert.equal(f.operation_status,'NOT_CONNECTED');assert.equal(f.data_status,'NOT_EVALUATED');}
 assert.equal(catalog.technical_catalog_sha256,requirementCatalog.catalog_sha256);
 assert.equal(requirementCatalog.cards.length,47);
 assert.equal(catalog.status,'PROPOSED_FOR_HUMAN_REVIEW');
});
test('each activity shares canonical definitions and retains dependencies, regulated is a modifier',()=>{
 assert.deepEqual(new Set(catalog.profiles.map(p=>p.archetype_id)),new Set(ArchetypeId.options));
 for(const p of catalog.profiles){const entries=reviewFeaturesForProfile(p.archetype_id),ids=new Set(entries.map(e=>e.feature.id));
  assert.equal(ids.size,entries.length);
  for(const e of entries){assert.equal(e.feature,catalog.features.find(f=>f.id===e.feature.id));for(const dep of e.feature.depends_on)assert(ids.has(dep));}
 }
 assert.match(catalog.profiles.find(p=>p.archetype_id==='regulated_services')!.caveat,/Modificador/);
});
test('own ordering is a lifecycle, table inventory and calendar are never confirmation by appearance',()=>{
 const find=(id:string)=>catalog.features.find(f=>f.id===id)!;
 assert.deepEqual(find('checkout').depends_on,['cart','fulfilment','privacy']);
 assert.deepEqual(find('order_management').depends_on,['checkout']);
 assert.deepEqual(find('table_map').depends_on,['live_booking']);
 assert.match(find('table_map').acceptance_checks.join(' '),/simulada/);
 assert.match(find('calendar').acceptance_checks.join(' '),/no confirma/);
 assert.deepEqual(find('calendar').depends_on,[],'event calendar does not silently require a reservation');
 assert.deepEqual(find('booking_management').depends_on,['privacy'],'authorized existing reservations can be managed without live inventory');
 assert.deepEqual(find('fulfilment').depends_on,[],'delivery/pickup information does not imply own cart');
 assert.equal(find('loyalty').registry_relation,'EXTENSION_REQUIRED');
 assert.deepEqual(find('loyalty').registry_references,[]);
});
test('reviews, price and inventory specifications bind exact subjects instead of inheriting every branch value',()=>{
 const find=(id:string)=>catalog.features.find(f=>f.id===id)!;
 assert.deepEqual(find('reviews').business_data.map(d=>d.scope),['EXACT_REVIEW','EXACT_REVIEW','EXACT_REVIEW_SUBJECT','EXACT_REVIEW_SUBJECT']);
 for(const d of find('profiles').business_data.slice(0,3))assert.equal(d.scope,'EXACT_PERSON',d.label);
 assert.match(find('profiles').business_data[3]!.label,/persona exacta/);
 assert.match(find('profiles').acceptance_checks.join(' '),/independientes/);
 assert.match(find('reviews').acceptance_checks.join(' '),/no autoriza las demás/);
 assert.equal(find('review_submission').business_data[0]!.scope,'EXACT_OFFERING');
 for(const d of find('cart').business_data.slice(0,4))assert.equal(d.scope,'EXACT_OFFERING',d.label);
 assert(find('ingredients').business_data.every(d=>d.scope==='EXACT_OFFERING'));
 assert.equal(find('table_map').business_data[1]!.scope,'EXACT_RESOURCE');
 assert.equal(find('table_map').business_data[3]!.scope,'EXACT_RESOURCE');
 assert.match(find('reviews').acceptance_checks.join(' '),/no se atribuye a un plato/);
 assert.match(find('cart').acceptance_checks.join(' '),/otro plato no completa/);
 assert(find('media').business_data.every(d=>d.scope==='EXACT_MEDIA_USAGE'));
 // This sidecar is specification only. Live cross-offering evaluation remains
 // in existing B1 tests; no real input was marked satisfied by this catalogue.
 assert.equal(catalog.business_input_evaluation,'NOT_PERFORMED');
});
test('offering truth, unknown parking and field performance retain explicit guards',()=>{
 const find=(id:string)=>catalog.features.find(f=>f.id===id)!;
 assert(find('offer_detail').business_data.every(d=>d.scope==='EXACT_OFFERING'));
 assert.match(find('ingredients').risks.join(' '),/no deducir alérgenos/);
 assert.match(find('nutrition').risks.join(' '),/No inventar calorías/);
 assert.match(find('arrival').acceptance_checks.join(' '),/desconocido/);
 assert(find('performance').business_data.every(d=>d.owner==='PLATFORM'));
 assert(find('media').business_data.some(d=>d.owner==='RIGHTS_HOLDER'));
 assert.equal(catalog.performance_source.measurement_status,'NOT_MEASURED_FOR_FINAL_SITE');
});
test('review contract denies invented readiness, dangling references and resealed dependency cycles',()=>{
 const promoted=structuredClone(catalog);(promoted.features[0] as any).frontend_status='IMPLEMENTED';assert.throws(()=>validateHumanReviewCatalog(reseal(promoted)));
 const dangling=structuredClone(catalog);dangling.profiles[0]!.features[0]!.feature_id='invented';assert.throws(()=>validateHumanReviewCatalog(reseal(dangling)),/REVIEW_BAD_FEATURE_REFERENCE/);
 const cyclic=structuredClone(catalog);cyclic.features[0]!.depends_on=[cyclic.features[1]!.id];cyclic.features[1]!.depends_on=[cyclic.features[0]!.id];assert.throws(()=>validateHumanReviewCatalog(reseal(cyclic)),/REVIEW_DEPENDENCY_CYCLE/);
 const hash=structuredClone(catalog);hash.features[0]!.label='changed';assert.throws(()=>validateHumanReviewCatalog(hash),/REVIEW_CATALOG_HASH_MISMATCH/);
});
