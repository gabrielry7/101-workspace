import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {z} from 'zod';
import {loadB1Fixtures} from '../scripts/lib/b1-fixtures.ts';
import {loadMappingRegistry} from '../scripts/load-taxonomy.ts';
import {loadPlannerFixtures} from '../scripts/load-planner-fixtures.ts';
import {CapabilityId,SitePlanV1,BusinessProfileV1,CapabilityProfileV1} from '../src/contracts/v1/schemas.ts';
import type {BusinessInput} from '../src/contracts/v1/schemas.ts';
import {classifyContextually} from '../src/taxonomy/context.ts';
import {contextPolicy} from '../src/taxonomy/context-policy.ts';
import {contextContracts} from '../src/taxonomy/context-contracts.ts';
import {requirementCatalog,validateRequirementCatalog} from '../src/requirements/catalog.ts';
import {requirementContracts} from '../src/requirements/contracts.ts';
import {diagnoseBusiness,verifyFunctionalDiagnostic} from '../src/requirements/diagnose.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
import {planBusiness} from '../src/planner/plan.ts';
import {validateSemanticPlan} from '../src/planner/validate.ts';
const fixtures=await loadB1Fixtures(),{rules}=await loadMappingRegistry();
const fixture=(name='restaurante')=>structuredClone(fixtures.find(f=>f.scenario===name)!);
const options=(f:ReturnType<typeof fixture>)=>({rules,activity_links:f.activity_links,activity_relationships:f.activity_relationships,category_context:f.category_context,objective_decisions:f.objective_decisions});
const run=(f=fixture())=>diagnoseBusiness(f.input,options(f));
function add(input:BusinessInput,id:string,kind:string,value:string|number|boolean,scope=input.business_id,publication:BusinessInput['facts'][number]['publication']='APPROVED') {
 input.facts.push({id,kind,value,scope_id:scope,publication,publication_decision_id:`synthetic-${id}`,source:'synthetic-b1-test',observed_at:'2026-10-01T00:00:00Z'});
}
function reseal<T extends {catalog_sha256:string}>(value:T){const {catalog_sha256:_,...body}=value;return {...body,catalog_sha256:inputSha256(body)};}
test('master catalogue covers all 47 registry capabilities; levels have reusable definitions and no live integration claims',()=>{
 const catalog=validateRequirementCatalog(requirementCatalog);assert.equal(catalog.cards.length,47);
 assert.deepEqual(new Set(catalog.cards.map(c=>c.id)),new Set(CapabilityId.options));
 const reservation=catalog.cards.find(c=>c.id==='reservation')!;
 assert.deepEqual(reservation.levels.map(l=>l.id),['contact','request','external_link','connected_confirmation']);
 assert.ok(reservation.levels.find(l=>l.id==='request')!.visitor_inputs.some(i=>i.id==='party_size'));
 assert.equal(reservation.levels.find(l=>l.id==='external_link')!.visitor_inputs.length,0);
 assert.ok(!reservation.levels.find(l=>l.id==='connected_confirmation')!.requirement_ids.includes('action_destination'));
 assert.ok(reservation.levels.find(l=>l.id==='connected_confirmation')!.requirement_ids.includes('integration_configuration'));
 assert.ok(catalog.cards.every(c=>c.levels.every(l=>l.backend==='NOT_CONNECTED'&&l.verification==='NOT_VERIFIED_OPERATIONALLY')));
});
test('catalogue rejects missing capability even with a new checksum, semantic drift, missing data definition and wrong group',()=>{
 const missing=structuredClone(requirementCatalog);missing.cards.pop();assert.throws(()=>validateRequirementCatalog(reseal(missing)),/CATALOG_CAPABILITY_COVERAGE/);
 const drift=structuredClone(requirementCatalog);drift.cards.find(c=>c.id==='menu')!.offering_kinds=['product'];assert.throws(()=>validateRequirementCatalog(reseal(drift)),/CATALOG_SEMANTIC_DRIFT/);
 const refs=structuredClone(requirementCatalog);refs.cards[0]!.levels[0]!.requirement_ids.push('nonexistent');assert.throws(()=>validateRequirementCatalog(reseal(refs)),/CATALOG_LEVEL_DEFINITION_INVALID/);
 const group=structuredClone(requirementCatalog);group.groups[0]!.capability_ids=[];assert.throws(()=>validateRequirementCatalog(reseal(group)),/CATALOG_GROUP_DRIFT/);
 const relaxed=structuredClone(requirementCatalog);relaxed.cards.find(c=>c.id==='reservation')!.levels.find(l=>l.id==='connected_confirmation')!.requirement_ids=['business_name'];
 assert.throws(()=>validateRequirementCatalog(reseal(relaxed)),/CATALOG_UNSUPPORTED_POLICY_REVISION/);
});
for(const f of fixtures)test(`B1/${f.scenario}: context ${f.expected_context_status}, H2 ${f.expected_planner_status}, all scopes retain complete inventory`,()=>{
 const before=structuredClone(f),result=run(f);assert.equal(result.context.status,f.expected_context_status);assert.equal(result.planner.status,f.expected_planner_status);assert.deepEqual(f,before);
 for(const scope of [f.input.business_id,...f.input.locations.map(l=>l.id)]) {
  const expected=requirementCatalog.cards.filter(c=>scope===f.input.business_id||c.scope_policy!=='BUSINESS_ONLY').map(c=>c.id);
  assert.deepEqual(new Set(result.diagnostic.entries.filter(e=>e.scope_id===scope).map(e=>e.capability_id)),new Set(expected));
 }
 assert.deepEqual(run(f),result);assert.deepEqual(verifyFunctionalDiagnostic(result.diagnostic,f.input,options(f)),result.diagnostic);
 if(result.planner.status==='READY') {
  const p=result.planner;assert.ok(SitePlanV1.safeParse(p.plan).success&&BusinessProfileV1.safeParse(p.profile).success&&CapabilityProfileV1.safeParse(p.capabilities).success);
  assert.ok(validateSemanticPlan({input:p.input,profile:p.profile,capabilities:p.capabilities,plan:p.plan},p.requirements).success);
 }
});
test('UNKNOWN category survives literally while approved description and menu resolve activity without confirming reservations/delivery',()=>{
 const f=fixture(),result=run(f);assert.equal(result.context.status,'RESOLVED');assert.equal(result.context.original_categories[0]!.value,'Unknown');
 assert.deepEqual(result.planner.capabilities!.capabilities.map(c=>({id:c.id,scope_id:c.scope_id,status:c.status,evidence_ids:c.evidence_ids})),
  [...f.input.business_capabilities].sort((a,b)=>a.scope_id.localeCompare(b.scope_id)||a.id.localeCompare(b.id)));
 assert.ok(result.context.signals.some(s=>s.kind==='DESCRIPTION'));assert.ok(result.context.signals.some(s=>s.kind==='OFFERING'));
 assert.equal(result.context.calibrated_confidence,null);
});
test('reservation reports all unmet future data despite first H2 missing destination; receiver is not a confirmed booking',()=>{
 const f=fixture(),result=run(f),entry=result.diagnostic.entries.find(e=>e.capability_id==='reservation'&&e.scope_id===f.input.locations[0]!.id)!;
 assert.deepEqual(entry.h2_missing_inputs,['approved_action_destination']);
 const level=entry.levels.find(l=>l.level_id==='connected_confirmation')!;
 for(const kind of ['booking_hours','timezone','booking_capacity','booking_availability','party_limits','booking_rules','confirmation_policy','cancellation_policy','customer_fields','personal_data_policy'])
  assert.ok(level.requirements.some(r=>r.requirement_id.includes(`:${kind}:`)&&r.status==='MISSING'),kind);
 assert.ok(level.requirements.some(r=>r.requirement_id==='backend_support'&&r.status==='SUPPORT_PENDING'));
 assert.ok(level.requirements.some(r=>r.owner==='PROVIDER_RIGHTS'&&r.status==='RIGHTS_REVIEW_PENDING'));
 const linked=run(fixture('reserva-enlace')).diagnostic.entries.find(e=>e.capability_id==='reservation'&&e.scope_id===f.input.locations[0]!.id)!;
 assert.equal(linked.levels.find(l=>l.level_id==='external_link')!.status,'EXTERNAL_INTENT_PLANNED');
 assert.equal(linked.levels.find(l=>l.level_id==='connected_confirmation')!.status,'PENDING');
});
test('absence/unknown is retained as factual state and never becomes justified non-applicability',()=>{
 const result=run(fixture('ferreteria'));
 for(const entry of result.diagnostic.entries.filter(e=>e.evidence_status==='UNKNOWN'||e.evidence_status==='CONFIRMED_ABSENT'))assert.notEqual(entry.relevance,'NOT_APPLICABLE_JUSTIFIED');
 assert.ok(result.diagnostic.entries.some(e=>e.evidence_status==='CONFIRMED_ABSENT'));
});
test('explicit rejected and justified non-applicable goals preserve requirements and remain exact-scope',()=>{
 const f=fixture('objetivo-explicito'),result=run(f),branch=f.input.locations[0]!.id;
 assert.equal(result.diagnostic.entries.find(e=>e.scope_id===branch&&e.capability_id==='delivery')!.relevance,'NOT_APPLICABLE_JUSTIFIED');
 assert.notEqual(result.diagnostic.entries.find(e=>e.scope_id===f.input.business_id&&e.capability_id==='delivery')!.relevance,'NOT_APPLICABLE_JUSTIFIED');
 assert.ok(result.diagnostic.entries.find(e=>e.scope_id===branch&&e.capability_id==='reservation')!.levels.every(l=>l.status==='REJECTED'&&l.requirements.length>0));
 const bad=fixture('objetivo-explicito');bad.input.facts.find(f=>f.id==='b1-not-applicable')!.publication='WITHHELD';assert.throws(()=>run(bad),/OBJECTIVE_UNVERIFIED_DECISION/);
 const hides=fixture();const ref='deny-menu',scope=hides.input.locations[0]!.id;add(hides.input,ref,'objective:rejected:menu',true,scope);
 hides.objective_decisions=[{id:'hide-required',scope_id:scope,capability_id:'menu',disposition:'REJECTED',evidence_ids:[ref],reason:'synthetic contradiction'}];
 assert.throws(()=>run(hides),/OBJECTIVE_DECISION_CONFLICTS_WITH_EMITTED_PLAN/);
});
test('a genuine multiscope classification does not create restaurant modules at the hotel branch',()=>{
 const f=fixture('sucursales'),result=run(f);assert.equal(result.context.status,'MULTISCOPE');assert.equal(result.planner.status,'READY');
 if(result.planner.status!=='READY')return;
 const branch2=f.input.locations[1]!.id;assert.ok(!result.planner.plan.pages.flatMap(p=>p.modules).some(m=>m.capability_id==='menu'&&m.scope_id===branch2));
 assert.equal(result.diagnostic.entries.find(e=>e.scope_id===branch2&&e.capability_id==='menu')!.emitted_in_plan,false);
});
test('hybrid needs approved coexistence at the same branch; no inheritance of its operational capabilities',()=>{
 const f=fixture('hibrido');f.activity_links=[];assert.equal(run(f).context.status,'AMBIGUOUS');
 const bad=fixture('hibrido');bad.activity_links[0]!.evidence_ids=['f-name'];assert.throws(()=>run(bad),/CONTEXT_UNVERIFIED_ACTIVITY_LINK/);
});
test('expired capability retains all requirements and typed offering fields; withholding/conflict is not erased',()=>{
 const f=fixture();f.input.facts.find(f=>f.kind==='capability:menu')!.expires_at='2026-10-10T00:00:00Z';
 const result=diagnoseBusiness(f.input,{...options(f),evaluation_time:'2026-10-12T00:00:00Z'}),entry=result.diagnostic.entries.find(e=>e.capability_id==='menu'&&e.scope_id===f.input.locations[0]!.id)!;
 assert.equal(result.planner.status,'CONTENT_BLOCKED');assert.ok(entry.levels[0]!.requirements.some(r=>r.status==='STALE'));assert.ok(entry.levels[1]!.requirements.length>entry.levels[0]!.requirements.length);
 const withheld=fixture();withheld.input.facts.find(f=>f.kind==='offering_name')!.publication='WITHHELD';const held=run(withheld);
 assert.ok(held.diagnostic.entries.find(e=>e.capability_id==='menu'&&e.scope_id===withheld.input.locations[0]!.id)!.levels[0]!.requirements.some(r=>r.status==='WITHHELD'));
});
test('uninspected DOCUMENTED media and fabricated backend verification never satisfy a rights/operational gate',()=>{
 const f=fixture('recurso-no-inspeccionado');add(f.input,'fake-verified','backend_verified',true,f.input.locations[0]!.id);
 const result=run(f);assert.equal(result.context.status,'UNKNOWN');assert.ok(result.context.ignored.some(i=>i.id==='b1-uninspected-media'));
 const gallery=result.diagnostic.entries.find(e=>e.capability_id==='gallery'&&e.scope_id===f.input.locations[0]!.id)!;
 assert.ok(gallery.levels[0]!.requirements.some(r=>r.requirement_id==='media_file'&&r.status==='MISSING'));
 assert.ok(gallery.levels[0]!.requirements.some(r=>r.requirement_id==='media_rights'&&r.status==='RIGHTS_REVIEW_PENDING'));
 assert.equal(result.diagnostic.operational_integrations,'NOT_CONNECTED');
});
test('price/currency binding is per affected offering; another item or branch cannot fill its missing currency',()=>{
 const f=fixture(),scope=f.input.locations[0]!.id,item=f.input.offerings[0]!;add(f.input,'price-one','price',20,scope);
 if(item.kind!=='menu_item')throw Error('test setup');item.price_fact_id='price-one';
 add(f.input,'currency-other','currency','COP',f.input.business_id);
 let r=run(f).diagnostic.entries.find(e=>e.capability_id==='menu'&&e.scope_id===scope)!;
 assert.equal(r.levels[0]!.requirements.find(c=>c.requirement_id.includes(':currency:'))!.status,'MISSING');
 item.fact_ids.push('currency-other');r=run(f).diagnostic.entries.find(e=>e.capability_id==='menu'&&e.scope_id===scope)!;
 assert.equal(r.levels[0]!.requirements.find(c=>c.requirement_id.includes(':currency:'))!.status,'SATISFIED');
});
test('name and nearby/negated subject prose cannot force business type, resources or operations',()=>{
 const f=fixture('insuficiente');add(f.input,'nearby','business_description','Estamos cerca de un restaurante y un gimnasio.');assert.equal(run(f).context.status,'UNKNOWN');
 const no=fixture('insuficiente');add(no.input,'negation','business_description','No somos un restaurante.');assert.equal(run(no).context.status,'UNKNOWN');
 const held=fixture('insuficiente');add(held.input,'held-description','business_description','Somos un restaurante.',held.input.business_id,'WITHHELD');assert.equal(run(held).context.status,'UNKNOWN');
});
test('policy handles explicit ES/EN subject descriptions of all non-regulatory archetypes without declaring their operations',()=>{
 for(const [archetype,phrases] of Object.entries(contextPolicy.descriptions)) {
  const f=fixture('insuficiente');add(f.input,'description','business_description',`Somos ${phrases[0]}.`);
  const result=classifyContextually(f.input,options(f));assert.equal(result.status,'RESOLVED',archetype);assert.deepEqual(result.profile.archetypes.map(a=>a.id),[archetype]);
  assert.equal(planBusiness(f.input,{rules,classification_mode:'CONTEXTUAL_V1'}).status,'CONTENT_BLOCKED');
 }
 const en=fixture('insuficiente');add(en.input,'english','business_description','We are a restaurant serving seasonal food.');assert.equal(run(en).context.status,'RESOLVED');
});
test('invalid context references, mismatched category literals and malformed typed class data reject or preserve clarification',()=>{
 const f=fixture('ferreteria');f.input.category_observations[0]!.value='restaurant';assert.equal(run(f).context.status,'CONFLICTED');
 const gym=fixture('gimnasio'),item=gym.input.offerings.find(o=>o.kind==='class_session')!;
 if(item.kind!=='class_session')throw Error('test setup');gym.input.facts.find(f=>f.id===item.timezone_fact_id)!.value='Invalid/Zone';
 assert.equal(run(gym).planner.status,'CONTENT_BLOCKED');
});
test('an explicit same-subject compound description can establish coexistence; an alternative stays ambiguous',()=>{
 const f=fixture('hibrido');f.activity_links=[];add(f.input,'compound','business_description','Somos un gimnasio y una tienda.',f.input.locations[0]!.id);
 const result=run(f);assert.equal(result.context.status,'HYBRID');assert.ok(result.context.signals.some(s=>s.fact_ids.includes('compound')));
 const alternatives=fixture('insuficiente');add(alternatives.input,'alternative','business_description','Somos un restaurante o un gimnasio.');assert.equal(run(alternatives).context.status,'AMBIGUOUS');
});
test('past/negative claims do not become positive from their noun, even when other current sources support it',()=>{
 const f=fixture();add(f.input,'no-longer','business_description','Ya no somos un restaurante.');assert.equal(run(f).context.status,'CONFLICTED');
});
test('a nearby shop in the same description is not a coexisting activity of the gym',()=>{
 const f=fixture('insuficiente');add(f.input,'nearby-shop','business_description','Somos un gimnasio con una tienda al lado.');
 assert.deepEqual(run(f).context.profile.archetypes.map(a=>a.id),['membership_and_classes']);
});
test('recomputed diagnostic rejects edited status, hidden requirement, scope substitution and false confidence/approval',()=>{
 const f=fixture(),result=run(f);
 for(const mutate of [(r:typeof result.diagnostic)=>{r.entries[0]!.levels[0]!.requirements.pop();},(r:typeof result.diagnostic)=>{r.entries[0]!.scope_id='another-branch';},
  (r:typeof result.diagnostic)=>{r.entries[0]!.levels[0]!.status='PENDING';}]) {
  const modified=structuredClone(result.diagnostic);mutate(modified);const {diagnostic_sha256:_,...body}=modified;modified.diagnostic_sha256=inputSha256(body);
  assert.throws(()=>verifyFunctionalDiagnostic(modified,f.input,options(f)),/FUNCTIONAL_DIAGNOSTIC_MISMATCH/);
 }
 assert.equal(requirementContracts.FunctionalDiagnosticV1.safeParse({...result.diagnostic,human_design_approval:'APPROVED'}).success,false);
 assert.equal(contextContracts.ContextualInterpretationV1.safeParse({...result.context,calibrated_confidence:1}).success,false);
});
test('default H2 planner byte-identical semantic artifacts and V1 consumers survive contextual opt-in',async()=>{
 for(const fixture of await loadPlannerFixtures()) {
  const old=JSON.parse(await readFile(`data/derived/planner-v1/${fixture.scenario}.json`,'utf8'));
  assert.deepEqual(planBusiness(fixture.input,{rules,activity_relationships:fixture.activity_relationships}),old,fixture.scenario);
 }
});
for(const [folder,schemas] of [['taxonomy/context-v1',contextContracts],['requirements/v1',requirementContracts]] as const)
 for(const [name,schema] of Object.entries(schemas))test(`new associated schema export ${folder}/${name} matches contract`,async()=>{
  const exported=JSON.parse(await readFile(`contracts/${folder}/${name}.schema.json`,'utf8'));
  const {title:_title,description:_description,$id:_id,...body}=exported;assert.deepEqual(body,z.toJSONSchema(schema,{target:'draft-2020-12'}));
 });
