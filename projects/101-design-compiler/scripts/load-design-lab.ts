import { readFile } from 'node:fs/promises';
import { loadCompositionLab } from './load-composition-lab.ts';
import { searchDesigns } from '../src/design/search.ts';
import { inputSha256 } from '../src/upstream/v1/protocol.ts';

export const H5_BUDGET = { proposals:3, samples:24, renders:4, finalists:4, max_output_bytes:24000, new_provider_calls:0, new_spend:0 } as const;
export const H5_SEED = 1010508;
export async function loadDesignLab() {
  const lab = await loadCompositionLab();
  const proposals = JSON.parse(await readFile('fixtures/design/h5/llm-output.json','utf8'));
  const provenance = JSON.parse(await readFile('fixtures/design/h5/provenance.json','utf8'));
  const context = JSON.parse(await readFile('fixtures/design/h5/context.json','utf8'));
  const prompt = await readFile('fixtures/design/h5/prompt.txt','utf8');
  if (provenance.output_sha256 !== inputSha256(proposals) || provenance.context_sha256 !== inputSha256(context)
    || provenance.prompt_sha256 !== inputSha256(prompt)) throw new Error('LLM_PROVENANCE_MISMATCH');
  const result = searchDesigns(proposals,lab,H5_BUDGET,H5_SEED);
  if (result.context_sha256 !== provenance.context_sha256 || result.status !== 'FINALISTS_READY_FOR_BROWSER'
    || result.finalists.length !== H5_BUDGET.finalists) throw new Error('H5_SEARCH_BLOCKED');
  return { lab, result, provenance };
}
