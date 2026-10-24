import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { loadDesignLab } from './load-design-lab.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';
const { result } = await loadDesignLab();
const file = 'data/derived/design-v1/restaurante-search.json';
const text = JSON.stringify(result,null,2)+'\n';
if (process.argv.includes('--replay')) {
  if (await readFile(file,'utf8') !== text) throw new Error('DESIGN_REPLAY_MISMATCH');
} else { await mkdir('data/derived/design-v1',{recursive:true}); await writeFile(file,text); }
console.log(JSON.stringify({status:result.status,candidates:result.candidates.length,finalists:result.finalists.map(p=>p.id),sha256:inputSha256(result),replay:process.argv.includes('--replay')}));
