import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {loadB1Fixtures} from './lib/b1-fixtures.ts';
import {loadMappingRegistry} from './load-taxonomy.ts';
import {requirementCatalog,validateRequirementCatalog} from '../src/requirements/catalog.ts';
import {diagnoseBusiness,verifyFunctionalDiagnostic} from '../src/requirements/diagnose.ts';
import {inputSha256} from '../src/upstream/v1/protocol.ts';
const verify=process.argv.includes('--verify'),folder='data/derived/requirements-v1',{rules}=await loadMappingRegistry();
validateRequirementCatalog(requirementCatalog);
if(!verify)await mkdir(folder,{recursive:true});
const artifacts:{path:string;sha256:string}[]=[];
async function persist(path:string,value:unknown) {
 const bytes=JSON.stringify(value,null,2)+'\n';
 if(verify){if(await readFile(path,'utf8')!==bytes)throw Error(`B1_REPLAY_MISMATCH:${path}`);}else await writeFile(path,bytes);
 artifacts.push({path,sha256:inputSha256(value)});
}
await persist(`${folder}/catalog.json`,requirementCatalog);
for(const fixture of await loadB1Fixtures()) {
 const options={rules,activity_links:fixture.activity_links,activity_relationships:fixture.activity_relationships,category_context:fixture.category_context,objective_decisions:fixture.objective_decisions};
 const result=diagnoseBusiness(fixture.input,options);
 if(result.context.status!==fixture.expected_context_status||result.planner.status!==fixture.expected_planner_status)throw Error(`B1_FIXTURE_UNEXPECTED:${fixture.scenario}:${result.context.status}/${result.planner.status}`);
 verifyFunctionalDiagnostic(result.diagnostic,fixture.input,options);
 await persist(`${folder}/${fixture.scenario}.json`,result);
 console.log(`${fixture.scenario}: context ${result.context.status}, H2 ${result.planner.status}, ${result.diagnostic.entries.length} scope/capability entries`);
}
console.log(JSON.stringify({status:verify?'B1_REPLAY_VERIFIED':'B1_FIXTURES_EXPORTED',catalog:requirementCatalog.catalog_sha256,artifacts},null,2));
