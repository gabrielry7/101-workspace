import {z} from 'zod';
import {mkdir,writeFile} from 'node:fs/promises';
import {evaluatorContracts} from '../src/design/evaluators/contracts.ts';
await mkdir('contracts/design/evaluation-v1',{recursive:true});
for(const [name,schema] of Object.entries(evaluatorContracts))await writeFile(`contracts/design/evaluation-v1/${name}.schema.json`,JSON.stringify({...z.toJSONSchema(schema,{target:'draft-2020-12'}),$id:`urn:unocerouno:contracts:${name}:1.0.0`,title:name},null,2)+'\n');
console.log('Design evaluation contracts exported; historical V1 contracts unchanged.');
