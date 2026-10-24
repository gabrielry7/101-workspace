// H9 read-only evidence inventory. No provider acquisition, benchmark simulation or approval creation.
import { readFile,writeFile,mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { verifyPackageFiles } from '../src/media/package.ts';
const folder='docs/evidence/h9',output=`${folder}/inventory.json`;
const paths=new Set<string>();
const json=async(path:string)=>{paths.add(path);return JSON.parse(await readFile(path,'utf8'));};
const acquisition=await json('fixtures/media/pilot/acquisition.json');
const media=await json('data/derived/media-v1/real-restaurante-pilot.json');
const packageProof=await json('fixtures/media/pilot/package-proof.json');
const packageCheck=await verifyPackageFiles(packageProof,media.manifest);assert.ok(packageCheck.success,packageCheck.codes.join(','));
for(const f of [...packageProof.files,...packageProof.documents])paths.add(f.path);
for(const key of ['html_path','screenshot_path','receipt_path'])paths.add(packageProof.render[key]);
paths.add(acquisition.review_path);paths.add('scripts/inventory-h9.ts');
const grant=media.manifest.grants.find((g:any)=>g.original_asset_id===acquisition.file.asset_id);assert.ok(grant);
assert.equal(grant.multiple_clients,'UNKNOWN');assert.equal(grant.reuse,'UNKNOWN');assert.deepEqual(grant.automation,{search:'UNKNOWN',download:'UNKNOWN'});
const h5=await json('fixtures/design/h5/provenance.json');
const h5Browser=await json('docs/evidence/h5/browser-audit.json');
const h6=await json('docs/evidence/h6/run.json');
const h7=await json('docs/evidence/h7/run.json');
const h8=await json('docs/evidence/h8/run.json');
const reservation=await json('fixtures/cohort/h7/reservation.json');
const cohort=await json('data/derived/cohort-v1/h7.json');
assert.equal(reservation.data_mode,'SYNTHETIC_FIXTURE');assert.equal(reservation.external_evidence,false);
const proposalMetering=[];
for(const scenario of ['hotel','dentista','servicio','hibrido','media-unknown']){
 const p=await json(`fixtures/cohort/h7/proposals/${scenario}/provenance.json`);assert.equal(p.cost,null);assert.equal(p.tokens,null);assert.equal(p.human_preference,'NOT_COLLECTED');
 proposalMetering.push({scenario,source:p.source,tokens:p.tokens,cost:p.cost,measured:p.measured,new_spend:p.new_spend,provider_api_calls:p.provider_api_calls});
}
assert.equal(h5.cost,null);assert.equal(h5.tokens,null);assert.equal(h5.human_preference,'NOT_COLLECTED');
for(const run of [h6,h7,h8]){assert.equal(run.human_preference,'NOT_COLLECTED');assert.equal(run.production_ready,false);}
const locks=[];
for(const id of ['pilot-flow','pilot-rail','hybrid-no-media']){
 const l=await json(`fixtures/locks/h8/${id}.json`);assert.equal(l.semantic.input.data_mode,'SYNTHETIC_FIXTURE');assert.equal(l.approval.human_preference,'NOT_COLLECTED');assert.equal(l.approval.production_ready,false);
 locks.push({id,lock_sha256:l.lock_sha256,business_id:l.semantic.input.business_id,data_mode:l.semantic.input.data_mode,approval:l.approval,eligible_for_approved_real_site_economics:false});
}
const fixtureCases=cohort.cases.map((c:any)=>{assert.equal(c.result.input.data_mode,'SYNTHETIC_FIXTURE');return {scenario:c.scenario,business_id:c.result.input.business_id,data_mode:c.result.input.data_mode,selected_plans:c.search?.finalists?.length??0,real_provider_coverage_status:'NOT_TESTED',eligible_for_approved_real_site_economics:false};});
const fingerprints=await Promise.all([...paths].sort().map(async path=>{const raw=await readFile(path),normalization=/\.(?:json|ts)$/.test(path)?'LF_TEXT':'BINARY',b=normalization==='LF_TEXT'?Buffer.from(raw.toString('utf8').replace(/\r\n/g,'\n')):raw;return {path,normalization,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};}));
const inventory={inventory_version:'h9-evidence-inventory-1',milestone:'H9',status:'BLOCKED_EXTERNAL_EVIDENCE',
 scope:'Known workspace H3 package, H5-H8 laboratory receipts/locks and H7 cohort/proposal records listed in source_files; not a claim about evidence outside this workspace.',
 source_cutoff:h8.created_at,source_files:fingerprints,
 provider_evidence:{provider:acquisition.provider,acquired_assets:1,acquisition_date:acquisition.obtained_date,acquisition_method:acquisition.acquisition_method,cost_statement:acquisition.cost,numeric_amount:null,currency:null,
  evidence_kind:'REAL_ASSET_FOR_SYNTHETIC_PILOT_ONLY',package_verification:packageCheck,internal_grant_at_h3_cutoff:{id:grant.id,client_ids:grant.client_ids,project_ids:grant.project_ids,scope_ids:grant.scope_ids,purposes:grant.purposes,pages:grant.pages,commercial_web:grant.commercial_web,multiple_clients:grant.multiple_clients,reuse:grant.reuse,automation:grant.automation,ai:grant.ai,derivatives:grant.derivatives,redistribution:grant.redistribution,sublicensing:grant.sublicensing,retention_until:grant.retention_until,cost:grant.cost},
  general_provider_legal_approval:'NOT_ESTABLISHED',new_terms_research:'NOT_PERFORMED',catalog_benchmark:'NOT_TESTED',catalog_sample_size:0,api_agreement:'MISSING',volume_automation:'NOT_AUTHORIZED',
  caching:{observed:'LOCAL_FROZEN_PILOT_BYTES_REPLAY',general_api_or_multiclient_cache_permission:'NOT_VERIFIED',retention_interpretation:'NULL_IS_NOT_UNLIMITED_PERMISSION',storage_cost:'NOT_MEASURED'}},
 cohort:fixtureCases,technical_locks:locks,
 observed_laboratory_metrics:{
  h5:{browser_receipts:h5Browser.receipts.length,stress_receipts:h5Browser.stress.length,session_tokens:h5.tokens,session_cost:h5.cost,metering_status:h5.metering_status,new_provider_calls:h5.new_provider_calls,new_spend:h5.new_spend},
  h6:{declared_budget:h6.budget,monetary_cost:'NOT_MEASURED',human_time:'NOT_MEASURED',human_preference:h6.human_preference},
  h7:{actual:h7.actual,proposal_metering:proposalMetering},h8:{actual:h8.actual},
  interpretation:'Actual browser/build wall and zero NEW calls/spend are laboratory observations, not total site cost, human duration, commercial latency or approved-site samples.'},
 economics:{status:'NOT_TESTED',eligible_approved_real_sites:0,sample_size:0,currency:null,p50:null,p90:null,quantile_method:'NOT_APPLIED_EMPTY_ELIGIBLE_COHORT',legal_documentation_cost:'NOT_MEASURED',human_time:'NOT_MEASURED',human_cost:'NOT_MEASURED',provider_total_cost:'NOT_MEASURED',llm_total_cost:'NOT_MEASURED',storage_total_cost:'NOT_MEASURED',total_site_cost:'NOT_MEASURED'},
 dependencies:[
  {id:'REAL_APPROVED_SITE_COHORT',missing:'Real authorized business inputs and actual human site acceptance records; all inspected current inputs are synthetic and human preferences NOT_COLLECTED.'},
  {id:'ITEMIZED_ACTUAL_COSTS',missing:'Dated provider/license/API/LLM usage and invoices, legal/documentary expenses, storage and human duration/rates/currency linked to each site and all rejected attempts; session totals unavailable.'},
  {id:'AUTHORIZED_PROVIDER_BENCHMARK',missing:'Verified access/download/AI/cache/multiclient permissions or agreements and comparable authorized samples by vertical; one internal pilot asset is not catalog coverage or volume evidence.'}],
 new_actions:{provider_calls:0,downloads:0,new_spend:0,production_deployments:0,human_votes_created:0},production_ready:false,h9_complete:false};
if(process.argv.includes('--verify')){assert.deepEqual(JSON.parse(await readFile(output,'utf8')),inventory);console.log('H9 inventory VERIFIED; H9 BLOCKED/NOT_TESTED, zero eligible approved real sites, p50/p90 null. No acquisition or provider calls.');}
else{await mkdir(folder,{recursive:true});await writeFile(output,JSON.stringify(inventory,null,2)+'\n');console.log('H9 inventory recorded; H9 BLOCKED/NOT_TESTED. Evidence integrity verified; no economic benchmark or approval fabricated.');}
