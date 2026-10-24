import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { loadCohortLab } from './load-cohort-lab.ts';
const result=await loadCohortLab(true);const text=JSON.stringify(result,null,2)+'\n';const path='data/derived/cohort-v1/h7.json';
if(process.argv.includes('--replay')){if(await readFile(path,'utf8')!==text)throw Error('H7_COHORT_REPLAY_DRIFT');console.log('H7 exact replay PASS');}
else{await mkdir('data/derived/cohort-v1',{recursive:true});await writeFile(path,text);console.log(result.cases.map(c=>({scenario:c.scenario,status:c.result.status,finalists:c.search?.finalists.length,pages:c.lab?.content.pages.length,media:c.media?.manifest.decisions})));}
